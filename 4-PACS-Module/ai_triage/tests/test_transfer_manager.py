import unittest
from unittest.mock import MagicMock, patch
import time
import sys
import os

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from transfer_manager import TransferManager, TransferPriority, TransferItem

class TestTransferManager(unittest.TestCase):

    def setUp(self):
        self.manager = TransferManager()
        # Mock AuditService
        self.manager.audit_service = MagicMock()
        
        self.test_instances = [
            {'id': 'inst_1', 'instance_number': 1, 'path': '/tmp/1.dcm', 'size': 100},
            {'id': 'inst_2', 'instance_number': 2, 'path': '/tmp/2.dcm', 'size': 200},
            {'id': 'inst_3', 'instance_number': 3, 'path': '/tmp/3.dcm', 'size': 300},
        ]

    def test_priority_queueing(self):
        # Triage result says slice 2 is critical
        triage_results = {
            'status': 'critical',
            'critical_slices': [2]
        }
        
        self.manager.queue_study('study_1', self.test_instances, triage_results)
        
        # Check total size calculation
        self.assertEqual(self.manager.study_sizes['study_1'], 600)
        
        # Queue should have 3 items
        self.assertEqual(len(self.manager.queue), 3)
        
        # Pop items and check order
        # Expected: inst_2 (Critical=0) -> inst_1 (High=1) -> inst_3 (High=1)
        # Note: inst_1 and inst_3 have same priority, order depends on timestamp/insertion
        
        item1 = self.manager.queue[0] # Peek
        self.assertEqual(item1.instance_id, 'inst_2')
        self.assertEqual(item1.priority, TransferPriority.CRITICAL.value)

    def test_normal_study_priority(self):
        triage_results = {
            'status': 'normal',
            'critical_slices': []
        }
        self.manager.queue_study('study_2', self.test_instances, triage_results)
        
        # All should be LOW priority (3)
        for item in self.manager.queue:
            self.assertEqual(item.priority, TransferPriority.LOW.value)

    def test_process_queue_success(self):
        triage_results = {'status': 'normal', 'critical_slices': []}
        self.manager.queue_study('study_1', self.test_instances, triage_results)
        
        # Mock execute to return True
        # We need to mock _execute_transfer but keep the logic that calls audit service?
        # No, _execute_transfer calls audit service. 
        # If we mock _execute_transfer, we bypass audit logging.
        # So we should NOT mock _execute_transfer if we want to test audit logging integration.
        # But _execute_transfer does network calls (mocked).
        # Let's mock the network part inside _execute_transfer or just let it run since it's mocked in the class.
        # The class implementation of _execute_transfer is:
        # logger.info...
        # audit_service.log_transfer...
        # return True
        
        # So we don't need to mock _execute_transfer, just let it run.
        
        count = self.manager.process_queue(batch_size=3)
        
        self.assertEqual(count, 3)
        self.assertEqual(len(self.manager.completed), 3)
        self.assertEqual(len(self.manager.queue), 0)
        
        # Verify audit logging
        self.assertEqual(self.manager.audit_service.log_transfer.call_count, 3)
        # Check one call
        self.manager.audit_service.log_transfer.assert_any_call(
            study_instance_uid='study_1',
            total_size_bytes=600,
            transferred_size_bytes=100, # inst_1
            priority='LOW'
        )

    def test_retry_logic(self):
        triage_results = {'status': 'normal', 'critical_slices': []}
        # Queue just one instance
        self.manager.queue_study('study_1', [self.test_instances[0]], triage_results)
        
        # Mock execute to fail once then succeed
        # We need to mock _execute_transfer here because we want to control return value
        # But if we mock it, we lose audit logging.
        # That's fine for this test, we are testing retry logic.
        self.manager._execute_transfer = MagicMock(side_effect=[False, True])
        
        # First attempt (fails)
        self.manager.process_queue(batch_size=1)
        
        # Should be back in queue with retry_count 1
        self.assertEqual(len(self.manager.queue), 1)
        self.assertEqual(self.manager.queue[0].retry_count, 1)
        self.assertNotIn('inst_1', self.manager.completed)
        
        # Second attempt (succeeds)
        self.manager.process_queue(batch_size=1)
        
        self.assertEqual(len(self.manager.queue), 0)
        self.assertIn('inst_1', self.manager.completed)

    def test_max_retries_exceeded(self):
        self.manager.max_retries = 1
        triage_results = {'status': 'normal', 'critical_slices': []}
        self.manager.queue_study('study_1', [self.test_instances[0]], triage_results)
        
        self.manager._execute_transfer = MagicMock(return_value=False)
        
        # Attempt 1 (Fail) -> Retry 1
        self.manager.process_queue(batch_size=1)
        # Attempt 2 (Fail) -> Max retries reached
        self.manager.process_queue(batch_size=1)
        
        self.assertEqual(len(self.manager.queue), 0)
        self.assertIn('inst_1', self.manager.failed)

    def test_request_full_study(self):
        # Queue as normal (LOW priority)
        triage_results = {'status': 'normal', 'critical_slices': []}
        self.manager.queue_study('study_1', self.test_instances, triage_results)
        
        # Verify priority is LOW
        self.assertEqual(self.manager.queue[0].priority, TransferPriority.LOW.value)
        
        # Request full study (elevates to HIGH)
        self.manager.request_full_study('study_1', self.test_instances)
        
        # Heap should now contain duplicates, but the top ones should be HIGH
        # We pop until we see HIGH
        
        import heapq
        top_item = heapq.heappop(self.manager.queue)
        self.assertEqual(top_item.priority, TransferPriority.HIGH.value)

if __name__ == '__main__':
    unittest.main()
