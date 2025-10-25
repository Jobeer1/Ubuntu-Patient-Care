"""
Database Initialization and Testing Script
Run this script to set up and test the database foundation
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent))

from schema_generator import DatabaseType, DatabaseSchemaGenerator, get_orthanc_management_schema
from connection_manager import DatabaseManager, DatabaseConfig, load_database_config
from migration_system import MigrationManager, Migration, create_initial_migrations
from dao import DAOFactory, QueryResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_schema_generation():
    """Test schema generation for different database types"""
    logger.info("Testing schema generation...")
    
    schema_tables = get_orthanc_management_schema()
    
    # Test MySQL schema generation
    mysql_generator = DatabaseSchemaGenerator(DatabaseType.MYSQL)
    logger.info("✓ MySQL schema generator created")
    
    # Test PostgreSQL schema generation
    postgres_generator = DatabaseSchemaGenerator(DatabaseType.POSTGRESQL)
    logger.info("✓ PostgreSQL schema generator created")
    
    # Test SQLite schema generation
    sqlite_generator = DatabaseSchemaGenerator(DatabaseType.SQLITE)
    logger.info("✓ SQLite schema generator created")
    
    # Test Firebird schema generation
    firebird_generator = DatabaseSchemaGenerator(DatabaseType.FIREBIRD)
    logger.info("✓ Firebird schema generator created")
    
    # Generate sample SQL for first table
    first_table = schema_tables[0]
    mysql_sql = mysql_generator.generate_table_sql(first_table)
    logger.info(f"✓ Generated MySQL SQL for table '{first_table.name}': {len(mysql_sql)} statements")
    
    logger.info("Schema generation test completed successfully!")


async def test_sqlite_connection():
    """Test SQLite connection and basic operations"""
    logger.info("Testing SQLite connection...")
    
    # Create SQLite configuration
    sqlite_config = DatabaseConfig(
        db_type=DatabaseType.SQLITE,
        file_path="./test_orthanc.db"
    )
    
    # Create connection
    connection = DatabaseManager.create_connection("test_sqlite", sqlite_config)
    
    try:
        # Connect
        await connection.connect()
        logger.info("✓ SQLite connection established")
        
        # Test basic query
        await connection.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT)")
        logger.info("✓ Test table created")
        
        # Insert test data
        await connection.execute("INSERT INTO test_table (name) VALUES (?)", ("Test Record",))
        logger.info("✓ Test record inserted")
        
        # Query test data
        result = await connection.fetch_one("SELECT * FROM test_table WHERE name = ?", ("Test Record",))
        if result:
            logger.info(f"✓ Test record retrieved: {result}")
        
        # Clean up
        await connection.execute("DROP TABLE test_table")
        logger.info("✓ Test table dropped")
        
        # Disconnect
        await connection.disconnect()
        logger.info("✓ SQLite connection closed")
        
        # Clean up test file
        import os
        if os.path.exists("./test_orthanc.db"):
            os.remove("./test_orthanc.db")
            logger.info("✓ Test database file cleaned up")
        
    except Exception as e:
        logger.error(f"SQLite test failed: {e}")
        raise


async def test_migration_system():
    """Test migration system functionality"""
    logger.info("Testing migration system...")
    
    # Create test database
    sqlite_config = DatabaseConfig(
        db_type=DatabaseType.SQLITE,
        file_path="./test_migrations.db"
    )
    
    connection = DatabaseManager.create_connection("test_migrations", sqlite_config)
    
    try:
        await connection.connect()
        
        # Initialize migration manager
        migration_manager = MigrationManager("./test_migrations")
        
        # Create sample migrations
        migrations = create_initial_migrations()
        
        # Save migrations
        for migration in migrations:
            migration_manager.save_migration(migration)
        logger.info(f"✓ Saved {len(migrations)} test migrations")
        
        # Load migrations
        migration_manager.load_migrations_from_directory()
        logger.info(f"✓ Loaded {len(migration_manager.migrations)} migrations")
        
        # Test migration ordering
        ordered_migrations = migration_manager.get_ordered_migrations()
        logger.info(f"✓ Migration ordering successful: {[m.version for m in ordered_migrations]}")
        
        await connection.disconnect()
        logger.info("✓ Migration system test completed")
        
    except Exception as e:
        logger.error(f"Migration system test failed: {e}")
        raise
    finally:
        # Clean up
        import shutil
        import os
        if os.path.exists("./test_migrations"):
            shutil.rmtree("./test_migrations")
        if os.path.exists("./test_migrations.db"):
            os.remove("./test_migrations.db")
        logger.info("✓ Migration test files cleaned up")


async def test_dao_operations():
    """Test DAO operations"""
    logger.info("Testing DAO operations...")
    
    # Create test database
    sqlite_config = DatabaseConfig(
        db_type=DatabaseType.SQLITE,
        file_path="./test_dao.db"
    )
    
    connection = DatabaseManager.create_connection("test_dao", sqlite_config)
    
    try:
        await connection.connect()
        
        # Initialize basic table for testing
        await connection.execute("""
            CREATE TABLE referring_doctors (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                hpcsa_number TEXT UNIQUE,
                email TEXT,
                specialization TEXT,
                province TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,
                last_access TEXT
            )
        """)
        
        # Test DAO operations
        doctor_dao = DAOFactory.get_referring_doctor_dao("test_dao")
        
        # Test create
        doctor_data = {
            'name': 'Dr. Test Doctor',
            'hpcsa_number': 'HP99999',
            'email': 'test@doctor.com',
            'specialization': 'Test Specialty',
            'province': 'Test Province'
        }
        
        create_result = await doctor_dao.create(doctor_data)
        if create_result.success:
            doctor_id = create_result.data['id']
            logger.info(f"✓ Created doctor with ID: {doctor_id}")
        else:
            raise Exception(f"Failed to create doctor: {create_result.error}")
        
        # Test find_by_id
        find_result = await doctor_dao.find_by_id(doctor_id)
        if find_result.success and find_result.data:
            logger.info(f"✓ Found doctor: {find_result.data['name']}")
        else:
            raise Exception("Failed to find doctor by ID")
        
        # Test find_all
        all_result = await doctor_dao.find_all()
        if all_result.success:
            logger.info(f"✓ Found {len(all_result.data)} doctors")
        
        # Test update
        update_result = await doctor_dao.update(doctor_id, {'specialization': 'Updated Specialty'})
        if update_result.success:
            logger.info("✓ Doctor updated successfully")
        
        # Test count
        count_result = await doctor_dao.count()
        if count_result.success:
            logger.info(f"✓ Doctor count: {count_result.data}")
        
        # Test delete
        delete_result = await doctor_dao.delete(doctor_id)
        if delete_result.success:
            logger.info("✓ Doctor deleted successfully")
        
        await connection.disconnect()
        logger.info("✓ DAO operations test completed")
        
    except Exception as e:
        logger.error(f"DAO operations test failed: {e}")
        raise
    finally:
        # Clean up
        import os
        if os.path.exists("./test_dao.db"):
            os.remove("./test_dao.db")
        logger.info("✓ DAO test database cleaned up")


async def test_full_initialization():
    """Test full database initialization process"""
    logger.info("Testing full database initialization...")
    
    # Create test configuration
    test_config = {
        "sqlite_test": {
            "type": "sqlite",
            "file_path": "./test_full_init.db"
        }
    }
    
    # Save test config
    with open("test_config.json", "w") as f:
        json.dump(test_config, f, indent=2)
    
    try:
        # Load configuration
        configs = load_database_config("test_config.json")
        logger.info(f"✓ Loaded {len(configs)} database configurations")
        
        # Create connections
        for name, config in configs.items():
            DatabaseManager.create_connection(name, config)
        logger.info("✓ Database connections created")
        
        # Connect all
        await DatabaseManager.connect_all()
        logger.info("✓ All databases connected")
        
        # Initialize schema
        await DatabaseManager.initialize_schema("sqlite_test")
        logger.info("✓ Database schema initialized")
        
        # Test that tables were created
        connection = DatabaseManager.get_connection("sqlite_test")
        result = await connection.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        
        table_names = [row['name'] for row in result]
        expected_tables = [
            'referring_doctors', 'patient_referrals', 'patient_authorizations',
            'patient_shares', 'orthanc_configs', 'orthanc_server_status',
            'audit_logs', 'notification_queue', 'schema_versions'
        ]
        
        for table in expected_tables:
            if table in table_names:
                logger.info(f"✓ Table '{table}' created successfully")
            else:
                logger.warning(f"⚠ Table '{table}' not found")
        
        # Disconnect all
        await DatabaseManager.disconnect_all()
        logger.info("✓ All databases disconnected")
        
        logger.info("Full initialization test completed successfully!")
        
    except Exception as e:
        logger.error(f"Full initialization test failed: {e}")
        raise
    finally:
        # Clean up
        import os
        if os.path.exists("test_config.json"):
            os.remove("test_config.json")
        if os.path.exists("./test_full_init.db"):
            os.remove("./test_full_init.db")
        logger.info("✓ Full initialization test files cleaned up")


async def run_all_tests():
    """Run all database foundation tests"""
    logger.info("=" * 60)
    logger.info("ORTHANC MANAGEMENT MODULE - DATABASE FOUNDATION TESTS")
    logger.info("=" * 60)
    
    tests = [
        ("Schema Generation", test_schema_generation),
        ("SQLite Connection", test_sqlite_connection),
        ("Migration System", test_migration_system),
        ("DAO Operations", test_dao_operations),
        ("Full Initialization", test_full_initialization),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running test: {test_name}")
        logger.info("-" * 40)
        
        try:
            await test_func()
            logger.info(f"✅ {test_name} - PASSED")
            passed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} - FAILED: {e}")
            failed += 1
    
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total tests: {len(tests)}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    
    if failed == 0:
        logger.info("🎉 ALL TESTS PASSED! Database foundation is ready for use.")
    else:
        logger.error(f"⚠️  {failed} tests failed. Please review the errors above.")
    
    return failed == 0


def print_system_info():
    """Print system information"""
    logger.info("System Information:")
    logger.info(f"Python version: {sys.version}")
    
    # Check database driver availability
    drivers = {
        "SQLite (aiosqlite)": False,
        "MySQL (aiomysql)": False,
        "PostgreSQL (asyncpg)": False,
        "ODBC (aioodbc)": False,
    }
    
    try:
        import aiosqlite
        drivers["SQLite (aiosqlite)"] = True
    except ImportError:
        pass
    
    try:
        import aiomysql
        drivers["MySQL (aiomysql)"] = True
    except ImportError:
        pass
    
    try:
        import asyncpg
        drivers["PostgreSQL (asyncpg)"] = True
    except ImportError:
        pass
    
    try:
        import aioodbc
        drivers["ODBC (aioodbc)"] = True
    except ImportError:
        pass
    
    logger.info("Available database drivers:")
    for driver, available in drivers.items():
        status = "✓" if available else "✗"
        logger.info(f"  {status} {driver}")


if __name__ == "__main__":
    print_system_info()
    
    # Run tests
    success = asyncio.run(run_all_tests())
    
    if success:
        logger.info("\n🚀 Database foundation is ready!")
        logger.info("Next steps:")
        logger.info("1. Configure your database in database_config.json")
        logger.info("2. Run: python init_database.py --config database_config.json")
        logger.info("3. Start using the DAO classes for data operations")
    else:
        logger.error("\n❌ Tests failed. Please fix the issues before proceeding.")
        sys.exit(1)
