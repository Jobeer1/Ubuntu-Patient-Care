#!/usr/bin/env python3
"""
Owner Approval CLI for Emergency Credential Requests

Command-line tool for offline owner approval with Ed25519 digital signatures.

Usage:
    approve-request --req-id REQ-20251110-120000-abc123 \
                    --owner owner1@hospital.com \
                    --sign /etc/mcp-server/owner-keys/owner1.key \
                    --output approval.json \
                    --ttl 300

Output (approval.json):
{
    "req_id": "REQ-20251110-120000-abc123",
    "approver": "owner1@hospital.com",
    "approved_ts": "2025-11-10T12:00:00Z",
    "signature": "base64-encoded-ed25519-signature",
    "ttl_seconds": 300
}
"""

import argparse
import json
import sys
import os
from pathlib import Path
from getpass import getpass
from typing import Optional

try:
    from mcp_medical_server.services.signature_service import ApprovalSignatureFactory
except ImportError:
    # Fallback for testing
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from services.signature_service import ApprovalSignatureFactory


def validate_req_id(req_id: str) -> bool:
    """
    Validate request ID format.
    
    Expected format: REQ-YYYYMMDD-HHMMSS-{12-hex-random}
    Example: REQ-20251110-120000-abc123def456
    
    Args:
        req_id: Request ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    parts = req_id.split('-')
    if len(parts) != 4:
        return False
    
    if parts[0] != 'REQ':
        return False
    
    # Check date format (YYYYMMDD)
    if len(parts[1]) != 8 or not parts[1].isdigit():
        return False
    
    # Check time format (HHMMSS)
    if len(parts[2]) != 6 or not parts[2].isdigit():
        return False
    
    # Check random part (hex)
    if not all(c in '0123456789abcdefABCDEF' for c in parts[3]):
        return False
    
    return True


def main():
    """Main entry point for CLI"""
    
    parser = argparse.ArgumentParser(
        description="Sign a credential request approval offline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sign approval with passphrase prompt
  %(prog)s --req-id REQ-20251110-120000-abc123 \\
           --owner owner1@hospital.com \\
           --sign /etc/mcp-server/owner-keys/owner1.key \\
           --output approval.json
  
  # Sign with custom TTL
  %(prog)s --req-id REQ-20251110-120000-abc123 \\
           --owner owner1@hospital.com \\
           --sign /etc/mcp-server/owner-keys/owner1.key \\
           --output approval.json \\
           --ttl 600
  
  # Sign with passphrase from environment
  export APPROVE_PASSPHRASE="secret123"
  %(prog)s --req-id REQ-20251110-120000-abc123 \\
           --owner owner1@hospital.com \\
           --sign /etc/mcp-server/owner-keys/owner1.key \\
           --output approval.json
        """
    )
    
    parser.add_argument(
        '--req-id',
        required=True,
        help='Credential request ID (format: REQ-YYYYMMDD-HHMMSS-{hex})'
    )
    
    parser.add_argument(
        '--owner',
        required=True,
        help='Owner/approver ID (e.g., owner1@hospital.com)'
    )
    
    parser.add_argument(
        '--sign',
        required=True,
        dest='key_path',
        help='Path to owner private key (passphrase protected)'
    )
    
    parser.add_argument(
        '--output',
        required=True,
        help='Output JSON file with signature'
    )
    
    parser.add_argument(
        '--ttl',
        type=int,
        default=300,
        help='Token time-to-live in seconds (default: 300)'
    )
    
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify signature after creation'
    )
    
    args = parser.parse_args()
    
    # Validate request ID
    if not validate_req_id(args.req_id):
        print(f"Error: Invalid request ID format: {args.req_id}", file=sys.stderr)
        print(f"Expected format: REQ-YYYYMMDD-HHMMSS-{{hex}}", file=sys.stderr)
        sys.exit(1)
    
    # Check key file exists
    if not os.path.exists(args.key_path):
        print(f"Error: Private key file not found: {args.key_path}", file=sys.stderr)
        sys.exit(1)
    
    # Get passphrase
    passphrase = os.environ.get('APPROVE_PASSPHRASE')
    if not passphrase:
        passphrase = getpass(f"Enter passphrase for {args.key_path}: ")
        if not passphrase:
            print("Error: Passphrase required", file=sys.stderr)
            sys.exit(1)
    
    # Create signature factory
    factory = ApprovalSignatureFactory()
    
    # Sign approval
    try:
        approval = factory.sign_approval(
            req_id=args.req_id,
            approver_id=args.owner,
            private_key_path=args.key_path,
            passphrase=passphrase,
            ttl_seconds=args.ttl
        )
    except ValueError as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    # Write output file
    try:
        output_dir = os.path.dirname(args.output)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        with open(args.output, 'w') as f:
            json.dump(approval, f, indent=2)
        
        print(f"✓ Approval signed successfully", file=sys.stderr)
        print(f"✓ Output written to: {args.output}", file=sys.stderr)
        print(f"✓ Approver: {approval['approver']}", file=sys.stderr)
        print(f"✓ Timestamp: {approval['approved_ts']}", file=sys.stderr)
        print(f"✓ TTL: {approval['ttl_seconds']} seconds", file=sys.stderr)
        
    except IOError as e:
        print(f"Error: Failed to write output file: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    # Optional: verify signature
    if args.verify:
        print(f"\n✓ Verifying signature...", file=sys.stderr)
        
        # Extract public key path from private key path
        public_key_path = args.key_path.replace('.key', '.pub')
        
        if not os.path.exists(public_key_path):
            print(f"Note: Public key not found at {public_key_path}, skipping verification", file=sys.stderr)
        else:
            is_valid = factory.verify_approval(approval, public_key_path)
            if is_valid:
                print(f"✓ Signature verified successfully", file=sys.stderr)
            else:
                print(f"✗ Signature verification FAILED", file=sys.stderr)
                sys.exit(1)
    
    # Print approval to stdout for piping
    print(json.dumps(approval, indent=2))
    sys.exit(0)


if __name__ == '__main__':
    main()
