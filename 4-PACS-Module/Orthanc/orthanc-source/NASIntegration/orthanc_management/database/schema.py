"""
Orthanc Management Module - Database Schema Base
Multi-database compatible base classes and utilities using SQLAlchemy
"""

from sqlalchemy import String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

from .config import DatabaseType, db_settings

# Create base class for all models
Base = declarative_base()


def generate_id():
    """Generate unique ID compatible with all databases"""
    return str(uuid.uuid4())


def get_timestamp_default():
    """Get current timestamp - database agnostic"""
    from datetime import datetime
    return datetime.utcnow()


class DatabaseCompatibleMixin:
    """Mixin class for database compatibility features"""
    
    @classmethod
    def get_table_name(cls):
        """Get table name"""
        return cls.__tablename__
    
    @classmethod
    def get_primary_key_type(cls):
        """Get appropriate primary key type for current database"""
        db_type = db_settings.database_type
        
        if db_type == DatabaseType.SQLITE:
            return String(50)  # Use UUID strings for SQLite
        elif db_type == DatabaseType.MYSQL:
            return String(50)  # Use UUID strings for MySQL
        elif db_type == DatabaseType.POSTGRESQL:
            return String(50)  # PostgreSQL supports UUID type but string is more compatible
        elif db_type == DatabaseType.FIREBIRD:
            return String(50)  # Firebird uses strings
        elif db_type == DatabaseType.MSSQL:
            return String(50)  # SQL Server uses UNIQUEIDENTIFIER but string is compatible
        elif db_type == DatabaseType.ORACLE:
            return String(50)  # Oracle uses RAW(16) for UUID but string is compatible
        else:
            return String(50)  # Default fallback


# Database-specific sequence creation for databases that need it
def create_sequences(engine):
    """Create sequences for databases that require them (Firebird, Oracle)"""
    from sqlalchemy import event
    from .config import DatabaseType, db_settings
    
    if db_settings.database_type in [DatabaseType.FIREBIRD, DatabaseType.ORACLE]:
        
        @event.listens_for(Base.metadata, 'before_create')
        def create_sequences_listener(target, connection, **kw):
            # Create sequences for auto-increment fields if needed
            sequences = [
                'seq_referring_doctors_id',
                'seq_patient_referrals_id',
                'seq_patient_auth_id',
                'seq_patient_shares_id',
                'seq_orthanc_configs_id',
                'seq_audit_logs_id',
            ]
            
            for seq_name in sequences:
                try:
                    if db_settings.database_type == DatabaseType.FIREBIRD:
                        connection.execute(f"CREATE SEQUENCE {seq_name}")
                    elif db_settings.database_type == DatabaseType.ORACLE:
                        connection.execute(f"CREATE SEQUENCE {seq_name} START WITH 1 INCREMENT BY 1")
                except Exception as e:
                    # Sequence might already exist
                    pass


# Export only base components
__all__ = [
    'Base',
    'DatabaseCompatibleMixin',
    'generate_id',
    'get_timestamp_default',
    'create_sequences'
]
