"""
Local Merkle Ledger for Agent

Append-only ledger that records all agent operations.
Each entry is Merkle-stamped for tamper detection.

Author: Kiro Team
Task: K2.5
"""

import os
import json
import hashlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalLedger:
    """
    Append-only Merkle ledger for agent operations.
    
    Each entry contains:
    - Event data
    - Timestamp
    - Previous hash (Merkle chain)
    - Current hash
    
    File format: JSONL (one JSON object per line)
    """
    
    def __init__(self, ledger_path: str = "data/agent_ledger.jsonl"):
        """
        Initialize local ledger.
        
        Args:
            ledger_path: Path to ledger file
        """
        self.ledger_path = ledger_path
        self.previous_hash = None
        self.entry_count = 0
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
        
        # Load existing ledger
        self._load_ledger()
        
        logger.info(f"Local ledger initialized: {ledger_path} ({self.entry_count} entries)")
    
    def _load_ledger(self):
        """Load existing ledger and verify chain."""
        if not os.path.exists(self.ledger_path):
            logger.info("No existing ledger, starting fresh")
            return
        
        try:
            with open(self.ledger_path, 'r') as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        self.previous_hash = entry.get('hash')
                        self.entry_count += 1
            
            logger.info(f"Loaded {self.entry_count} entries from ledger")
        
        except Exception as e:
            logger.error(f"Failed to load ledger: {e}")
    
    def _compute_hash(self, data: Dict[str, Any], previous_hash: Optional[str]) -> str:
        """
        Compute Merkle hash for entry.
        
        Hash = SHA256(previous_hash + JSON(data))
        """
        hasher = hashlib.sha256()
        
        # Include previous hash (Merkle chain)
        if previous_hash:
            hasher.update(previous_hash.encode())
        
        # Include entry data
        data_json = json.dumps(data, sort_keys=True)
        hasher.update(data_json.encode())
        
        return hasher.hexdigest()
    
    def append_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Append event to ledger.
        
        Args:
            event_data: Event data to record
        
        Returns:
            Complete entry with hash
        """
        try:
            # Add metadata
            entry = {
                "entry_id": self.entry_count + 1,
                "timestamp": datetime.utcnow().isoformat(),
                "previous_hash": self.previous_hash,
                "data": event_data
            }
            
            # Compute hash
            entry_hash = self._compute_hash(event_data, self.previous_hash)
            entry["hash"] = entry_hash
            
            # Write to file
            with open(self.ledger_path, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            
            # Update state
            self.previous_hash = entry_hash
            self.entry_count += 1
            
            logger.debug(f"Appended entry {self.entry_count}: {event_data.get('type', 'UNKNOWN')}")
            
            return entry
        
        except Exception as e:
            logger.error(f"Failed to append entry: {e}")
            raise
    
    def verify_chain(self) -> bool:
        """
        Verify integrity of Merkle chain.
        
        Returns:
            True if chain is valid, False if tampered
        """
        if not os.path.exists(self.ledger_path):
            return True  # Empty ledger is valid
        
        try:
            previous_hash = None
            entry_count = 0
            
            with open(self.ledger_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    entry = json.loads(line)
                    entry_count += 1
                    
                    # Verify previous hash matches
                    if entry.get('previous_hash') != previous_hash:
                        logger.error(f"Chain broken at entry {entry_count}: previous hash mismatch")
                        return False
                    
                    # Recompute hash
                    computed_hash = self._compute_hash(entry['data'], previous_hash)
                    if computed_hash != entry['hash']:
                        logger.error(f"Chain broken at entry {entry_count}: hash mismatch")
                        return False
                    
                    previous_hash = entry['hash']
            
            logger.info(f"Chain verified: {entry_count} entries valid")
            return True
        
        except Exception as e:
            logger.error(f"Chain verification failed: {e}")
            return False
    
    def get_entries(
        self,
        limit: Optional[int] = None,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get entries from ledger.
        
        Args:
            limit: Maximum number of entries to return
            event_type: Filter by event type
        
        Returns:
            List of entries
        """
        if not os.path.exists(self.ledger_path):
            return []
        
        entries = []
        
        try:
            with open(self.ledger_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    entry = json.loads(line)
                    
                    # Filter by event type
                    if event_type and entry['data'].get('type') != event_type:
                        continue
                    
                    entries.append(entry)
                    
                    # Check limit
                    if limit and len(entries) >= limit:
                        break
            
            return entries
        
        except Exception as e:
            logger.error(f"Failed to read entries: {e}")
            return []
    
    def get_entry_count(self) -> int:
        """Get total number of entries."""
        return self.entry_count
    
    def get_last_entry(self) -> Optional[Dict[str, Any]]:
        """Get the last entry in the ledger."""
        entries = self.get_entries(limit=1)
        return entries[-1] if entries else None
    
    def export_ledger(self, output_path: str):
        """
        Export ledger to another file.
        
        Args:
            output_path: Destination file path
        """
        try:
            import shutil
            shutil.copy2(self.ledger_path, output_path)
            logger.info(f"Ledger exported to {output_path}")
        
        except Exception as e:
            logger.error(f"Failed to export ledger: {e}")
            raise
