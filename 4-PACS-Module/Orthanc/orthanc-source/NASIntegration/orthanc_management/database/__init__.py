"""
Orthanc Management Module - Database Initialization
Sets up the database with multi-backend support and runs initial migrations
"""

import os
import sys
import logging
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from .config import DatabaseSettings, DatabaseType
from .manager import DatabaseManager
from .migrations import MigrationManager, create_initial_migrations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Handles complete database initialization for Orthanc Management Module"""
    
    def __init__(self, db_settings: Optional[DatabaseSettings] = None):
        self.db_settings = db_settings or DatabaseSettings()
        self.db_manager = DatabaseManager(self.db_settings)
        self.migration_manager = None
    
    def check_requirements(self) -> bool:
        """Check if required packages are installed for the database type"""
        try:
            from .config import DatabaseConfig
            db_config = DatabaseConfig()
            required_packages = db_config.get_required_packages(self.db_settings.database_type)
            
            missing_packages = []
            
            for package in required_packages:
                try:
                    if package == 'PyMySQL':
                        import pymysql
                    elif package == 'psycopg2-binary':
                        import psycopg2
                    elif package == 'fdb':
                        import fdb
                    elif package == 'pyodbc':
                        import pyodbc
                    elif package == 'cx_Oracle':
                        import cx_Oracle
                    elif package == 'SQLAlchemy':
                        import sqlalchemy
                except ImportError:
                    missing_packages.append(package)
            
            if missing_packages:
                logger.error(f"Missing required packages for {self.db_settings.database_type.value}: {missing_packages}")
                logger.info("Please install missing packages:")
                for package in missing_packages:
                    logger.info(f"  pip install {package}")
                return False
            
            logger.info(f"All required packages for {self.db_settings.database_type.value} are installed")
            return True
            
        except Exception as e:
            logger.error(f"Error checking requirements: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            logger.info(f"Testing connection to {self.db_settings.database_type.value} database...")
            
            if self.db_manager.initialize():
                logger.info("Database connection successful")
                return True
            else:
                logger.error("Database connection failed")
                return False
                
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def initialize_database(self) -> bool:
        """Complete database initialization"""
        try:
            logger.info("Starting database initialization...")
            
            # Step 1: Check requirements
            if not self.check_requirements():
                return False
            
            # Step 2: Test connection
            if not self.test_connection():
                return False
            
            # Step 3: Initialize migration manager
            self.migration_manager = MigrationManager(self.db_manager)
            
            # Step 4: Create initial migrations if they don't exist
            if len(self.migration_manager.migrations) == 0:
                logger.info("Creating initial migrations...")
                create_initial_migrations(self.migration_manager)
            
            # Step 5: Run migrations
            logger.info("Running database migrations...")
            if not self.migration_manager.migrate():
                logger.error("Migration failed")
                return False
            
            # Step 6: Verify database structure
            if not self.verify_database():
                logger.error("Database verification failed")
                return False
            
            logger.info("Database initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    def verify_database(self) -> bool:
        """Verify database structure and health"""
        try:
            logger.info("Verifying database structure...")
            
            # Check that all required tables exist
            required_tables = [
                'referring_doctors',
                'patient_referrals', 
                'patient_authorizations',
                'patient_shares',
                'orthanc_configs',
                'audit_logs',
                'schema_migrations'
            ]
            
            health = self.db_manager.health_check()
            
            if health['status'] != 'healthy':
                logger.error(f"Database health check failed: {health}")
                return False
            
            # Verify table counts
            stats = self.db_manager.get_database_stats()
            
            for table_name in required_tables:
                if table_name not in stats.get('tables', {}):
                    logger.error(f"Required table {table_name} not found")
                    return False
                elif 'error' in stats['tables'][table_name]:
                    logger.error(f"Error accessing table {table_name}: {stats['tables'][table_name]['error']}")
                    return False
            
            logger.info("Database verification completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database verification failed: {e}")
            return False
    
    def create_sample_data(self) -> bool:
        """Create sample data for testing"""
        try:
            logger.info("Creating sample data...")
            
            with self.db_manager.get_session() as session:
                from sqlalchemy import text
                
                # Create sample referring doctor
                session.execute(text("""
                    INSERT OR IGNORE INTO referring_doctors 
                    (id, name, hpcsa_number, email, practice_name, specialization, facility_type, province, access_level, is_active)
                    VALUES 
                    ('sample-doctor-1', 'Dr. Sample Physician', 'MP123456', 'sample.doctor@example.com', 
                     'Sample Medical Practice', 'Radiology', 'private_practice', 'Gauteng', 'full_access', 1)
                """))
                
                # Create sample Orthanc configuration
                sample_config = {
                    "Name": "Orthanc Management Test",
                    "HttpPort": 8042,
                    "DicomPort": 4242,
                    "RemoteAccessAllowed": True,
                    "AuthenticationEnabled": True
                }
                
                import json
                session.execute(text("""
                    INSERT OR IGNORE INTO orthanc_configs 
                    (id, config_name, config_data, description, is_default, created_by)
                    VALUES 
                    ('sample-config-1', 'Default Configuration', :config_data, 
                     'Default Orthanc configuration for testing', 1, 'system')
                """), {'config_data': json.dumps(sample_config)})
                
                logger.info("Sample data created successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create sample data: {e}")
            return False
    
    def reset_database(self) -> bool:
        """Reset database (drop all tables and recreate)"""
        try:
            logger.warning("Resetting database - all data will be lost!")
            
            # Drop all tables
            if self.migration_manager:
                # Rollback all migrations
                applied = self.migration_manager.get_applied_migrations()
                if applied:
                    first_version = applied[0]
                    # Create a version before the first to rollback everything
                    target_version = "00000000000000"
                    self.migration_manager.rollback(target_version)
            
            # Reinitialize
            return self.initialize_database()
            
        except Exception as e:
            logger.error(f"Database reset failed: {e}")
            return False
    
    def get_status(self) -> dict:
        """Get current database status"""
        try:
            status = {
                'database_type': self.db_settings.database_type.value,
                'connection_string': self.db_settings.get_connection_string().split('@')[0] + '@***',
                'initialized': False,
                'health': {},
                'migrations': {},
                'stats': {}
            }
            
            # Test initialization
            if self.db_manager.initialize():
                status['initialized'] = True
                
                # Get health status
                status['health'] = self.db_manager.health_check()
                
                # Get migration status
                if not self.migration_manager:
                    self.migration_manager = MigrationManager(self.db_manager)
                status['migrations'] = self.migration_manager.get_migration_status()
                
                # Get database stats
                status['stats'] = self.db_manager.get_database_stats()
            
            return status
            
        except Exception as e:
            return {'error': str(e)}


def main():
    """Main initialization function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Orthanc Management Database Initialization')
    parser.add_argument('--reset', action='store_true', help='Reset database (drop all tables)')
    parser.add_argument('--sample-data', action='store_true', help='Create sample data')
    parser.add_argument('--status', action='store_true', help='Show database status')
    parser.add_argument('--db-type', choices=[dt.value for dt in DatabaseType], 
                       help='Database type to use')
    
    args = parser.parse_args()
    
    # Set database type if specified
    if args.db_type:
        os.environ['ORTHANC_DB_TYPE'] = args.db_type
    
    # Create initializer
    initializer = DatabaseInitializer()
    
    try:
        if args.status:
            # Show status
            status = initializer.get_status()
            print("\nDatabase Status:")
            print(f"Type: {status.get('database_type', 'Unknown')}")
            print(f"Initialized: {status.get('initialized', False)}")
            
            if 'health' in status:
                health = status['health']
                print(f"Health: {health.get('status', 'Unknown')}")
                if health.get('errors'):
                    print(f"Errors: {health['errors']}")
            
            if 'migrations' in status:
                migrations = status['migrations']
                print(f"Migrations: {migrations.get('applied_count', 0)}/{migrations.get('total_migrations', 0)} applied")
                if migrations.get('pending_count', 0) > 0:
                    print(f"Pending migrations: {migrations['pending_count']}")
            
            if 'stats' in status and 'tables' in status['stats']:
                print("\nTable counts:")
                for table, info in status['stats']['tables'].items():
                    count = info.get('count', 'Error')
                    print(f"  {table}: {count}")
        
        elif args.reset:
            # Reset database
            if initializer.reset_database():
                print("Database reset successfully")
                if args.sample_data:
                    initializer.create_sample_data()
                    print("Sample data created")
            else:
                print("Database reset failed")
                sys.exit(1)
        
        else:
            # Normal initialization
            if initializer.initialize_database():
                print("Database initialized successfully")
                if args.sample_data:
                    initializer.create_sample_data()
                    print("Sample data created")
            else:
                print("Database initialization failed")
                sys.exit(1)
    
    except Exception as e:
        logger.error(f"Initialization script failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
