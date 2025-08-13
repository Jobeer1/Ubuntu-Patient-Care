"""
Migration System for Orthanc Management Module
Handles database schema versioning, migrations, and rollbacks
"""

import asyncio
import logging
import json
import hashlib
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod

from connection_manager import DatabaseManager, DatabaseConnection
from schema_generator import DatabaseType, DatabaseSchemaGenerator


@dataclass
class Migration:
    """Represents a single database migration"""
    version: str
    name: str
    description: str
    up_sql: List[str]
    down_sql: List[str]
    dependencies: List[str] = None
    checksum: Optional[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.checksum is None:
            self.checksum = self.calculate_checksum()
    
    def calculate_checksum(self) -> str:
        """Calculate migration checksum for integrity verification"""
        content = f"{self.version}{self.name}{';'.join(self.up_sql)}{';'.join(self.down_sql)}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Migration':
        return cls(**data)


class MigrationRunner:
    """Handles migration execution and rollback"""
    
    def __init__(self, connection: DatabaseConnection):
        self.connection = connection
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def ensure_migration_table(self) -> None:
        """Ensure migration tracking table exists"""
        
        # Database-specific migration table SQL
        migration_table_sql = {
            DatabaseType.MYSQL: """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    checksum VARCHAR(64) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    applied_by VARCHAR(100),
                    execution_time_ms INT,
                    rollback_sql LONGTEXT
                )
            """,
            DatabaseType.POSTGRESQL: """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    checksum VARCHAR(64) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    applied_by VARCHAR(100),
                    execution_time_ms INTEGER,
                    rollback_sql TEXT
                )
            """,
            DatabaseType.SQLITE: """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    checksum TEXT NOT NULL,
                    applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    applied_by TEXT,
                    execution_time_ms INTEGER,
                    rollback_sql TEXT
                )
            """,
            DatabaseType.FIREBIRD: """
                CREATE TABLE schema_migrations (
                    version VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    description BLOB SUB_TYPE TEXT,
                    checksum VARCHAR(64) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    applied_by VARCHAR(100),
                    execution_time_ms INTEGER,
                    rollback_sql BLOB SUB_TYPE TEXT
                )
            """
        }
        
        sql = migration_table_sql.get(self.connection.config.db_type)
        if sql:
            await self.connection.execute(sql)
        else:
            raise ValueError(f"Unsupported database type: {self.connection.config.db_type}")
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions"""
        await self.ensure_migration_table()
        
        rows = await self.connection.fetch_all(
            "SELECT version FROM schema_migrations ORDER BY applied_at"
        )
        return [row['version'] for row in rows]
    
    async def is_migration_applied(self, version: str) -> bool:
        """Check if a migration version is already applied"""
        await self.ensure_migration_table()
        
        result = await self.connection.fetch_one(
            "SELECT 1 FROM schema_migrations WHERE version = ?",
            (version,)
        )
        return result is not None
    
    async def apply_migration(self, migration: Migration, applied_by: str = "system") -> None:
        """Apply a single migration"""
        if await self.is_migration_applied(migration.version):
            self.logger.info(f"Migration {migration.version} already applied, skipping")
            return
        
        self.logger.info(f"Applying migration {migration.version}: {migration.name}")
        start_time = datetime.now()
        
        try:
            # Begin transaction
            await self.connection.begin_transaction()
            
            # Execute migration SQL
            for sql_statement in migration.up_sql:
                if sql_statement.strip():
                    await self.connection.execute(sql_statement)
            
            # Record migration
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            placeholder = self.connection.get_placeholder()
            if placeholder == "$":
                # PostgreSQL uses $1, $2, etc.
                params_sql = "($1, $2, $3, $4, $5, $6, $7, $8)"
            else:
                params_sql = f"({', '.join([placeholder] * 8)})"
            
            await self.connection.execute(
                f"""
                INSERT INTO schema_migrations 
                (version, name, description, checksum, applied_by, execution_time_ms, rollback_sql)
                VALUES {params_sql}
                """,
                (
                    migration.version,
                    migration.name,
                    migration.description,
                    migration.checksum,
                    applied_by,
                    execution_time,
                    ';'.join(migration.down_sql)
                )
            )
            
            await self.connection.commit()
            self.logger.info(f"Migration {migration.version} applied successfully in {execution_time}ms")
            
        except Exception as e:
            await self.connection.rollback()
            self.logger.error(f"Failed to apply migration {migration.version}: {e}")
            raise
    
    async def rollback_migration(self, version: str, rolled_back_by: str = "system") -> None:
        """Rollback a single migration"""
        if not await self.is_migration_applied(version):
            self.logger.warning(f"Migration {version} not applied, cannot rollback")
            return
        
        # Get rollback SQL from migration record
        result = await self.connection.fetch_one(
            "SELECT rollback_sql FROM schema_migrations WHERE version = ?",
            (version,)
        )
        
        if not result or not result['rollback_sql']:
            raise ValueError(f"No rollback SQL found for migration {version}")
        
        rollback_statements = result['rollback_sql'].split(';')
        
        self.logger.info(f"Rolling back migration {version}")
        
        try:
            await self.connection.begin_transaction()
            
            # Execute rollback SQL
            for sql_statement in rollback_statements:
                if sql_statement.strip():
                    await self.connection.execute(sql_statement)
            
            # Remove migration record
            await self.connection.execute(
                "DELETE FROM schema_migrations WHERE version = ?",
                (version,)
            )
            
            await self.connection.commit()
            self.logger.info(f"Migration {version} rolled back successfully")
            
        except Exception as e:
            await self.connection.rollback()
            self.logger.error(f"Failed to rollback migration {version}: {e}")
            raise


class MigrationManager:
    """Manages migration discovery, ordering, and execution"""
    
    def __init__(self, migration_dir: str = "migrations"):
        self.migration_dir = Path(migration_dir)
        self.migrations: Dict[str, Migration] = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def add_migration(self, migration: Migration) -> None:
        """Add a migration to the manager"""
        self.migrations[migration.version] = migration
    
    def load_migrations_from_directory(self) -> None:
        """Load migrations from directory"""
        if not self.migration_dir.exists():
            self.migration_dir.mkdir(parents=True, exist_ok=True)
            return
        
        for migration_file in self.migration_dir.glob("*.json"):
            try:
                with open(migration_file, 'r') as f:
                    migration_data = json.load(f)
                
                migration = Migration.from_dict(migration_data)
                self.add_migration(migration)
                self.logger.debug(f"Loaded migration {migration.version} from {migration_file}")
                
            except Exception as e:
                self.logger.error(f"Failed to load migration from {migration_file}: {e}")
    
    def save_migration(self, migration: Migration) -> None:
        """Save migration to file"""
        self.migration_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{migration.version}_{migration.name.lower().replace(' ', '_')}.json"
        filepath = self.migration_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(migration.to_dict(), f, indent=2)
        
        self.logger.info(f"Migration {migration.version} saved to {filepath}")
    
    def get_ordered_migrations(self) -> List[Migration]:
        """Get migrations ordered by dependencies and version"""
        ordered = []
        processed = set()
        
        def add_migration_with_deps(version: str):
            if version in processed or version not in self.migrations:
                return
            
            migration = self.migrations[version]
            
            # Add dependencies first
            for dep_version in migration.dependencies:
                add_migration_with_deps(dep_version)
            
            ordered.append(migration)
            processed.add(version)
        
        # Process all migrations
        for version in sorted(self.migrations.keys()):
            add_migration_with_deps(version)
        
        return ordered
    
    def get_pending_migrations(self, applied_versions: List[str]) -> List[Migration]:
        """Get migrations that haven't been applied yet"""
        applied_set = set(applied_versions)
        ordered_migrations = self.get_ordered_migrations()
        
        return [m for m in ordered_migrations if m.version not in applied_set]
    
    async def migrate_to_latest(self, connection_name: Optional[str] = None) -> None:
        """Run all pending migrations"""
        connection = DatabaseManager.get_connection(connection_name)
        runner = MigrationRunner(connection)
        
        # Load migrations
        self.load_migrations_from_directory()
        
        # Get applied migrations
        applied_versions = await runner.get_applied_migrations()
        
        # Get pending migrations
        pending_migrations = self.get_pending_migrations(applied_versions)
        
        if not pending_migrations:
            self.logger.info("No pending migrations")
            return
        
        self.logger.info(f"Running {len(pending_migrations)} pending migrations")
        
        for migration in pending_migrations:
            await runner.apply_migration(migration)
    
    async def rollback_to_version(self, target_version: str, connection_name: Optional[str] = None) -> None:
        """Rollback to a specific version"""
        connection = DatabaseManager.get_connection(connection_name)
        runner = MigrationRunner(connection)
        
        applied_versions = await runner.get_applied_migrations()
        
        # Find migrations to rollback (in reverse order)
        migrations_to_rollback = []
        for version in reversed(applied_versions):
            if version == target_version:
                break
            migrations_to_rollback.append(version)
        
        if not migrations_to_rollback:
            self.logger.info(f"Already at version {target_version}")
            return
        
        self.logger.info(f"Rolling back {len(migrations_to_rollback)} migrations to version {target_version}")
        
        for version in migrations_to_rollback:
            await runner.rollback_migration(version)


def create_initial_migrations() -> List[Migration]:
    """Create initial migrations for all supported databases"""
    migrations = []
    
    # Initial schema migration
    initial_migration = Migration(
        version="001_001_000",
        name="Initial Schema",
        description="Create initial Orthanc Management Module schema",
        up_sql=[
            # This will be populated with actual schema creation SQL
            # from the schema generator for each database type
        ],
        down_sql=[
            "DROP TABLE IF EXISTS notification_queue",
            "DROP TABLE IF EXISTS audit_logs", 
            "DROP TABLE IF EXISTS orthanc_server_status",
            "DROP TABLE IF EXISTS orthanc_configs",
            "DROP TABLE IF EXISTS patient_shares",
            "DROP TABLE IF EXISTS patient_authorizations",
            "DROP TABLE IF EXISTS patient_referrals",
            "DROP TABLE IF EXISTS referring_doctors",
            "DROP TABLE IF EXISTS schema_migrations"
        ]
    )
    
    migrations.append(initial_migration)
    
    # Sample data migration
    sample_data_migration = Migration(
        version="001_002_000",
        name="Sample Data",
        description="Insert sample referring doctors and test data",
        up_sql=[
            """
            INSERT INTO referring_doctors (id, name, hpcsa_number, email, specialization, province, is_active)
            VALUES 
            ('DOC001', 'Dr. Sarah Johnson', 'HP12345', 'sarah.johnson@example.com', 'Radiology', 'Gauteng', true),
            ('DOC002', 'Dr. Michael Chen', 'HP67890', 'michael.chen@example.com', 'Orthopedics', 'Western Cape', true),
            ('DOC003', 'Dr. Priya Patel', 'HP54321', 'priya.patel@example.com', 'Cardiology', 'KwaZulu-Natal', true)
            """,
            """
            INSERT INTO orthanc_configs (id, config_name, description, environment, is_default, config_data)
            VALUES 
            ('CFG001', 'Default Configuration', 'Standard Orthanc configuration for production', 'production', true, '{}')
            """
        ],
        down_sql=[
            "DELETE FROM orthanc_configs WHERE id IN ('CFG001')",
            "DELETE FROM referring_doctors WHERE id IN ('DOC001', 'DOC002', 'DOC003')"
        ],
        dependencies=["001_001_000"]
    )
    
    migrations.append(sample_data_migration)
    
    return migrations


if __name__ == "__main__":
    # Example usage
    async def example_usage():
        # Setup migration manager
        migration_manager = MigrationManager("./migrations")
        
        # Create and save initial migrations
        initial_migrations = create_initial_migrations()
        for migration in initial_migrations:
            migration_manager.save_migration(migration)
        
        print("Initial migrations created and saved to ./migrations directory")
        print("Use migration_manager.migrate_to_latest() to apply migrations")
    
    asyncio.run(example_usage())
