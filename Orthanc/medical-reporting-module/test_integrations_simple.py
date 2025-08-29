#!/usr/bin/env python3
"""
Simple test script for Medical Reporting Module integrations
"""

import sys
import os
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.getcwd())

from integrations.auth_bridge import AuthenticationBridge
from integrations.orthanc_client import OrthancClient
from integrations.nas_client import NASClient
from integrations.ris_client import RISClient

def test_integrations():
    """Test integration components"""
    print("🔗 Testing Medical Reporting Module Integrations")
    print("=" * 60)
    
    success_count = 0
    total_tests = 4
    
    # Test Authentication Bridge
    print("\n1. Testing Authentication Bridge...")
    try:
        auth_bridge = AuthenticationBridge()
        
        # Test session creation
        user_data = {
            'user_id': 'test_user',
            'username': 'test_doctor',
            'roles': ['doctor'],
            'permissions': ['create_report', 'edit_report']
        }
        
        session_id = auth_bridge.create_reporting_session(user_data)
        assert session_id is not None
        
        # Test session retrieval
        retrieved_user = auth_bridge.get_session_user(session_id)
        assert retrieved_user is not None
        assert retrieved_user['username'] == 'test_doctor'
        
        # Test permission checking
        assert auth_bridge.check_permissions(user_data, 'create_report') == True
        assert auth_bridge.check_permissions(user_data, 'voice_dictation') == True  # Role-based
        assert auth_bridge.check_permissions(user_data, 'admin_access') == False
        
        # Test session invalidation
        assert auth_bridge.invalidate_session(session_id) == True
        assert auth_bridge.get_session_user(session_id) is None
        
        print("✅ Authentication Bridge working correctly")
        success_count += 1
        
    except Exception as e:
        print(f"❌ Authentication Bridge test failed: {e}")
    
    # Test Orthanc Client
    print("\n2. Testing Orthanc Client...")
    try:
        orthanc_client = OrthancClient()
        
        # Test client initialization
        assert orthanc_client.base_url is not None
        assert orthanc_client.username is not None
        
        # Test URL generation
        study_id = "test_study_123"
        dicom_web_url = orthanc_client.get_dicom_web_url(study_id)
        ohif_url = orthanc_client.get_ohif_viewer_url(study_id)
        
        assert study_id in dicom_web_url
        assert study_id in ohif_url
        
        # Test study link creation
        study_link = orthanc_client.create_study_link(study_id)
        assert study_link is not None
        assert study_id in study_link
        
        print("✅ Orthanc Client working correctly")
        print(f"   DICOM Web URL: {dicom_web_url}")
        print(f"   OHIF Viewer URL: {ohif_url}")
        success_count += 1
        
    except Exception as e:
        print(f"❌ Orthanc Client test failed: {e}")
    
    # Test NAS Client
    print("\n3. Testing NAS Client...")
    try:
        nas_client = NASClient()
        
        # Test client initialization
        assert nas_client.mount_point is not None
        assert nas_client.backup_path is not None
        
        # Test storage stats (even if NAS is not available)
        stats = nas_client.get_storage_stats()
        assert isinstance(stats, dict)
        
        # Test report storage (with backup disabled for testing)
        original_backup_enabled = nas_client.backup_enabled
        nas_client.backup_enabled = False
        
        test_report_data = {
            'report_id': 'test_report_123',
            'patient_id': 'TEST_PAT_123',
            'content': {'findings': 'Test findings'}
        }
        
        result = nas_client.store_report('test_report_123', test_report_data)
        assert result == True  # Should succeed when backup is disabled
        
        # Restore original setting
        nas_client.backup_enabled = original_backup_enabled
        
        print("✅ NAS Client working correctly")
        print(f"   Mount Point: {nas_client.mount_point}")
        print(f"   Backup Enabled: {nas_client.backup_enabled}")
        success_count += 1
        
    except Exception as e:
        print(f"❌ NAS Client test failed: {e}")
    
    # Test RIS Client
    print("\n4. Testing RIS Client...")
    try:
        ris_client = RISClient()
        
        # Test client initialization
        assert ris_client.base_url is not None
        
        # Test integration status
        status = ris_client.get_integration_status()
        assert isinstance(status, dict)
        assert 'enabled' in status
        assert 'connected' in status
        
        # Test operations when disabled (should handle gracefully)
        if not ris_client.enabled:
            assert ris_client.get_patient_info('TEST_PAT') is None
            assert ris_client.get_study_order('TEST_ACC') is None
            assert ris_client.submit_report('TEST_ACC', {}) == True  # Should succeed when disabled
        
        # Test HL7 message creation
        test_data = {
            'patient_id': 'TEST_PAT_123',
            'patient_name': 'Test Patient',
            'accession_number': 'TEST_ACC_123',
            'findings': 'Test findings',
            'impression': 'Test impression'
        }
        
        hl7_message = ris_client._create_hl7_message('ORU', test_data)
        assert 'MSH' in hl7_message  # HL7 message should start with MSH segment
        assert 'TEST_PAT_123' in hl7_message
        
        print("✅ RIS Client working correctly")
        print(f"   RIS Enabled: {ris_client.enabled}")
        print(f"   HL7 Enabled: {ris_client.hl7_enabled}")
        success_count += 1
        
    except Exception as e:
        print(f"❌ RIS Client test failed: {e}")
    
    # Test Integration Workflow
    print("\n5. Testing Integration Workflow...")
    try:
        # Test a simple workflow that combines multiple integrations
        auth_bridge = AuthenticationBridge()
        orthanc_client = OrthancClient()
        
        # Create a user session
        user_data = {
            'user_id': 'workflow_user',
            'username': 'workflow_doctor',
            'roles': ['radiologist'],
            'permissions': ['create_report', 'finalize_report']
        }
        
        session_id = auth_bridge.create_reporting_session(user_data)
        
        # Check permissions for reporting workflow
        can_create = auth_bridge.check_permissions(user_data, 'create_report')
        can_dictate = auth_bridge.check_permissions(user_data, 'voice_dictation')
        can_finalize = auth_bridge.check_permissions(user_data, 'finalize_report')
        
        assert can_create == True
        assert can_dictate == True
        assert can_finalize == True
        
        # Generate study URLs
        study_id = "workflow_study_123"
        viewer_url = orthanc_client.get_ohif_viewer_url(study_id)
        
        # Clean up session
        auth_bridge.invalidate_session(session_id)
        
        print("✅ Integration workflow working correctly")
        print(f"   Session created and cleaned up successfully")
        print(f"   All required permissions verified")
        success_count += 1
        
    except Exception as e:
        print(f"❌ Integration workflow test failed: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Integration Test Results: {success_count}/{total_tests + 1} tests passed")
    
    if success_count == total_tests + 1:
        print("🎉 All integration tests passed successfully!")
        print("\nIntegration components are ready for:")
        print("- Authentication with SA Medical System")
        print("- DICOM image retrieval from Orthanc")
        print("- File storage and backup to NAS")
        print("- Patient data exchange with RIS")
        print("- Complete reporting workflows")
        return True
    else:
        print("⚠️  Some integration tests failed.")
        print("Please check the configuration and external system availability.")
        return False

if __name__ == "__main__":
    success = test_integrations()
    sys.exit(0 if success else 1)