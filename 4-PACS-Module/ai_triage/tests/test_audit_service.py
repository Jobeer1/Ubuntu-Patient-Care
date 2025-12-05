import unittest
import os
import json
import tempfile
from audit_service import AuditService

class TestAuditService(unittest.TestCase):

    def setUp(self):
        # Create a temporary file for logging
        self.temp_log = tempfile.NamedTemporaryFile(delete=False)
        self.temp_log.close()
        self.audit_service = AuditService(log_file=self.temp_log.name)

    def tearDown(self):
        # Clean up handlers to release the file
        for handler in self.audit_service.logger.handlers:
            handler.close()
            self.audit_service.logger.removeHandler(handler)
        
        # Remove temp file
        if os.path.exists(self.temp_log.name):
            os.remove(self.temp_log.name)

    def test_log_transfer(self):
        self.audit_service.log_transfer(
            study_instance_uid="1.2.3",
            total_size_bytes=1000,
            transferred_size_bytes=200,
            priority="CRITICAL"
        )

        with open(self.temp_log.name, 'r') as f:
            line = f.readline()
            data = json.loads(line)
            
            self.assertEqual(data['event_type'], "TRANSFER_COMPLETE")
            self.assertEqual(data['study_uid'], "1.2.3")
            self.assertEqual(data['metrics']['savings_bytes'], 800)
            self.assertEqual(data['metrics']['savings_percent'], 80.0)

    def test_get_stats(self):
        # Log two events
        self.audit_service.log_transfer("1", 1048576, 524288, "HIGH") # 1MB total, 0.5MB sent -> 0.5MB saved
        self.audit_service.log_transfer("2", 2097152, 0, "LOW")       # 2MB total, 0MB sent -> 2MB saved

        stats = self.audit_service.get_stats()
        
        self.assertEqual(stats['count'], 2)
        self.assertEqual(stats['total_saved_mb'], 2.5) # 0.5 + 2.0
        self.assertEqual(stats['total_original_mb'], 3.0) # 1.0 + 2.0

if __name__ == '__main__':
    unittest.main()
