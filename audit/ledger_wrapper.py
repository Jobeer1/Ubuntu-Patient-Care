"""
Wrapper to make AuditLog compatible with CLI expectations
"""

from .poc_merkle import AuditLog
from typing import Dict, Any


class MerkleAuditLedger:
    """Wrapper around AuditLog to match CLI API"""
    
    def __init__(self, storage_path="./audit_data"):
        self._log = AuditLog(storage_path)
        self.entries = []
        self.tx_counter = 0
        self.root_hash = None
        self._sync_from_log()
    
    def _sync_from_log(self):
        """Sync state from underlying log"""
        events = self._log.get_all_events()
        self.entries = events
        self.tx_counter = len(events)
        self.root_hash = self._log.get_root_hash()
    
    def append(self, resource_id: str, practitioner_id: str, content_hash: str) -> Dict[str, Any]:
        """Append entry with CLI-expected signature"""
        event_id = self._log.append({
            "resource_id": resource_id,
            "practitioner_id": practitioner_id,
            "content_hash": content_hash
        })
        
        self._sync_from_log()
        
        return {
            "tx_id": event_id,
            "root_hash": self.root_hash,
            "resource_id": resource_id
        }
    
    def verify(self, tx_id: str) -> Dict[str, Any]:
        """Verify entry"""
        is_valid = self._log.verify(tx_id)
        event = self._log.get_event(tx_id)
        
        return {
            "valid": is_valid,
            "tx_id": tx_id,
            "entry": event if event else None
        }
    
    def export(self, output_format="json") -> str:
        """Export ledger"""
        events = self._log.get_all_events()
        
        if output_format == "json":
            import json
            return json.dumps({
                "entries": events,
                "root_hash": self.root_hash,
                "total_entries": len(events)
            }, indent=2)
        elif output_format == "csv":
            import csv
            import io
            output = io.StringIO()
            if events:
                writer = csv.DictWriter(output, fieldnames=events[0].keys())
                writer.writeheader()
                writer.writerows(events)
            return output.getvalue()
        else:
            raise ValueError(f"Unknown format: {output_format}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ledger statistics"""
        return {
            "total_entries": len(self.entries),
            "root_hash": self.root_hash,
            "storage_path": str(self._log.base_path)
        }


def get_default_ledger(storage_path="./audit_data"):
    """Get or create default ledger instance"""
    global _default_ledger
    if _default_ledger is None:
        _default_ledger = MerkleAuditLedger(storage_path)
    return _default_ledger


_default_ledger = None
