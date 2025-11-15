"""
Emergency Credential Request API - Phase 1

Provides endpoints for requesting emergency access to credentials/secrets.

Endpoints:
- POST /api/v1/credentials/request - Create emergency credential request
- GET /api/v1/credentials/request/{req_id} - Get request status
- GET /api/v1/credentials/requests - List pending requests (owner only)

Each request is immediately Merkle-stamped in audit ledger.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from audit.report_finalizer import ReportFinalizer, AuditEventType


class CredentialRequestStatus(str, Enum):
    """Status values for credential requests"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    RETRIEVED = "RETRIEVED"
    EXPIRED = "EXPIRED"
    DENIED = "DENIED"
    CANCELLED = "CANCELLED"


class CredentialRequest:
    """
    Represents a single credential access request with audit trail.
    
    Attributes:
        req_id: Unique request identifier
        requester_id: User requesting access (email/username)
        reason: Justification for emergency access
        target: {vault, path} - what credential is needed
        patient_context: {patient_id, study_id} - clinical context
        status: Current status (PENDING, APPROVED, etc.)
        created_ts: When request was created
        expires_ts: When request expires (SLA timeout)
        merkle_proof: Audit ledger proof
    """
    
    def __init__(
        self,
        req_id: str,
        requester_id: str,
        reason: str,
        target: Dict[str, str],
        patient_context: Dict[str, str],
        status: CredentialRequestStatus = CredentialRequestStatus.PENDING,
        created_ts: Optional[str] = None,
        expires_ts: Optional[str] = None,
        merkle_proof: Optional[Dict] = None,
        sla_seconds: int = 120  # Default 2-minute SLA
    ):
        self.req_id = req_id
        self.requester_id = requester_id
        self.reason = reason
        self.target = target
        self.patient_context = patient_context
        self.status = status
        self.created_ts = created_ts or datetime.utcnow().isoformat()
        
        # Calculate expiration based on SLA
        expires_dt = datetime.fromisoformat(self.created_ts) + timedelta(seconds=sla_seconds)
        self.expires_ts = expires_ts or expires_dt.isoformat()
        
        self.merkle_proof = merkle_proof or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "req_id": self.req_id,
            "requester_id": self.requester_id,
            "reason": self.reason,
            "target": self.target,
            "patient_context": self.patient_context,
            "status": self.status.value,
            "created_ts": self.created_ts,
            "expires_ts": self.expires_ts,
            "merkle_proof": self.merkle_proof
        }
    
    def is_expired(self) -> bool:
        """Check if request has expired based on SLA"""
        expires_dt = datetime.fromisoformat(self.expires_ts)
        return datetime.utcnow() > expires_dt


class CredentialRequestManager:
    """
    Manages credential requests with Merkle audit logging.
    
    Responsibilities:
    - Create new requests
    - Track request status
    - Merkle-stamp all operations
    - Validate permissions
    """
    
    def __init__(self, ledger_path: str = "audit.ledger"):
        """Initialize with path to audit ledger"""
        self.finalizer = ReportFinalizer(ledger_path)
        self.requests: Dict[str, CredentialRequest] = {}
    
    def create_request(
        self,
        requester_id: str,
        reason: str,
        target: Dict[str, str],
        patient_context: Dict[str, str],
        sla_seconds: int = 120
    ) -> Dict[str, Any]:
        """
        Create a new emergency credential request.
        
        Process:
        1. Generate unique request ID
        2. Create request object
        3. Merkle-stamp request in audit ledger
        4. Return request with proof
        
        Args:
            requester_id: User making the request (clinician email)
            reason: Justification for emergency access
            target: {"vault": str, "path": str} - credential location
            patient_context: {"patient_id": str, "study_id": str} - clinical context
            sla_seconds: Time before auto-escalation (default 120s)
            
        Returns:
            Dictionary with req_id, status, timestamps, and merkle_proof
            
        Raises:
            ValueError: If inputs are invalid
        """
        # Validate inputs
        if not requester_id or not isinstance(requester_id, str):
            raise ValueError("requester_id must be a non-empty string")
        
        if not reason or not isinstance(reason, str):
            raise ValueError("reason must be a non-empty string")
        
        if not isinstance(target, dict) or "vault" not in target or "path" not in target:
            raise ValueError("target must be dict with 'vault' and 'path' keys")
        
        if not isinstance(patient_context, dict):
            raise ValueError("patient_context must be a dictionary")
        
        # Generate unique request ID
        random_suffix = secrets.token_hex(6)  # 12 hex chars
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        req_id = f"REQ-{timestamp}-{random_suffix}"
        
        # Create request object
        request = CredentialRequest(
            req_id=req_id,
            requester_id=requester_id,
            reason=reason,
            target=target,
            patient_context=patient_context,
            sla_seconds=sla_seconds
        )
        
        # Merkle-stamp the request in audit ledger
        audit_result = self.finalizer.record_credential_event(
            event_type=AuditEventType.CREDENTIAL_REQUEST,
            req_id=req_id,
            actor_id=requester_id,
            metadata={
                "reason": reason,
                "target_vault": target["vault"],
                "target_path": target["path"],
                "patient_id": patient_context.get("patient_id"),
                "study_id": patient_context.get("study_id")
            }
        )
        
        # Attach merkle proof to request
        request.merkle_proof = {
            "ledger_tx_id": audit_result["ledger_tx_id"],
            "content_hash": audit_result["content_hash"],
            "timestamp": audit_result["timestamp"]
        }
        
        # Store request in memory (in production: database)
        self.requests[req_id] = request
        
        return request.to_dict()
    
    def get_request(self, req_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a credential request.
        
        Args:
            req_id: Request ID to look up
            
        Returns:
            Request dictionary or None if not found
        """
        if req_id not in self.requests:
            return None
        
        request = self.requests[req_id]
        
        # Auto-expire if past SLA
        if request.is_expired() and request.status == CredentialRequestStatus.PENDING:
            request.status = CredentialRequestStatus.EXPIRED
        
        return request.to_dict()
    
    def list_pending_requests(self) -> list:
        """
        List all pending credential requests.
        
        Used by owner to review requests waiting for approval.
        
        Returns:
            List of pending request dictionaries
        """
        pending = []
        for req_id, request in self.requests.items():
            # Auto-expire if past SLA
            if request.is_expired() and request.status == CredentialRequestStatus.PENDING:
                request.status = CredentialRequestStatus.EXPIRED
            
            if request.status == CredentialRequestStatus.PENDING:
                pending.append(request.to_dict())
        
        return pending
    
    def update_request_status(
        self,
        req_id: str,
        new_status: CredentialRequestStatus,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Update request status and Merkle-stamp the change.
        
        Args:
            req_id: Request to update
            new_status: New status value
            metadata: Additional data to include in audit (approval info, etc.)
            
        Returns:
            Updated request dictionary
            
        Raises:
            ValueError: If request not found
        """
        if req_id not in self.requests:
            raise ValueError(f"Request {req_id} not found")
        
        request = self.requests[req_id]
        old_status = request.status
        request.status = new_status
        
        # Determine event type based on new status
        event_type_map = {
            CredentialRequestStatus.APPROVED: AuditEventType.CREDENTIAL_APPROVED,
            CredentialRequestStatus.RETRIEVED: AuditEventType.CREDENTIAL_RETRIEVED,
            CredentialRequestStatus.DENIED: "CREDENTIAL_REQUEST_DENIED",
            CredentialRequestStatus.CANCELLED: "CREDENTIAL_REQUEST_CANCELLED",
        }
        
        event_type = event_type_map.get(
            new_status,
            f"CREDENTIAL_STATUS_CHANGED_{old_status}_TO_{new_status}"
        )
        
        # Merkle-stamp the status change
        audit_result = self.finalizer.record_credential_event(
            event_type=event_type,
            req_id=req_id,
            actor_id="system",  # In production: use actual actor ID
            metadata=metadata or {
                "old_status": old_status.value,
                "new_status": new_status.value
            }
        )
        
        # Store new audit proof
        if "merkle_proofs" not in request.merkle_proof:
            request.merkle_proof["merkle_proofs"] = []
        
        request.merkle_proof["merkle_proofs"].append({
            "status": new_status.value,
            "ledger_tx_id": audit_result["ledger_tx_id"],
            "timestamp": audit_result["timestamp"]
        })
        
        return request.to_dict()


# Example usage
if __name__ == "__main__":
    # Create manager
    manager = CredentialRequestManager("test_credentials.ledger")
    
    # Example: Clinician requests emergency access to PACS credentials
    request_result = manager.create_request(
        requester_id="dr_smith@clinic.org",
        reason="Emergency patient imaging - hemorrhage suspected",
        target={
            "vault": "subnet-1",
            "path": "pacs/admin"
        },
        patient_context={
            "patient_id": "PAT-20251110-001",
            "study_id": "STUDY-20251110-CT-001"
        }
    )
    
    print(f"Created request: {request_result['req_id']}")
    print(f"Status: {request_result['status']}")
    print(f"Expires: {request_result['expires_ts']}")
    print(f"Merkle Proof: {request_result['merkle_proof']}")
    
    # Check request status
    status = manager.get_request(request_result['req_id'])
    print(f"\nRequest status: {status['status']}")
    
    # Simulate owner approval
    approval_result = manager.update_request_status(
        request_result['req_id'],
        CredentialRequestStatus.APPROVED,
        {"approver": "owner@clinic.org"}
    )
    print(f"\nAfter approval: {approval_result['status']}")
    print(f"Merkle proofs: {approval_result['merkle_proof']}")
