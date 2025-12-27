"""
P1-AUD-002: Minimal Merkle Hash Store Proof of Concept

Simple, fast, immutable audit log using Merkle trees.
< 500 lines of code, no external dependencies.

Usage:
    from audit.poc_merkle import AuditLog
    
    log = AuditLog("/var/audit")
    tx_id = log.append({
        "action": "Report Finalized",
        "resource_id": "report-123",
        "practitioner_id": "DR-001"
    })
    
    # Verify integrity
    is_valid = log.verify(tx_id)
"""

import hashlib
import json
import os
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path


class MerkleNode:
    """Node in a Merkle tree"""
    
    def __init__(self, left=None, right=None, data=None):
        self.left = left
        self.right = right
        self.data = data
        self.hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute hash of this node"""
        if self.data:
            # Leaf node - hash the data
            return hashlib.sha256(json.dumps(self.data, sort_keys=True).encode()).hexdigest()
        else:
            # Internal node - hash of children
            left_hash = self.left.hash if self.left else ""
            right_hash = self.right.hash if self.right else ""
            return hashlib.sha256((left_hash + right_hash).encode()).hexdigest()


class MerkleTree:
    """Simple Merkle tree for audit events"""
    
    def __init__(self, events: List[Dict[str, Any]]):
        self.events = events
        self.levels = []  # Store all levels for proof generation
        self.root = self._build_tree()
    
    def _build_tree(self) -> Optional[MerkleNode]:
        """Build Merkle tree from events"""
        if not self.events:
            return None
        
        # Create leaf nodes
        nodes = [MerkleNode(data=event) for event in self.events]
        self.levels.append(nodes.copy())  # Store level 0
        
        # Build tree bottom-up
        while len(nodes) > 1:
            next_level = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else None
                
                if right is None:
                    # Odd one out - carry forward without modification
                    next_level.append(left)
                else:
                    # Pair exists - create parent
                    parent = MerkleNode(left=left, right=right)
                    next_level.append(parent)
            
            nodes = next_level
            self.levels.append(nodes.copy())  # Store each level
        
        return nodes[0] if nodes else None
    
    def get_root_hash(self) -> str:
        """Get root hash of tree"""
        return self.root.hash if self.root else ""
    
    def get_proof(self, index: int) -> List[tuple]:
        """Get Merkle proof for event at index using stored tree levels"""
        if index >= len(self.events):
            return []
        
        proof = []
        target_idx = index
        
        # Traverse from leaf level (level 0) to root
        for level_num in range(len(self.levels) - 1):
            current_level = self.levels[level_num]
            
            # Find which pair the target is in
            for i in range(0, len(current_level), 2):
                left_idx = i
                right_idx = i + 1 if i + 1 < len(current_level) else None
                
                # Check if target is in this pair
                if left_idx == target_idx:
                    # Target is left node
                    if right_idx is not None:
                        right_node = current_level[right_idx]
                        proof.append(('R', right_node.hash))
                    # Move to next level - this pair becomes one node
                    target_idx = i // 2
                    break
                    
                elif right_idx == target_idx:
                    # Target is right node
                    left_node = current_level[left_idx]
                    proof.append(('L', left_node.hash))
                    # Move to next level
                    target_idx = i // 2
                    break
        
        return proof
    
    @staticmethod
    def verify_proof(event: Dict[str, Any], proof: List[tuple], root_hash: str) -> bool:
        """Verify Merkle proof for an event"""
        # Compute leaf hash
        current_hash = hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()
        
        # Apply proof steps
        for direction, sibling_hash in proof:
            if direction == 'L':
                combined = sibling_hash + current_hash
            else:  # 'R'
                combined = current_hash + sibling_hash
            current_hash = hashlib.sha256(combined.encode()).hexdigest()
        
        return current_hash == root_hash


class AuditLog:
    """Immutable audit log with Merkle tree verification"""
    
    def __init__(self, base_path: str = "/var/audit"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.events_dir = self.base_path / "events"
        self.merkle_dir = self.base_path / "merkle"
        self.roots_dir = self.base_path / "roots"
        
        for dir_path in [self.events_dir, self.merkle_dir, self.roots_dir]:
            dir_path.mkdir(exist_ok=True)
        
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.events_cache = []
        self._load_today_events()
    
    def _get_event_file(self, date: str = None) -> Path:
        """Get event log file for date"""
        date = date or self.current_date
        return self.events_dir / f"{date}.log"
    
    def _get_merkle_file(self, date: str = None) -> Path:
        """Get Merkle tree file for date"""
        date = date or self.current_date
        return self.merkle_dir / f"{date}.tree"
    
    def _get_root_file(self, date: str = None) -> Path:
        """Get root hash file for date"""
        date = date or self.current_date
        return self.roots_dir / f"{date}.root"
    
    def _load_today_events(self):
        """Load today's events into cache"""
        event_file = self._get_event_file()
        if event_file.exists():
            with open(event_file, 'r') as f:
                self.events_cache = [json.loads(line) for line in f if line.strip()]
    
    def append(self, event_data: Dict[str, Any]) -> str:
        """
        Append event to audit log
        
        Args:
            event_data: Event data to log
            
        Returns:
            Transaction ID (event_id)
        """
        # Check if date rolled over
        current_date = datetime.now().strftime("%Y-%m-%d")
        if current_date != self.current_date:
            self._finalize_day()
            self.current_date = current_date
            self.events_cache = []
        
        # Create event record
        event = {
            "event_id": f"{int(time.time() * 1000000)}",  # Microsecond timestamp
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **event_data
        }
        
        # Compute hash
        event["hash"] = hashlib.sha256(
            json.dumps(event_data, sort_keys=True).encode()
        ).hexdigest()
        
        # Link to previous event (blockchain-style)
        if self.events_cache:
            event["previous_hash"] = self.events_cache[-1]["hash"]
        else:
            event["previous_hash"] = "0" * 64  # Genesis event
        
        # Append to file (WORM)
        event_file = self._get_event_file()
        with open(event_file, 'a') as f:
            f.write(json.dumps(event) + '\n')
        
        # Add to cache
        self.events_cache.append(event)
        
        # Update Merkle tree
        self._update_merkle_tree()
        
        return event["event_id"]
    
    def _update_merkle_tree(self):
        """Update Merkle tree with current events"""
        if not self.events_cache:
            return
        
        # Build tree
        tree = MerkleTree(self.events_cache)
        root_hash = tree.get_root_hash()
        
        # Store root hash
        root_file = self._get_root_file()
        with open(root_file, 'w') as f:
            f.write(json.dumps({
                "root_hash": root_hash,
                "event_count": len(self.events_cache),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }))
        
        # Store tree (for proof generation)
        merkle_file = self._get_merkle_file()
        with open(merkle_file, 'w') as f:
            json.dump({
                "root_hash": root_hash,
                "event_count": len(self.events_cache)
            }, f)
    
    def _finalize_day(self):
        """Finalize previous day's audit log"""
        self._update_merkle_tree()
        # In production, trigger backup here
    
    def verify(self, event_id: str) -> bool:
        """
        Verify integrity of an event
        
        Args:
            event_id: Event ID to verify
            
        Returns:
            True if event is valid and unmodified
        """
        # Find event
        event = None
        for e in self.events_cache:
            if e["event_id"] == event_id:
                event = e
                break
        
        if not event:
            return False
        
        # Verify hash
        event_data = {k: v for k, v in event.items() 
                     if k not in ["event_id", "timestamp", "hash", "previous_hash"]}
        computed_hash = hashlib.sha256(
            json.dumps(event_data, sort_keys=True).encode()
        ).hexdigest()
        
        if computed_hash != event["hash"]:
            return False
        
        # Verify chain link
        event_index = self.events_cache.index(event)
        if event_index > 0:
            prev_event = self.events_cache[event_index - 1]
            if event["previous_hash"] != prev_event["hash"]:
                return False
        
        # Verify Merkle proof
        tree = MerkleTree(self.events_cache)
        proof = tree.get_proof(event_index)
        root_hash = tree.get_root_hash()
        
        return MerkleTree.verify_proof(event, proof, root_hash)
    
    def get_root_hash(self) -> str:
        """Get current Merkle root hash"""
        root_file = self._get_root_file()
        if root_file.exists():
            with open(root_file, 'r') as f:
                data = json.load(f)
                return data["root_hash"]
        return ""
    
    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get event by ID"""
        for event in self.events_cache:
            if event["event_id"] == event_id:
                return event
        return None
    
    def get_all_events(self) -> List[Dict[str, Any]]:
        """Get all events for today"""
        return self.events_cache.copy()


# CLI for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python poc_merkle.py append <action> <resource_id>")
        print("  python poc_merkle.py verify <event_id>")
        print("  python poc_merkle.py root")
        print("  python poc_merkle.py list")
        sys.exit(1)
    
    log = AuditLog("./audit_data")
    
    command = sys.argv[1]
    
    if command == "append":
        action = sys.argv[2] if len(sys.argv) > 2 else "Test Action"
        resource_id = sys.argv[3] if len(sys.argv) > 3 else "test-123"
        
        event_id = log.append({
            "action": action,
            "resource_id": resource_id,
            "practitioner_id": "DR-001"
        })
        print(f"✓ Event appended: {event_id}")
        print(f"  Root hash: {log.get_root_hash()}")
    
    elif command == "verify":
        event_id = sys.argv[2]
        is_valid = log.verify(event_id)
        if is_valid:
            print(f"✓ Event {event_id} is VALID")
        else:
            print(f"✗ Event {event_id} is INVALID or not found")
    
    elif command == "root":
        root_hash = log.get_root_hash()
        print(f"Current root hash: {root_hash}")
        print(f"Event count: {len(log.get_all_events())}")
    
    elif command == "list":
        events = log.get_all_events()
        print(f"Total events: {len(events)}")
        for event in events[-10:]:  # Last 10
            print(f"  {event['event_id']}: {event.get('action', 'N/A')}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


# Helper function for CLI compatibility
_default_ledger = None

def get_default_ledger(storage_path="./audit_data"):
    """Get or create default ledger instance for CLI use"""
    global _default_ledger
    if _default_ledger is None:
        _default_ledger = AuditLog(storage_path)
    return _default_ledger
