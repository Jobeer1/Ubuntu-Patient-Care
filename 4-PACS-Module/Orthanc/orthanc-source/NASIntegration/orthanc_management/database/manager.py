"""
Orthanc Management Module - Database Abstraction Layer
Provides unified interface for multiple database backends with SQL syntax adaptation
"""

from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from typing import Dict, Any, Optional, List, Union
import logging
import uuid
from datetime import datetime

from .config import DatabaseSettings, DatabaseType, DatabaseConfig

# Configure logging
logger = logging.getLogger(__name__)

# Create base class for all models
Base = declarative_base()


class DatabaseManager:
    """
    Unified database manager supporting multiple SQL backends
    Handles connection management, schema creation, and SQL syntax adaptation
    """
    
    def __init__(self, db_settings: Optional[DatabaseSettings] = None):
        self.db_settings = db_settings or DatabaseSettings()
        self.db_config = DatabaseConfig()
        self.engine = None
        self.SessionLocal = None
        self.metadata = MetaData()
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize database connection and session factory"""
        try:
            # Validate configuration
            config_errors = self.db_settings.validate_configuration()
            if config_errors:
                for error in config_errors:
                    logger.error(f"Database configuration error: {error}")
                return False
            
            # Create engine
            connection_string = self.db_settings.get_connection_string()
            engine_kwargs = self.db_settings.get_engine_kwargs()
            
            logger.info(f"Initializing database connection to {self.db_settings.database_type.value}")
            self.engine = create_engine(connection_string, **engine_kwargs)
            
            # Test connection
            with self.engine.connect() as conn:
                self._test_connection(conn)
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
            
            self._initialized = True
            logger.info("Database connection initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
    
    def _test_connection(self, connection):
        """Test database connection with appropriate SQL for each database type"""
        test_queries = {
            DatabaseType.SQLITE: "SELECT 1",
            DatabaseType.MYSQL: "SELECT 1",
            DatabaseType.POSTGRESQL: "SELECT 1",
            DatabaseType.FIREBIRD: "SELECT 1 FROM RDB$DATABASE",
            DatabaseType.MSSQL: "SELECT 1",
            DatabaseType.ORACLE: "SELECT 1 FROM DUAL",
        }
        
        query = test_queries.get(self.db_settings.database_type, "SELECT 1")
        result = connection.execute(text(query))
        result.fetchone()
        logger.debug(f"Database connection test successful: {self.db_settings.database_type.value}")
    
    @contextmanager
    def get_session(self) -> Session:
        """Get database session with automatic cleanup"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def create_all_tables(self) -> bool:
        """Create all tables in the database"""
        try:
            if not self._initialized:
                self.initialize()
            
            logger.info("Creating database tables...")
            
            # Import all models to ensure they're registered
            from ..models.referring_doctor import ReferringDoctor
            from ..models.patient_referral import PatientReferral
            # from ..models.patient_authorization import PatientAuthorization
            # from ..models.patient_share import PatientShare
            # from ..models.orthanc_config import OrthancConfig
            # from ..models.audit_log import AuditLog
            
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            
            # Create database-specific optimizations
            self._create_database_optimizations()
            
            logger.info("Database tables created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            return False
    
    def _create_database_optimizations(self):
        """Create database-specific indexes and optimizations"""
        try:
            with self.engine.connect() as conn:
                # Common indexes for all databases
                indexes = self._get_optimization_sql()
                
                for index_sql in indexes:
                    try:
                        conn.execute(text(index_sql))
                        logger.debug(f"Created index: {index_sql}")
                    except Exception as e:
                        logger.warning(f"Failed to create index: {e}")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to create database optimizations: {e}")
    
    def _get_optimization_sql(self) -> List[str]:
        """Get database-specific optimization SQL"""
        base_indexes = [
            # Referring doctors indexes
            "CREATE INDEX IF NOT EXISTS idx_referring_doctors_hpcsa ON referring_doctors(hpcsa_number)",
            "CREATE INDEX IF NOT EXISTS idx_referring_doctors_email ON referring_doctors(email)",
            "CREATE INDEX IF NOT EXISTS idx_referring_doctors_active ON referring_doctors(is_active)",
            
            # Patient referrals indexes
            "CREATE INDEX IF NOT EXISTS idx_patient_referrals_patient ON patient_referrals(patient_id)",
            "CREATE INDEX IF NOT EXISTS idx_patient_referrals_doctor ON patient_referrals(referring_doctor_id)",
            "CREATE INDEX IF NOT EXISTS idx_patient_referrals_study ON patient_referrals(study_instance_uid)",
            "CREATE INDEX IF NOT EXISTS idx_patient_referrals_date ON patient_referrals(referral_date)",
            
            # Patient authorizations indexes
            "CREATE INDEX IF NOT EXISTS idx_patient_auth_doctor ON patient_authorizations(doctor_id)",
            "CREATE INDEX IF NOT EXISTS idx_patient_auth_patient ON patient_authorizations(patient_id)",
            "CREATE INDEX IF NOT EXISTS idx_patient_auth_study ON patient_authorizations(study_instance_uid)",
            "CREATE INDEX IF NOT EXISTS idx_patient_auth_expires ON patient_authorizations(expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_patient_auth_active ON patient_authorizations(is_active)",
            
            # Patient shares indexes
            "CREATE INDEX IF NOT EXISTS idx_patient_shares_token ON patient_shares(share_token)",
            "CREATE INDEX IF NOT EXISTS idx_patient_shares_patient ON patient_shares(patient_id)",
            "CREATE INDEX IF NOT EXISTS idx_patient_shares_expires ON patient_shares(expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_patient_shares_active ON patient_shares(is_active)",
            
            # Audit logs indexes
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id)",
        ]
        
        # Adapt SQL for different database types
        adapted_indexes = []
        for sql in base_indexes:
            adapted_sql = self._adapt_sql_syntax(sql)
            if adapted_sql:
                adapted_indexes.append(adapted_sql)
        
        return adapted_indexes
    
    def _adapt_sql_syntax(self, sql: str) -> str:
        """Adapt SQL syntax for different database types"""
        db_type = self.db_settings.database_type
        
        if db_type == DatabaseType.MYSQL:
            # MySQL doesn't support IF NOT EXISTS for indexes
            return sql.replace("CREATE INDEX IF NOT EXISTS", "CREATE INDEX")
        
        elif db_type == DatabaseType.POSTGRESQL:
            # PostgreSQL supports standard syntax
            return sql
        
        elif db_type == DatabaseType.FIREBIRD:
            # Firebird has different index syntax
            return sql.replace("CREATE INDEX IF NOT EXISTS", "CREATE INDEX")
        
        elif db_type == DatabaseType.MSSQL:
            # SQL Server uses different syntax
            return sql.replace("CREATE INDEX IF NOT EXISTS", "CREATE NONCLUSTERED INDEX")
        
        elif db_type == DatabaseType.ORACLE:
            # Oracle has different syntax
            return sql.replace("CREATE INDEX IF NOT EXISTS", "CREATE INDEX")
        
        else:  # SQLite and default
            return sql
    
    def execute_raw_sql(self, sql: str, params: Dict[str, Any] = None) -> Any:
        """Execute raw SQL with parameter binding"""
        try:
            with self.get_session() as session:
                result = session.execute(text(sql), params or {})
                return result.fetchall()
        except Exception as e:
            logger.error(f"Failed to execute SQL: {e}")
            raise
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get table information (columns, indexes, etc.)"""
        try:
            with self.engine.connect() as conn:
                # Use database-specific system queries
                if self.db_settings.database_type == DatabaseType.SQLITE:
                    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                elif self.db_settings.database_type == DatabaseType.MYSQL:
                    result = conn.execute(text(f"DESCRIBE {table_name}"))
                elif self.db_settings.database_type == DatabaseType.POSTGRESQL:
                    result = conn.execute(text(f"""
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns 
                        WHERE table_name = '{table_name}'
                    """))
                else:
                    # Generic fallback
                    result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 0"))
                
                return {'columns': [dict(row) for row in result]}
                
        except Exception as e:
            logger.error(f"Failed to get table info for {table_name}: {e}")
            return {}
    
    def backup_database(self, backup_path: str) -> bool:
        """Create database backup (implementation varies by database type)"""
        try:
            if self.db_settings.database_type == DatabaseType.SQLITE:
                import shutil
                shutil.copy2(self.db_settings.database_path, backup_path)
                logger.info(f"SQLite database backed up to {backup_path}")
                return True
            else:
                logger.warning(f"Backup not implemented for {self.db_settings.database_type.value}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            stats = {
                'database_type': self.db_settings.database_type.value,
                'connection_string': self.db_settings.get_connection_string().split('@')[0] + '@***',  # Hide credentials
                'tables': {}
            }
            
            # Get table counts
            table_names = [
                'referring_doctors', 'patient_referrals', 'patient_authorizations',
                'patient_shares', 'orthanc_configs', 'audit_logs'
            ]
            
            with self.get_session() as session:
                for table_name in table_names:
                    try:
                        count_sql = f"SELECT COUNT(*) as count FROM {table_name}"
                        result = session.execute(text(count_sql))
                        count = result.scalar()
                        stats['tables'][table_name] = {'count': count}
                    except Exception:
                        stats['tables'][table_name] = {'count': 0, 'error': 'Table not found'}
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {'error': str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        health = {
            'status': 'unknown',
            'database_type': self.db_settings.database_type.value,
            'initialized': self._initialized,
            'connection_test': False,
            'tables_exist': False,
            'errors': []
        }
        
        try:
            # Test connection
            if self._initialized:
                with self.engine.connect() as conn:
                    self._test_connection(conn)
                    health['connection_test'] = True
            
            # Check if tables exist
            try:
                with self.get_session() as session:
                    session.execute(text("SELECT 1 FROM referring_doctors LIMIT 1"))
                    health['tables_exist'] = True
            except Exception:
                health['errors'].append("Core tables not found")
            
            # Overall status
            if health['connection_test'] and health['tables_exist']:
                health['status'] = 'healthy'
            elif health['connection_test']:
                health['status'] = 'partial'
            else:
                health['status'] = 'unhealthy'
                
        except Exception as e:
            health['errors'].append(str(e))
            health['status'] = 'error'
        
        return health


# Global database manager instance
db_manager = DatabaseManager()


# Utility functions for common database operations
def get_session():
    """Get database session - convenience function"""
    return db_manager.get_session()


def init_database() -> bool:
    """Initialize database - convenience function"""
    return db_manager.initialize()


def create_tables() -> bool:
    """Create all tables - convenience function"""
    return db_manager.create_all_tables()


def get_db_stats() -> Dict[str, Any]:
    """Get database statistics - convenience function"""
    return db_manager.get_database_stats()


def health_check() -> Dict[str, Any]:
    """Database health check - convenience function"""
    return db_manager.health_check()
