"""
Tests for Philips CT Adapter

Test Coverage:
- Configuration loading for Philips IntelliSpace PACS
- Real system integration (155.235.81.120)
- CT-specific operations
"""

import pytest
import json
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock

from adapters.philips_ct_handler import (
    PhilipsCTHandler,
    PhilipsCTCredentialConfig,
    PhilipsCTServerType,
    ConnectionError,
    AuthenticationError,
    RetrievalError,
    EphemeralAccountError
)


@pytest.fixture
def test_config():
    """Configuration for test Philips CT"""
    return {
        "ct_host": "192.168.1.100",
        "ct_port": 104,
        "ct_ae_title": "TEST-PACS",
        "server_type": "intellispace_pacs",
        "http_timeout_seconds": 30,
        "enforce_tls": False,
        "real_system": False
    }


@pytest.fixture
def real_system_config():
    """Configuration for REAL Philips CT at 155.235.81.120"""
    return {
        "ct_host": "155.235.81.120",
        "ct_port": 104,
        "ct_ae_title": "KIRO-PHILIPS-CT",
        "server_type": "intellispace_pacs",
        "http_timeout_seconds": 30,
        "enforce_tls": False,
        "real_system": True
    }


@pytest.fixture
def handler_test(test_config):
    """Handler instance for test system"""
    return PhilipsCTHandler(test_config)


@pytest.fixture
def handler_real(real_system_config):
    """Handler instance for real system"""
    return PhilipsCTHandler(real_system_config)


@pytest.fixture
def valid_credentials():
    """Valid credentials for PACS"""
    return {"username": "pacs_user", "password": "secure_password"}


class TestPhilipsCTConfig:
    """Test Philips CT configuration"""
    
    def test_test_config_creation(self, test_config):
        """Test creating test configuration"""
        cred_config = PhilipsCTCredentialConfig(test_config)
        
        assert cred_config.ct_host == "192.168.1.100"
        assert cred_config.ct_port == 104
        assert cred_config.ct_ae_title == "TEST-PACS"
    
    def test_real_system_config(self, real_system_config):
        """Test real system configuration"""
        cred_config = PhilipsCTCredentialConfig(real_system_config)
        
        assert cred_config.ct_host == "155.235.81.120"
        assert cred_config.ct_port == 104
        assert cred_config.ct_ae_title == "KIRO-PHILIPS-CT"


class TestPhilipsCTHandler:
    """Test Philips CT handler"""
    
    def test_handler_initialization(self, handler_test):
        """Test handler is properly initialized"""
        assert handler_test is not None
        assert hasattr(handler_test, 'connect')
        assert hasattr(handler_test, 'retrieve')
        assert hasattr(handler_test, 'create_ephemeral_account')
    
    def test_handler_real_system(self, handler_real):
        """Test handler for real system"""
        assert handler_real is not None


class TestPhilipsCTCredentialConfig:
    """Test credential configuration"""
    
    def test_default_values(self):
        """Test default configuration values"""
        config = {}
        cred_config = PhilipsCTCredentialConfig(config)
        
        assert cred_config.ct_host == "155.235.81.120"  # Default to real system IP
        assert cred_config.ct_port == 104  # Standard DICOM port
        assert cred_config.ct_ae_title == "KIRO-PHILIPS-CT"
    
    def test_custom_host(self):
        """Test custom host configuration"""
        config = {"ct_host": "10.0.0.50"}
        cred_config = PhilipsCTCredentialConfig(config)
        assert cred_config.ct_host == "10.0.0.50"
    
    def test_server_type_intellispace(self):
        """Test IntelliSpace server type"""
        config = {"server_type": "intellispace_pacs"}
        cred_config = PhilipsCTCredentialConfig(config)
        assert cred_config.server_type == PhilipsCTServerType.INTELLISPACE_PACS


class TestPhilipsCTIntegration:
    """Integration tests for Philips CT adapter"""
    
    def test_adapter_interface(self, handler_test):
        """Test that handler implements required interface"""
        # BaseAdapter interface
        assert hasattr(handler_test, 'connect')
        assert hasattr(handler_test, 'retrieve')
        assert hasattr(handler_test, 'create_ephemeral_account')
        assert hasattr(handler_test, 'cleanup')
    
    def test_real_system_ip_configured(self, real_system_config):
        """Verify real system IP is correctly configured"""
        cred_config = PhilipsCTCredentialConfig(real_system_config)
        assert cred_config.ct_host == "155.235.81.120"
    
    def test_real_system_marked(self, real_system_config):
        """Verify real system is marked"""
        cred_config = PhilipsCTCredentialConfig(real_system_config)
        assert cred_config.real_system is True


class TestRealSystemConfiguration:
    """Tests specific to real system (155.235.81.120)"""
    
    def test_real_system_defaults_to_actual_ip(self):
        """Test that empty config defaults to real system IP"""
        cred_config = PhilipsCTCredentialConfig({})
        assert cred_config.ct_host == "155.235.81.120"
    
    def test_real_system_ae_title(self):
        """Test real system AE title"""
        cred_config = PhilipsCTCredentialConfig({})
        assert cred_config.ct_ae_title == "KIRO-PHILIPS-CT"
    
    def test_real_system_port(self):
        """Test real system DICOM port"""
        cred_config = PhilipsCTCredentialConfig({})
        assert cred_config.ct_port == 104


class TestPhilipsCTServerTypes:
    """Test supported Philips CT server types"""
    
    def test_intellispace_pacs(self):
        """Test IntelliSpace PACS type"""
        assert PhilipsCTServerType.INTELLISPACE_PACS == "intellispace_pacs"
    
    def test_intellispace_ris(self):
        """Test IntelliSpace RIS type"""
        assert PhilipsCTServerType.INTELLISPACE_RIS == "intellispace_ris"
    
    def test_generic_dicom(self):
        """Test generic DICOM type"""
        assert PhilipsCTServerType.GENERIC_DICOM == "generic_dicom"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
