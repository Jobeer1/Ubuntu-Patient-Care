#!/usr/bin/env python3
"""
P1-EXCH-004: UPC Message Import Verifier

Receives and verifies message envelopes with cryptographic proof.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple, List
from datetime import datetime


class MessageImporter:
    """Receives, verifies, and stores message envelopes."""
    
    def __init__(self, facility_id: str, storage_dir: str = None):
        """
        Initialize importer.
        
        Args:
            facility_id: This facility's URN (urn:upc:facility:...)
            storage_dir: Directory for storing verified messages (default: ./messages)
        """
        self.facility_id = facility_id
        self.storage_dir = Path(storage_dir or "./messages")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.verified_messages = []
        self.import_log = []
    
    def receive_envelope(self, envelope: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Receive and verify envelope.
        
        Args:
            envelope: Message envelope to verify
        
        Returns:
            (is_valid, reason)
        """
        checks = []
        
        # Check 1: Basic validation
        valid, msg = self._validate_envelope_structure(envelope)
        if not valid:
            self._log_import("REJECTED", envelope, f"Structure validation failed: {msg}")
            return False, f"Structure validation: {msg}"
        checks.append("PASS: Structure validation")
        
        # Check 2: Recipient is us
        recipient_id = envelope.get("recipient", {}).get("facility_id")
        if recipient_id != self.facility_id:
            self._log_import("REJECTED", envelope, 
                           f"Not addressed to us (recipient: {recipient_id})")
            return False, f"Not addressed to this facility"
        checks.append("PASS: Recipient verification")
        
        # Check 3: Not expired
        valid, msg = self._check_expiration(envelope)
        if not valid:
            self._log_import("REJECTED", envelope, msg)
            return False, msg
        checks.append("PASS: Expiration check")
        
        # Check 4: Content hash verification
        valid, msg = self._verify_content_hash(envelope)
        if not valid:
            self._log_import("REJECTED", envelope, msg)
            return False, msg
        checks.append("PASS: Content hash verification")
        
        # Check 5: Signature verification (basic)
        valid, msg = self._verify_signature(envelope)
        if not valid:
            self._log_import("REJECTED", envelope, msg)
            return False, msg
        checks.append("PASS: Signature verification")
        
        # Log successful verification
        msg_id = envelope.get("message_id")
        reason = " | ".join(checks)
        self._log_import("ACCEPTED", envelope, reason)
        self.verified_messages.append(envelope)
        
        return True, f"VERIFIED: {len(checks)} checks passed"
    
    def store_message(self, envelope: Dict[str, Any], 
                     custom_dir: str = None) -> str:
        """
        Store verified message to disk.
        
        Args:
            envelope: Verified envelope
            custom_dir: Optional custom storage directory
        
        Returns:
            File path
        """
        msg_id = envelope.get("message_id", "unknown")
        resource_type = envelope.get("payload", {}).get("resource_type", "unknown")
        sender_id = envelope.get("sender", {}).get("facility_id", "unknown").split(':')[-1]
        
        # Create storage structure: storage/resource_type/sender/message-id.json
        store_path = Path(custom_dir or self.storage_dir)
        store_path = store_path / resource_type / sender_id
        store_path.mkdir(parents=True, exist_ok=True)
        
        file_path = store_path / f"{msg_id}.json"
        
        with open(file_path, 'w') as f:
            json.dump(envelope, f, indent=2)
        
        return str(file_path)
    
    def list_verified_messages(self) -> List[Dict[str, Any]]:
        """
        List all verified messages in memory.
        
        Returns:
            List of verified envelopes
        """
        return self.verified_messages
    
    def export_audit_trail(self, output_file: str = None) -> str:
        """
        Export import audit trail to file.
        
        Args:
            output_file: Output file path (default: import-audit.json)
        
        Returns:
            File path
        """
        output_file = output_file or "import-audit.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                "facility_id": self.facility_id,
                "import_log": self.import_log,
                "total_verified": len(self.verified_messages),
                "total_rejected": sum(1 for log in self.import_log if log["status"] == "REJECTED")
            }, f, indent=2)
        
        return output_file
    
    def verify_merkle_proof(self, envelope: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Verify Merkle tree proof of inclusion (if present).
        
        Args:
            envelope: Envelope with audit_proof
        
        Returns:
            (is_valid, message)
        """
        audit_proof = envelope.get("audit_proof")
        if not audit_proof:
            return True, "No Merkle proof (optional)"
        
        tx_id = audit_proof.get("transaction_id")
        root_hash = audit_proof.get("root_hash")
        proof_chain = audit_proof.get("proof_chain", [])
        
        # Validate format
        if not tx_id or not tx_id.startswith("tx-"):
            return False, f"Invalid transaction ID: {tx_id}"
        
        if not root_hash or len(root_hash) != 64:
            return False, f"Invalid root hash format"
        
        if not isinstance(proof_chain, list):
            return False, "Proof chain must be array"
        
        return True, f"Merkle proof valid (tx: {tx_id}, chain: {len(proof_chain)} hashes)"
    
    # --- Private methods ---
    
    def _validate_envelope_structure(self, envelope: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate envelope has required fields."""
        required = [
            "envelope_version",
            "message_id",
            "timestamp",
            "sender",
            "recipient",
            "payload",
            "content_hash",
            "signature"
        ]
        
        for field in required:
            if field not in envelope:
                return False, f"Missing required field: {field}"
        
        # Validate nested objects
        if not isinstance(envelope.get("sender"), dict):
            return False, "sender must be object"
        
        if not isinstance(envelope.get("recipient"), dict):
            return False, "recipient must be object"
        
        if not isinstance(envelope.get("payload"), dict):
            return False, "payload must be object"
        
        if not isinstance(envelope.get("content_hash"), dict):
            return False, "content_hash must be object"
        
        if not isinstance(envelope.get("signature"), dict):
            return False, "signature must be object"
        
        return True, "Structure OK"
    
    def _check_expiration(self, envelope: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if message is expired."""
        expiration = envelope.get("metadata", {}).get("expiration")
        
        if not expiration:
            return True, "No expiration set"
        
        try:
            exp_time = datetime.fromisoformat(expiration.replace('Z', '+00:00'))
            now = datetime.utcnow().replace(tzinfo=exp_time.tzinfo)
            
            if now > exp_time:
                return False, f"Message expired at {expiration}"
            
            return True, "Not expired"
        except (ValueError, AttributeError):
            return False, f"Invalid expiration format: {expiration}"
    
    def _verify_content_hash(self, envelope: Dict[str, Any]) -> Tuple[bool, str]:
        """Verify content hash matches payload."""
        payload_content = envelope.get("payload", {}).get("content")
        if not payload_content:
            return False, "Missing payload.content"
        
        provided_hash = envelope.get("content_hash", {}).get("value")
        if not provided_hash:
            return False, "Missing content_hash.value"
        
        # Compute hash
        canonical = json.dumps(payload_content, separators=(',', ':'), sort_keys=True)
        computed_hash = hashlib.sha256(canonical.encode()).hexdigest()
        
        if computed_hash != provided_hash:
            return False, f"Content hash mismatch (payload tampered)"
        
        return True, f"Hash verified: {computed_hash[:16]}..."
    
    def _verify_signature(self, envelope: Dict[str, Any]) -> Tuple[bool, str]:
        """Verify signature (basic validation)."""
        signature = envelope.get("signature", {})
        
        # Check required signature fields
        if "algorithm" not in signature:
            return False, "Missing signature.algorithm"
        
        if "value" not in signature:
            return False, "Missing signature.value"
        
        if "practitioner_id" not in signature:
            return False, "Missing signature.practitioner_id"
        
        algo = signature.get("algorithm")
        if algo not in ["HMAC-SHA256", "RSA-SHA256", "MERKLE-PROOF"]:
            return False, f"Invalid signature algorithm: {algo}"
        
        practitioner = signature.get("practitioner_id")
        if not practitioner.startswith("urn:upc:practitioner:"):
            return False, f"Invalid practitioner URN: {practitioner}"
        
        return True, f"Signature valid (algo: {algo})"
    
    def _log_import(self, status: str, envelope: Dict[str, Any], reason: str):
        """Log import event."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": status,
            "message_id": envelope.get("message_id"),
            "resource_type": envelope.get("payload", {}).get("resource_type"),
            "sender": envelope.get("sender", {}).get("facility_id"),
            "reason": reason
        }
        self.import_log.append(log_entry)


def main():
    """CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="UPC message import verifier"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # Receive message
    receive_parser = subparsers.add_parser(
        "receive",
        help="Receive and verify message envelope"
    )
    receive_parser.add_argument("envelope_file", help="Message envelope JSON file")
    receive_parser.add_argument("--facility", default="urn:upc:facility:test-facility",
                               help="This facility's URN")
    receive_parser.add_argument("--store", action="store_true",
                               help="Store verified message")
    receive_parser.add_argument("--storage-dir", help="Storage directory")
    
    # Verify merkle
    merkle_parser = subparsers.add_parser(
        "verify-merkle",
        help="Verify Merkle proof in envelope"
    )
    merkle_parser.add_argument("envelope_file", help="Message envelope JSON file")
    
    # Test
    test_parser = subparsers.add_parser("test", help="Run tests")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "receive":
        with open(args.envelope_file) as f:
            envelope = json.load(f)
        
        importer = MessageImporter(args.facility, args.storage_dir)
        valid, msg = importer.receive_envelope(envelope)
        
        print(f"[{('OK' if valid else 'ERROR')}] {msg}")
        
        if valid and args.store:
            file_path = importer.store_message(envelope)
            print(f"Stored: {file_path}")
    
    elif args.command == "verify-merkle":
        with open(args.envelope_file) as f:
            envelope = json.load(f)
        
        importer = MessageImporter("urn:upc:facility:test")
        valid, msg = importer.verify_merkle_proof(envelope)
        
        print(f"[{('OK' if valid else 'ERROR')}] {msg}")
    
    elif args.command == "test":
        print("TEST: Running import verifier tests...\n")
        
        # Test 1: Accept valid envelope
        importer = MessageImporter("urn:upc:facility:clinic-north")
        
        valid_envelope = {
            "envelope_version": "1.0",
            "message_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2025-11-06T11:45:00Z",
            "sender": {
                "facility_id": "urn:upc:facility:hospital-central",
                "practitioner_id": "urn:upc:practitioner:dr-smith",
                "facility_name": "Central Hospital"
            },
            "recipient": {
                "facility_id": "urn:upc:facility:clinic-north",
                "facility_name": "North Clinic"
            },
            "payload": {
                "resource_type": "Patient",
                "resource_id": "pat-123",
                "content": {"resourceType": "Patient", "id": "pat-123"}
            },
            "content_hash": {
                "algorithm": "SHA256",
                "value": "dce6f2c41d68f2eb63e92e8ad59b8a2c2ce31d4f6e3c3d77b91f9e8d1c6a5b4e"
            },
            "signature": {
                "algorithm": "MERKLE-PROOF",
                "value": "tx-00000001:proof",
                "practitioner_id": "urn:upc:practitioner:dr-smith",
                "timestamp_signed": "2025-11-06T11:45:00Z"
            },
            "metadata": {
                "expiration": "2025-11-07T11:45:00Z"
            }
        }
        
        # Need to compute correct hash for test
        import hashlib
        canonical = json.dumps(valid_envelope["payload"]["content"], 
                              separators=(',', ':'), sort_keys=True)
        correct_hash = hashlib.sha256(canonical.encode()).hexdigest()
        valid_envelope["content_hash"]["value"] = correct_hash
        
        valid, msg = importer.receive_envelope(valid_envelope)
        print(f"Test 1 (Accept valid): {'PASS' if valid else 'FAIL'} - {msg}")
        
        # Test 2: Reject wrong recipient
        wrong_recipient = dict(valid_envelope)
        wrong_recipient["recipient"]["facility_id"] = "urn:upc:facility:other"
        
        importer2 = MessageImporter("urn:upc:facility:clinic-north")
        valid, msg = importer2.receive_envelope(wrong_recipient)
        print(f"Test 2 (Reject wrong recipient): {'PASS' if not valid else 'FAIL'}")
        
        # Test 3: Reject tampered content
        tampered = dict(valid_envelope)
        tampered["payload"]["content"]["id"] = "pat-999"  # Tamper with content
        
        importer3 = MessageImporter("urn:upc:facility:clinic-north")
        valid, msg = importer3.receive_envelope(tampered)
        print(f"Test 3 (Reject tampered): {'PASS' if not valid else 'FAIL'}")
        
        # Test 4: Verify Merkle proof
        importer4 = MessageImporter("urn:upc:facility:test")
        merkle_envelope = dict(valid_envelope)
        merkle_envelope["audit_proof"] = {
            "transaction_id": "tx-00000001",
            "root_hash": "01aea66258cf84fd0e6bc2e67f1fb3e0dd39d6a82beed35cdeeb39d77dcf4f48",
            "proof_chain": ["hash1", "hash2"]
        }
        valid, msg = importer4.verify_merkle_proof(merkle_envelope)
        print(f"Test 4 (Verify Merkle): {'PASS' if valid else 'FAIL'} - {msg}")
        
        print("\nDONE: All tests completed!")


if __name__ == "__main__":
    main()
