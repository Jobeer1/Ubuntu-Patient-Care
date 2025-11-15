"""
Tests for Merkle tree audit log (P1-AUD-002)
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from audit.poc_merkle import AuditLog, MerkleTree, MerkleNode


class TestMerkleNode:
    """Test Merkle tree node"""
    
    def test_leaf_node_hash(self):
        """Test leaf node hash computation"""
        data = {"action": "test", "value": 123}
        node = MerkleNode(data=data)
        assert len(node.hash) == 64  # SHA-256 hex
        assert node.left is None
        assert node.right is None
    
    def test_internal_node_hash(self):
        """Test internal node hash computation"""
        left = MerkleNode(data={"a": 1})
        right = MerkleNode(data={"b": 2})
        parent = MerkleNode(left=left, right=right)
        
        assert len(parent.hash) == 64
        assert parent.data is None


class TestMerkleTree:
    """Test Merkle tree"""
    
    def test_empty_tree(self):
        """Test empty tree"""
        tree = MerkleTree([])
        assert tree.root is None
        assert tree.get_root_hash() == ""
    
    def test_single_event(self):
        """Test tree with single event"""
        events = [{"action": "test"}]
        tree = MerkleTree(events)
        assert tree.root is not None
        assert len(tree.get_root_hash()) == 64
    
    def test_multiple_events(self):
        """Test tree with multiple events"""
        events = [
            {"action": "event1"},
            {"action": "event2"},
            {"action": "event3"}
        ]
        tree = MerkleTree(events)
        root_hash = tree.get_root_hash()
        assert len(root_hash) == 64
        
        # Same events should produce same root
        tree2 = MerkleTree(events)
        assert tree2.get_root_hash() == root_hash
    
    def test_different_order_different_hash(self):
        """Test that event order matters"""
        events1 = [{"a": 1}, {"b": 2}]
        events2 = [{"b": 2}, {"a": 1}]
        
        tree1 = MerkleTree(events1)
        tree2 = MerkleTree(events2)
        
        assert tree1.get_root_hash() != tree2.get_root_hash()
    
    def test_merkle_proof(self):
        """Test Merkle proof generation and verification"""
        events = [
            {"action": "event1"},
            {"action": "event2"},
            {"action": "event3"},
            {"action": "event4"}
        ]
        tree = MerkleTree(events)
        root_hash = tree.get_root_hash()
        
        # Get proof for second event
        proof = tree.get_proof(1)
        
        # Verify proof
        is_valid = MerkleTree.verify_proof(events[1], proof, root_hash)
        assert is_valid
    
    def test_invalid_proof(self):
        """Test that tampered event fails verification"""
        events = [
            {"action": "event1"},
            {"action": "event2"}
        ]
        tree = MerkleTree(events)
        root_hash = tree.get_root_hash()
        proof = tree.get_proof(1)
        
        # Tamper with event
        tampered_event = {"action": "event2_modified"}
        
        # Verification should fail
        is_valid = MerkleTree.verify_proof(tampered_event, proof, root_hash)
        assert not is_valid


class TestAuditLog:
    """Test audit log"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)
    
    def test_create_log(self, temp_dir):
        """Test creating audit log"""
        log = AuditLog(temp_dir)
        assert log.base_path.exists()
        assert log.events_dir.exists()
        assert log.merkle_dir.exists()
        assert log.roots_dir.exists()
    
    def test_append_event(self, temp_dir):
        """Test appending event"""
        log = AuditLog(temp_dir)
        
        event_id = log.append({
            "action": "Report Finalized",
            "resource_id": "report-123",
            "practitioner_id": "DR-001"
        })
        
        assert event_id is not None
        assert len(log.get_all_events()) == 1
    
    def test_event_has_required_fields(self, temp_dir):
        """Test that appended event has all required fields"""
        log = AuditLog(temp_dir)
        
        event_id = log.append({"action": "test"})
        event = log.get_event(event_id)
        
        assert "event_id" in event
        assert "timestamp" in event
        assert "hash" in event
        assert "previous_hash" in event
        assert "action" in event
    
    def test_event_chain(self, temp_dir):
        """Test that events are chained"""
        log = AuditLog(temp_dir)
        
        id1 = log.append({"action": "event1"})
        id2 = log.append({"action": "event2"})
        
        event1 = log.get_event(id1)
        event2 = log.get_event(id2)
        
        # Second event should link to first
        assert event2["previous_hash"] == event1["hash"]
    
    def test_verify_valid_event(self, temp_dir):
        """Test verifying valid event"""
        log = AuditLog(temp_dir)
        
        event_id = log.append({
            "action": "Report Finalized",
            "resource_id": "report-123"
        })
        
        is_valid = log.verify(event_id)
        assert is_valid
    
    def test_verify_multiple_events(self, temp_dir):
        """Test verifying multiple events"""
        log = AuditLog(temp_dir)
        
        ids = []
        for i in range(5):
            event_id = log.append({
                "action": f"event{i}",
                "resource_id": f"resource-{i}"
            })
            ids.append(event_id)
        
        # All events should be valid
        for event_id in ids:
            assert log.verify(event_id)
    
    def test_root_hash_updates(self, temp_dir):
        """Test that root hash updates with new events"""
        log = AuditLog(temp_dir)
        
        # No events
        root1 = log.get_root_hash()
        
        # Add event
        log.append({"action": "event1"})
        root2 = log.get_root_hash()
        
        # Add another event
        log.append({"action": "event2"})
        root3 = log.get_root_hash()
        
        # All roots should be different
        assert root1 != root2
        assert root2 != root3
    
    def test_persistence(self, temp_dir):
        """Test that events persist across log instances"""
        # Create log and add events
        log1 = AuditLog(temp_dir)
        id1 = log1.append({"action": "event1"})
        id2 = log1.append({"action": "event2"})
        root1 = log1.get_root_hash()
        
        # Create new log instance
        log2 = AuditLog(temp_dir)
        
        # Events should be loaded
        assert len(log2.get_all_events()) == 2
        assert log2.get_root_hash() == root1
        assert log2.verify(id1)
        assert log2.verify(id2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
