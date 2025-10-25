"""
Unit Tests for PACS Connector
Tests database connectivity and query methods
"""
import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.pacs_connector import PACSConnector

# PACS database path
PACS_DB_PATH = "../../../4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/orthanc-index/pacs_metadata.db"

class TestPACSConnector(unittest.TestCase):
    """Test cases for PACS Connector"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.connector = PACSConnector(PACS_DB_PATH)
    
    def test_01_database_connection(self):
        """Test database connection"""
        conn = self.connector.get_connection()
        self.assertIsNotNone(conn)
        conn.close()
        print("✅ Database connection successful")
    
    def test_02_get_database_stats(self):
        """Test database statistics"""
        stats = self.connector.get_database_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('total_patients', stats)
        self.assertIn('total_studies', stats)
        self.assertGreater(stats['total_patients'], 0)
        print(f"✅ Database stats: {stats['total_patients']} patients, {stats['total_studies']} studies")
    
    def test_03_get_patient_list(self):
        """Test getting patient list"""
        patients, total = self.connector.get_patient_list(offset=0, limit=10)
        self.assertIsInstance(patients, list)
        self.assertGreater(total, 0)
        if patients:
            patient = patients[0]
            self.assertIn('patient_id', patient)
            self.assertIn('patient_name', patient)
            print(f"✅ Patient list: {len(patients)} patients retrieved (total: {total})")
    
    def test_04_get_patient_info(self):
        """Test getting patient information"""
        # Get a patient ID from the list
        patients, _ = self.connector.get_patient_list(offset=0, limit=1)
        if patients:
            patient_id = patients[0]['patient_id']
            info = self.connector.get_patient_info(patient_id)
            self.assertIsNotNone(info)
            self.assertEqual(info['patient_id'], patient_id)
            self.assertIn('study_count', info)
            print(f"✅ Patient info retrieved: {patient_id} ({info['study_count']} studies)")
        else:
            self.skipTest("No patients in database")
    
    def test_05_get_patient_studies(self):
        """Test getting patient studies"""
        # Get a patient ID from the list
        patients, _ = self.connector.get_patient_list(offset=0, limit=1)
        if patients:
            patient_id = patients[0]['patient_id']
            studies = self.connector.get_patient_studies(patient_id)
            self.assertIsInstance(studies, list)
            if studies:
                study = studies[0]
                self.assertIn('study_date', study)
                self.assertIn('modality', study)
                print(f"✅ Patient studies retrieved: {len(studies)} studies for {patient_id}")
        else:
            self.skipTest("No patients in database")
    
    def test_06_verify_patient_exists(self):
        """Test patient existence verification"""
        # Test with existing patient
        patients, _ = self.connector.get_patient_list(offset=0, limit=1)
        if patients:
            patient_id = patients[0]['patient_id']
            exists = self.connector.verify_patient_exists(patient_id)
            self.assertTrue(exists)
            print(f"✅ Patient exists: {patient_id}")
        
        # Test with non-existing patient
        exists = self.connector.verify_patient_exists("NONEXISTENT-ID-12345")
        self.assertFalse(exists)
        print("✅ Non-existent patient correctly identified")
    
    def test_07_search_patients(self):
        """Test patient search"""
        # Get a patient name to search for
        patients, _ = self.connector.get_patient_list(offset=0, limit=1)
        if patients and patients[0]['patient_name']:
            # Search by first few characters of name
            search_term = patients[0]['patient_name'][:3]
            results = self.connector.search_patients(search_term)
            self.assertIsInstance(results, list)
            print(f"✅ Search results: {len(results)} patients found for '{search_term}'")
        else:
            self.skipTest("No patients with names in database")
    
    def test_08_get_study_details(self):
        """Test getting study details"""
        # Get a study UID
        patients, _ = self.connector.get_patient_list(offset=0, limit=1)
        if patients:
            patient_id = patients[0]['patient_id']
            studies = self.connector.get_patient_studies(patient_id)
            if studies:
                # Get study UID from studies table
                conn = self.connector.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT study_instance_uid FROM studies LIMIT 1")
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    study_uid = row[0]
                    details = self.connector.get_study_details(study_uid)
                    if details:
                        self.assertIn('study_instance_uid', details)
                        print(f"✅ Study details retrieved: {study_uid}")
                    else:
                        print("⚠️  Study details not found (may be expected)")
        else:
            self.skipTest("No studies in database")

def run_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("PACS Connector Unit Tests")
    print("=" * 60 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPACSConnector)
    
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
