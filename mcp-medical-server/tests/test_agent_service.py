"""
Tests for Agent Service

Author: Kiro Team
Task: K2.5
"""

import os
import sys
import json
import time
import pytest
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.service import AgentService
from agent.local_ledger import LocalLedger


class TestAgentService:
    """Test agent service functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def test_config(self, temp_dir):
        """Create test configuration."""
        config_path = os.path.join(temp_dir, "config.json")
        config = {
            "agent_id": "test-agent",
            "subnet_id": "test-subnet",
            "ledger_path": os.path.join(temp_dir, "ledger.jsonl"),
            "vault": {
                "storage_path": os.path.join(temp_dir, "vault.db"),
                "key_material": "test-key"
            },
            "adapters": {
                "ssh": {"enabled": False},
                "files": {"enabled": True},
                "smb": {"enabled": False},
                "api": {"enabled": False}
            }
        }
        
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        return config_path
    
    def test_agent_initialization(self, test_config):
        """Test agent initializes correctly."""
        agent = AgentService(config_path=test_config)
        
        assert agent.agent_id == "test-agent"
        assert agent.subnet_id == "test-subnet"
        assert agent.request_count == 0
        assert agent.error_count == 0
    
    def test_health_check(self, test_config):
        """Test health check returns correct data."""
        agent = AgentService(config_path=test_config)
        
        health = agent.get_health()
        
        assert health['status'] == 'healthy'
        assert health['agent_id'] == 'test-agent'
        assert health['subnet_id'] == 'test-subnet'
        assert 'uptime_seconds' in health
        assert 'adapters' in health
        assert health['request_count'] == 0
    
    def test_token_validation_valid(self, test_config):
        """Test token validation with valid token."""
        agent = AgentService(config_path=test_config)
        
        # Create valid token
        import base64
        token_data = {
            "req_id": "REQ-001",
            "vault": "test-vault",
            "path": "test/path",
            "exp": int(time.time()) + 300
        }
        token_str = base64.b64encode(json.dumps(token_data).encode()).decode()
        
        result = agent.validate_token(token_str)
        
        assert result is not None
        assert result['req_id'] == 'REQ-001'
        assert result['vault'] == 'test-vault'
    
    def test_token_validation_expired(self, test_config):
        """Test token validation with expired token."""
        agent = AgentService(config_path=test_config)
        
        # Create expired token
        import base64
        token_data = {
            "req_id": "REQ-001",
            "vault": "test-vault",
            "path": "test/path",
            "exp": int(time.time()) - 300  # Expired
        }
        token_str = base64.b64encode(json.dumps(token_data).encode()).decode()
        
        result = agent.validate_token(token_str)
        
        assert result is None
    
    def test_token_validation_missing_fields(self, test_config):
        """Test token validation with missing required fields."""
        agent = AgentService(config_path=test_config)
        
        # Create token missing required fields
        import base64
        token_data = {
            "req_id": "REQ-001"
            # Missing vault and path
        }
        token_str = base64.b64encode(json.dumps(token_data).encode()).decode()
        
        result = agent.validate_token(token_str)
        
        assert result is None
    
    def test_ledger_integration(self, test_config):
        """Test agent writes to ledger."""
        agent = AgentService(config_path=test_config)
        
        # Trigger an event
        agent.ledger.append_event({
            "type": "TEST_EVENT",
            "data": "test"
        })
        
        # Verify ledger has entry
        assert agent.ledger.get_entry_count() == 1
        
        entries = agent.ledger.get_entries()
        assert len(entries) == 1
        assert entries[0]['data']['type'] == 'TEST_EVENT'
    
    def test_adapter_loading(self, test_config):
        """Test adapters are loaded correctly."""
        agent = AgentService(config_path=test_config)
        
        # Check adapters
        adapters = agent.adapter_loader.list_adapters()
        
        # Only files adapter should be enabled
        assert 'files' in adapters
        assert 'ssh' not in adapters  # Disabled in config
    
    def test_shutdown(self, test_config):
        """Test graceful shutdown."""
        agent = AgentService(config_path=test_config)
        
        # Perform some operations
        agent.request_count = 10
        
        # Shutdown
        agent.shutdown()
        
        # Verify shutdown event in ledger
        entries = agent.ledger.get_entries(event_type='AGENT_SHUTDOWN')
        assert len(entries) == 1
        assert entries[0]['data']['total_requests'] == 10


class TestLocalLedger:
    """Test local Merkle ledger."""
    
    @pytest.fixture
    def temp_ledger(self):
        """Create temporary ledger."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as f:
            ledger_path = f.name
        
        yield ledger_path
        
        # Cleanup
        if os.path.exists(ledger_path):
            os.unlink(ledger_path)
    
    def test_ledger_initialization(self, temp_ledger):
        """Test ledger initializes correctly."""
        ledger = LocalLedger(ledger_path=temp_ledger)
        
        assert ledger.entry_count == 0
        assert ledger.previous_hash is None
    
    def test_append_event(self, temp_ledger):
        """Test appending events to ledger."""
        ledger = LocalLedger(ledger_path=temp_ledger)
        
        # Append event
        entry = ledger.append_event({
            "type": "TEST_EVENT",
            "data": "test"
        })
        
        assert entry['entry_id'] == 1
        assert entry['hash'] is not None
        assert entry['previous_hash'] is None
        assert ledger.entry_count == 1
    
    def test_merkle_chain(self, temp_ledger):
        """Test Merkle chain is maintained."""
        ledger = LocalLedger(ledger_path=temp_ledger)
        
        # Append multiple events
        entry1 = ledger.append_event({"type": "EVENT_1"})
        entry2 = ledger.append_event({"type": "EVENT_2"})
        entry3 = ledger.append_event({"type": "EVENT_3"})
        
        # Verify chain
        assert entry1['previous_hash'] is None
        assert entry2['previous_hash'] == entry1['hash']
        assert entry3['previous_hash'] == entry2['hash']
    
    def test_verify_chain_valid(self, temp_ledger):
        """Test chain verification with valid chain."""
        ledger = LocalLedger(ledger_path=temp_ledger)
        
        # Append events
        ledger.append_event({"type": "EVENT_1"})
        ledger.append_event({"type": "EVENT_2"})
        ledger.append_event({"type": "EVENT_3"})
        
        # Verify chain
        assert ledger.verify_chain() is True
    
    def test_verify_chain_tampered(self, temp_ledger):
        """Test chain verification detects tampering."""
        ledger = LocalLedger(ledger_path=temp_ledger)
        
        # Append events
        ledger.append_event({"type": "EVENT_1"})
        ledger.append_event({"type": "EVENT_2"})
        
        # Tamper with ledger file
        with open(temp_ledger, 'r') as f:
            lines = f.readlines()
        
        # Modify first entry
        entry = json.loads(lines[0])
        entry['data']['type'] = 'TAMPERED'
        lines[0] = json.dumps(entry) + '\n'
        
        with open(temp_ledger, 'w') as f:
            f.writelines(lines)
        
        # Reload and verify
        ledger2 = LocalLedger(ledger_path=temp_ledger)
        assert ledger2.verify_chain() is False
    
    def test_get_entries(self, temp_ledger):
        """Test retrieving entries."""
        ledger = LocalLedger(ledger_path=temp_ledger)
        
        # Append events
        ledger.append_event({"type": "EVENT_1"})
        ledger.append_event({"type": "EVENT_2"})
        ledger.append_event({"type": "EVENT_1"})
        
        # Get all entries
        all_entries = ledger.get_entries()
        assert len(all_entries) == 3
        
        # Get filtered entries
        event1_entries = ledger.get_entries(event_type='EVENT_1')
        assert len(event1_entries) == 2
        
        # Get limited entries
        limited = ledger.get_entries(limit=2)
        assert len(limited) == 2
    
    def test_export_ledger(self, temp_ledger):
        """Test exporting ledger."""
        ledger = LocalLedger(ledger_path=temp_ledger)
        
        # Append events
        ledger.append_event({"type": "EVENT_1"})
        ledger.append_event({"type": "EVENT_2"})
        
        # Export
        export_path = temp_ledger + '.export'
        ledger.export_ledger(export_path)
        
        # Verify export
        assert os.path.exists(export_path)
        
        # Load exported ledger
        ledger2 = LocalLedger(ledger_path=export_path)
        assert ledger2.entry_count == 2
        assert ledger2.verify_chain() is True
        
        # Cleanup
        os.unlink(export_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
