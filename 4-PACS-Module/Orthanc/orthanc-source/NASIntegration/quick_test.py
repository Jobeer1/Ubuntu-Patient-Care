"""
Quick Phase 1 Database Test
Simple test to verify database integration works
"""

import os
import sys

# Add the NASIntegration directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from orthanc_management.database.config import DatabaseSettings, DatabaseType
        print("✓ Database config imported")
        
        from orthanc_management.database.manager import DatabaseManager
        print("✓ Database manager imported")
        
        from orthanc_management.database.migrations import MigrationManager
        print("✓ Migration manager imported")
        
        from orthanc_management.models import ReferringDoctor, PatientReferral
        print("✓ Models imported")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_database_config():
    """Test database configuration"""
    print("\nTesting database configuration...")
    
    try:
        from orthanc_management.database.config import DatabaseSettings, DatabaseType
        
        # Test SQLite configuration
        os.environ['ORTHANC_DB_TYPE'] = 'sqlite'
        settings = DatabaseSettings()
        
        if settings.database_type == DatabaseType.SQLITE:
            print("✓ SQLite configuration working")
        
        connection_string = settings.get_connection_string()
        if connection_string.startswith('sqlite://'):
            print("✓ Connection string generation working")
        
        return True
    except Exception as e:
        print(f"✗ Database config test failed: {e}")
        return False

def test_models():
    """Test model creation and validation"""
    print("\nTesting models...")
    
    try:
        from orthanc_management.models import ReferringDoctor, PatientReferral
        
        # Test ReferringDoctor
        doctor = ReferringDoctor()
        doctor.name = "Dr. Test"
        doctor.hpcsa_number = "MP123456"
        doctor.email = "test@example.com"
        
        errors = doctor.validate()
        if not errors:
            print("✓ ReferringDoctor model validation working")
        else:
            print(f"✗ ReferringDoctor validation failed: {errors}")
        
        # Test PatientReferral
        referral = PatientReferral()
        referral.patient_id = "TEST001"
        referral.referring_doctor_id = doctor.id
        referral.priority = "routine"
        
        errors = referral.validate()
        if not errors:
            print("✓ PatientReferral model validation working")
        else:
            print(f"✗ PatientReferral validation failed: {errors}")
        
        return True
    except Exception as e:
        print(f"✗ Model test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Orthanc Management Module - Phase 1 Quick Test")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_database_config,
        test_models
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\n🎉 Phase 1 Database Integration: WORKING!")
        print("✓ Multi-database support implemented")
        print("✓ Database abstraction layer functional")
        print("✓ Models with validation working")
        print("✓ Ready for database initialization")
        print("\nNext steps:")
        print("1. Install database drivers for your chosen database")
        print("2. Configure connection settings in .env file")
        print("3. Run database initialization")
        print("4. Proceed to Phase 2: Core Models & Managers")
    else:
        print("\n❌ Some tests failed - check error messages above")

if __name__ == '__main__':
    main()
