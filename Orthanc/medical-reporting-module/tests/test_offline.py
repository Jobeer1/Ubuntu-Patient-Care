"""
Tests for offline functionality in Medical Reporting Module
"""

import pytest
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json
import sqlite3

from services.offline_manager import OfflineManager, ConnectivityStatus
from services.cache_service import CacheService
from services.synchronization_queue import SynchronizationQueue
from services.conflict_resolver import ConflictResolver, ConflictType, ConflictResolution

class TestOfflineManager:
    """Test offline manager functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock config to use temp directory
        with patch('services.offline_manager.OfflineConfig') as mock_config:
            mock_config.OFFLINE_DATA_DIR = self.temp_dir
            mock_config.SYNC_INTERVAL_SECONDS = 1
            mock_config.CONNECTIVITY_CHECK_URLS = [
                'http://test-orthanc:8042/system',
                'http://test-sa:5000/health',
                'https://www.google.com'
            ]
            mock_config.CONNECTIVITY_TIMEOUT = 1
            
            self.offline_manager = OfflineManager()
    
    def teardown_method(self):
        """Clean up test environment"""
        if hasattr(self, 'offline_manager'):
            self.offline_manager.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test offline manager initialization"""
        assert self.offline_manager is not None
        assert hasattr(self.offline_manager, 'cache_service')
        assert hasattr(self.offline_manager, 'sync_queue')
        assert hasattr(self.offline_manager, 'conflict_resolver')
    
    @patch('requests.get')
    def test_connectivity_check(self, mock_get):
        """Test connectivity checking"""
        # Mock successful responses
        mock_get.return_value.status_code = 200
        
        self.offline_manager._check_connectivity()
        
        status = self.offline_manager.get_connectivity_status()
        assert status['online'] == True
        assert status['orthanc_available'] == True
        assert status['sa_system_available'] == True
    
    @patch('requests.get')
    def test_connectivity_failure(self, mock_get):
        """Test connectivity failure handling"""
        # Mock failed responses
        mock_get.side_effect = Exception("Connection failed")
        
        self.offline_manager._check_connectivity()
        
        status = self.offline_manager.get_connectivity_status()
        assert status['online'] == False
        assert status['orthanc_available'] == False
        assert status['sa_system_available'] == False
    
    def test_queue_for_sync(self):
        """Test queuing items for synchronization"""
        test_data = {'report_id': 'test123', 'content': 'Test report'}
        
        self.offline_manager.queue_for_sync('report', test_data, priority=1)
        
        # Check if item was queued
        pending_count = self.offline_manager.sync_queue.get_pending_count()
        assert pending_count == 1
    
    def test_offline_stats(self):
        """Test getting offline statistics"""
        stats = self.offline_manager.get_offline_stats()
        
        assert 'connectivity' in stats
        assert 'sync_queue_size' in stats
        assert 'cache_stats' in stats
        assert 'offline_features' in stats

class TestCacheService:
    """Test cache service functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        with patch('services.cache_service.OfflineConfig') as mock_config:
            mock_config.OFFLINE_CACHE_DB = f"{self.temp_dir}/test_cache.db"
            mock_config.CACHE_RETENTION_DAYS = 30
            
            self.cache_service = CacheService()
    
    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_dicom_image_caching(self):
        """Test DICOM image caching"""
        test_image_data = b"fake_dicom_image_data"
        test_metadata = {'PatientID': 'PAT123', 'StudyDate': '20240115'}
        
        # Cache image
        success = self.cache_service.cache_dicom_image(
            'study123', 'series456', 'instance789',
            test_image_data, test_metadata
        )
        assert success == True
        
        # Retrieve image
        cached_data = self.cache_service.get_cached_dicom_image(
            'study123', 'series456', 'instance789'
        )
        assert cached_data is not None
        assert cached_data[0] == test_image_data
        assert cached_data[1] == test_metadata
    
    def test_report_caching(self):
        """Test report caching"""
        test_report = {
            'report_id': 'report123',
            'patient_id': 'PAT123',
            'study_id': 'study456',
            'content': {'findings': 'Normal study'},
            'status': 'draft'
        }
        
        # Cache report
        success = self.cache_service.cache_report('report123', test_report)
        assert success == True
        
        # Retrieve report
        cached_report = self.cache_service.get_cached_report('report123')
        assert cached_report is not None
        assert cached_report['report_id'] == 'report123'
        assert cached_report['content']['findings'] == 'Normal study'
    
    def test_template_caching(self):
        """Test template caching"""
        test_template = {
            'template_id': 'template123',
            'name': 'CT Chest Template',
            'category': 'chest',
            'structure': {'sections': ['findings', 'impression']}
        }
        
        # Cache template
        success = self.cache_service.cache_template('template123', test_template)
        assert success == True
        
        # Retrieve templates
        cached_templates = self.cache_service.get_cached_templates('chest')
        assert len(cached_templates) == 1
        assert cached_templates[0]['name'] == 'CT Chest Template'
    
    def test_cache_stats(self):
        """Test cache statistics"""
        # Add some test data
        self.cache_service.cache_dicom_image(
            'study1', 'series1', 'instance1', b"test_data", {}
        )
        self.cache_service.cache_report('report1', {'report_id': 'report1'})
        
        stats = self.cache_service.get_cache_stats()
        
        assert 'dicom_cache' in stats
        assert 'report_cache' in stats
        assert stats['dicom_cache']['total_items'] >= 1
        assert stats['report_cache']['count'] >= 1

class TestSynchronizationQueue:
    """Test synchronization queue functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        with patch('services.synchronization_queue.OfflineConfig') as mock_config:
            mock_config.OFFLINE_QUEUE_DB = f"{self.temp_dir}/test_queue.db"
            mock_config.SYNC_BATCH_SIZE = 10
            
            self.sync_queue = SynchronizationQueue()
    
    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_add_item(self):
        """Test adding items to sync queue"""
        test_data = {'report_id': 'test123', 'content': 'Test report'}
        
        item_id = self.sync_queue.add_item('report', 'create', test_data, priority=1)
        
        assert item_id is not None
        assert len(item_id) > 0
        
        # Check if item was added
        pending_count = self.sync_queue.get_pending_count()
        assert pending_count == 1
    
    def test_get_pending_items(self):
        """Test retrieving pending items"""
        # Add test items
        test_data1 = {'report_id': 'test1'}
        test_data2 = {'report_id': 'test2'}
        
        self.sync_queue.add_item('report', 'create', test_data1, priority=1)
        self.sync_queue.add_item('report', 'update', test_data2, priority=2)
        
        # Get pending items
        pending_items = self.sync_queue.get_pending_items(limit=10)
        
        assert len(pending_items) == 2
        # Should be ordered by priority
        assert pending_items[0]['priority'] == 1
        assert pending_items[1]['priority'] == 2
    
    def test_mark_completed(self):
        """Test marking items as completed"""
        test_data = {'report_id': 'test123'}
        item_id = self.sync_queue.add_item('report', 'create', test_data)
        
        # Mark as completed
        success = self.sync_queue.mark_completed(item_id)
        assert success == True
        
        # Check status
        status = self.sync_queue.get_item_status(item_id)
        assert status['status'] == 'completed'
    
    def test_mark_failed_with_retry(self):
        """Test marking items as failed with retry logic"""
        test_data = {'report_id': 'test123'}
        item_id = self.sync_queue.add_item('report', 'create', test_data)
        
        # Mark as failed (should retry)
        success = self.sync_queue.mark_failed(item_id, "Network error")
        assert success == True
        
        # Check status (should be pending for retry)
        status = self.sync_queue.get_item_status(item_id)
        assert status['status'] == 'pending'
        assert status['retry_count'] == 1
    
    def test_queue_stats(self):
        """Test queue statistics"""
        # Add test items with different statuses
        item1_id = self.sync_queue.add_item('report', 'create', {'id': '1'})
        item2_id = self.sync_queue.add_item('template', 'update', {'id': '2'})
        
        self.sync_queue.mark_completed(item1_id)
        
        stats = self.sync_queue.get_queue_stats()
        
        assert 'status_counts' in stats
        assert 'type_counts' in stats
        assert stats['total_items'] == 2

class TestConflictResolver:
    """Test conflict resolver functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.conflict_resolver = ConflictResolver()
    
    def test_detect_report_conflicts(self):
        """Test detecting conflicts in report data"""
        local_data = {
            'report_id': 'test123',
            'content': {'findings': 'Normal study'},
            'status': 'draft',
            'modified_at': '2024-01-15 10:00:00'
        }
        
        remote_data = {
            'report_id': 'test123',
            'content': {'findings': 'Abnormal findings detected'},
            'status': 'reviewed',
            'modified_at': '2024-01-15 11:00:00'
        }
        
        conflicts = self.conflict_resolver.detect_conflicts(local_data, remote_data, 'report')
        
        assert len(conflicts) > 0
        # Should detect content and status conflicts
        conflict_types = [c['type'] for c in conflicts]
        assert ConflictType.CONTENT_MODIFIED in conflict_types
        assert ConflictType.STATUS_CHANGED in conflict_types
    
    def test_resolve_status_conflict(self):
        """Test resolving status conflicts"""
        conflict = {
            'type': ConflictType.STATUS_CHANGED,
            'field': 'status',
            'local_value': 'draft',
            'remote_value': 'reviewed',
            'severity': 'medium'
        }
        
        local_data = {'status': 'draft'}
        remote_data = {'status': 'reviewed'}
        
        resolution, message = self.conflict_resolver._resolve_status_conflict(
            conflict, local_data, remote_data
        )
        
        # Should use remote (higher priority status)
        assert resolution == ConflictResolution.USE_REMOTE
        assert 'higher priority' in message
    
    def test_resolve_conflicts(self):
        """Test complete conflict resolution"""
        conflicts = [
            {
                'type': ConflictType.STATUS_CHANGED,
                'field': 'status',
                'local_value': 'draft',
                'remote_value': 'reviewed',
                'severity': 'medium'
            }
        ]
        
        local_data = {'status': 'draft', 'content': 'test'}
        remote_data = {'status': 'reviewed', 'content': 'test'}
        
        resolved_data, log = self.conflict_resolver.resolve_conflicts(
            conflicts, local_data, remote_data
        )
        
        assert resolved_data['status'] == 'reviewed'  # Should use remote
        assert len(log) > 0
    
    def test_merge_values(self):
        """Test merging conflicting values"""
        local_dict = {'a': 1, 'b': 2}
        remote_dict = {'b': 3, 'c': 4}
        
        merged = self.conflict_resolver._merge_values(local_dict, remote_dict, 'test_field')
        
        assert merged['a'] == 1  # From local
        assert merged['b'] == 3  # From remote (conflict resolution)
        assert merged['c'] == 4  # From remote
    
    def test_minor_content_change_detection(self):
        """Test detection of minor content changes"""
        local_content = "This is a test report."
        remote_content = "This  is  a  test  report."  # Extra whitespace
        
        is_minor = self.conflict_resolver._is_minor_content_change(
            local_content, remote_content
        )
        
        assert is_minor == True
        
        # Test significant change
        remote_content_significant = "This is a completely different report."
        is_minor_significant = self.conflict_resolver._is_minor_content_change(
            local_content, remote_content_significant
        )
        
        assert is_minor_significant == False
    
    def test_conflict_summary(self):
        """Test conflict summary generation"""
        conflicts = [
            {
                'type': ConflictType.CONTENT_MODIFIED,
                'severity': 'high'
            },
            {
                'type': ConflictType.STATUS_CHANGED,
                'severity': 'medium'
            },
            {
                'type': ConflictType.CONTENT_MODIFIED,
                'severity': 'high'
            }
        ]
        
        summary = self.conflict_resolver.get_conflict_summary(conflicts)
        
        assert summary['total'] == 3
        assert summary['by_type']['content_modified'] == 2
        assert summary['by_type']['status_changed'] == 1
        assert summary['by_severity']['high'] == 2
        assert summary['by_severity']['medium'] == 1

class TestOfflineIntegration:
    """Test integration between offline components"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock configs for all services
        with patch('services.offline_manager.OfflineConfig') as mock_config1, \
             patch('services.cache_service.OfflineConfig') as mock_config2, \
             patch('services.synchronization_queue.OfflineConfig') as mock_config3:
            
            mock_config1.OFFLINE_DATA_DIR = self.temp_dir
            mock_config1.SYNC_INTERVAL_SECONDS = 1
            mock_config2.OFFLINE_CACHE_DB = f"{self.temp_dir}/cache.db"
            mock_config3.OFFLINE_QUEUE_DB = f"{self.temp_dir}/queue.db"
            
            self.offline_manager = OfflineManager()
    
    def teardown_method(self):
        """Clean up test environment"""
        if hasattr(self, 'offline_manager'):
            self.offline_manager.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_complete_offline_workflow(self):
        """Test complete offline workflow"""
        # 1. Cache some data
        test_report = {
            'report_id': 'test123',
            'content': {'findings': 'Test findings'},
            'status': 'draft'
        }
        
        cache_success = self.offline_manager.cache_service.cache_report('test123', test_report)
        assert cache_success == True
        
        # 2. Queue for sync
        self.offline_manager.queue_for_sync('report', test_report, priority=1)
        
        # 3. Check stats
        stats = self.offline_manager.get_offline_stats()
        assert stats['sync_queue_size'] > 0
        assert stats['cache_stats']['report_cache']['count'] > 0
        
        # 4. Force sync (would normally happen automatically)
        with patch.object(self.offline_manager, 'is_online', return_value=True):
            with patch.object(self.offline_manager, '_sync_report', return_value=True):
                result = self.offline_manager.force_sync()
                assert result['success'] == True

def run_offline_tests():
    """Run all offline functionality tests"""
    pytest.main([__file__, "-v"])

if __name__ == "__main__":
    run_offline_tests()