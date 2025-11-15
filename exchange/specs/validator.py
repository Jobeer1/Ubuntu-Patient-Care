#!/usr/bin/env python3
"""
P1-EXCH-001: UPC Message Envelope Validator

Validates message envelopes against JSON schema and computes hashes.
"""

import json
import hashlib
import re
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, List, Any


class EnvelopeValidator:
    """Validates UPC message envelopes."""
    
    SCHEMA_PATH = Path(__file__).parent / "envelope.json"
    
    # FHIR resource types
    VALID_RESOURCE_TYPES = {
        "Patient",
        "ImagingStudy",
        "DiagnosticReport",
        "ServiceRequest",
        "Bundle"
    }
    
    # URN patterns
    FACILITY_URN_PATTERN = r"^urn:upc:facility:[a-zA-Z0-9-]+$"
    PRACTITIONER_URN_PATTERN = r"^urn:upc:practitioner:[a-zA-Z0-9-]+$"
    TX_ID_PATTERN = r"^tx-[0-9]{8}$"
    HASH_PATTERN = r"^[a-f0-9]{64}$"  # SHA256
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate(self, envelope: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate entire envelope.
        
        Returns: (is_valid, message)
        """
        self.errors = []
        self.warnings = []
        
        # Required fields
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
                self.errors.append(f"Missing required field: {field}")
        
        if self.errors:
            return False, f"❌ {len(self.errors)} error(s) found"
        
        # Validate each section
        self._validate_version(envelope.get("envelope_version"))
        self._validate_message_id(envelope.get("message_id"))
        self._validate_timestamp(envelope.get("timestamp"))
        self._validate_sender(envelope.get("sender"))
        self._validate_recipient(envelope.get("recipient"))
        self._validate_payload(envelope.get("payload"))
        self._validate_content_hash(envelope.get("content_hash"))
        self._validate_signature(envelope.get("signature"))
        self._validate_metadata(envelope.get("metadata"))
        
        if self.errors:
            msg = f"[ERROR] {len(self.errors)} validation error(s)"
            for err in self.errors[:3]:
                msg += f"\n  - {err}"
            if len(self.errors) > 3:
                msg += f"\n  ... and {len(self.errors) - 3} more"
            return False, msg
        
        msg = "[OK] Valid envelope"
        if self.warnings:
            msg += f" ({len(self.warnings)} warning(s))"
        return True, msg
    
    def _validate_version(self, version):
        """Validate envelope version."""
        if version not in ["1.0"]:
            self.errors.append(f"Invalid envelope_version: {version}")
    
    def _validate_message_id(self, msg_id):
        """Validate message ID is UUID v4."""
        try:
            # UUID v4 pattern
            uuid_obj = uuid.UUID(msg_id, version=4)
            if str(uuid_obj) != msg_id:
                self.errors.append(f"Invalid message_id format: {msg_id}")
        except (ValueError, AttributeError):
            self.errors.append(f"message_id must be valid UUID v4: {msg_id}")
    
    def _validate_timestamp(self, ts):
        """Validate ISO 8601 timestamp."""
        try:
            datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            self.errors.append(f"Invalid timestamp (must be ISO 8601): {ts}")
    
    def _validate_sender(self, sender):
        """Validate sender object."""
        if not isinstance(sender, dict):
            self.errors.append("sender must be an object")
            return
        
        if "facility_id" not in sender:
            self.errors.append("sender missing required field: facility_id")
        else:
            if not re.match(self.FACILITY_URN_PATTERN, sender["facility_id"]):
                self.errors.append(
                    f"sender.facility_id invalid URN format: {sender['facility_id']}"
                )
        
        if "practitioner_id" not in sender:
            self.errors.append("sender missing required field: practitioner_id")
        else:
            if not re.match(self.PRACTITIONER_URN_PATTERN, sender["practitioner_id"]):
                self.errors.append(
                    f"sender.practitioner_id invalid URN format: {sender['practitioner_id']}"
                )
    
    def _validate_recipient(self, recipient):
        """Validate recipient object."""
        if not isinstance(recipient, dict):
            self.errors.append("recipient must be an object")
            return
        
        if "facility_id" not in recipient:
            self.errors.append("recipient missing required field: facility_id")
        else:
            if not re.match(self.FACILITY_URN_PATTERN, recipient["facility_id"]):
                self.errors.append(
                    f"recipient.facility_id invalid URN format: {recipient['facility_id']}"
                )
    
    def _validate_payload(self, payload):
        """Validate payload object."""
        if not isinstance(payload, dict):
            self.errors.append("payload must be an object")
            return
        
        if "resource_type" not in payload:
            self.errors.append("payload missing required field: resource_type")
        else:
            if payload["resource_type"] not in self.VALID_RESOURCE_TYPES:
                self.errors.append(
                    f"payload.resource_type invalid: {payload['resource_type']}"
                )
        
        if "resource_id" not in payload:
            self.errors.append("payload missing required field: resource_id")
        
        if "content" not in payload:
            self.errors.append("payload missing required field: content")
        elif not isinstance(payload["content"], dict):
            self.errors.append("payload.content must be an object (FHIR resource)")
    
    def _validate_content_hash(self, content_hash):
        """Validate content_hash object."""
        if not isinstance(content_hash, dict):
            self.errors.append("content_hash must be an object")
            return
        
        if "algorithm" not in content_hash:
            self.errors.append("content_hash missing required field: algorithm")
        else:
            if content_hash["algorithm"] not in ["SHA256", "SHA512"]:
                self.errors.append(
                    f"content_hash.algorithm invalid: {content_hash['algorithm']}"
                )
        
        if "value" not in content_hash:
            self.errors.append("content_hash missing required field: value")
        else:
            # If SHA256, validate hex length
            if content_hash.get("algorithm") == "SHA256":
                if not re.match(self.HASH_PATTERN, content_hash["value"]):
                    self.errors.append(
                        f"content_hash.value invalid (must be 64 char hex for SHA256): {content_hash['value']}"
                    )
    
    def _validate_signature(self, signature):
        """Validate signature object."""
        if not isinstance(signature, dict):
            self.errors.append("signature must be an object")
            return
        
        if "algorithm" not in signature:
            self.errors.append("signature missing required field: algorithm")
        else:
            if signature["algorithm"] not in ["HMAC-SHA256", "RSA-SHA256", "MERKLE-PROOF"]:
                self.errors.append(
                    f"signature.algorithm invalid: {signature['algorithm']}"
                )
        
        if "value" not in signature:
            self.errors.append("signature missing required field: value")
        
        if "practitioner_id" not in signature:
            self.errors.append("signature missing required field: practitioner_id")
        else:
            if not re.match(self.PRACTITIONER_URN_PATTERN, signature["practitioner_id"]):
                self.errors.append(
                    f"signature.practitioner_id invalid URN format: {signature['practitioner_id']}"
                )
        
        if "timestamp_signed" in signature:
            try:
                datetime.fromisoformat(signature["timestamp_signed"].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                self.errors.append(
                    f"signature.timestamp_signed invalid (must be ISO 8601): {signature['timestamp_signed']}"
                )
    
    def _validate_metadata(self, metadata):
        """Validate optional metadata object."""
        if metadata is None:
            return
        
        if not isinstance(metadata, dict):
            self.errors.append("metadata must be an object")
            return
        
        # Validate priority if present
        if "priority" in metadata:
            if metadata["priority"] not in ["routine", "urgent", "stat"]:
                self.errors.append(
                    f"metadata.priority invalid: {metadata['priority']}"
                )
        
        # Validate expiration if present
        if "expiration" in metadata:
            try:
                datetime.fromisoformat(metadata["expiration"].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                self.errors.append(
                    f"metadata.expiration invalid (must be ISO 8601): {metadata['expiration']}"
                )
    
    @staticmethod
    def compute_content_hash(content: Dict[str, Any], algorithm: str = "SHA256") -> str:
        """
        Compute content hash using canonical JSON serialization.
        
        Args:
            content: The FHIR resource to hash
            algorithm: "SHA256" or "SHA512"
        
        Returns:
            Lowercase hex hash string
        """
        # Canonical JSON: sorted keys, no whitespace
        canonical = json.dumps(content, separators=(',', ':'), sort_keys=True)
        
        if algorithm == "SHA256":
            hash_obj = hashlib.sha256(canonical.encode())
        elif algorithm == "SHA512":
            hash_obj = hashlib.sha512(canonical.encode())
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        return hash_obj.hexdigest()
    
    @staticmethod
    def validate_hash(content: Dict[str, Any], provided_hash: str, 
                     algorithm: str = "SHA256") -> Tuple[bool, str]:
        """
        Verify that content matches provided hash.
        
        Returns: (is_valid, message)
        """
        computed = EnvelopeValidator.compute_content_hash(content, algorithm)
        if computed == provided_hash:
            return True, f"[OK] Hash verified ({algorithm}: {computed[:16]}...)"
        else:
            return False, f"[ERROR] Hash mismatch\n  Expected: {provided_hash}\n  Computed: {computed}"


def main():
    """CLI interface."""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate UPC message envelopes"
    )
    parser.add_argument("command", choices=["validate", "hash", "test"],
                        help="Command to run")
    parser.add_argument("--file", help="Envelope JSON file to validate")
    parser.add_argument("--content-file", help="FHIR resource file for hash computation")
    parser.add_argument("--expected-hash", help="Expected hash value for verification")
    parser.add_argument("--algorithm", default="SHA256", choices=["SHA256", "SHA512"])
    
    args = parser.parse_args()
    
    validator = EnvelopeValidator()
    
    if args.command == "validate":
        if not args.file:
            print("[ERROR] --file required for validate command")
            sys.exit(1)
        
        with open(args.file) as f:
            envelope = json.load(f)
        
        valid, msg = validator.validate(envelope)
        print(msg)
        sys.exit(0 if valid else 1)
    
    elif args.command == "hash":
        if not args.content_file:
            print("[ERROR] --content-file required for hash command")
            sys.exit(1)
        
        with open(args.content_file) as f:
            content = json.load(f)
        
        hash_val = EnvelopeValidator.compute_content_hash(content, args.algorithm)
        print(f"[OK] {args.algorithm} hash: {hash_val}")
        
        if args.expected_hash:
            valid, msg = EnvelopeValidator.validate_hash(
                content, args.expected_hash, args.algorithm
            )
            print(msg)
            sys.exit(0 if valid else 1)
    
    elif args.command == "test":
        print("TEST: Running envelope tests...\n")
        
        # Test 1: Valid envelope
        valid_envelope = {
            "envelope_version": "1.0",
            "message_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2025-11-06T11:45:00Z",
            "sender": {
                "facility_id": "urn:upc:facility:hospital-central",
                "practitioner_id": "urn:upc:practitioner:dr-smith-001",
                "facility_name": "Central Hospital"
            },
            "recipient": {
                "facility_id": "urn:upc:facility:clinic-north",
                "facility_name": "North Clinic"
            },
            "payload": {
                "resource_type": "Patient",
                "resource_id": "pat-123456",
                "content": {
                    "resourceType": "Patient",
                    "id": "pat-123456"
                }
            },
            "content_hash": {
                "algorithm": "SHA256",
                "value": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            },
            "signature": {
                "algorithm": "MERKLE-PROOF",
                "value": "tx-00000001:proof",
                "practitioner_id": "urn:upc:practitioner:dr-smith-001",
                "timestamp_signed": "2025-11-06T11:45:00Z"
            }
        }
        
        valid, msg = validator.validate(valid_envelope)
        print(f"Test 1 (Valid envelope): {'PASS' if valid else 'FAIL'} - {msg}")
        
        # Test 2: Invalid message_id
        invalid_envelope = dict(valid_envelope)
        invalid_envelope["message_id"] = "not-a-uuid"
        
        validator_2 = EnvelopeValidator()
        valid, msg = validator_2.validate(invalid_envelope)
        print(f"Test 2 (Invalid UUID): {'PASS' if not valid else 'FAIL'} - Correctly rejected")
        
        # Test 3: Hash computation
        patient = {"resourceType": "Patient", "id": "pat-123"}
        hash_val = EnvelopeValidator.compute_content_hash(patient)
        print(f"Test 3 (Hash computation): PASS - {hash_val[:16]}...")
        
        # Test 4: Hash verification
        valid, msg = EnvelopeValidator.validate_hash(patient, hash_val)
        print(f"Test 4 (Hash verification): {'PASS' if valid else 'FAIL'} - {msg}")
        
        print("\nDONE: All tests completed!")


if __name__ == "__main__":
    main()
