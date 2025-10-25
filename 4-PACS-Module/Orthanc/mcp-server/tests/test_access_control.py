"""
Unit Tests for Access Control Service
Tests role-based access control logic
"""
import unittest
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.pacs_connector import PACSConnector
from app.services.access_control import AccessControlService

# Database paths
PACS_DB_PATH = "../../../4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/orthanc-index/pacs_metadata.db"
MCP_DB_PATH = str(Path(__file__).parent.parent / "mcp_server.db")

class TestAccessControlService(unittest.TestCase):
    """Test cases for Access Control Service"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        # Initialize PACS connector
        cls.pacs_connector = PACSConnector(PACS_DB_PATH)
        
        # Connect to MCP database
        cls.mcp_db = sqlite3.connect(MCP_DB_PATH)
        cls.mcp_db.row_factory = sqlite3.Row
        
        # Initialize access control service
        cls.access_control = AccessControlService(cls.pacs_connector, cls.mcp_db)
        
        # Get a real patient ID for testing
        patients, _ = cls.pacs_connector.get_patient_list(limit=1)
        cls.test_patient_id = patients[0]['patient_id'] if patients else None
        
        # Create test data
        cls._create_test_data()
    
    @classmethod
    def _create_test_data(cls):
        """Create test data in MCP database"""
        cursor = cls.mcp_db.cursor()
        
        # Create test users if they don't exist
        test_users = [
            (100, 'test_admin@test.com', 'Test Admin', 'Admin'),
            (101, 'test_doctor@test.com', 'Test Doctor', 'Referring Doctor'),
            (102, 'test_patient@test.com', 'Test Patient', 'Patient'),
            (103, 'test_radiologist@test.com', 'Test Radiologist', 'Radiologist'),
        ]
        
        for user_id, email, name, role in test_users:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO users (id, email, name, role)
                    VALUES (?, ?, ?, ?)
                """, (user_id, email, name, role))
            except:
                pass  # User might already exist
        
        # Create test patient relationship (patient self-access)
        if cls.test_patient_id:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO patient_relationships 
                    (user_id, patient_identifier, relationship_type, created_by, is_active)
                    VALUES (?, ?, 'self', 100, 1)
                """, (102, cls.test_patient_id))
            except:
                pass
            
            # Create test doctor assignment
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO doctor_patient_assignments 
                    (doctor_user_id, patient_identifier, assigned_by, is_active)
                    VALUES (?, ?, 100, 1)
                """, (101, cls.test_patient_id))
            except:
                pass
        
        cls.mcp_db.commit()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures"""
        # Clean up test data
        try:
            cursor = cls.mcp_db.cursor()
            cursor.execute("DELETE FROM patient_relationships WHERE user_id IN (100, 101, 102, 103)")
            cursor.execute("DELETE FROM doctor_patient_assignments WHERE doctor_user_id IN (100, 101, 102, 103)")
            cursor.execute("DELETE FROM family_access WHERE parent_user_id IN (100, 101, 102, 103)")
            cls.mcp_db.commit()
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
        finally:
            cls.mcp_db.close()
    
    def test_01_admin_full_access(self):
        """Test admin has access to all patients"""
        accessible = self.access_control.get_accessible_patients(100, 'Admin')
        self.assertIn('*', accessible)
        print("✅ Admin has full access (wildcard)")
    
    def test_02_radiologist_full_access(self):
        """Test radiologist has access to all patients"""
        accessible = self.access_control.get_accessible_patients(103, 'Radiologist')
        self.assertIn('*', accessible)
        print("✅ Radiologist has full access (wildcard)")
    
    def test_03_doctor_assigned_patients(self):
        """Test doctor can access assigned patients"""
        if not self.test_patient_id:
            self.skipTest("No test patient available")
        
        accessible = self.access_control.get_accessible_patients(101, 'Referring Doctor')
        self.assertIsInstance(accessible, list)
        self.assertIn(self.test_patient_id, accessible)
        print(f"✅ Doctor has access to {len(accessible)} assigned patient(s)")
    
    def test_04_patient_self_access(self):
        """Test patient can access own records"""
        if not self.test_patient_id:
            self.skipTest("No test patient available")
        
        accessible = self.access_control.get_accessible_patients(102, 'Patient')
        self.assertIsInstance(accessible, list)
        self.assertIn(self.test_patient_id, accessible)
        print(f"✅ Patient has access to {len(accessible)} patient record(s)")
    
    def test_05_can_access_patient_admin(self):
        """Test admin can access any patient"""
        if not self.test_patient_id:
            self.skipTest("No test patient available")
        
        can_access = self.access_control.can_access_patient(100, 'Admin', self.test_patient_id)
        self.assertTrue(can_access)
        print(f"✅ Admin can access patient {self.test_patient_id}")
    
    def test_06_can_access_patient_doctor(self):
        """Test doctor can access assigned patient"""
        if not self.test_patient_id:
            self.skipTest("No test patient available")
        
        can_access = self.access_control.can_access_patient(101, 'Referring Doctor', self.test_patient_id)
        self.assertTrue(can_access)
        print(f"✅ Doctor can access assigned patient {self.test_patient_id}")
    
    def test_07_cannot_access_unassigned_patient(self):
        """Test doctor cannot access unassigned patient"""
        # Use a different patient ID
        can_access = self.access_control.can_access_patient(101, 'Referring Doctor', 'NONEXISTENT-PATIENT')
        self.assertFalse(can_access)
        print("✅ Doctor cannot access unassigned patient")
    
    def test_08_get_user_studies_admin(self):
        """Test getting studies for admin"""
        studies = self.access_control.get_user_studies(100, 'Admin', limit=10)
        self.assertIsInstance(studies, list)
        print(f"✅ Admin can retrieve {len(studies)} studies")
    
    def test_09_get_user_studies_doctor(self):
        """Test getting studies for doctor"""
        studies = self.access_control.get_user_studies(101, 'Referring Doctor', limit=10)
        self.assertIsInstance(studies, list)
        print(f"✅ Doctor can retrieve {len(studies)} studies from assigned patients")
    
    def test_10_get_accessible_patient_count(self):
        """Test getting accessible patient count"""
        # Admin should have access to all
        count = self.access_control.get_accessible_patient_count(100, 'Admin')
        self.assertGreater(count, 0)
        print(f"✅ Admin has access to {count} patients")
        
        # Doctor should have limited access
        count = self.access_control.get_accessible_patient_count(101, 'Referring Doctor')
        self.assertGreaterEqual(count, 0)
        print(f"✅ Doctor has access to {count} patients")
    
    def test_11_log_access_attempt(self):
        """Test access logging"""
        if not self.test_patient_id:
            self.skipTest("No test patient available")
        
        # Log successful access
        self.access_control.log_access_attempt(
            user_id=100,
            patient_id=self.test_patient_id,
            access_type='view',
            granted=True,
            ip_address='127.0.0.1',
            user_agent='Test Browser'
        )
        
        # Verify log entry
        try:
            cursor = self.mcp_db.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM access_audit_log 
                WHERE user_id = 100 AND patient_identifier = ?
            """, (self.test_patient_id,))
            count = cursor.fetchone()[0]
            self.assertGreater(count, 0)
            print(f"✅ Access attempt logged successfully ({count} entries)")
        except sqlite3.OperationalError as e:
            self.skipTest(f"Audit log table not available: {e}")
    
    def test_12_get_access_summary(self):
        """Test getting access summary"""
        # Admin summary
        summary = self.access_control.get_access_summary(100, 'Admin')
        self.assertIsInstance(summary, dict)
        self.assertTrue(summary['has_full_access'])
        print(f"✅ Admin summary: {summary['accessible_patient_count']} patients")
        
        # Doctor summary
        summary = self.access_control.get_access_summary(101, 'Referring Doctor')
        self.assertIsInstance(summary, dict)
        self.assertFalse(summary['has_full_access'])
        self.assertIn('assigned_patients', summary)
        print(f"✅ Doctor summary: {summary['accessible_patient_count']} patients")
        
        # Patient summary
        summary = self.access_control.get_access_summary(102, 'Patient')
        self.assertIsInstance(summary, dict)
        self.assertIn('self_access', summary)
        self.assertIn('family_access', summary)
        print(f"✅ Patient summary: {summary['accessible_patient_count']} patients")

def run_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Access Control Service Unit Tests")
    print("=" * 60 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAccessControlService)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All tests passed!")
    else:
        print(f"❌ {len(result.failures)} test(s) failed")
        print(f"❌ {len(result.errors)} test(s) had errors")
    print("=" * 60)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
