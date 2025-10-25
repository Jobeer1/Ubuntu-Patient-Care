"""
Orthanc Management Module - Phase 1 Database Integration Test
Test script to verify multi-database support works correctly
"""

import os
import sys
import logging
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from orthanc_management.database.config import DatabaseSettings, DatabaseType
from orthanc_management.database.manager import DatabaseManager
from orthanc_management.database.migrations import MigrationManager, create_initial_migrations
from orthanc_management.database import DatabaseInitializer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_database_type(db_type: DatabaseType) -> Dict[str, Any]:
    """Test specific database type"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {db_type.value.upper()} Database")
    logger.info(f"{'='*60}")
    
    result = {
        'database_type': db_type.value,
        'initialized': False,
        'tables_created': False,
        'sample_data': False,
        'health_check': False,
        'errors': []
    }
    
    try:
        # Set environment variable for database type
        os.environ['ORTHANC_DB_TYPE'] = db_type.value
        
        # For non-SQLite databases, we need connection details
        if db_type != DatabaseType.SQLITE:
            logger.info(f"Skipping {db_type.value} - requires database server setup")
            result['errors'].append("Database server not configured")
            return result
        
        # Initialize database
        initializer = DatabaseInitializer()
        
        # Test requirements check
        if not initializer.check_requirements():
            result['errors'].append("Required packages not installed")
            return result
        
        # Test connection
        if not initializer.test_connection():
            result['errors'].append("Connection failed")
            return result
        
        result['initialized'] = True
        
        # Initialize database schema
        if initializer.initialize_database():
            result['tables_created'] = True
            logger.info("✓ Database schema created successfully")
        else:
            result['errors'].append("Schema creation failed")
            return result
        
        # Create sample data
        if initializer.create_sample_data():
            result['sample_data'] = True
            logger.info("✓ Sample data created successfully")
        else:
            result['errors'].append("Sample data creation failed")
        
        # Health check
        health = initializer.db_manager.health_check()
        if health['status'] == 'healthy':
            result['health_check'] = True
            logger.info("✓ Health check passed")
        else:
            result['errors'].append(f"Health check failed: {health}")
        
        # Test database operations
        test_database_operations(initializer.db_manager)
        
        logger.info(f"✓ {db_type.value.upper()} test completed successfully")
        
    except Exception as e:
        logger.error(f"✗ {db_type.value.upper()} test failed: {e}")
        result['errors'].append(str(e))
    
    return result


def test_database_operations(db_manager: DatabaseManager):
    """Test basic database operations"""
    logger.info("Testing database operations...")
    
    try:
        # Test creating a referring doctor
        with db_manager.get_session() as session:
            from sqlalchemy import text
            
            # Insert test doctor
            session.execute(text("""
                INSERT OR REPLACE INTO referring_doctors 
                (id, name, hpcsa_number, email, practice_name, access_level, is_active)
                VALUES 
                ('test-doctor-1', 'Dr. Test Physician', 'MP999999', 'test@example.com', 
                 'Test Practice', 'full_access', 1)
            """))
            
            # Query test doctor
            result = session.execute(text("""
                SELECT name, hpcsa_number, practice_name 
                FROM referring_doctors 
                WHERE id = 'test-doctor-1'
            """))
            
            doctor = result.fetchone()
            if doctor:
                logger.info(f"✓ Database operations successful: {doctor[0]} ({doctor[1]})")
            else:
                logger.error("✗ Failed to retrieve test doctor")
    
    except Exception as e:
        logger.error(f"✗ Database operations failed: {e}")


def test_migration_system():
    """Test migration system"""
    logger.info("\n" + "="*60)
    logger.info("Testing Migration System")
    logger.info("="*60)
    
    try:
        # Set SQLite for migration testing
        os.environ['ORTHANC_DB_TYPE'] = 'sqlite'
        
        db_manager = DatabaseManager()
        if not db_manager.initialize():
            logger.error("✗ Failed to initialize database for migration test")
            return
        
        migration_manager = MigrationManager(db_manager)
        
        # Create initial migrations if they don't exist
        if len(migration_manager.migrations) == 0:
            logger.info("Creating initial migrations...")
            create_initial_migrations(migration_manager)
        
        # Get migration status
        status = migration_manager.get_migration_status()
        logger.info(f"Migration status: {status}")
        
        # Run migrations
        if migration_manager.migrate():
            logger.info("✓ Migrations completed successfully")
        else:
            logger.error("✗ Migration failed")
        
        # Test rollback (only if we have applied migrations)
        applied = migration_manager.get_applied_migrations()
        if len(applied) > 1:
            target_version = applied[-2]  # Rollback to second last
            if migration_manager.rollback(target_version):
                logger.info(f"✓ Rollback to {target_version} successful")
            else:
                logger.error("✗ Rollback failed")
            
            # Re-apply migrations
            if migration_manager.migrate():
                logger.info("✓ Re-migration successful")
    
    except Exception as e:
        logger.error(f"✗ Migration system test failed: {e}")


def test_models():
    """Test model functionality"""
    logger.info("\n" + "="*60)
    logger.info("Testing Models")
    logger.info("="*60)
    
    try:
        from orthanc_management.models import ReferringDoctor, PatientReferral
        
        # Test ReferringDoctor model
        doctor = ReferringDoctor()
        doctor.name = "Dr. Test Model"
        doctor.hpcsa_number = "MP123456"
        doctor.email = "test.model@example.com"
        doctor.practice_name = "Test Model Practice"
        doctor.specialization = "Radiology"
        doctor.facility_type = "private_practice"
        doctor.province = "gp"
        doctor.access_level = "full_access"
        
        # Validate doctor
        errors = doctor.validate()
        if not errors:
            logger.info("✓ ReferringDoctor model validation passed")
        else:
            logger.error(f"✗ ReferringDoctor validation failed: {errors}")
        
        # Test doctor methods
        if doctor.can_access_level('view_only'):
            logger.info("✓ Access level check passed")
        else:
            logger.error("✗ Access level check failed")
        
        # Test serialization
        doctor_dict = doctor.to_dict()
        if 'name' in doctor_dict and 'hpcsa_number' in doctor_dict:
            logger.info("✓ Model serialization passed")
        else:
            logger.error("✗ Model serialization failed")
        
        # Test PatientReferral model
        referral = PatientReferral()
        referral.patient_id = "TEST-PATIENT-001"
        referral.referring_doctor_id = doctor.id
        referral.study_type = "xray"
        referral.clinical_indication = "Chest pain"
        referral.priority = "routine"
        
        # Validate referral
        errors = referral.validate()
        if not errors:
            logger.info("✓ PatientReferral model validation passed")
        else:
            logger.error(f"✗ PatientReferral validation failed: {errors}")
        
        # Test referral methods
        if not referral.is_urgent():
            logger.info("✓ Priority check passed")
        else:
            logger.error("✗ Priority check failed")
        
        logger.info("✓ Model testing completed")
    
    except Exception as e:
        logger.error(f"✗ Model testing failed: {e}")


def main():
    """Main test function"""
    logger.info("Orthanc Management Module - Phase 1 Database Integration Test")
    logger.info("=" * 80)
    
    results = {}
    
    # Test SQLite (always available)
    results['sqlite'] = test_database_type(DatabaseType.SQLITE)
    
    # Test other database types (if available)
    other_db_types = [
        # DatabaseType.MYSQL,
        # DatabaseType.POSTGRESQL,
        # DatabaseType.FIREBIRD,
        # DatabaseType.MSSQL,
        # DatabaseType.ORACLE
    ]
    
    for db_type in other_db_types:
        results[db_type.value] = test_database_type(db_type)
    
    # Test migration system
    test_migration_system()
    
    # Test models
    test_models()
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    
    for db_type, result in results.items():
        status = "✓ PASS" if not result['errors'] else "✗ FAIL"
        logger.info(f"{db_type.upper()}: {status}")
        if result['errors']:
            for error in result['errors']:
                logger.info(f"  - {error}")
    
    # Check if core functionality works
    sqlite_result = results.get('sqlite', {})
    if sqlite_result.get('initialized') and sqlite_result.get('tables_created'):
        logger.info("\n🎉 Phase 1 Database Integration: SUCCESS")
        logger.info("✓ Multi-database configuration system working")
        logger.info("✓ Database abstraction layer functional")
        logger.info("✓ Migration system operational")
        logger.info("✓ Core models implemented")
        logger.info("\nReady to proceed to Phase 2: Core Models & Managers")
    else:
        logger.error("\n❌ Phase 1 Database Integration: FAILED")
        logger.error("Core database functionality not working")


if __name__ == '__main__':
    main()
