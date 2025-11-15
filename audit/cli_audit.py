#!/usr/bin/env python3
"""
CLI tool for interacting with the Merkle Audit Ledger (P1-AUD-002)

Usage:
    upc-audit append --resource <id> --practitioner <id> --hash <hash>
    upc-audit verify --tx-id <id>
    upc-audit export --format json --output <path>
    upc-audit stats
    upc-audit list [--limit 10]
"""

import argparse
import json
import sys
from pathlib import Path
from audit.ledger_wrapper import get_default_ledger


def cmd_append(args):
    """Append a new entry to the ledger"""
    ledger = get_default_ledger(args.storage)
    
    result = ledger.append(
        resource_id=args.resource,
        practitioner_id=args.practitioner,
        content_hash=args.hash
    )
    
    print(json.dumps(result, indent=2))
    return 0


def cmd_verify(args):
    """Verify an entry in the ledger"""
    ledger = get_default_ledger(args.storage)
    
    result = ledger.verify(args.tx_id)
    
    print(json.dumps(result, indent=2, default=str))
    return 0 if result['valid'] else 1


def cmd_export(args):
    """Export ledger to file"""
    ledger = get_default_ledger(args.storage)
    
    export_data = ledger.export(output_format=args.format)
    
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(export_data)
        print(f"✓ Exported to {args.output}")
    else:
        print(export_data)
    
    return 0


def cmd_stats(args):
    """Display ledger statistics"""
    ledger = get_default_ledger(args.storage)
    
    stats = ledger.get_stats()
    print(json.dumps(stats, indent=2))
    return 0


def cmd_list(args):
    """List recent entries from the ledger"""
    ledger = get_default_ledger(args.storage)
    
    limit = args.limit if args.limit else 10
    entries = ledger.entries[-limit:]
    
    print(f"Recent {len(entries)} entries (total: {len(ledger.entries)}):")
    print("-" * 100)
    
    for entry in entries:
        print(f"  {entry['tx_id']}: {entry['resource_id']} "
              f"(by {entry['practitioner_id']}) @ {entry['timestamp']}")
    
    print("-" * 100)
    print(f"Current root hash: {ledger.root_hash}")
    
    return 0


def cmd_test(args):
    """Run a quick test of the ledger"""
    print("Testing Merkle Audit Ledger...")
    
    ledger = get_default_ledger("test_ledger_temp.json")
    
    # Clear any existing test data
    ledger.entries = []
    ledger.tx_counter = 0
    ledger.root_hash = None
    
    print("\n1. Appending test entries...")
    test_entries = [
        ("patient-001", "doc-001", "hash_report_001"),
        ("patient-002", "doc-002", "hash_report_002"),
        ("patient-001", "doc-003", "hash_report_003"),
    ]
    
    tx_ids = []
    for resource, practitioner, content_hash in test_entries:
        result = ledger.append(resource, practitioner, content_hash)
        tx_ids.append(result['tx_id'])
        print(f"   ✓ {result['tx_id']}")
    
    print(f"\n2. Verifying entries...")
    for tx_id in tx_ids:
        verification = ledger.verify(tx_id)
        status = "✓" if verification['valid'] else "✗"
        print(f"   {status} {tx_id}: {verification['entry']['resource_id']}")
    
    print(f"\n3. Statistics:")
    stats = ledger.get_stats()
    print(f"   Total entries: {stats['total_entries']}")
    print(f"   Root hash: {stats['root_hash'][:16]}...")
    
    print(f"\n4. Export sample:")
    export = ledger.export(output_format='json')
    data = json.loads(export)
    print(f"   {len(data['ledger'])} entries in ledger")
    
    print("\n✓ All tests passed!")
    return 0


def main():
    """Parse arguments and dispatch to command handlers"""
    parser = argparse.ArgumentParser(
        description="Merkle Audit Ledger CLI (P1-AUD-002)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Append an entry
  upc-audit append --resource patient-123 --practitioner doc-456 --hash abc123...

  # Verify an entry
  upc-audit verify --tx-id tx-00000001

  # Export ledger
  upc-audit export --format json --output ledger.json

  # View statistics
  upc-audit stats

  # List recent entries
  upc-audit list --limit 20

  # Run tests
  upc-audit test
        """
    )
    
    parser.add_argument(
        "--storage",
        default="audit_ledger.json",
        help="Path to ledger storage file (default: audit_ledger.json)"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Append command
    append_parser = subparsers.add_parser('append', help='Append entry to ledger')
    append_parser.add_argument('--resource', required=True, help='Resource identifier')
    append_parser.add_argument('--practitioner', required=True, help='Practitioner identifier')
    append_parser.add_argument('--hash', required=True, help='Content hash (SHA256)')
    append_parser.set_defaults(func=cmd_append)
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify entry in ledger')
    verify_parser.add_argument('--tx-id', required=True, help='Transaction ID to verify')
    verify_parser.set_defaults(func=cmd_verify)
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export ledger')
    export_parser.add_argument(
        '--format',
        choices=['json', 'csv'],
        default='json',
        help='Export format'
    )
    export_parser.add_argument('--output', help='Output file (default: stdout)')
    export_parser.set_defaults(func=cmd_export)
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show ledger statistics')
    stats_parser.set_defaults(func=cmd_stats)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List recent entries')
    list_parser.add_argument('--limit', type=int, default=10, help='Number of entries to show')
    list_parser.set_defaults(func=cmd_list)
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run ledger tests')
    test_parser.set_defaults(func=cmd_test)
    
    # Parse and execute
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        return args.func(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
