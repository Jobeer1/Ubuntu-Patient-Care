"""
P1-AUD-004: Hash & Stamp Integration for Report Generation

Integrates Merkle audit hashing with report generation.
When a report is finalized, this module:
1. Computes a cryptographic hash of the report content
2. Stores the hash in the Merkle audit ledger
3. Adds an audit stamp to the report metadata

This provides:
- Non-repudiation: Who finalized the report and when
- Tamper detection: Any modification can be detected
- Audit trail: Complete history in Merkle ledger
- Compliance: Immutable evidence for healthcare regulations
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from audit.ledger_wrapper import MerkleAuditLedger


# Event types for audit logging
class AuditEventType:
    """Constants for audit event types"""
    # Report events
    REPORT_FINALIZED = "REPORT_FINALIZED"
    
    # Credential retrieval events (Phase 1)
    CREDENTIAL_REQUEST = "CREDENTIAL_REQUEST"
    CREDENTIAL_APPROVED = "CREDENTIAL_APPROVED"
    CREDENTIAL_RETRIEVED = "CREDENTIAL_RETRIEVED"
    CREDENTIAL_EPHEMERAL_CREATED = "CREDENTIAL_EPHEMERAL_CREATED"
    
    # Additional credential events (future phases)
    CREDENTIAL_APPROVAL_ESCALATED = "CREDENTIAL_APPROVAL_ESCALATED"
    CREDENTIAL_EPHEMERAL_EXPIRED = "CREDENTIAL_EPHEMERAL_EXPIRED"
    CREDENTIAL_DEBRIEF_SUBMITTED = "CREDENTIAL_DEBRIEF_SUBMITTED"


@dataclass
class ReportAuditStamp:
    """Audit stamp attached to a finalized report"""
    
    report_id: str
    content_hash: str
    timestamp: str
    practitioner_id: str
    ledger_tx_id: str
    signature: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "report_id": self.report_id,
            "content_hash": self.content_hash,
            "timestamp": self.timestamp,
            "practitioner_id": self.practitioner_id,
            "ledger_tx_id": self.ledger_tx_id,
            "signature": self.signature
        }


class ReportFinalizer:
    """
    Finalizes diagnostic reports with audit stamps and Merkle hashing.
    
    Usage:
        finalizer = ReportFinalizer(ledger_path="/path/to/audit.ledger")
        stamp = finalizer.finalize_report(
            report_id="REPORT-2025-001",
            content=report_data,
            practitioner_id="DOC-123"
        )
        # Report metadata now includes audit stamp
    """
    
    def __init__(self, ledger_path: str = "audit.ledger"):
        """Initialize with path to Merkle audit ledger"""
        self.ledger = MerkleAuditLedger(ledger_path)
    
    def compute_content_hash(self, content: Dict[str, Any]) -> str:
        """
        Compute SHA256 hash of report content.
        
        Uses canonical JSON serialization to ensure consistent hashing
        regardless of key ordering.
        
        Args:
            content: Report content dictionary
            
        Returns:
            Hex-encoded SHA256 hash
        """
        # Canonical JSON: sort keys, no whitespace
        json_str = json.dumps(content, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def finalize_report(
        self,
        report_id: str,
        content: Dict[str, Any],
        practitioner_id: str,
        signature: str = ""
    ) -> ReportAuditStamp:
        """
        Finalize a report with audit stamp and Merkle hashing.
        
        Process:
        1. Compute content hash
        2. Record in Merkle ledger (returns TX ID)
        3. Create audit stamp with metadata
        4. Return stamp for addition to report
        
        Args:
            report_id: Unique identifier for the report
            content: Report content (dictionary)
            practitioner_id: ID of practitioner finalizing
            signature: Optional digital signature
            
        Returns:
            ReportAuditStamp with all audit information
            
        Raises:
            ValueError: If report_id or content is invalid
        """
        if not report_id or not isinstance(report_id, str):
            raise ValueError("report_id must be a non-empty string")
        
        if not isinstance(content, dict):
            raise ValueError("content must be a dictionary")
        
        if not practitioner_id or not isinstance(practitioner_id, str):
            raise ValueError("practitioner_id must be a non-empty string")
        
        # Compute hash
        content_hash = self.compute_content_hash(content)
        
        # Create audit event
        timestamp = datetime.utcnow().isoformat()
        audit_event = {
            "event_type": "REPORT_FINALIZED",
            "report_id": report_id,
            "content_hash": content_hash,
            "practitioner_id": practitioner_id,
            "timestamp": timestamp
        }
        
        # Store in Merkle ledger (returns TX ID)
        result = self.ledger.append(
            resource_id=report_id,
            practitioner_id=practitioner_id,
            content_hash=content_hash
        )
        ledger_tx_id = result['tx_id']
    
    def record_credential_event(
        self,
        event_type: str,
        req_id: str,
        actor_id: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Record credential retrieval events in Merkle audit ledger.
        
        Supports: CREDENTIAL_REQUEST, CREDENTIAL_APPROVED, CREDENTIAL_RETRIEVED,
                  CREDENTIAL_EPHEMERAL_CREATED, and others.
        
        Args:
            event_type: One of AuditEventType constants
            req_id: Request ID (unique identifier)
            actor_id: User/actor ID performing action
            metadata: Additional event metadata (vault, path, patient_id, etc.)
            
        Returns:
            Dictionary with ledger_tx_id and timestamp
            
        Raises:
            ValueError: If event_type is invalid
        """
        # Validate event type
        valid_types = {
            AuditEventType.CREDENTIAL_REQUEST,
            AuditEventType.CREDENTIAL_APPROVED,
            AuditEventType.CREDENTIAL_RETRIEVED,
            AuditEventType.CREDENTIAL_EPHEMERAL_CREATED,
            AuditEventType.CREDENTIAL_APPROVAL_ESCALATED,
            AuditEventType.CREDENTIAL_EPHEMERAL_EXPIRED,
            AuditEventType.CREDENTIAL_DEBRIEF_SUBMITTED,
        }
        
        if event_type not in valid_types:
            raise ValueError(f"Invalid event_type: {event_type}. Must be one of {valid_types}")
        
        if not req_id or not isinstance(req_id, str):
            raise ValueError("req_id must be a non-empty string")
        
        if not actor_id or not isinstance(actor_id, str):
            raise ValueError("actor_id must be a non-empty string")
        
        # Create credential audit event
        timestamp = datetime.utcnow().isoformat()
        
        # Build event metadata
        event_metadata = {
            "event_type": event_type,
            "req_id": req_id,
            "actor_id": actor_id,
            "timestamp": timestamp
        }
        
        # Add optional metadata
        if metadata:
            event_metadata.update(metadata)
        
        # Compute hash of event metadata
        content_hash = self.compute_content_hash(event_metadata)
        
        # Store in Merkle ledger
        result = self.ledger.append(
            resource_id=req_id,
            practitioner_id=actor_id,
            content_hash=content_hash
        )
        
        return {
            "ledger_tx_id": result['tx_id'],
            "timestamp": timestamp,
            "content_hash": content_hash,
            "event_type": event_type
        }
        
        # Create audit stamp
        stamp = ReportAuditStamp(
            report_id=report_id,
            content_hash=content_hash,
            timestamp=timestamp,
            practitioner_id=practitioner_id,
            ledger_tx_id=ledger_tx_id,
            signature=signature
        )
        
        return stamp
    
    def verify_report_stamp(
        self,
        report_id: str,
        content: Dict[str, Any],
        stamp: ReportAuditStamp
    ) -> bool:
        """
        Verify a report's audit stamp and content integrity.
        
        Checks:
        1. Report ID matches stamp
        2. Content hash matches stamp (tamper detection)
        3. Merkle ledger contains matching event
        
        Args:
            report_id: Unique identifier for the report
            content: Current report content
            stamp: ReportAuditStamp from report metadata
            
        Returns:
            True if stamp is valid, False otherwise
        """
        # Check report ID
        if report_id != stamp.report_id:
            return False
        
        # Compute current hash
        current_hash = self.compute_content_hash(content)
        
        # Check hash matches (tamper detection)
        if current_hash != stamp.content_hash:
            return False
        
        # Verify in Merkle ledger
        verified_result = self.ledger.verify(stamp.ledger_tx_id)
        
        # Handle both dict and bool returns
        if isinstance(verified_result, dict):
            return verified_result.get('valid', False)
        return bool(verified_result)
    
    def get_audit_trail(self, report_id: str) -> list:
        """
        Get complete audit trail for a report.
        
        Returns all events related to a specific report from the ledger.
        
        Args:
            report_id: Unique identifier for the report
            
        Returns:
            List of audit events for the report
        """
        events = []
        for entry in self.ledger.entries:
            if entry.get("resource_id") == report_id:
                events.append(entry)
        return events


# Example usage
if __name__ == "__main__":
    # Create finalizer
    finalizer = ReportFinalizer("test_audit.ledger")
    
    # Example report
    report_data = {
        "patient_id": "PAT-123",
        "imaging_study_id": "STUDY-456",
        "findings": "No abnormalities detected",
        "conclusion": "Normal study"
    }
    
    # Finalize report
    stamp = finalizer.finalize_report(
        report_id="REPORT-2025-001",
        content=report_data,
        practitioner_id="DOC-789",
        signature="sig_abc123"
    )
    
    print(f"Report finalized: {stamp.report_id}")
    print(f"Content hash: {stamp.content_hash}")
    print(f"Ledger TX ID: {stamp.ledger_tx_id}")
    print(f"Audit stamp: {json.dumps(stamp.to_dict(), indent=2)}")
    
    # Verify stamp
    is_valid = finalizer.verify_report_stamp(stamp.report_id, report_data, stamp)
    print(f"Stamp valid: {is_valid}")
    
    # Get audit trail
    trail = finalizer.get_audit_trail(stamp.report_id)
    print(f"Audit trail entries: {len(trail)}")
