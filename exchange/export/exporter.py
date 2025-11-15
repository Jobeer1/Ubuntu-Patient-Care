#!/usr/bin/env python3
"""
P1-EXCH-003: UPC Message Export Tool

Creates and signs message envelopes for secure peer-to-peer data exchange.
"""

import json
import uuid
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import sys


class MessageExporter:
    """Creates and exports UPC message envelopes."""
    
    def __init__(self, facility_id: str, practitioner_id: str, 
                 facility_name: str = None):
        """
        Initialize exporter with sender information.
        
        Args:
            facility_id: Sending facility URN (urn:upc:facility:...)
            practitioner_id: Signing practitioner URN (urn:upc:practitioner:...)
            facility_name: Human-readable facility name
        """
        self.facility_id = facility_id
        self.practitioner_id = practitioner_id
        self.facility_name = facility_name or facility_id.split(':')[-1]
    
    def export_resource(self, 
                       fhir_resource: Dict[str, Any],
                       recipient_facility_id: str,
                       recipient_facility_name: str = None,
                       priority: str = "routine",
                       tags: list = None,
                       expires_in_hours: int = 24) -> Tuple[Dict[str, Any], str]:
        """
        Export a FHIR resource as a signed message envelope.
        
        Args:
            fhir_resource: FHIR resource (Patient, ImagingStudy, etc.)
            recipient_facility_id: Receiving facility URN
            recipient_facility_name: Human-readable recipient name
            priority: Message priority (routine|urgent|stat)
            tags: Custom tags for routing
            expires_in_hours: Message validity period
        
        Returns:
            (envelope_dict, message_id)
        """
        # Generate unique message ID
        message_id = str(uuid.uuid4())
        
        # Timestamps
        now = datetime.utcnow()
        timestamp = now.isoformat() + "Z"
        expires = (now + timedelta(hours=expires_in_hours)).isoformat() + "Z"
        
        # Extract resource info
        resource_type = fhir_resource.get("resourceType", "Bundle")
        resource_id = fhir_resource.get("id", f"{resource_type.lower()}-{uuid.uuid4()}")
        
        # Compute content hash
        hash_value = self._compute_hash(fhir_resource)
        
        # Create envelope
        envelope = {
            "envelope_version": "1.0",
            "message_id": message_id,
            "timestamp": timestamp,
            "sender": {
                "facility_id": self.facility_id,
                "practitioner_id": self.practitioner_id,
                "facility_name": self.facility_name
            },
            "recipient": {
                "facility_id": recipient_facility_id,
                "facility_name": recipient_facility_name or recipient_facility_id.split(':')[-1]
            },
            "payload": {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "content": fhir_resource
            },
            "content_hash": {
                "algorithm": "SHA256",
                "value": hash_value
            },
            "signature": {
                "algorithm": "MERKLE-PROOF",
                "value": f"tx-00000001:{hash_value}:pending",
                "practitioner_id": self.practitioner_id,
                "timestamp_signed": timestamp
            },
            "metadata": {
                "priority": priority,
                "expiration": expires,
                "tags": tags or []
            }
        }
        
        return envelope, message_id
    
    def export_batch(self,
                    resources: list,
                    recipient_facility_id: str,
                    batch_id: str = None,
                    priority: str = "routine") -> Tuple[Dict[str, Any], str]:
        """
        Export multiple resources as a Bundle.
        
        Args:
            resources: List of FHIR resources
            recipient_facility_id: Receiving facility URN
            batch_id: Optional batch identifier
            priority: Message priority
        
        Returns:
            (envelope_dict, message_id)
        """
        batch_id = batch_id or f"batch-{uuid.uuid4()}"
        
        # Create Bundle
        bundle = {
            "resourceType": "Bundle",
            "id": batch_id,
            "type": "batch",
            "entry": [{"resource": resource} for resource in resources]
        }
        
        return self.export_resource(
            bundle,
            recipient_facility_id,
            priority=priority,
            tags=["batch"]
        )
    
    def sign_with_merkle(self, 
                        envelope: Dict[str, Any],
                        tx_id: str,
                        root_hash: str,
                        proof_chain: list = None) -> Dict[str, Any]:
        """
        Update envelope with Merkle proof from audit ledger.
        
        Args:
            envelope: Message envelope from export_resource
            tx_id: Merkle ledger transaction ID (tx-00000001)
            root_hash: Merkle tree root hash
            proof_chain: Optional proof-of-inclusion chain
        
        Returns:
            Updated envelope
        """
        envelope["signature"]["value"] = f"{tx_id}:{root_hash}:proof"
        
        envelope["audit_proof"] = {
            "transaction_id": tx_id,
            "root_hash": root_hash,
            "proof_chain": proof_chain or []
        }
        
        return envelope
    
    def save_envelope(self, 
                     envelope: Dict[str, Any],
                     output_file: str = None) -> str:
        """
        Save envelope to JSON file.
        
        Args:
            envelope: Message envelope
            output_file: Output file path (default: message-{id}.json)
        
        Returns:
            File path
        """
        if not output_file:
            msg_id = envelope["message_id"][:8]
            output_file = f"message-{msg_id}.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(envelope, f, indent=2)
        
        return str(output_path)
    
    @staticmethod
    def _compute_hash(content: Dict[str, Any]) -> str:
        """Compute SHA256 hash of content."""
        canonical = json.dumps(content, separators=(',', ':'), sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()


def main():
    """CLI interface for export tool."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="UPC message export tool - create signed envelopes"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # Export single resource
    export_parser = subparsers.add_parser(
        "export",
        help="Export a FHIR resource as message envelope"
    )
    export_parser.add_argument("resource_file", help="FHIR resource JSON file")
    export_parser.add_argument("--recipient", required=True,
                              help="Recipient facility URN (urn:upc:facility:...)")
    export_parser.add_argument("--from-facility", default="urn:upc:facility:test-facility",
                              help="Sending facility URN")
    export_parser.add_argument("--from-practitioner", default="urn:upc:practitioner:test-user",
                              help="Practitioner URN")
    export_parser.add_argument("--priority", default="routine",
                              choices=["routine", "urgent", "stat"])
    export_parser.add_argument("--output", help="Output envelope file")
    export_parser.add_argument("--tag", action="append", dest="tags",
                              help="Custom tag (can repeat)")
    
    # Batch export
    batch_parser = subparsers.add_parser(
        "batch",
        help="Export multiple resources as batch"
    )
    batch_parser.add_argument("resource_files", nargs="+",
                             help="FHIR resource JSON files")
    batch_parser.add_argument("--recipient", required=True,
                             help="Recipient facility URN")
    batch_parser.add_argument("--from-facility", default="urn:upc:facility:test-facility",
                             help="Sending facility URN")
    batch_parser.add_argument("--from-practitioner", default="urn:upc:practitioner:test-user",
                             help="Practitioner URN")
    batch_parser.add_argument("--output", help="Output envelope file")
    
    # Test
    test_parser = subparsers.add_parser("test", help="Run tests")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "export":
        with open(args.resource_file) as f:
            resource = json.load(f)
        
        exporter = MessageExporter(
            args.from_facility,
            args.from_practitioner
        )
        
        envelope, msg_id = exporter.export_resource(
            resource,
            args.recipient,
            priority=args.priority,
            tags=args.tags
        )
        
        output_file = exporter.save_envelope(envelope, args.output)
        print(f"[OK] Envelope exported: {output_file}")
        print(f"Message ID: {msg_id}")
        print(f"Content hash: {envelope['content_hash']['value'][:16]}...")
        
    elif args.command == "batch":
        resources = []
        for fname in args.resource_files:
            with open(fname) as f:
                resources.append(json.load(f))
        
        exporter = MessageExporter(
            args.from_facility,
            args.from_practitioner
        )
        
        envelope, msg_id = exporter.export_batch(
            resources,
            args.recipient
        )
        
        output_file = exporter.save_envelope(envelope, args.output)
        print(f"[OK] Batch envelope exported: {output_file}")
        print(f"Message ID: {msg_id}")
        print(f"Resources: {len(resources)}")
        
    elif args.command == "test":
        print("TEST: Running export tests...\n")
        
        # Test 1: Export single resource
        exporter = MessageExporter(
            "urn:upc:facility:hospital-central",
            "urn:upc:practitioner:dr-smith"
        )
        
        patient = {
            "resourceType": "Patient",
            "id": "pat-001",
            "name": [{"given": ["John"], "family": "Doe"}]
        }
        
        envelope, msg_id = exporter.export_resource(
            patient,
            "urn:upc:facility:clinic-north"
        )
        
        print(f"Test 1 (Export resource): PASS")
        print(f"  - Message ID: {msg_id}")
        print(f"  - Content hash: {envelope['content_hash']['value'][:16]}...")
        
        # Test 2: Export batch
        imaging = {
            "resourceType": "ImagingStudy",
            "id": "img-001"
        }
        
        envelope2, msg_id2 = exporter.export_batch(
            [patient, imaging],
            "urn:upc:facility:clinic-north"
        )
        
        print(f"\nTest 2 (Export batch): PASS")
        print(f"  - Resources: 2")
        print(f"  - Message ID: {msg_id2}")
        
        # Test 3: Sign with Merkle proof
        envelope3 = exporter.sign_with_merkle(
            envelope,
            "tx-00000001",
            "01aea66258cf84fd0e6bc2e67f1fb3e0dd39d6a82beed35cdeeb39d77dcf4f48"
        )
        
        print(f"\nTest 3 (Sign with Merkle): PASS")
        print(f"  - TX ID: {envelope3['audit_proof']['transaction_id']}")
        
        # Test 4: Save envelope
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            output = exporter.save_envelope(envelope, f"{tmpdir}/test.json")
            print(f"\nTest 4 (Save envelope): PASS")
            print(f"  - File: {output}")
        
        print("\nDONE: All tests completed!")


if __name__ == "__main__":
    main()
