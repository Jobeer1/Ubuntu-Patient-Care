"""
Unit tests for Emergency Credential Request API (credentials.py)

Tests request creation, validation, status tracking, and Merkle audit logging.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_medical_server.api.credentials import (
    CredentialRequest,
    CredentialRequestStatus,
    CredentialRequestManager
)


class TestCredentialRequestStatus:
    """Test credential request status enum"""
    
    def test_status_values_exist(self):
        """Verify all status values are defined"""
        assert CredentialRequestStatus.PENDING.value == "PENDING"
        assert CredentialRequestStatus.APPROVED.value == "APPROVED"
        assert CredentialRequestStatus.RETRIEVED.value == "RETRIEVED"
        assert CredentialRequestStatus.EXPIRED.value == "EXPIRED"
        assert CredentialRequestStatus.DENIED.value == "DENIED"


class TestCredentialRequest:
    """Test CredentialRequest model"""
    
    def test_create_credential_request(self):
        """Test creating a credential request"""
        request = CredentialRequest(
            req_id="REQ-20251110-ABC123",
            requester_id="doctor@clinic.org",
            reason="Emergency patient access",
            target={"vault": "subnet-1", "path": "pacs/admin"},
            patient_context={"patient_id": "PAT-123", "study_id": "STUDY-456"}
        )
        
        assert request.req_id == "REQ-20251110-ABC123"
        assert request.requester_id == "doctor@clinic.org"
        assert request.status == CredentialRequestStatus.PENDING
        assert request.target["vault"] == "subnet-1"
    
    def test_request_to_dict(self):
        """Test converting request to dictionary"""
        request = CredentialRequest(
            req_id="REQ-20251110-ABC123",
            requester_id="doctor@clinic.org",
            reason="Emergency access",
            target={"vault": "subnet-1", "path": "pacs/admin"},
            patient_context={"patient_id": "PAT-123", "study_id": "STUDY-456"}
        )
        
        request_dict = request.to_dict()
        
        assert request_dict["req_id"] == "REQ-20251110-ABC123"
        assert request_dict["status"] == "PENDING"
        assert "created_ts" in request_dict
        assert "expires_ts" in request_dict
    
    def test_request_expiration_check(self):
        """Test that request expiration is calculated correctly"""
        now = datetime.utcnow().isoformat()
        request = CredentialRequest(
            req_id="REQ-20251110-ABC123",
            requester_id="doctor@clinic.org",
            reason="Emergency access",
            target={"vault": "subnet-1", "path": "pacs/admin"},
            patient_context={"patient_id": "PAT-123", "study_id": "STUDY-456"},
            created_ts=now,
            sla_seconds=60
        )
        
        # Request should not be expired immediately
        assert not request.is_expired()
    
    def test_request_expired_after_sla(self):
        """Test that request is marked expired after SLA"""
        # Create request with past timestamp
        past_time = (datetime.utcnow() - timedelta(seconds=130)).isoformat()
        request = CredentialRequest(
            req_id="REQ-20251110-ABC123",
            requester_id="doctor@clinic.org",
            reason="Emergency access",
            target={"vault": "subnet-1", "path": "pacs/admin"},
            patient_context={"patient_id": "PAT-123", "study_id": "STUDY-456"},
            created_ts=past_time,
            sla_seconds=120
        )
        
        # Request should be expired
        assert request.is_expired()


class TestCredentialRequestManager:
    """Test CredentialRequestManager"""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """Create a manager with temporary ledger"""
        ledger_path = str(tmp_path / "test_credentials.ledger")
        return CredentialRequestManager(ledger_path)
    
    def test_create_request_success(self, manager):
        """Test successful request creation"""
        result = manager.create_request(
            requester_id="doctor@clinic.org",
            reason="Emergency patient imaging",
            target={"vault": "subnet-1", "path": "pacs/admin"},
            patient_context={"patient_id": "PAT-123", "study_id": "STUDY-456"}
        )
        
        # Verify response structure
        assert "req_id" in result
        assert result["status"] == "PENDING"
        assert "created_ts" in result
        assert "expires_ts" in result
        assert "merkle_proof" in result
        
        # Verify merkle proof
        assert "ledger_tx_id" in result["merkle_proof"]
        assert "content_hash" in result["merkle_proof"]
    
    def test_create_request_validates_requester_id(self, manager):
        """Test that requester_id is validated"""
        with pytest.raises(ValueError, match="requester_id"):
            manager.create_request(
                requester_id="",
                reason="Emergency access",
                target={"vault": "subnet-1", "path": "pacs/admin"},
                patient_context={"patient_id": "PAT-123"}
            )
    
    def test_create_request_validates_reason(self, manager):
        """Test that reason is validated"""
        with pytest.raises(ValueError, match="reason"):
            manager.create_request(
                requester_id="doctor@clinic.org",
                reason="",
                target={"vault": "subnet-1", "path": "pacs/admin"},
                patient_context={"patient_id": "PAT-123"}
            )
    
    def test_create_request_validates_target(self, manager):
        """Test that target format is validated"""
        with pytest.raises(ValueError, match="target"):
            manager.create_request(
                requester_id="doctor@clinic.org",
                reason="Emergency access",
                target={"invalid": "format"},
                patient_context={"patient_id": "PAT-123"}
            )
    
    def test_get_request(self, manager):
        """Test retrieving a request by ID"""
        # Create request
        created = manager.create_request(
            requester_id="doctor@clinic.org",
            reason="Emergency access",
            target={"vault": "subnet-1", "path": "pacs/admin"},
            patient_context={"patient_id": "PAT-123", "study_id": "STUDY-456"}
        )
        req_id = created["req_id"]
        
        # Retrieve request
        retrieved = manager.get_request(req_id)
        
        assert retrieved is not None
        assert retrieved["req_id"] == req_id
        assert retrieved["status"] == "PENDING"
    
    def test_get_nonexistent_request_returns_none(self, manager):
        """Test that getting nonexistent request returns None"""
        result = manager.get_request("REQ-NONEXISTENT")
        assert result is None
    
    def test_list_pending_requests(self, manager):
        """Test listing pending requests"""
        # Create multiple requests
        req1 = manager.create_request(
            requester_id="doctor1@clinic.org",
            reason="Access 1",
            target={"vault": "subnet-1", "path": "pacs/admin"},
            patient_context={"patient_id": "PAT-1"}
        )
        
        req2 = manager.create_request(
            requester_id="doctor2@clinic.org",
            reason="Access 2",
            target={"vault": "subnet-2", "path": "nas/backup"},
            patient_context={"patient_id": "PAT-2"}
        )
        
        # List pending
        pending = manager.list_pending_requests()
        
        assert len(pending) >= 2
        assert any(r["req_id"] == req1["req_id"] for r in pending)
        assert any(r["req_id"] == req2["req_id"] for r in pending)
    
    def test_update_request_status(self, manager):
        """Test updating request status"""
        # Create request
        created = manager.create_request(
            requester_id="doctor@clinic.org",
            reason="Emergency access",
            target={"vault": "subnet-1", "path": "pacs/admin"},
            patient_context={"patient_id": "PAT-123"}
        )
        req_id = created["req_id"]
        
        # Update to approved
        updated = manager.update_request_status(
            req_id,
            CredentialRequestStatus.APPROVED,
            {"approver": "owner@clinic.org"}
        )
        
        assert updated["status"] == "APPROVED"
        assert "merkle_proofs" in updated["merkle_proof"]
    
    def test_update_nonexistent_request_raises_error(self, manager):
        """Test that updating nonexistent request raises ValueError"""
        with pytest.raises(ValueError, match="not found"):
            manager.update_request_status(
                "REQ-NONEXISTENT",
                CredentialRequestStatus.APPROVED
            )


class TestCredentialRequestFlow:
    """Test complete credential request flow"""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """Create a manager with temporary ledger"""
        ledger_path = str(tmp_path / "test_flow.ledger")
        return CredentialRequestManager(ledger_path)
    
    def test_complete_request_approval_flow(self, manager):
        """Test: create request -> list -> approve -> retrieve"""
        
        # Step 1: Clinician creates emergency access request
        request_result = manager.create_request(
            requester_id="clinician@clinic.org",
            reason="Emergency patient hemorrhage - STAT",
            target={"vault": "subnet-1", "path": "pacs/admin"},
            patient_context={
                "patient_id": "PAT-99999",
                "study_id": "STUDY-STAT-001"
            }
        )
        
        req_id = request_result["req_id"]
        assert request_result["status"] == "PENDING"
        
        # Step 2: Owner retrieves pending requests
        pending = manager.list_pending_requests()
        assert any(r["req_id"] == req_id for r in pending)
        
        # Step 3: Owner approves request
        approved = manager.update_request_status(
            req_id,
            CredentialRequestStatus.APPROVED,
            {"approver": "owner@clinic.org", "ttl_seconds": 300}
        )
        
        assert approved["status"] == "APPROVED"
        
        # Step 4: Check pending list - should not include approved request
        pending = manager.list_pending_requests()
        assert not any(r["req_id"] == req_id for r in pending)
        
        # Step 5: Update to retrieved status
        retrieved = manager.update_request_status(
            req_id,
            CredentialRequestStatus.RETRIEVED,
            {"retrieved_by": "mcp-agent-subnet-1"}
        )
        
        assert retrieved["status"] == "RETRIEVED"
    
    def test_multiple_status_transitions_tracked(self, manager):
        """Test that all status transitions are audited"""
        
        # Create request
        req = manager.create_request(
            requester_id="doctor@clinic.org",
            reason="Emergency access",
            target={"vault": "subnet-1", "path": "pacs/admin"},
            patient_context={"patient_id": "PAT-123"}
        )
        req_id = req["req_id"]
        
        # Transition: PENDING -> APPROVED
        approved = manager.update_request_status(
            req_id,
            CredentialRequestStatus.APPROVED
        )
        
        # Transition: APPROVED -> RETRIEVED
        retrieved = manager.update_request_status(
            req_id,
            CredentialRequestStatus.RETRIEVED
        )
        
        # Verify audit trail
        assert retrieved["status"] == "RETRIEVED"
        assert "merkle_proofs" in retrieved["merkle_proof"]
        assert len(retrieved["merkle_proof"]["merkle_proofs"]) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
