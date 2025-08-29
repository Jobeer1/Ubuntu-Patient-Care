"""
Integration tests for Medical Reporting Module
"""

import pytest
import requests_mock
from unittest.mock import patch, MagicMock
from datetime import datetime

from integrations.auth_bridge import AuthenticationBridge, auth_bridge
from integrations.orthanc_client import OrthancClient, orthanc_client
from integrations.nas_client import NASClient, nas_client
from integrations.ris_client import RISClient, ris_client

class TestAuthenticationBridge:
    """Test authentication bridge functionality"""
    
    def test_session_validation_success(self):
        """Test successful session validation"""
        auth = AuthenticationBridge()
        
        with requests_mock.Mocker() as m:
            # Mock successful validation response
            m.get(
                f"{auth.base_url}/api/auth/validate",
                json={
                    'user_id': 'user123',
                    'username': 'doctor1',
                    'roles': ['doctor'],
                    'permissions': ['create_report', 'edit_report']
                }
            )
            
            user_data = auth.validate_session('test_token')
            
            assert user_data is not None
            assert user_data['username'] == 'doctor1'
            assert 'doctor' in user_data['roles']
    
    def test_session_validation_failure(self):
        """Test failed session validation"""
        auth = AuthenticationBridge()
        
        with requests_mock.Mocker() as m:
            # Mock failed validation response
            m.get(
                f"{auth.base_url}/api/auth/validate",
                status_code=401
            )
            
            user_data = auth.validate_session('invalid_token')
            assert user_data is None
    
    def test_permission_checking(self):
        """Test permission checking logic"""
        auth = AuthenticationBridge()
        
        user_data = {
            'user_id': 'user123',
            'roles': ['doctor'],
            'permissions': ['create_report']
        }
        
        # Test direct permission
        assert auth.check_permissions(user_data, 'create_report') == True
        
        # Test role-based permission
        assert auth.check_permissions(user_data, 'voice_dictation') == True
        
        # Test denied permission
        assert auth.check_permissions(user_data, 'admin_access') == False
    
    def test_session_caching(self):
        """Test session caching functionality"""
        auth = AuthenticationBridge()
        
        # Create a session
        user_data = {'user_id': 'user123', 'username': 'doctor1'}
        session_id = auth.create_reporting_session(user_data)
        
        # Retrieve cached session
        cached_user = auth.get_session_user(session_id)
        assert cached_user is not None
        assert cached_user['username'] == 'doctor1'
        
        # Invalidate session
        assert auth.invalidate_session(session_id) == True
        
        # Should not be able to retrieve invalidated session
        cached_user = auth.get_session_user(session_id)
        assert cached_user is None

class TestOrthancClient:
    """Test Orthanc client functionality"""
    
    def test_system_info_retrieval(self):
        """Test getting Orthanc system information"""
        client = OrthancClient()
        
        with requests_mock.Mocker() as m:
            # Mock system info response
            m.get(
                f"{client.base_url}/system",
                json={
                    'Version': '1.12.0',
                    'DatabaseVersion': 6,
                    'StorageAreaPlugin': 'Default'
                }
            )
            
            system_info = client.get_system_info()
            
            assert system_info is not None
            assert system_info['Version'] == '1.12.0'
    
    def test_study_search(self):
        """Test study search functionality"""
        client = OrthancClient()
        
        with requests_mock.Mocker() as m:
            # Mock study search response
            m.post(
                f"{client.base_url}/tools/find",
                json=[
                    {
                        'ID': 'study123',
                        'MainDicomTags': {
                            'StudyDate': '20240115',
                            'StudyDescription': 'CT Chest'
                        },
                        'PatientMainDicomTags': {
                            'PatientID': 'PAT123',
                            'PatientName': 'Test Patient'
                        }
                    }
                ]
            )
            
            studies = client.search_studies({'PatientID': 'PAT123'})
            
            assert len(studies) == 1
            assert studies[0]['ID'] == 'study123'
            assert studies[0]['MainDicomTags']['StudyDescription'] == 'CT Chest'
    
    def test_connectivity_check(self):
        """Test Orthanc connectivity check"""
        client = OrthancClient()
        
        with requests_mock.Mocker() as m:
            # Mock successful system info response
            m.get(
                f"{client.base_url}/system",
                json={'Version': '1.12.0'}
            )
            
            assert client.check_connectivity() == True
            
            # Mock failed response
            m.get(
                f"{client.base_url}/system",
                status_code=500
            )
            
            assert client.check_connectivity() == False

class TestNASClient:
    """Test NAS client functionality"""
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.unlink')
    def test_connectivity_check(self, mock_unlink, mock_write_text, mock_is_dir, mock_exists):
        """Test NAS connectivity check"""
        client = NASClient()
        
        # Mock successful connectivity
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        mock_write_text.return_value = None
        mock_unlink.return_value = None
        
        assert client.check_connectivity() == True
        
        # Mock failed connectivity (mount point doesn't exist)
        mock_exists.return_value = False
        
        assert client.check_connectivity() == False
    
    @patch('pathlib.Path.mkdir')
    @patch('builtins.open')
    @patch('json.dump')
    def test_report_storage(self, mock_json_dump, mock_open, mock_mkdir):
        """Test report storage to NAS"""
        client = NASClient()
        client.backup_enabled = True
        
        report_data = {
            'report_id': 'report123',
            'patient_id': 'PAT123',
            'content': {'findings': 'Normal study'}
        }
        
        # Mock file operations
        mock_mkdir.return_value = None
        mock_open.return_value.__enter__.return_value = MagicMock()
        mock_json_dump.return_value = None
        
        result = client.store_report('report123', report_data)
        assert result == True
    
    def test_storage_stats(self):
        """Test storage statistics retrieval"""
        client = NASClient()
        
        with patch('os.statvfs') as mock_statvfs:
            # Mock disk usage stats
            mock_statvfs.return_value = MagicMock(
                f_frsize=4096,
                f_blocks=1000000,
                f_available=500000
            )
            
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.rglob', return_value=[]):
                    stats = client.get_storage_stats()
                    
                    assert 'total_bytes' in stats
                    assert 'free_bytes' in stats
                    assert 'usage_percent' in stats
                    assert stats['backup_enabled'] == client.backup_enabled

class TestRISClient:
    """Test RIS client functionality"""
    
    def test_patient_info_retrieval(self):
        """Test patient information retrieval"""
        client = RISClient()
        client.enabled = True
        
        with requests_mock.Mocker() as m:
            # Mock patient info response
            m.get(
                f"{client.base_url}/api/patients/PAT123",
                json={
                    'patient_id': 'PAT123',
                    'name': 'Test Patient',
                    'dob': '1980-01-01',
                    'gender': 'M'
                }
            )
            
            patient_info = client.get_patient_info('PAT123')
            
            assert patient_info is not None
            assert patient_info['patient_id'] == 'PAT123'
            assert patient_info['name'] == 'Test Patient'
    
    def test_study_order_retrieval(self):
        """Test study order retrieval"""
        client = RISClient()
        client.enabled = True
        
        with requests_mock.Mocker() as m:
            # Mock study order response
            m.get(
                f"{client.base_url}/api/orders/accession/ACC123",
                json={
                    'accession_number': 'ACC123',
                    'patient_id': 'PAT123',
                    'procedure_code': 'CT_CHEST',
                    'procedure_name': 'CT Chest with Contrast',
                    'referring_physician_id': 'DOC456'
                }
            )
            
            study_order = client.get_study_order('ACC123')
            
            assert study_order is not None
            assert study_order['accession_number'] == 'ACC123'
            assert study_order['procedure_code'] == 'CT_CHEST'
    
    def test_report_submission(self):
        """Test report submission to RIS"""
        client = RISClient()
        client.enabled = True
        
        with requests_mock.Mocker() as m:
            # Mock successful report submission
            m.post(
                f"{client.base_url}/api/reports",
                status_code=201
            )
            
            report_data = {
                'content': {
                    'findings': 'Normal chest CT',
                    'impression': 'No acute findings',
                    'recommendations': 'Routine follow-up'
                },
                'doctor_id': 'DOC123',
                'status': 'final'
            }
            
            result = client.submit_report('ACC123', report_data)
            assert result == True
    
    def test_disabled_ris(self):
        """Test behavior when RIS is disabled"""
        client = RISClient()
        client.enabled = False
        
        # All operations should return success/empty when disabled
        assert client.check_connectivity() == False
        assert client.get_patient_info('PAT123') is None
        assert client.get_study_order('ACC123') is None
        assert client.submit_report('ACC123', {}) == True  # Should succeed when disabled

class TestIntegrationWorkflow:
    """Test complete integration workflow"""
    
    def test_complete_reporting_workflow(self):
        """Test complete workflow from authentication to report submission"""
        # This would test the complete workflow:
        # 1. Authenticate user
        # 2. Get study from Orthanc
        # 3. Get patient info from RIS
        # 4. Create report
        # 5. Store to NAS
        # 6. Submit to RIS
        
        # Mock all external services
        with requests_mock.Mocker() as m:
            # Mock authentication
            m.get(
                "http://localhost:5000/api/auth/validate",
                json={'user_id': 'user123', 'username': 'doctor1', 'roles': ['doctor']}
            )
            
            # Mock Orthanc study retrieval
            m.get(
                "http://localhost:8042/studies/study123",
                json={
                    'ID': 'study123',
                    'MainDicomTags': {'StudyDescription': 'CT Chest'},
                    'PatientMainDicomTags': {'PatientID': 'PAT123'}
                }
            )
            
            # Mock RIS patient info
            m.get(
                "/api/patients/PAT123",
                json={'patient_id': 'PAT123', 'name': 'Test Patient'}
            )
            
            # Mock RIS report submission
            m.post("/api/reports", status_code=201)
            
            # Test the workflow
            user_data = auth_bridge.validate_session('test_token')
            assert user_data is not None
            
            study_data = orthanc_client.get_study_details('study123')
            assert study_data is not None
            
            # In a real workflow, we would create a report, store it, and submit it
            # This is just testing that the integration components work together

def run_integration_tests():
    """Run all integration tests"""
    pytest.main([__file__, "-v"])

if __name__ == "__main__":
    run_integration_tests()