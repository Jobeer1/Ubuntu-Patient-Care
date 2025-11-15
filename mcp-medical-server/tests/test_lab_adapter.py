"""
Tests for Lab LIS Adapter

Test Coverage:
- Connection establishment (Epic, Cerner, generic HL7)
- Credential validation
- Lab result queries
- Result retrieval (JSON, CSV, PDF formats)
- Ephemeral account creation
- Error handling
"""

import pytest
import json
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock
import requests

from adapters.lab_lis_handler import (
    LabLISHandler,
    LabLISConfig,
    LabRequestPayload,
    LISServerType,
    ConnectionError,
    AuthenticationError,
    RetrievalError,
    EphemeralAccountError
)


@pytest.fixture
def epic_config():
    """Configuration for Epic EHR"""
    return LabLISConfig.for_epic("192.168.1.200", 80)


@pytest.fixture
def handler_epic(epic_config):
    """Handler instance for Epic"""
    return LabLISHandler(epic_config)


@pytest.fixture
def valid_credentials():
    """Valid credentials for LIS"""
    return {"username": "lab_user", "password": "secure_password"}


@pytest.fixture
def valid_target():
    """Valid target configuration"""
    return {"host": "192.168.1.200", "port": 80}


class TestLabConfig:
    """Test Lab configuration"""
    
    def test_epic_config_creation(self):
        """Test Epic config builder"""
        config = LabLISConfig.for_epic("192.168.1.200", 80)
        
        assert config["lis_host"] == "192.168.1.200"
        assert config["lis_port"] == 80
        assert config["server_type"] == "epic"
    
    def test_cerner_config_creation(self):
        """Test Cerner config builder"""
        config = LabLISConfig.for_cerner("192.168.1.210", 80)
        
        assert config["lis_host"] == "192.168.1.210"
        assert config["server_type"] == "cerner"


class TestLabConnection:
    """Test Lab connection"""
    
    @patch('adapters.lab_lis_handler.requests.get')
    def test_connect_epic_success(self, mock_get, handler_epic, valid_target, valid_credentials):
        """Test successful Epic connection"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = handler_epic.connect(valid_target, valid_credentials)
        
        assert result is True
        assert handler_epic.connected is True
        assert handler_epic.authenticated_user == "lab_user"
    
    @patch('adapters.lab_lis_handler.requests.get')
    def test_connect_epic_auth_failure(self, mock_get, handler_epic, valid_target):
        """Test Epic connection with invalid credentials"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        with pytest.raises(AuthenticationError):
            handler_epic.connect(valid_target, {"username": "lab_user", "password": "wrong"})
    
    def test_connect_missing_credentials(self, handler_epic, valid_target):
        """Test connection with missing credentials"""
        with pytest.raises(AuthenticationError):
            handler_epic.connect(valid_target, {"username": "lab_user"})


class TestLabRetrieval:
    """Test Lab result retrieval"""
    
    @patch('adapters.lab_lis_handler.LabLISHandler._query_lab_results')
    def test_retrieve_json_format(self, mock_query):
        """Test lab result retrieval in JSON format"""
        # Create handler manually without actual connection
        config = LabLISConfig.for_epic("192.168.1.200", 80)
        handler = LabLISHandler(config)
        handler.connected = True
        handler.authenticated_user = "lab_user"
        
        # Mock the results from query
        mock_query.return_value = [
            {
                "test_name": "Glucose",
                "value": {"valueQuantity": {"value": 95, "unit": "mg/dL"}},
                "date": "2025-11-10T10:00:00",
                "status": "final"
            }
        ]
        
        result = handler.retrieve(
            path="/patients/MRN12345/lab-results",
            format="json"
        )
        
        assert isinstance(result, bytes)
        data = json.loads(result)
        assert "results" in data
        assert len(data["results"]) > 0
    
    def test_retrieve_not_connected(self, handler_epic):
        """Test retrieval when not connected"""
        with pytest.raises(RetrievalError, match="Not connected"):
            handler_epic.retrieve(path="/patients/MRN123/lab-results")
    
    def test_extract_mrn(self, handler_epic):
        """Test MRN extraction"""
        mrn = handler_epic._extract_mrn("/patients/MRN12345/lab-results")
        assert mrn == "MRN12345"


class TestLabEphemeralAccounts:
    """Test ephemeral account creation"""
    
    @patch('adapters.lab_lis_handler.requests.get')
    def test_create_ephemeral_account(self, mock_get, handler_epic, valid_target, valid_credentials):
        """Test ephemeral account creation"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        handler_epic.connect(valid_target, valid_credentials)
        
        result = handler_epic.create_ephemeral_account(
            ttl_seconds=3600,
            scope="read-only"
        )
        
        assert "username" in result
        assert "password" in result
        assert "expires_ts" in result
        assert result["scope"] == "read-only"
    
    def test_create_ephemeral_not_connected(self, handler_epic):
        """Test ephemeral account creation when not connected"""
        with pytest.raises(EphemeralAccountError, match="Not connected"):
            handler_epic.create_ephemeral_account(ttl_seconds=3600)


class TestLabPayload:
    """Test Lab request payload"""
    
    def test_lab_request_payload_creation(self):
        """Test lab request payload"""
        payload = LabRequestPayload.create(
            requester_id="doctor@clinic.org",
            patient_id="PAT-12345",
            mrn="MRN12345",
            reason="Routine lab review"
        )
        
        assert payload["requester_id"] == "doctor@clinic.org"
        assert payload["patient_context"]["mrn"] == "MRN12345"
        assert payload["emergency"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
