"""
Orthanc Management Module - Database Configuration
Supports multiple database backends: SQLite, MySQL, PostgreSQL, FirebirdSQL, SQL Server, Oracle
"""

import os
from enum import Enum
from typing import Dict, Any, Optional


class DatabaseType(Enum):
    """Supported database types"""
    SQLITE = "sqlite"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    FIREBIRD = "firebird"
    MSSQL = "mssql"
    ORACLE = "oracle"


class DatabaseConfig:
    """Database configuration manager supporting multiple backends"""
    
    def __init__(self):
        self.configs = {
            DatabaseType.SQLITE: {
                'driver': 'sqlite3',
                'connection_string_template': 'sqlite:///{database_path}',
                'default_path': os.path.join(os.path.dirname(__file__), '../data/orthanc_management.db'),
                'supports_schemas': False,
                'supports_foreign_keys': True,
                'auto_increment_syntax': 'INTEGER PRIMARY KEY AUTOINCREMENT',
                'timestamp_type': 'TIMESTAMP',
                'text_type': 'TEXT',
                'boolean_type': 'INTEGER',  # SQLite uses INTEGER for boolean
            },
            DatabaseType.MYSQL: {
                'driver': 'mysql+pymysql',
                'connection_string_template': 'mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4',
                'default_port': 3306,
                'supports_schemas': False,
                'supports_foreign_keys': True,
                'auto_increment_syntax': 'INT AUTO_INCREMENT PRIMARY KEY',
                'timestamp_type': 'TIMESTAMP',
                'text_type': 'TEXT',
                'boolean_type': 'BOOLEAN',
            },
            DatabaseType.POSTGRESQL: {
                'driver': 'postgresql+psycopg2',
                'connection_string_template': 'postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}',
                'default_port': 5432,
                'supports_schemas': True,
                'supports_foreign_keys': True,
                'auto_increment_syntax': 'SERIAL PRIMARY KEY',
                'timestamp_type': 'TIMESTAMP',
                'text_type': 'TEXT',
                'boolean_type': 'BOOLEAN',
            },
            DatabaseType.FIREBIRD: {
                'driver': 'firebird+fdb',
                'connection_string_template': 'firebird+fdb://{username}:{password}@{host}:{port}/{database_path}',
                'default_port': 3050,
                'supports_schemas': False,
                'supports_foreign_keys': True,
                'auto_increment_syntax': 'INTEGER NOT NULL',  # Firebird uses generators/sequences
                'timestamp_type': 'TIMESTAMP',
                'text_type': 'BLOB SUB_TYPE TEXT',
                'boolean_type': 'SMALLINT',  # Firebird uses SMALLINT for boolean
                'sequence_syntax': True,  # Uses sequences for auto increment
            },
            DatabaseType.MSSQL: {
                'driver': 'mssql+pyodbc',
                'connection_string_template': 'mssql+pyodbc://{username}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server',
                'default_port': 1433,
                'supports_schemas': True,
                'supports_foreign_keys': True,
                'auto_increment_syntax': 'INT IDENTITY(1,1) PRIMARY KEY',
                'timestamp_type': 'DATETIME2',
                'text_type': 'NVARCHAR(MAX)',
                'boolean_type': 'BIT',
            },
            DatabaseType.ORACLE: {
                'driver': 'oracle+cx_oracle',
                'connection_string_template': 'oracle+cx_oracle://{username}:{password}@{host}:{port}/{database}',
                'default_port': 1521,
                'supports_schemas': True,
                'supports_foreign_keys': True,
                'auto_increment_syntax': 'NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY',
                'timestamp_type': 'TIMESTAMP',
                'text_type': 'CLOB',
                'boolean_type': 'NUMBER(1)',  # Oracle uses NUMBER(1) for boolean
                'sequence_syntax': True,  # Uses sequences for auto increment
            }
        }
    
    def get_config(self, db_type: DatabaseType) -> Dict[str, Any]:
        """Get configuration for specific database type"""
        return self.configs.get(db_type, {})
    
    def get_connection_string(self, db_type: DatabaseType, **kwargs) -> str:
        """Generate connection string for database type"""
        config = self.get_config(db_type)
        template = config.get('connection_string_template', '')
        
        # Set default values
        if db_type == DatabaseType.SQLITE:
            kwargs.setdefault('database_path', config['default_path'])
        else:
            kwargs.setdefault('port', config.get('default_port', 5432))
            kwargs.setdefault('host', 'localhost')
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required parameter for {db_type.value}: {e}")
    
    def get_required_packages(self, db_type: DatabaseType) -> list:
        """Get required Python packages for database type"""
        package_map = {
            DatabaseType.SQLITE: [],  # Built-in
            DatabaseType.MYSQL: ['PyMySQL', 'SQLAlchemy'],
            DatabaseType.POSTGRESQL: ['psycopg2-binary', 'SQLAlchemy'],
            DatabaseType.FIREBIRD: ['fdb', 'SQLAlchemy'],
            DatabaseType.MSSQL: ['pyodbc', 'SQLAlchemy'],
            DatabaseType.ORACLE: ['cx_Oracle', 'SQLAlchemy'],
        }
        return package_map.get(db_type, [])
    
    @staticmethod
    def detect_database_type(connection_string: str) -> Optional[DatabaseType]:
        """Detect database type from connection string"""
        connection_string = connection_string.lower()
        
        if connection_string.startswith('sqlite'):
            return DatabaseType.SQLITE
        elif 'mysql' in connection_string:
            return DatabaseType.MYSQL
        elif 'postgresql' in connection_string:
            return DatabaseType.POSTGRESQL
        elif 'firebird' in connection_string:
            return DatabaseType.FIREBIRD
        elif 'mssql' in connection_string:
            return DatabaseType.MSSQL
        elif 'oracle' in connection_string:
            return DatabaseType.ORACLE
        
        return None


class DatabaseSettings:
    """Environment-based database settings"""
    
    def __init__(self):
        self.db_config = DatabaseConfig()
        self._load_from_environment()
    
    def _load_from_environment(self):
        """Load database settings from environment variables"""
        # Default to SQLite if no database type specified
        db_type_str = os.environ.get('ORTHANC_DB_TYPE', 'sqlite').lower()
        
        try:
            self.database_type = DatabaseType(db_type_str)
        except ValueError:
            print(f"Warning: Unknown database type '{db_type_str}', defaulting to SQLite")
            self.database_type = DatabaseType.SQLITE
        
        # Common settings
        self.host = os.environ.get('ORTHANC_DB_HOST', 'localhost')
        self.port = int(os.environ.get('ORTHANC_DB_PORT', 
                                      self.db_config.get_config(self.database_type).get('default_port', 5432)))
        self.database = os.environ.get('ORTHANC_DB_NAME', 'orthanc_management')
        self.username = os.environ.get('ORTHANC_DB_USER', '')
        self.password = os.environ.get('ORTHANC_DB_PASSWORD', '')
        
        # SQLite specific
        self.database_path = os.environ.get('ORTHANC_DB_PATH', 
                                           self.db_config.get_config(DatabaseType.SQLITE)['default_path'])
        
        # Connection pool settings
        self.pool_size = int(os.environ.get('ORTHANC_DB_POOL_SIZE', '5'))
        self.max_overflow = int(os.environ.get('ORTHANC_DB_MAX_OVERFLOW', '10'))
        self.pool_timeout = int(os.environ.get('ORTHANC_DB_POOL_TIMEOUT', '30'))
        
        # SSL settings for remote databases
        self.ssl_mode = os.environ.get('ORTHANC_DB_SSL_MODE', 'prefer')
        self.ssl_cert = os.environ.get('ORTHANC_DB_SSL_CERT', '')
        self.ssl_key = os.environ.get('ORTHANC_DB_SSL_KEY', '')
        self.ssl_ca = os.environ.get('ORTHANC_DB_SSL_CA', '')
    
    def get_connection_string(self) -> str:
        """Generate connection string based on current settings"""
        if self.database_type == DatabaseType.SQLITE:
            return self.db_config.get_connection_string(
                self.database_type,
                database_path=self.database_path
            )
        else:
            return self.db_config.get_connection_string(
                self.database_type,
                username=self.username,
                password=self.password,
                host=self.host,
                port=self.port,
                database=self.database
            )
    
    def get_engine_kwargs(self) -> Dict[str, Any]:
        """Get additional engine configuration"""
        kwargs = {
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'pool_timeout': self.pool_timeout,
            'echo': os.environ.get('ORTHANC_DB_ECHO', 'false').lower() == 'true'
        }
        
        # Database-specific configurations
        if self.database_type == DatabaseType.SQLITE:
            kwargs.update({
                'pool_pre_ping': True,
                'connect_args': {'check_same_thread': False}
            })
        elif self.database_type == DatabaseType.MYSQL:
            kwargs.update({
                'pool_pre_ping': True,
                'connect_args': {
                    'charset': 'utf8mb4',
                    'autocommit': False
                }
            })
        elif self.database_type == DatabaseType.POSTGRESQL:
            kwargs.update({
                'pool_pre_ping': True,
                'connect_args': {
                    'sslmode': self.ssl_mode,
                    'application_name': 'orthanc_management'
                }
            })
        elif self.database_type == DatabaseType.FIREBIRD:
            kwargs.update({
                'pool_pre_ping': True,
                'connect_args': {
                    'charset': 'UTF8'
                }
            })
        
        return kwargs
    
    def validate_configuration(self) -> list:
        """Validate current database configuration"""
        errors = []
        
        if self.database_type != DatabaseType.SQLITE:
            if not self.username:
                errors.append("Database username is required for non-SQLite databases")
            if not self.password:
                errors.append("Database password is required for non-SQLite databases")
            if not self.database:
                errors.append("Database name is required for non-SQLite databases")
        
        if self.database_type == DatabaseType.SQLITE:
            import os
            db_dir = os.path.dirname(self.database_path)
            if not os.path.exists(db_dir):
                try:
                    os.makedirs(db_dir, exist_ok=True)
                except Exception as e:
                    errors.append(f"Cannot create SQLite database directory: {e}")
        
        return errors


# Global database settings instance
db_settings = DatabaseSettings()
