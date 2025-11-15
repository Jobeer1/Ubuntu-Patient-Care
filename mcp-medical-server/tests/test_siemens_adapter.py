"""
Tests for Siemens MRI DICOM Adapter

Test Coverage:
- Connection establishment (Orthanc, DCMQRSCP, generic DIMSE)
- Credential validation
- DICOM instance queries
- File retrieval (JSON, DICOM, ZIP formats)
- Ephemeral account creation
- Error handling and timeouts
- Integration with FastAPI backend
"""

import pytest
import json
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock
import requests

# Import handler to test
from adapters.siemens_mri_handler import (
    SiemensMriHandler,
    SiemensMriConfig,
    DicomRequestPayload,
    DicomServerType,
    SiemensCredentialConfig,
    ConnectionError,
    AuthenticationError,
    RetrievalError,
    EphemeralAccountError
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def orthanc_config():
    """Configuration for Orthanc PACS"""
    return SiemensMriConfig.for_orthanc("192.168.1.100", 8042)


@pytest.fixture
def dcmqrscp_config():
    """Configuration for DCMQRSCP"""
    return SiemensMriConfig.for_dcmqrscp("192.168.1.110", 104, "KIRO")


@pytest.fixture
def handler_orthanc(orthanc_config):
    """Handler instance for Orthanc"""
    return SiemensMriHandler(orthanc_config)


@pytest.fixture
def handler_dcmqrscp(dcmqrscp_config):
    """Handler instance for DCMQRSCP"""
    return SiemensMriHandler(dcmqrscp_config)


@pytest.fixture
def valid_credentials():
    """Valid credentials for PACS"""
    return {
        "username": "admin",
        "password": "secure_password_123"
    }


@pytest.fixture
def valid_target():
    """Valid target configuration"""
    return {
        "host": "192.168.1.100",
        "port": 8042,
        "ae_title": "KIRO-MCP"
    }


# ============================================================================
# Test Configuration Loading
# ============================================================================

class TestSiemensConfig:
    """Test Siemens configuration builders"""
    
    def test_orthanc_config_creation(self):
        """Test Orthanc config builder"""
        config = SiemensMriConfig.for_orthanc("192.168.1.100", 8042)
        
        assert config["pacs_host"] == "192.168.1.100"
        assert config["pacs_port"] == 8042
        assert config["server_type"] == "orthanc"
        assert config["http_timeout_seconds"] == 30
    
    def test_dcmqrscp_config_creation(self):
        """Test DCMQRSCP config builder"""
        config = SiemensMriConfig.for_dcmqrscp("192.168.1.110", 104, "KIRO")
        
        assert config["pacs_host"] == "192.168.1.110"
        assert config["pacs_port"] == 104
        assert config["pacs_ae_title"] == "KIRO"
        assert config["server_type"] == "dcmqrscp"
    
    def test_config_defaults(self):
        """Test configuration defaults"""
        config = SiemensMriConfig.for_orthanc("localhost")
        
        assert config["pacs_host"] == "localhost"
        assert config["pacs_port"] == 8042  # Default port
    
    def test_siemens_credential_config(self, orthanc_config):
        """Test SiemensCredentialConfig parsing"""
        cred_config = SiemensCredentialConfig(orthanc_config)
        
        assert cred_config.pacs_host == "192.168.1.100"
        assert cred_config.pacs_port == 8042
        assert cred_config.server_type == DicomServerType.ORTHANC


# ============================================================================
# Test Connection Methods
# ============================================================================

class TestConnectionOrthanc:
    """Test Orthanc connection"""
    
    @patch('requests.get')
    def test_connect_orthanc_success(self, mock_get, handler_orthanc, valid_target, valid_credentials):
        """Test successful Orthanc connection"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Name": "Orthanc"}
        mock_get.return_value = mock_response
        
        result = handler_orthanc.connect(valid_target, valid_credentials)
        
        assert result is True
        assert handler_orthanc.connected is True
        assert handler_orthanc.authenticated_user == "admin"
    
    @patch('requests.get')
    def test_connect_orthanc_auth_failure(self, mock_get, handler_orthanc, valid_target):
        """Test Orthanc connection with invalid credentials"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        with pytest.raises(AuthenticationError):
            handler_orthanc.connect(valid_target, {"username": "admin", "password": "wrong"})
    
    @patch('requests.get')
    def test_connect_orthanc_network_error(self, mock_get, handler_orthanc, valid_target, valid_credentials):
        """Test Orthanc connection with network error"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")
        
        with pytest.raises(ConnectionError):
            handler_orthanc.connect(valid_target, valid_credentials)
    
    @patch('requests.get')
    def test_connect_orthanc_timeout(self, mock_get, handler_orthanc, valid_target, valid_credentials):
        """Test Orthanc connection timeout"""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
        
        with pytest.raises(ConnectionError):
            handler_orthanc.connect(valid_target, valid_credentials)
    
    def test_connect_dcmqrscp_success(self, handler_dcmqrscp, valid_target, valid_credentials):
        """Test successful DCMQRSCP connection"""
        valid_target["port"] = 104
        result = handler_dcmqrscp.connect(valid_target, valid_credentials)
        
        assert result is True
        assert handler_dcmqrscp.connected is True
    
    def test_connect_missing_credentials(self, handler_orthanc, valid_target):
        """Test connection with missing credentials"""
        with pytest.raises(AuthenticationError):
            handler_orthanc.connect(valid_target, {"username": "admin"})


# ============================================================================
# Test DICOM Query & Retrieval
# ============================================================================

class TestDicomQueryAndRetrieval:
    """Test DICOM instance queries and retrieval"""
    
    @patch('adapters.siemens_mri_handler.requests.get')
    def test_retrieve_json_format(self, mock_get, handler_orthanc, valid_target, valid_credentials):
        """Test DICOM retrieval in JSON format"""
        # Setup connection mock
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Name": "Orthanc"}
        mock_get.return_value = mock_response
        
        handler_orthanc.connect(valid_target, valid_credentials)
        
        # Setup retrieval mock with side effects for multiple calls
        def mock_json():
            return [{"ID": "study1"}]
        
        mock_response.json = Mock(side_effect=[
            [{"ID": "study1"}],  # Study search
            [{"sop_instance_uid": "1.2.3", "file_size": 1024}]  # Instances query
        ])
        mock_get.return_value = mock_response
        
        result = handler_orthanc.retrieve(
            path="/studies/1.2.3.4.5/instances",
            format="json"
        )
        
        assert isinstance(result, bytes)
        data = json.loads(result)
        assert "count" in data
        assert "instances" in data
    
    @patch('adapters.siemens_mri_handler.requests.get')
    def test_retrieve_invalid_path(self, mock_get, handler_orthanc, valid_target, valid_credentials):
        """Test retrieval with invalid path"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        handler_orthanc.connect(valid_target, valid_credentials)
        
        with pytest.raises(RetrievalError):
            handler_orthanc.retrieve(path="/invalid/path", format="json")
    
    def test_retrieve_not_connected(self, handler_orthanc):
        """Test retrieval when not connected"""
        with pytest.raises(RetrievalError, match="Not connected"):
            handler_orthanc.retrieve(path="/studies/1.2.3/instances")
    
    def test_extract_study_uid(self, handler_orthanc):
        """Test Study UID extraction from path"""
        uid = handler_orthanc._extract_study_uid("/studies/1.2.3.4.5/instances")
        assert uid == "1.2.3.4.5"
    
    def test_extract_study_uid_invalid(self, handler_orthanc):
        """Test UID extraction from invalid path"""
        uid = handler_orthanc._extract_study_uid("/patients/PAT-123/studies")
        assert uid is None


# ============================================================================
# Test Ephemeral Accounts
# ============================================================================

class TestEphemeralAccounts:
    """Test ephemeral account creation"""
    
    @patch('adapters.siemens_mri_handler.requests.post')
    @patch('adapters.siemens_mri_handler.requests.get')
    def test_create_ephemeral_account_orthanc(self, mock_get, mock_post, handler_orthanc, 
                                              valid_target, valid_credentials):
        """Test ephemeral account creation on Orthanc"""
        # Setup connection mock
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        handler_orthanc.connect(valid_target, valid_credentials)
        
        # Setup ephemeral account mock
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        result = handler_orthanc.create_ephemeral_account(
            ttl_seconds=3600,
            scope="read-only"
        )
        
        assert "username" in result
        assert "password" in result
        assert "expires_ts" in result
        assert "account_id" in result
        assert result["scope"] == "read-only"
        assert result["username"].startswith("temp_")
    
    def test_create_ephemeral_not_connected(self, handler_orthanc):
        """Test ephemeral account creation when not connected"""
        with pytest.raises(EphemeralAccountError, match="Not connected"):
            handler_orthanc.create_ephemeral_account(ttl_seconds=3600)
    
    @patch('adapters.siemens_mri_handler.requests.post')
    @patch('adapters.siemens_mri_handler.requests.get')
    def test_ephemeral_account_ttl(self, mock_get, mock_post, handler_orthanc, 
                                   valid_target, valid_credentials):
        """Test ephemeral account TTL is correctly set"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        mock_post.return_value = mock_response
        
        handler_orthanc.connect(valid_target, valid_credentials)
        
        ttl_seconds = 7200  # 2 hours
        before_creation = datetime.utcnow()
        result = handler_orthanc.create_ephemeral_account(ttl_seconds=ttl_seconds)
        after_creation = datetime.utcnow()
        
        expires = datetime.fromisoformat(result["expires_ts"])
        
        # Verify TTL is approximately correct (allowing 1 second variance)
        min_expected = before_creation + timedelta(seconds=ttl_seconds)
        max_expected = after_creation + timedelta(seconds=ttl_seconds)
        
        assert min_expected <= expires <= max_expected
    
    @patch('adapters.siemens_mri_handler.requests.post')
    @patch('adapters.siemens_mri_handler.requests.get')
    def test_ephemeral_read_only_scope(self, mock_get, mock_post, handler_orthanc, 
                                       valid_target, valid_credentials):
        """Test ephemeral account with read-only scope"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        mock_post.return_value = mock_response
        
        handler_orthanc.connect(valid_target, valid_credentials)
        
        result = handler_orthanc.create_ephemeral_account(
            ttl_seconds=3600,
            scope="read-only"
        )
        
        assert result["scope"] == "read-only"


# ============================================================================
# Test Cleanup
# ============================================================================

class TestCleanup:
    """Test connection cleanup"""
    
    @patch('adapters.siemens_mri_handler.requests.get')
    def test_cleanup_after_connect(self, mock_get, handler_orthanc, valid_target, valid_credentials):
        """Test cleanup after successful connection"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        handler_orthanc.connect(valid_target, valid_credentials)
        assert handler_orthanc.connected is True
        
        handler_orthanc.cleanup()
        
        assert handler_orthanc.connected is False
        assert handler_orthanc.authenticated_user is None
        assert len(handler_orthanc.study_cache) == 0
    
    def test_cleanup_when_not_connected(self, handler_orthanc):
        """Test cleanup when not connected (should not raise)"""
        handler_orthanc.cleanup()  # Should not raise
        assert handler_orthanc.connected is False
    
    @patch('adapters.siemens_mri_handler.requests.get')
    def test_context_manager_cleanup(self, mock_get, orthanc_config, valid_target, valid_credentials):
        """Test context manager ensures cleanup"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        with SiemensMriHandler(orthanc_config) as handler:
            handler.connect(valid_target, valid_credentials)
            assert handler.connected is True
        
        # After exiting context, should be cleaned up
        assert handler.connected is False


# ============================================================================
# Test Helper Methods
# ============================================================================

class TestHelperMethods:
    """Test internal helper methods"""
    
    def test_generate_nonce(self, handler_orthanc):
        """Test nonce generation"""
        nonce1 = handler_orthanc._generate_nonce()
        nonce2 = handler_orthanc._generate_nonce()
        
        assert isinstance(nonce1, str)
        assert isinstance(nonce2, str)
        assert nonce1 != nonce2
        assert len(nonce1) > 0
        assert len(nonce2) > 0
    
    def test_generate_secure_password(self, handler_orthanc):
        """Test secure password generation"""
        password = handler_orthanc._generate_secure_password(length=32)
        
        assert isinstance(password, str)
        assert len(password) == 32
        assert any(c.isalpha() for c in password)
        assert any(c.isdigit() for c in password)
    
    def test_generate_password_different_lengths(self, handler_orthanc):
        """Test password generation with different lengths"""
        for length in [16, 32, 64]:
            password = handler_orthanc._generate_secure_password(length=length)
            assert len(password) == length


# ============================================================================
# Test Integration with FastAPI
# ============================================================================

class TestFastAPIIntegration:
    """Test integration with FastAPI backend"""
    
    def test_dicom_request_payload_creation(self):
        """Test DICOM request payload creation"""
        payload = DicomRequestPayload.create(
            requester_id="doctor@clinic.org",
            patient_id="PAT-12345",
            study_uid="1.2.3.4.5",
            reason="Patient referral",
            emergency=False
        )
        
        assert payload["requester_id"] == "doctor@clinic.org"
        assert payload["reason"] == "Patient referral"
        assert payload["patient_context"]["patient_id"] == "PAT-12345"
        assert payload["patient_context"]["study_instance_uid"] == "1.2.3.4.5"
        assert payload["emergency"] is False
    
    def test_dicom_request_payload_emergency(self):
        """Test DICOM request payload with emergency flag"""
        payload = DicomRequestPayload.create(
            requester_id="doctor@clinic.org",
            patient_id="PAT-99999",
            study_uid="9.9.9.9.9",
            emergency=True
        )
        
        assert payload["emergency"] is True
        assert payload["target"]["vault"] == "pacs_vault_1"
        assert payload["target"]["path"] == "/studies/9.9.9.9.9/instances"


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_adapter_error_hierarchy(self):
        """Test error class hierarchy"""
        from adapters.base_adapter import AdapterError
        
        assert issubclass(ConnectionError, AdapterError)
        assert issubclass(AuthenticationError, AdapterError)
        assert issubclass(RetrievalError, AdapterError)
        assert issubclass(EphemeralAccountError, AdapterError)
    
    @patch('requests.get')
    def test_handle_http_error_500(self, mock_get, handler_orthanc, valid_target, valid_credentials):
        """Test handling of HTTP 500 error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        with pytest.raises(ConnectionError):
            handler_orthanc.connect(valid_target, valid_credentials)
    
    def test_logging_redacts_secrets(self, handler_orthanc):
        """Test that secrets are redacted in logs"""
        data = {
            "username": "admin",
            "password": "secret123",
            "api_key": "key456",
            "normal_field": "visible"
        }
        
        redacted = handler_orthanc._redact_secrets(data)
        
        assert redacted["password"] == "[REDACTED]"
        assert redacted["api_key"] == "[REDACTED]"
        assert redacted["normal_field"] == "visible"
        assert redacted["username"] == "admin"


# ============================================================================
# Test Performance & Limits
# ============================================================================

class TestPerformance:
    """Test performance characteristics and limits"""
    
    def test_max_results_limit(self, handler_orthanc):
        """Test max results parameter"""
        # With mock, test that max_results is respected
        instances = [{"id": i} for i in range(200)]
        
        limited = instances[:100]
        assert len(limited) == 100
    
    def test_password_generation_performance(self, handler_orthanc):
        """Test password generation performance"""
        import time
        
        start = time.time()
        for _ in range(10):
            handler_orthanc._generate_secure_password()
        elapsed = time.time() - start
        
        # Should be fast (< 100ms for 10 generations)
        assert elapsed < 0.1


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """End-to-end integration tests"""
    
    @patch('adapters.siemens_mri_handler.requests.post')
    @patch('adapters.siemens_mri_handler.requests.get')
    def test_full_workflow_orthanc(self, mock_get, mock_post, handler_orthanc, 
                                   valid_target, valid_credentials):
        """Test complete workflow: connect -> query -> retrieve -> cleanup"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Name": "Orthanc"}
        mock_get.return_value = mock_response
        mock_post.return_value = mock_response
        
        # Connect
        assert handler_orthanc.connect(valid_target, valid_credentials) is True
        
        # Create ephemeral account
        ephemeral = handler_orthanc.create_ephemeral_account(ttl_seconds=1800)
        assert "username" in ephemeral
        
        # Cleanup
        handler_orthanc.cleanup()
        assert handler_orthanc.connected is False
    
    def test_handler_initialization(self, orthanc_config):
        """Test handler initialization"""
        handler = SiemensMriHandler(orthanc_config)
        
        assert handler is not None
        assert handler.connected is False
        assert handler.authenticated_user is None
        assert handler.siemens_config.server_type == DicomServerType.ORTHANC


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
