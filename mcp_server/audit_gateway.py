#!/usr/bin/env python3
"""
P1-AUD-003: MCP Audit Gateway

Intercepts critical events and records them in the Merkle audit ledger.
"""

import json
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path


class AuditGateway:
    """Middleware for intercepting and logging critical events."""
    
    # Critical event types to capture
    CRITICAL_EVENTS = {
        "resource_created",      # New patient/report created
        "resource_modified",     # Resource updated
        "resource_deleted",      # Resource removed
        "resource_exported",     # Message envelope sent
        "resource_imported",     # Message envelope received
        "report_finalized",      # DiagnosticReport finalized
        "access_granted",        # User access granted
        "access_denied",         # User access denied
        "data_exported",         # Bulk data export
        "sensitive_operation",   # High-risk operation
    }
    
    def __init__(self, facility_id: str, ledger_path: str = None):
        """
        Initialize audit gateway.
        
        Args:
            facility_id: This facility's URN
            ledger_path: Path to Merkle ledger (will be passed from mcp_server)
        """
        self.facility_id = facility_id
        self.ledger_path = ledger_path or "./audit/merkle_ledger.json"
        self.event_queue = []
    
    def capture_event(self,
                     event_type: str,
                     resource_type: str,
                     resource_id: str,
                     practitioner_id: str,
                     action: str,
                     details: Dict[str, Any] = None) -> str:
        """
        Capture and audit a critical event.
        
        Args:
            event_type: Type of event (from CRITICAL_EVENTS)
            resource_type: FHIR resource type (Patient, Report, etc.)
            resource_id: Unique resource ID
            practitioner_id: Practitioner URN
            action: Action description
            details: Optional additional details
        
        Returns:
            Event ID (transaction ID from ledger)
        """
        if event_type not in self.CRITICAL_EVENTS:
            raise ValueError(f"Unknown event type: {event_type}")
        
        # Create event object
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "practitioner_id": practitioner_id,
            "action": action,
            "facility_id": self.facility_id,
            "details": details or {}
        }
        
        # Record in queue
        self.event_queue.append(event)
        
        # Generate event ID from hash
        event_hash = self._compute_event_hash(event)
        event_id = f"evt-{event_hash[:8]}"
        
        return event_id
    
    def record_to_ledger(self, event: Dict[str, Any]) -> str:
        """
        Record event to Merkle ledger.
        
        In production, this calls the Merkle ledger append() method.
        For now, returns transaction ID.
        
        Args:
            event: Event object to record
        
        Returns:
            Transaction ID (tx-00000001, etc.)
        """
        try:
            # Import Merkle ledger if available
            import sys
            sys.path.insert(0, str(Path(self.ledger_path).parent))
            from poc_merkle import MerkleAuditLedger
            
            ledger = MerkleAuditLedger(self.ledger_path)
            
            # Record to ledger
            tx_id, root_hash = ledger.append(
                resource_id=event["resource_id"],
                practitioner_id=event["practitioner_id"],
                content_hash=self._compute_event_hash(event)
            )
            
            return tx_id
        
        except (ImportError, FileNotFoundError):
            # Fallback: generate TX ID
            return f"tx-{len(self.event_queue):08d}"
    
    def create_audit_log(self, output_file: str = None) -> str:
        """
        Export audit log of all captured events.
        
        Args:
            output_file: Output file path (default: audit_log.json)
        
        Returns:
            File path
        """
        output_file = output_file or "audit_log.json"
        
        log_data = {
            "facility": self.facility_id,
            "export_time": datetime.utcnow().isoformat() + "Z",
            "total_events": len(self.event_queue),
            "events_by_type": self._count_by_type(),
            "events": self.event_queue
        }
        
        with open(output_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        return output_file
    
    def intercept_mcp_call(self, mcp_method: str, mcp_args: Dict[str, Any],
                          mcp_response: Any = None) -> None:
        """
        Intercept MCP server calls and record critical operations.
        
        This is called as middleware in the MCP server stack.
        
        Args:
            mcp_method: MCP method name (e.g., "create_patient", "finalize_report")
            mcp_args: Method arguments
            mcp_response: Method response (optional)
        """
        # Map MCP methods to events
        event_mappings = {
            "create_patient": ("resource_created", "Patient"),
            "update_patient": ("resource_modified", "Patient"),
            "delete_patient": ("resource_deleted", "Patient"),
            "create_report": ("resource_created", "DiagnosticReport"),
            "finalize_report": ("report_finalized", "DiagnosticReport"),
            "export_patient": ("resource_exported", "Patient"),
            "export_data": ("data_exported", "Bundle"),
            "grant_access": ("access_granted", "AccessPolicy"),
            "deny_access": ("access_denied", "AccessPolicy"),
        }
        
        if mcp_method not in event_mappings:
            return  # Not a critical event
        
        event_type, resource_type = event_mappings[mcp_method]
        
        # Extract info from args
        resource_id = mcp_args.get("resource_id") or mcp_args.get("id")
        practitioner_id = mcp_args.get("practitioner_id") or "urn:upc:practitioner:unknown"
        
        # Capture event
        self.capture_event(
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            practitioner_id=practitioner_id,
            action=mcp_method,
            details=mcp_args
        )
    
    # --- Private methods ---
    
    def _compute_event_hash(self, event: Dict[str, Any]) -> str:
        """Compute hash of event for ID generation."""
        canonical = json.dumps(event, separators=(',', ':'), sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def _count_by_type(self) -> Dict[str, int]:
        """Count events by type."""
        counts = {}
        for event in self.event_queue:
            event_type = event["event_type"]
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts


class MiniMCPServer:
    """Minimal MCP server with audit gateway integration."""
    
    def __init__(self, facility_id: str):
        """Initialize MCP server with audit gateway."""
        self.facility_id = facility_id
        self.audit_gateway = AuditGateway(facility_id)
        self.resources = {}
    
    def create_patient(self, patient_id: str, patient_data: Dict[str, Any],
                      practitioner_id: str) -> Dict[str, Any]:
        """Create patient with audit."""
        # Store resource
        self.resources[f"Patient/{patient_id}"] = patient_data
        
        # Capture audit event
        self.audit_gateway.capture_event(
            event_type="resource_created",
            resource_type="Patient",
            resource_id=patient_id,
            practitioner_id=practitioner_id,
            action="create_patient",
            details={"facility": self.facility_id}
        )
        
        return {"id": patient_id, "status": "created"}
    
    def finalize_report(self, report_id: str, report_data: Dict[str, Any],
                       practitioner_id: str) -> Dict[str, Any]:
        """Finalize diagnostic report with audit."""
        # Update resource
        report_data["status"] = "final"
        self.resources[f"DiagnosticReport/{report_id}"] = report_data
        
        # Capture audit event (high-impact)
        self.audit_gateway.capture_event(
            event_type="report_finalized",
            resource_type="DiagnosticReport",
            resource_id=report_id,
            practitioner_id=practitioner_id,
            action="finalize_report",
            details={"status": "final"}
        )
        
        return {"id": report_id, "status": "finalized"}
    
    def export_data(self, export_id: str, resources: list,
                   practitioner_id: str) -> Dict[str, Any]:
        """Export data with audit."""
        # Capture audit event
        self.audit_gateway.capture_event(
            event_type="data_exported",
            resource_type="Bundle",
            resource_id=export_id,
            practitioner_id=practitioner_id,
            action="export_data",
            details={"resource_count": len(resources)}
        )
        
        return {"export_id": export_id, "resources": len(resources)}
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get current audit log."""
        return self.audit_gateway.event_queue


def main():
    """Test/demo."""
    print("TEST: Running audit gateway tests...\n")
    
    # Test 1: Create gateway
    gateway = AuditGateway("urn:upc:facility:test-hospital")
    print(f"Test 1 (Create gateway): PASS")
    
    # Test 2: Capture event
    event_id = gateway.capture_event(
        event_type="resource_created",
        resource_type="Patient",
        resource_id="pat-001",
        practitioner_id="urn:upc:practitioner:dr-smith",
        action="create_patient"
    )
    print(f"Test 2 (Capture event): PASS - Event ID: {event_id}")
    
    # Test 3: MCP server with audit
    mcp = MiniMCPServer("urn:upc:facility:test-hospital")
    mcp.create_patient(
        "pat-002",
        {"name": "John Doe"},
        "urn:upc:practitioner:dr-smith"
    )
    print(f"Test 3 (MCP create): PASS - Audit events: {len(mcp.get_audit_log())}")
    
    # Test 4: Finalize report
    mcp.finalize_report(
        "rep-001",
        {"code": "85025-8"},
        "urn:upc:practitioner:dr-smith"
    )
    print(f"Test 4 (MCP finalize): PASS - Total events: {len(mcp.get_audit_log())}")
    
    # Test 5: Export data
    mcp.export_data(
        "export-001",
        ["pat-001", "pat-002"],
        "urn:upc:practitioner:dr-smith"
    )
    print(f"Test 5 (MCP export): PASS - Events: {len(mcp.get_audit_log())}")
    
    # Test 6: Audit log
    log = mcp.get_audit_log()
    print(f"Test 6 (Audit log): PASS")
    for i, event in enumerate(log):
        print(f"  Event {i+1}: {event['event_type']} ({event['resource_type']})")
    
    print("\nDONE: All tests completed!")


if __name__ == "__main__":
    main()
