"""
Orthanc Management Module - Database Migration System
Handles database versioning, schema updates, and data migrations across multiple database types
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, DateTime, Integer
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError
from contextlib import contextmanager

from .config import DatabaseSettings, DatabaseType
from .manager import DatabaseManager

logger = logging.getLogger(__name__)


class Migration:
    """Represents a single database migration"""
    
    def __init__(self, version: str, name: str, up_sql: str, down_sql: str = "", 
                 description: str = "", dependencies: List[str] = None):
        self.version = version
        self.name = name
        self.up_sql = up_sql
        self.down_sql = down_sql
        self.description = description
        self.dependencies = dependencies or []
        self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert migration to dictionary"""
        return {
            'version': self.version,
            'name': self.name,
            'up_sql': self.up_sql,
            'down_sql': self.down_sql,
            'description': self.description,
            'dependencies': self.dependencies,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Migration':
        """Create migration from dictionary"""
        migration = cls(
            version=data['version'],
            name=data['name'],
            up_sql=data['up_sql'],
            down_sql=data.get('down_sql', ''),
            description=data.get('description', ''),
            dependencies=data.get('dependencies', [])
        )
        if 'created_at' in data:
            migration.created_at = datetime.fromisoformat(data['created_at'])
        return migration


class MigrationManager:
    """Manages database migrations across multiple database backends"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
        self.migrations: List[Migration] = []
        self._ensure_migrations_dir()
        self._load_migrations()
    
    def _ensure_migrations_dir(self):
        """Ensure migrations directory exists"""
        os.makedirs(self.migrations_dir, exist_ok=True)
    
    def _load_migrations(self):
        """Load all migration files"""
        self.migrations.clear()
        
        # Load from JSON files in migrations directory
        if os.path.exists(self.migrations_dir):
            for filename in sorted(os.listdir(self.migrations_dir)):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.migrations_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            migration_data = json.load(f)
                            migration = Migration.from_dict(migration_data)
                            self.migrations.append(migration)
                    except Exception as e:
                        logger.error(f"Failed to load migration {filename}: {e}")
        
        # Sort by version
        self.migrations.sort(key=lambda m: m.version)
        logger.info(f"Loaded {len(self.migrations)} migrations")
    
    def create_migration_table(self) -> bool:
        """Create the schema_migrations table if it doesn't exist"""
        try:
            # SQL for creating migrations table - database agnostic
            create_table_sql = self._get_create_migrations_table_sql()
            
            with self.db_manager.get_session() as session:
                session.execute(text(create_table_sql))
                logger.info("Created schema_migrations table")
                return True
                
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.debug("schema_migrations table already exists")
                return True
            logger.error(f"Failed to create schema_migrations table: {e}")
            return False
    
    def _get_create_migrations_table_sql(self) -> str:
        """Get database-specific SQL for creating migrations table"""
        db_type = self.db_manager.db_settings.database_type
        
        base_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(50) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            execution_time_ms INTEGER DEFAULT 0,
            checksum VARCHAR(64),
            success BOOLEAN DEFAULT TRUE
        )
        """
        
        if db_type == DatabaseType.MYSQL:
            return base_sql.replace("IF NOT EXISTS", "")
        elif db_type == DatabaseType.FIREBIRD:
            return base_sql.replace("IF NOT EXISTS", "").replace("BOOLEAN", "SMALLINT")
        elif db_type == DatabaseType.MSSQL:
            return base_sql.replace("IF NOT EXISTS", "").replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "DATETIME2 DEFAULT GETDATE()").replace("BOOLEAN", "BIT")
        elif db_type == DatabaseType.ORACLE:
            return base_sql.replace("IF NOT EXISTS", "").replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP").replace("BOOLEAN", "NUMBER(1)")
        else:
            return base_sql
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions"""
        try:
            with self.db_manager.get_session() as session:
                result = session.execute(text("SELECT version FROM schema_migrations WHERE success = 1 ORDER BY version"))
                return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get applied migrations: {e}")
            return []
    
    def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations"""
        applied = set(self.get_applied_migrations())
        return [m for m in self.migrations if m.version not in applied]
    
    def apply_migration(self, migration: Migration) -> bool:
        """Apply a single migration"""
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Applying migration {migration.version}: {migration.name}")
            
            with self.db_manager.get_session() as session:
                # Execute migration SQL
                adapted_sql = self._adapt_migration_sql(migration.up_sql)
                
                if adapted_sql.strip():
                    # Split SQL into individual statements
                    statements = self._split_sql_statements(adapted_sql)
                    
                    for statement in statements:
                        if statement.strip():
                            session.execute(text(statement))
                
                # Record migration as applied
                execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                checksum = self._calculate_checksum(migration.up_sql)
                
                session.execute(text("""
                    INSERT INTO schema_migrations (version, name, applied_at, execution_time_ms, checksum, success)
                    VALUES (:version, :name, :applied_at, :execution_time, :checksum, :success)
                """), {
                    'version': migration.version,
                    'name': migration.name,
                    'applied_at': start_time,
                    'execution_time': execution_time,
                    'checksum': checksum,
                    'success': True
                })
                
                logger.info(f"Successfully applied migration {migration.version} in {execution_time}ms")
                return True
                
        except Exception as e:
            logger.error(f"Failed to apply migration {migration.version}: {e}")
            
            # Record failed migration
            try:
                with self.db_manager.get_session() as session:
                    execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    session.execute(text("""
                        INSERT INTO schema_migrations (version, name, applied_at, execution_time_ms, success)
                        VALUES (:version, :name, :applied_at, :execution_time, :success)
                    """), {
                        'version': migration.version,
                        'name': migration.name,
                        'applied_at': start_time,
                        'execution_time': execution_time,
                        'success': False
                    })
            except Exception:
                pass  # Don't fail if we can't record the failure
            
            return False
    
    def rollback_migration(self, migration: Migration) -> bool:
        """Rollback a single migration"""
        if not migration.down_sql:
            logger.error(f"No rollback SQL available for migration {migration.version}")
            return False
        
        try:
            logger.info(f"Rolling back migration {migration.version}: {migration.name}")
            
            with self.db_manager.get_session() as session:
                # Execute rollback SQL
                adapted_sql = self._adapt_migration_sql(migration.down_sql)
                
                if adapted_sql.strip():
                    statements = self._split_sql_statements(adapted_sql)
                    
                    for statement in statements:
                        if statement.strip():
                            session.execute(text(statement))
                
                # Remove migration record
                session.execute(text("DELETE FROM schema_migrations WHERE version = :version"), 
                              {'version': migration.version})
                
                logger.info(f"Successfully rolled back migration {migration.version}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to rollback migration {migration.version}: {e}")
            return False
    
    def _adapt_migration_sql(self, sql: str) -> str:
        """Adapt SQL for current database type"""
        db_type = self.db_manager.db_settings.database_type
        
        # Basic adaptations
        if db_type == DatabaseType.MYSQL:
            sql = sql.replace("IF NOT EXISTS", "")
            sql = sql.replace("BOOLEAN", "BOOLEAN")
        elif db_type == DatabaseType.FIREBIRD:
            sql = sql.replace("IF NOT EXISTS", "")
            sql = sql.replace("BOOLEAN", "SMALLINT")
            sql = sql.replace("CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP")
        elif db_type == DatabaseType.MSSQL:
            sql = sql.replace("IF NOT EXISTS", "")
            sql = sql.replace("BOOLEAN", "BIT")
            sql = sql.replace("CURRENT_TIMESTAMP", "GETDATE()")
        elif db_type == DatabaseType.ORACLE:
            sql = sql.replace("IF NOT EXISTS", "")
            sql = sql.replace("BOOLEAN", "NUMBER(1)")
        
        return sql
    
    def _split_sql_statements(self, sql: str) -> List[str]:
        """Split SQL into individual statements"""
        # Simple split by semicolon - could be improved for complex cases
        statements = []
        current_statement = ""
        
        for line in sql.split('\n'):
            line = line.strip()
            if not line or line.startswith('--'):
                continue
            
            current_statement += line + '\n'
            
            if line.endswith(';'):
                statements.append(current_statement.strip())
                current_statement = ""
        
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return statements
    
    def _calculate_checksum(self, content: str) -> str:
        """Calculate checksum for migration content"""
        import hashlib
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def migrate(self, target_version: Optional[str] = None) -> bool:
        """Apply all pending migrations up to target version"""
        # Ensure migration table exists
        if not self.create_migration_table():
            return False
        
        pending = self.get_pending_migrations()
        
        if target_version:
            # Filter to only migrations up to target version
            pending = [m for m in pending if m.version <= target_version]
        
        if not pending:
            logger.info("No pending migrations to apply")
            return True
        
        logger.info(f"Applying {len(pending)} pending migrations")
        
        success_count = 0
        for migration in pending:
            if self.apply_migration(migration):
                success_count += 1
            else:
                logger.error(f"Migration failed at {migration.version}, stopping")
                break
        
        logger.info(f"Applied {success_count}/{len(pending)} migrations successfully")
        return success_count == len(pending)
    
    def rollback(self, target_version: str) -> bool:
        """Rollback migrations to target version"""
        applied = self.get_applied_migrations()
        
        # Find migrations to rollback (in reverse order)
        to_rollback = []
        for version in reversed(applied):
            if version <= target_version:
                break
            # Find migration object
            migration = next((m for m in self.migrations if m.version == version), None)
            if migration:
                to_rollback.append(migration)
        
        if not to_rollback:
            logger.info(f"Already at or below target version {target_version}")
            return True
        
        logger.info(f"Rolling back {len(to_rollback)} migrations to version {target_version}")
        
        success_count = 0
        for migration in to_rollback:
            if self.rollback_migration(migration):
                success_count += 1
            else:
                logger.error(f"Rollback failed at {migration.version}, stopping")
                break
        
        logger.info(f"Rolled back {success_count}/{len(to_rollback)} migrations successfully")
        return success_count == len(to_rollback)
    
    def create_migration(self, name: str, up_sql: str, down_sql: str = "", 
                        description: str = "", dependencies: List[str] = None) -> Migration:
        """Create a new migration"""
        # Generate version number
        version = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        
        # Ensure unique version
        existing_versions = [m.version for m in self.migrations]
        counter = 1
        original_version = version
        while version in existing_versions:
            version = f"{original_version}_{counter:02d}"
            counter += 1
        
        migration = Migration(
            version=version,
            name=name,
            up_sql=up_sql,
            down_sql=down_sql,
            description=description,
            dependencies=dependencies
        )
        
        # Save to file
        filename = f"{version}_{name.lower().replace(' ', '_')}.json"
        filepath = os.path.join(self.migrations_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(migration.to_dict(), f, indent=2, default=str)
        
        # Reload migrations
        self._load_migrations()
        
        logger.info(f"Created migration {version}: {name}")
        return migration
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status"""
        try:
            applied = self.get_applied_migrations()
            pending = self.get_pending_migrations()
            
            return {
                'total_migrations': len(self.migrations),
                'applied_count': len(applied),
                'pending_count': len(pending),
                'applied_versions': applied,
                'pending_versions': [m.version for m in pending],
                'last_applied': applied[-1] if applied else None,
                'database_type': self.db_manager.db_settings.database_type.value
            }
        except Exception as e:
            return {'error': str(e)}


# Utility function to create initial migrations
def create_initial_migrations(migration_manager: MigrationManager):
    """Create initial database schema migrations"""
    
    # Migration 1: Create referring_doctors table
    migration_manager.create_migration(
        name="Create referring doctors table",
        description="Create table for HPCSA registered referring doctors",
        up_sql="""
        CREATE TABLE referring_doctors (
            id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            hpcsa_number VARCHAR(20) UNIQUE NOT NULL,
            email VARCHAR(100),
            phone VARCHAR(20),
            practice_name VARCHAR(100),
            specialization VARCHAR(50),
            facility_type VARCHAR(50),
            province VARCHAR(50),
            access_level VARCHAR(20) NOT NULL DEFAULT 'view_only',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_access TIMESTAMP
        );
        
        CREATE INDEX idx_referring_doctors_hpcsa ON referring_doctors(hpcsa_number);
        CREATE INDEX idx_referring_doctors_email ON referring_doctors(email);
        CREATE INDEX idx_referring_doctors_active ON referring_doctors(is_active);
        """,
        down_sql="DROP TABLE referring_doctors;"
    )
    
    # Migration 2: Create patient_referrals table
    migration_manager.create_migration(
        name="Create patient referrals table",
        description="Create table for tracking patient referrals and workflow",
        up_sql="""
        CREATE TABLE patient_referrals (
            id VARCHAR(50) PRIMARY KEY,
            patient_id VARCHAR(50) NOT NULL,
            referring_doctor_id VARCHAR(50) NOT NULL,
            study_instance_uid VARCHAR(100),
            referral_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            study_type VARCHAR(100),
            clinical_indication TEXT,
            priority VARCHAR(20) NOT NULL DEFAULT 'routine',
            access_granted BOOLEAN NOT NULL DEFAULT FALSE,
            access_expires TIMESTAMP,
            notification_sent BOOLEAN NOT NULL DEFAULT FALSE,
            patient_contacted BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (referring_doctor_id) REFERENCES referring_doctors(id)
        );
        
        CREATE INDEX idx_patient_referrals_patient ON patient_referrals(patient_id);
        CREATE INDEX idx_patient_referrals_doctor ON patient_referrals(referring_doctor_id);
        CREATE INDEX idx_patient_referrals_study ON patient_referrals(study_instance_uid);
        CREATE INDEX idx_patient_referrals_date ON patient_referrals(referral_date);
        """,
        down_sql="DROP TABLE patient_referrals;",
        dependencies=["referring_doctors"]
    )
    
    # Migration 3: Create patient_authorizations table
    migration_manager.create_migration(
        name="Create patient authorizations table",
        description="Create table for manual patient access authorization",
        up_sql="""
        CREATE TABLE patient_authorizations (
            id VARCHAR(50) PRIMARY KEY,
            doctor_id VARCHAR(50) NOT NULL,
            patient_id VARCHAR(50) NOT NULL,
            study_instance_uid VARCHAR(100),
            access_level VARCHAR(20) NOT NULL DEFAULT 'view_only',
            granted_by VARCHAR(50) NOT NULL,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            access_count INTEGER NOT NULL DEFAULT 0,
            last_accessed TIMESTAMP,
            FOREIGN KEY (doctor_id) REFERENCES referring_doctors(id)
        );
        
        CREATE INDEX idx_patient_auth_doctor ON patient_authorizations(doctor_id);
        CREATE INDEX idx_patient_auth_patient ON patient_authorizations(patient_id);
        CREATE INDEX idx_patient_auth_study ON patient_authorizations(study_instance_uid);
        CREATE INDEX idx_patient_auth_expires ON patient_authorizations(expires_at);
        CREATE INDEX idx_patient_auth_active ON patient_authorizations(is_active);
        """,
        down_sql="DROP TABLE patient_authorizations;",
        dependencies=["referring_doctors"]
    )
    
    # Migration 4: Create patient_shares table
    migration_manager.create_migration(
        name="Create patient shares table",
        description="Create table for secure patient link sharing",
        up_sql="""
        CREATE TABLE patient_shares (
            id VARCHAR(50) PRIMARY KEY,
            patient_id VARCHAR(50) NOT NULL,
            patient_name VARCHAR(100),
            patient_email VARCHAR(100),
            patient_phone VARCHAR(20),
            study_uids TEXT NOT NULL,
            share_token VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255),
            created_by VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            max_downloads INTEGER NOT NULL DEFAULT 10,
            download_count INTEGER NOT NULL DEFAULT 0,
            access_count INTEGER NOT NULL DEFAULT 0,
            last_accessed TIMESTAMP,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            mobile_optimized BOOLEAN NOT NULL DEFAULT TRUE
        );
        
        CREATE INDEX idx_patient_shares_token ON patient_shares(share_token);
        CREATE INDEX idx_patient_shares_patient ON patient_shares(patient_id);
        CREATE INDEX idx_patient_shares_expires ON patient_shares(expires_at);
        CREATE INDEX idx_patient_shares_active ON patient_shares(is_active);
        """,
        down_sql="DROP TABLE patient_shares;"
    )
    
    # Migration 5: Create orthanc_configs table
    migration_manager.create_migration(
        name="Create orthanc configs table",
        description="Create table for dynamic Orthanc configuration management",
        up_sql="""
        CREATE TABLE orthanc_configs (
            id VARCHAR(50) PRIMARY KEY,
            config_name VARCHAR(100) UNIQUE NOT NULL,
            config_data TEXT NOT NULL,
            description TEXT,
            is_active BOOLEAN NOT NULL DEFAULT FALSE,
            is_default BOOLEAN NOT NULL DEFAULT FALSE,
            created_by VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            applied_at TIMESTAMP
        );
        
        CREATE INDEX idx_orthanc_configs_name ON orthanc_configs(config_name);
        CREATE INDEX idx_orthanc_configs_active ON orthanc_configs(is_active);
        """,
        down_sql="DROP TABLE orthanc_configs;"
    )
    
    # Migration 6: Create audit_logs table
    migration_manager.create_migration(
        name="Create audit logs table",
        description="Create table for comprehensive audit logging",
        up_sql="""
        CREATE TABLE audit_logs (
            id VARCHAR(50) PRIMARY KEY,
            user_id VARCHAR(50),
            user_type VARCHAR(20) NOT NULL,
            user_name VARCHAR(100),
            action VARCHAR(50) NOT NULL,
            resource_type VARCHAR(50) NOT NULL,
            resource_id VARCHAR(50),
            details TEXT,
            ip_address VARCHAR(45),
            user_agent TEXT,
            session_id VARCHAR(100),
            success BOOLEAN NOT NULL DEFAULT TRUE,
            error_message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
        CREATE INDEX idx_audit_logs_action ON audit_logs(action);
        CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
        CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
        """,
        down_sql="DROP TABLE audit_logs;"
    )
    
    logger.info("Created initial database migrations")
