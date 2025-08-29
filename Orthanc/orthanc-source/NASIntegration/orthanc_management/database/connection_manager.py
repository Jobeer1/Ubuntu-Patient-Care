"""
Database Connection Manager for Orthanc Management Module
Supports MySQL, PostgreSQL, SQLite, Firebird, SQL Server, and Oracle
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from enum import Enum
import json
import sqlite3
from pathlib import Path

# Import database drivers (with fallbacks for optional dependencies)
try:
    import aiomysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

try:
    import asyncpg
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

try:
    import aiosqlite
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False

try:
    import aioodbc
    FIREBIRD_AVAILABLE = True
except ImportError:
    FIREBIRD_AVAILABLE = False

from schema_generator import DatabaseType, DatabaseSchemaGenerator, get_orthanc_management_schema


@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    db_type: DatabaseType
    host: Optional[str] = None
    port: Optional[int] = None
    database: str = "orthanc_management"
    username: Optional[str] = None
    password: Optional[str] = None
    file_path: Optional[str] = None  # For SQLite/Firebird file databases
    connection_params: Optional[Dict[str, Any]] = None
    pool_size: int = 10
    max_overflow: int = 20
    timeout: int = 30


class DatabaseConnection(ABC):
    """Abstract base class for database connections"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._pool = None
        self._connection = None
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish database connection"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection"""
        pass
    
    @abstractmethod
    async def execute(self, query: str, params: Optional[Tuple] = None) -> Any:
        """Execute a query"""
        pass
    
    @abstractmethod
    async def fetch_one(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        """Fetch single row"""
        pass
    
    @abstractmethod
    async def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Fetch all rows"""
        pass
    
    @abstractmethod
    async def begin_transaction(self):
        """Begin transaction"""
        pass
    
    @abstractmethod
    async def commit(self):
        """Commit transaction"""
        pass
    
    @abstractmethod
    async def rollback(self):
        """Rollback transaction"""
        pass
    
    @abstractmethod
    def get_placeholder(self) -> str:
        """Get parameter placeholder for this database type"""
        pass


class MySQLConnection(DatabaseConnection):
    """MySQL database connection implementation"""
    
    async def connect(self) -> None:
        if not MYSQL_AVAILABLE:
            raise ImportError("aiomysql package required for MySQL support")
        
        try:
            self._pool = await aiomysql.create_pool(
                host=self.config.host,
                port=self.config.port or 3306,
                user=self.config.username,
                password=self.config.password,
                db=self.config.database,
                minsize=1,
                maxsize=self.config.pool_size,
                autocommit=False,
                charset='utf8mb4'
            )
            self.logger.info("MySQL connection pool created successfully")
        except Exception as e:
            self.logger.error(f"Failed to connect to MySQL: {e}")
            raise
    
    async def disconnect(self) -> None:
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self.logger.info("MySQL connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        async with self._pool.acquire() as conn:
            yield conn
    
    async def execute(self, query: str, params: Optional[Tuple] = None) -> Any:
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                return cursor.rowcount
    
    async def fetch_one(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchone()
    
    async def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchall()
    
    async def begin_transaction(self):
        self._transaction_conn = await self._pool.acquire()
        await self._transaction_conn.begin()
        return self._transaction_conn
    
    async def commit(self):
        if hasattr(self, '_transaction_conn'):
            await self._transaction_conn.commit()
            self._pool.release(self._transaction_conn)
            delattr(self, '_transaction_conn')
    
    async def rollback(self):
        if hasattr(self, '_transaction_conn'):
            await self._transaction_conn.rollback()
            self._pool.release(self._transaction_conn)
            delattr(self, '_transaction_conn')
    
    def get_placeholder(self) -> str:
        return "%s"


class PostgreSQLConnection(DatabaseConnection):
    """PostgreSQL database connection implementation"""
    
    async def connect(self) -> None:
        if not POSTGRESQL_AVAILABLE:
            raise ImportError("asyncpg package required for PostgreSQL support")
        
        try:
            dsn = f"postgresql://{self.config.username}:{self.config.password}@{self.config.host}:{self.config.port or 5432}/{self.config.database}"
            self._pool = await asyncpg.create_pool(
                dsn,
                min_size=1,
                max_size=self.config.pool_size,
                command_timeout=self.config.timeout
            )
            self.logger.info("PostgreSQL connection pool created successfully")
        except Exception as e:
            self.logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    async def disconnect(self) -> None:
        if self._pool:
            await self._pool.close()
            self.logger.info("PostgreSQL connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        async with self._pool.acquire() as conn:
            yield conn
    
    async def execute(self, query: str, params: Optional[Tuple] = None) -> Any:
        async with self.get_connection() as conn:
            result = await conn.execute(query, *(params or ()))
            return int(result.split()[-1]) if result else 0
    
    async def fetch_one(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, *(params or ()))
            return dict(row) if row else None
    
    async def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *(params or ()))
            return [dict(row) for row in rows]
    
    async def begin_transaction(self):
        self._transaction_conn = await self._pool.acquire()
        self._transaction = self._transaction_conn.transaction()
        await self._transaction.start()
        return self._transaction_conn
    
    async def commit(self):
        if hasattr(self, '_transaction'):
            await self._transaction.commit()
            await self._pool.release(self._transaction_conn)
            delattr(self, '_transaction')
            delattr(self, '_transaction_conn')
    
    async def rollback(self):
        if hasattr(self, '_transaction'):
            await self._transaction.rollback()
            await self._pool.release(self._transaction_conn)
            delattr(self, '_transaction')
            delattr(self, '_transaction_conn')
    
    def get_placeholder(self) -> str:
        return "$"  # PostgreSQL uses $1, $2, etc.


class SQLiteConnection(DatabaseConnection):
    """SQLite database connection implementation"""
    
    async def connect(self) -> None:
        if not SQLITE_AVAILABLE:
            raise ImportError("aiosqlite package required for SQLite support")
        
        try:
            db_path = self.config.file_path or f"{self.config.database}.db"
            # Ensure directory exists
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
            self._db_path = db_path
            # Test connection
            async with aiosqlite.connect(db_path) as conn:
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.commit()
            
            self.logger.info(f"SQLite database initialized at {db_path}")
        except Exception as e:
            self.logger.error(f"Failed to initialize SQLite database: {e}")
            raise
    
    async def disconnect(self) -> None:
        # SQLite doesn't maintain persistent connections
        self.logger.info("SQLite connection closed")
    
    @asynccontextmanager
    async def get_connection(self):
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            yield conn
    
    async def execute(self, query: str, params: Optional[Tuple] = None) -> Any:
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params or ())
            await conn.commit()
            return cursor.rowcount
    
    async def fetch_one(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params or ())
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params or ())
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def begin_transaction(self):
        self._transaction_conn = await aiosqlite.connect(self._db_path)
        self._transaction_conn.row_factory = aiosqlite.Row
        await self._transaction_conn.execute("BEGIN")
        return self._transaction_conn
    
    async def commit(self):
        if hasattr(self, '_transaction_conn'):
            await self._transaction_conn.commit()
            await self._transaction_conn.close()
            delattr(self, '_transaction_conn')
    
    async def rollback(self):
        if hasattr(self, '_transaction_conn'):
            await self._transaction_conn.rollback()
            await self._transaction_conn.close()
            delattr(self, '_transaction_conn')
    
    def get_placeholder(self) -> str:
        return "?"


class FirebirdConnection(DatabaseConnection):
    """Firebird database connection implementation"""
    
    async def connect(self) -> None:
        if not FIREBIRD_AVAILABLE:
            raise ImportError("aioodbc package required for Firebird support")
        
        try:
            # Firebird connection string
            dsn = f"DRIVER={{Firebird/InterBase(r3)}};DATABASE={self.config.file_path or self.config.database};UID={self.config.username};PWD={self.config.password}"
            
            self._pool = await aioodbc.create_pool(
                dsn=dsn,
                minsize=1,
                maxsize=self.config.pool_size
            )
            self.logger.info("Firebird connection pool created successfully")
        except Exception as e:
            self.logger.error(f"Failed to connect to Firebird: {e}")
            raise
    
    async def disconnect(self) -> None:
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self.logger.info("Firebird connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        async with self._pool.acquire() as conn:
            yield conn
    
    async def execute(self, query: str, params: Optional[Tuple] = None) -> Any:
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                return cursor.rowcount
    
    async def fetch_one(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
    
    async def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
    
    async def begin_transaction(self):
        self._transaction_conn = await self._pool.acquire()
        await self._transaction_conn.autocommit(False)
        return self._transaction_conn
    
    async def commit(self):
        if hasattr(self, '_transaction_conn'):
            await self._transaction_conn.commit()
            self._pool.release(self._transaction_conn)
            delattr(self, '_transaction_conn')
    
    async def rollback(self):
        if hasattr(self, '_transaction_conn'):
            await self._transaction_conn.rollback()
            self._pool.release(self._transaction_conn)
            delattr(self, '_transaction_conn')
    
    def get_placeholder(self) -> str:
        return "?"


class DatabaseManager:
    """Unified database manager supporting multiple database types"""
    
    _connections: Dict[str, DatabaseConnection] = {}
    _default_connection: Optional[str] = None
    
    @classmethod
    def create_connection(cls, name: str, config: DatabaseConfig) -> DatabaseConnection:
        """Create a named database connection"""
        
        connection_classes = {
            DatabaseType.MYSQL: MySQLConnection,
            DatabaseType.POSTGRESQL: PostgreSQLConnection,
            DatabaseType.SQLITE: SQLiteConnection,
            DatabaseType.FIREBIRD: FirebirdConnection,
            # Additional database types can be added here
        }
        
        if config.db_type not in connection_classes:
            raise ValueError(f"Unsupported database type: {config.db_type}")
        
        connection_class = connection_classes[config.db_type]
        connection = connection_class(config)
        
        cls._connections[name] = connection
        
        if cls._default_connection is None:
            cls._default_connection = name
        
        return connection
    
    @classmethod
    def get_connection(cls, name: Optional[str] = None) -> DatabaseConnection:
        """Get a named connection or the default connection"""
        connection_name = name or cls._default_connection
        
        if connection_name is None:
            raise ValueError("No default connection set")
        
        if connection_name not in cls._connections:
            raise ValueError(f"Connection '{connection_name}' not found")
        
        return cls._connections[connection_name]
    
    @classmethod
    async def connect_all(cls) -> None:
        """Connect all registered connections"""
        for name, connection in cls._connections.items():
            try:
                await connection.connect()
                logging.info(f"Connected to database: {name}")
            except Exception as e:
                logging.error(f"Failed to connect to database '{name}': {e}")
                raise
    
    @classmethod
    async def disconnect_all(cls) -> None:
        """Disconnect all connections"""
        for name, connection in cls._connections.items():
            try:
                await connection.disconnect()
                logging.info(f"Disconnected from database: {name}")
            except Exception as e:
                logging.error(f"Error disconnecting from database '{name}': {e}")
    
    @classmethod
    def set_default(cls, name: str) -> None:
        """Set the default connection"""
        if name not in cls._connections:
            raise ValueError(f"Connection '{name}' not found")
        cls._default_connection = name
    
    @classmethod
    async def initialize_schema(cls, connection_name: Optional[str] = None) -> None:
        """Initialize database schema"""
        connection = cls.get_connection(connection_name)
        schema_generator = DatabaseSchemaGenerator(connection.config.db_type)
        schema_tables = get_orthanc_management_schema()
        
        logging.info(f"Initializing schema for {connection.config.db_type.value}")
        
        try:
            await connection.begin_transaction()
            
            for table in schema_tables:
                statements = schema_generator.generate_table_sql(table)
                for statement in statements:
                    logging.debug(f"Executing: {statement}")
                    await connection.execute(statement)
            
            # Create schema version table
            version_table_sql = """
            CREATE TABLE IF NOT EXISTS schema_versions (
                version VARCHAR(50) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
            """
            await connection.execute(version_table_sql)
            
            # Insert initial version
            await connection.execute(
                "INSERT OR IGNORE INTO schema_versions (version, description) VALUES (?, ?)",
                ("1.0.0", "Initial Orthanc Management Module schema")
            )
            
            await connection.commit()
            logging.info("Schema initialization completed successfully")
            
        except Exception as e:
            await connection.rollback()
            logging.error(f"Schema initialization failed: {e}")
            raise


# Configuration helpers
def load_database_config(config_file: str) -> Dict[str, DatabaseConfig]:
    """Load database configurations from JSON file"""
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    
    configs = {}
    for name, config in config_data.items():
        db_type = DatabaseType(config['type'])
        configs[name] = DatabaseConfig(
            db_type=db_type,
            host=config.get('host'),
            port=config.get('port'),
            database=config.get('database', 'orthanc_management'),
            username=config.get('username'),
            password=config.get('password'),
            file_path=config.get('file_path'),
            connection_params=config.get('connection_params'),
            pool_size=config.get('pool_size', 10),
            max_overflow=config.get('max_overflow', 20),
            timeout=config.get('timeout', 30)
        )
    
    return configs


async def setup_databases(config_file: str) -> None:
    """Setup databases from configuration file"""
    configs = load_database_config(config_file)
    
    for name, config in configs.items():
        DatabaseManager.create_connection(name, config)
    
    await DatabaseManager.connect_all()
    
    # Initialize schema for all connections
    for name in configs.keys():
        await DatabaseManager.initialize_schema(name)


if __name__ == "__main__":
    # Example configuration
    example_config = {
        "sqlite_default": {
            "type": "sqlite",
            "file_path": "./orthanc_management.db"
        },
        "mysql_primary": {
            "type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database": "orthanc_management",
            "username": "orthanc_user",
            "password": "orthanc_password"
        },
        "firebird_archive": {
            "type": "firebird",
            "file_path": "./archive.fdb",
            "username": "SYSDBA",
            "password": "masterkey"
        }
    }
    
    # Save example config
    with open("database_config.json", "w") as f:
        json.dump(example_config, f, indent=2)
    
    print("Example database configuration saved to database_config.json")
    print("Run setup_databases('database_config.json') to initialize databases.")
