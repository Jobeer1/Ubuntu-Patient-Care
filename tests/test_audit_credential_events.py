"""
Test suite for credential audit events in report_finalizer.py

Tests that the audit service can properly stamp and verify credential
retrieval events (requests, approvals, retrievals, ephemeral account creation).
"""

import pytest
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from audit.report_finalizer import ReportFinalizer, AuditEventType


class TestAuditEventTypes:
    """Test that event type constants are defined correctly"""
    
    def test_event_types_exist(self):
        """Verify all credential event types are defined"""
        assert hasattr(AuditEventType, 'CREDENTIAL_REQUEST')
        assert hasattr(AuditEventType, 'CREDENTIAL_APPROVED')
        assert hasattr(AuditEventType, 'CREDENTIAL_RETRIEVED')
        assert hasattr(AuditEventType, 'CREDENTIAL_EPHEMERAL_CREATED')
    
    def test_event_type_values(self):
        """Verify event type values are correct"""
        assert AuditEventType.CREDENTIAL_REQUEST == "CREDENTIAL_REQUEST"
        assert AuditEventType.CREDENTIAL_APPROVED == "CREDENTIAL_APPROVED"
        assert AuditEventType.CREDENTIAL_RETRIEVED == "CREDENTIAL_RETRIEVED"
        assert AuditEventType.CREDENTIAL_EPHEMERAL_CREATED == "CREDENTIAL_EPHEMERAL_CREATED"


class TestCredentialEventRecording:
    """Test credential event recording in Merkle audit ledger"""
    
    @pytest.fixture
    def finalizer(self, tmp_path):
        """Create a ReportFinalizer with temporary ledger"""
        ledger_path = str(tmp_path / "test_audit.ledger")
        return ReportFinalizer(ledger_path)
    
    def test_record_credential_request_event(self, finalizer):
        """Test recording a credential request event"""
        # Record a credential request
        result = finalizer.record_credential_event(
            event_type=AuditEventType.CREDENTIAL_REQUEST,
            req_id="REQ-20251110-0001",
            actor_id="doctor@clinic.org",
            metadata={
                "reason": "Emergency patient access",
                "patient_id": "PAT-12345",
                "target_vault": "subnet-1"
            }
        )
        
        # Verify result contains required fields
        assert "ledger_tx_id" in result
        assert "timestamp" in result
        assert "content_hash" in result
        assert result["event_type"] == AuditEventType.CREDENTIAL_REQUEST
        
        # Verify timestamp is valid ISO format
        assert "T" in result["timestamp"]
        
        # Verify content hash is hex string
        assert all(c in "0123456789abcdef" for c in result["content_hash"])
    
    def test_record_credential_approved_event(self, finalizer):
        """Test recording a credential approval event"""
        result = finalizer.record_credential_event(
            event_type=AuditEventType.CREDENTIAL_APPROVED,
            req_id="REQ-20251110-0001",
            actor_id="owner@clinic.org",
            metadata={
                "ttl_seconds": 300,
                "signature": "ed25519_signature_abc123"
            }
        )
        
        assert result["event_type"] == AuditEventType.CREDENTIAL_APPROVED
        assert "ledger_tx_id" in result
    
    def test_record_credential_retrieved_event(self, finalizer):
        """Test recording a credential retrieval event"""
        result = finalizer.record_credential_event(
            event_type=AuditEventType.CREDENTIAL_RETRIEVED,
            req_id="REQ-20251110-0001",
            actor_id="mcp-agent-subnet-1",
            metadata={
                "vault_id": "subnet-1",
                "path": "pacs/admin",
                "adapter": "ssh"
            }
        )
        
        assert result["event_type"] == AuditEventType.CREDENTIAL_RETRIEVED
        assert "ledger_tx_id" in result
    
    def test_record_ephemeral_account_created_event(self, finalizer):
        """Test recording ephemeral account creation event"""
        result = finalizer.record_credential_event(
            event_type=AuditEventType.CREDENTIAL_EPHEMERAL_CREATED,
            req_id="REQ-20251110-0001",
            actor_id="mcp-agent-subnet-1",
            metadata={
                "temp_user": "tmp_admin_20251110",
                "target_host": "nas.local",
                "expires_ts": "2025-11-10T14:15:00Z"
            }
        )
        
        assert result["event_type"] == AuditEventType.CREDENTIAL_EPHEMERAL_CREATED
        assert "ledger_tx_id" in result
    
    def test_invalid_event_type_raises_error(self, finalizer):
        """Test that invalid event types raise ValueError"""
        with pytest.raises(ValueError, match="Invalid event_type"):
            finalizer.record_credential_event(
                event_type="INVALID_EVENT_TYPE",
                req_id="REQ-20251110-0001",
                actor_id="doctor@clinic.org"
            )
    
    def test_missing_req_id_raises_error(self, finalizer):
        """Test that missing req_id raises ValueError"""
        with pytest.raises(ValueError, match="req_id must be a non-empty string"):
            finalizer.record_credential_event(
                event_type=AuditEventType.CREDENTIAL_REQUEST,
                req_id="",
                actor_id="doctor@clinic.org"
            )
    
    def test_missing_actor_id_raises_error(self, finalizer):
        """Test that missing actor_id raises ValueError"""
        with pytest.raises(ValueError, match="actor_id must be a non-empty string"):
            finalizer.record_credential_event(
                event_type=AuditEventType.CREDENTIAL_REQUEST,
                req_id="REQ-20251110-0001",
                actor_id=""
            )


class TestCredentialEventChain:
    """Test full credential event chain: request -> approve -> retrieve"""
    
    @pytest.fixture
    def finalizer(self, tmp_path):
        """Create a ReportFinalizer with temporary ledger"""
        ledger_path = str(tmp_path / "test_audit.ledger")
        return ReportFinalizer(ledger_path)
    
    def test_full_credential_request_chain(self, finalizer):
        """Test complete flow: request -> approve -> retrieve"""
        req_id = "REQ-20251110-CHAIN-001"
        
        # Step 1: Clinician requests emergency access
        request_result = finalizer.record_credential_event(
            event_type=AuditEventType.CREDENTIAL_REQUEST,
            req_id=req_id,
            actor_id="clinician@clinic.org",
            metadata={
                "reason": "Emergency patient imaging",
                "patient_id": "PAT-99999",
                "target": "pacs/admin"
            }
        )
        
        request_tx_id = request_result["ledger_tx_id"]
        assert request_tx_id is not None
        
        # Step 2: Owner approves the request
        approval_result = finalizer.record_credential_event(
            event_type=AuditEventType.CREDENTIAL_APPROVED,
            req_id=req_id,
            actor_id="owner@clinic.org",
            metadata={
                "approved_tx_id": request_tx_id,
                "ttl_seconds": 300
            }
        )
        
        approval_tx_id = approval_result["ledger_tx_id"]
        assert approval_tx_id is not None
        
        # Step 3: Agent retrieves the credential
        retrieval_result = finalizer.record_credential_event(
            event_type=AuditEventType.CREDENTIAL_RETRIEVED,
            req_id=req_id,
            actor_id="mcp-agent-subnet-1",
            metadata={
                "approval_tx_id": approval_tx_id,
                "vault_id": "subnet-1",
                "path": "pacs/admin",
                "adapter": "ssh"
            }
        )
        
        retrieval_tx_id = retrieval_result["ledger_tx_id"]
        assert retrieval_tx_id is not None
        
        # Verify all events are recorded in ledger
        audit_trail = finalizer.get_audit_trail(req_id)
        assert len(audit_trail) >= 3, f"Expected at least 3 events, got {len(audit_trail)}"
    
    def test_event_timestamps_are_ordered(self, finalizer):
        """Test that event timestamps progress logically"""
        req_id = "REQ-20251110-TIME-001"
        
        # Record three events in sequence
        events = []
        for i, event_type in enumerate([
            AuditEventType.CREDENTIAL_REQUEST,
            AuditEventType.CREDENTIAL_APPROVED,
            AuditEventType.CREDENTIAL_RETRIEVED
        ]):
            result = finalizer.record_credential_event(
                event_type=event_type,
                req_id=req_id,
                actor_id=f"actor-{i}@clinic.org"
            )
            events.append(result)
        
        # Parse timestamps and verify ordering
        timestamps = [datetime.fromisoformat(r["timestamp"]) for r in events]
        assert timestamps[0] <= timestamps[1] <= timestamps[2], \
            "Event timestamps should be in chronological order"


class TestCredentialEventMetadata:
    """Test metadata handling in credential events"""
    
    @pytest.fixture
    def finalizer(self, tmp_path):
        """Create a ReportFinalizer with temporary ledger"""
        ledger_path = str(tmp_path / "test_audit.ledger")
        return ReportFinalizer(ledger_path)
    
    def test_metadata_included_in_hash(self, finalizer):
        """Test that metadata is included in content hash"""
        req_id = "REQ-20251110-META-001"
        
        # Record event with metadata
        result1 = finalizer.record_credential_event(
            event_type=AuditEventType.CREDENTIAL_REQUEST,
            req_id=req_id,
            actor_id="doctor@clinic.org",
            metadata={"reason": "Emergency access"}
        )
        
        # Record similar event with different metadata
        result2 = finalizer.record_credential_event(
            event_type=AuditEventType.CREDENTIAL_REQUEST,
            req_id=req_id,
            actor_id="doctor@clinic.org",
            metadata={"reason": "Routine access"}
        )
        
        # Hashes should differ due to different metadata
        assert result1["content_hash"] != result2["content_hash"], \
            "Different metadata should produce different hashes"
    
    def test_optional_metadata_accepted(self, finalizer):
        """Test that metadata parameter is optional"""
        req_id = "REQ-20251110-OPT-001"
        
        # Record event without metadata
        result = finalizer.record_credential_event(
            event_type=AuditEventType.CREDENTIAL_REQUEST,
            req_id=req_id,
            actor_id="doctor@clinic.org"
        )
        
        assert "content_hash" in result
        assert "ledger_tx_id" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
