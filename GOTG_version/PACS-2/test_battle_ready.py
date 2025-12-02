#!/usr/bin/env python3
"""
GOTG PACS - Battle-Ready Validation Test Suite
Comprehensive testing to verify all enhancements work correctly
PRODUCTION-READY - Lives depend on this
"""

import unittest
import time
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Import the modules we're testing
import sys
sys.path.insert(0, '.')

from sync_manager_v2_enhanced import (
    SyncCircuitBreaker, CircuitBreakerConfig, CircuitState,
    ExponentialBackoffRetry, DataIntegrityChecker, LoadManager,
    SystemLoad, EnhancedSyncManager
)

try:
    from monitoring.health_dashboard import HealthDashboard
    from sync_engine.offline_resilience_manager import OfflineResilienceManager
except ImportError:
    print("Warning: Some modules not found, skipping those tests")

# ===== TEST SUITE =====

class TestCircuitBreaker(unittest.TestCase):
    """Test circuit breaker pattern"""
    
    def setUp(self):
        self.breaker = SyncCircuitBreaker(
            config=CircuitBreakerConfig(failure_threshold=3, success_threshold=2)
        )
    
    def test_circuit_starts_closed(self):
        """Circuit breaker should start in CLOSED state"""
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)
        self.assertTrue(self.breaker.can_attempt())
    
    def test_circuit_opens_after_failures(self):
        """Circuit breaker should open after N failures"""
        # Record 3 failures
        for i in range(3):
            self.breaker.record_failure(f"Error {i}")
        
        # Should be open now
        self.assertEqual(self.breaker.state, CircuitState.OPEN)
        self.assertFalse(self.breaker.can_attempt())
    
    def test_circuit_half_opens_after_timeout(self):
        """Circuit breaker should enter HALF_OPEN after timeout"""
        # Open the circuit
        for i in range(3):
            self.breaker.record_failure(f"Error {i}")
        
        self.assertEqual(self.breaker.state, CircuitState.OPEN)
        
        # Move time forward (mock)
        self.breaker.last_state_change = datetime.now() - timedelta(seconds=301)
        
        # Should allow attempt now
        self.assertTrue(self.breaker.can_attempt())
        self.assertEqual(self.breaker.state, CircuitState.HALF_OPEN)
    
    def test_circuit_closes_after_successes(self):
        """Circuit breaker should close after successful attempts from HALF_OPEN"""
        # Open circuit
        for i in range(3):
            self.breaker.record_failure(f"Error {i}")
        
        # Move time forward to enter HALF_OPEN
        self.breaker.last_state_change = datetime.now() - timedelta(seconds=301)
        self.breaker.can_attempt()  # Transition to HALF_OPEN
        
        # Record successes
        self.breaker.record_success()
        self.breaker.record_success()
        
        # Should be closed
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)

class TestExponentialBackoff(unittest.TestCase):
    """Test exponential backoff retry logic"""
    
    def setUp(self):
        self.retry = ExponentialBackoffRetry(max_retries=3, initial_wait=0.1, max_wait=1)
        self.attempt_count = 0
    
    def test_retry_succeeds_immediately(self):
        """Should return immediately on success"""
        def always_success():
            return "success"
        
        result = self.retry.retry(always_success)
        self.assertEqual(result, "success")
    
    def test_retry_succeeds_after_failures(self):
        """Should retry and eventually succeed"""
        def fails_twice_then_succeeds():
            self.attempt_count += 1
            if self.attempt_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = self.retry.retry(fails_twice_then_succeeds)
        self.assertEqual(result, "success")
        self.assertEqual(self.attempt_count, 3)
    
    def test_retry_fails_after_max_attempts(self):
        """Should raise exception after max retries"""
        def always_fails():
            raise Exception("Permanent failure")
        
        with self.assertRaises(Exception):
            self.retry.retry(always_fails)

class TestDataIntegrity(unittest.TestCase):
    """Test data integrity checking"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.checker = DataIntegrityChecker(log_path=self.temp_dir)
    
    def test_register_file(self):
        """Should register file with hash"""
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test content")
        
        self.checker.register_file("test_id", str(test_file))
        
        self.assertIn("test_id", self.checker.checksums)
        self.assertIn("hash", self.checker.checksums["test_id"])
    
    def test_verify_file_unchanged(self):
        """Should verify unchanged file"""
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test content")
        
        self.checker.register_file("test_id", str(test_file))
        result = self.checker.verify_file("test_id", str(test_file))
        
        self.assertTrue(result)
    
    def test_detect_corruption(self):
        """Should detect file corruption"""
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test content")
        
        self.checker.register_file("test_id", str(test_file))
        
        # Corrupt the file
        test_file.write_text("corrupted content")
        
        result = self.checker.verify_file("test_id", str(test_file))
        self.assertFalse(result)
    
    def tearDown(self):
        # Cleanup
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

class TestLoadManager(unittest.TestCase):
    """Test load management"""
    
    def setUp(self):
        self.load_mgr = LoadManager()
    
    def test_get_system_load(self):
        """Should return valid system load"""
        load = self.load_mgr.get_system_load()
        self.assertIn(load, [SystemLoad.NORMAL, SystemLoad.HIGH, 
                            SystemLoad.CRITICAL, SystemLoad.EMERGENCY])
    
    def test_get_degradation_profile(self):
        """Should return degradation profile based on load"""
        profile = self.load_mgr.get_degradation_level()
        
        self.assertIn('load_level', profile)
        self.assertIn('max_concurrent_syncs', profile)
        self.assertIn('compression_level', profile)
        self.assertGreater(profile['max_concurrent_syncs'], 0)

class TestEnhancedSyncManager(unittest.TestCase):
    """Test enhanced sync manager integration"""
    
    def setUp(self):
        self.sync_mgr = EnhancedSyncManager()
    
    def test_sync_manager_initialized(self):
        """Should initialize all components"""
        self.assertIsNotNone(self.sync_mgr.circuit_breaker)
        self.assertIsNotNone(self.sync_mgr.retry)
        self.assertIsNotNone(self.sync_mgr.integrity_checker)
        self.assertIsNotNone(self.sync_mgr.load_manager)
    
    def test_can_accept_sync(self):
        """Should track concurrent syncs"""
        initial = self.sync_mgr.can_accept_sync()
        self.assertTrue(initial)
        
        # Fill up concurrent syncs
        self.sync_mgr.current_syncs = 1000
        result = self.sync_mgr.can_accept_sync()
        self.assertFalse(result)
    
    def test_get_stats(self):
        """Should return sync statistics"""
        stats = self.sync_mgr.get_stats()
        
        self.assertIn('synced', stats)
        self.assertIn('failed', stats)
        self.assertIn('circuit_breaker_state', stats)
        self.assertEqual(stats['synced'], 0)

class TestHealthDashboard(unittest.TestCase):
    """Test health dashboard"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.dashboard = HealthDashboard(db_path=f"{self.temp_dir}/health.db")
    
    def test_record_event(self):
        """Should record health events"""
        self.dashboard.record_event('cpu', 'normal', 45.0, 'CPU OK')
        
        data = self.dashboard.get_dashboard_data()
        self.assertIn('cpu', data['components'])
        self.assertEqual(data['components']['cpu']['status'], 'normal')
    
    def test_alert_generation(self):
        """Should generate alerts for critical events"""
        self.dashboard.record_event('memory', 'critical', 95.0, 'Memory critical')
        
        alerts = self.dashboard.get_active_alerts()
        self.assertTrue(len(alerts) > 0)
        self.assertEqual(alerts[0]['severity'], 'critical')
    
    def test_overall_status(self):
        """Should calculate correct overall status"""
        self.dashboard.record_event('cpu', 'normal', 45.0, 'OK')
        self.dashboard.record_event('memory', 'warning', 82.0, 'High')
        
        data = self.dashboard.get_dashboard_data()
        self.assertEqual(data['status'], 'warning')
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

class TestOfflineResilience(unittest.TestCase):
    """Test offline resilience manager"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.resilience = OfflineResilienceManager(
            db_path=f"{self.temp_dir}/resilience.db"
        )
    
    def test_start_offline_period(self):
        """Should start offline period tracking"""
        self.resilience.start_offline_period("Test offline")
        
        self.assertIsNotNone(self.resilience.current_period_id)
    
    def test_end_offline_period(self):
        """Should end offline period"""
        self.resilience.start_offline_period("Test")
        time.sleep(0.1)  # Let some time pass
        self.resilience.end_offline_period(synced_items=10)
        
        stats = self.resilience.get_offline_statistics(hours=1)
        self.assertEqual(stats['offline_periods'], 1)
        self.assertGreater(stats['total_offline_hours'], 0)
    
    def test_queue_health(self):
        """Should check queue health"""
        health = self.resilience.check_queue_health()
        
        self.assertIn('queue_items', health)
        self.assertIn('queue_size_mb', health)
        self.assertIn('available_storage_mb', health)
        self.assertIn('can_sustain_30_days', health)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

# ===== INTEGRATION TESTS =====

class TestIntegration(unittest.TestCase):
    """Integration tests for all components"""
    
    def test_full_sync_flow(self):
        """Test complete sync flow with all components"""
        sync_mgr = EnhancedSyncManager()
        
        # Verify all components are working
        self.assertTrue(sync_mgr.can_accept_sync())
        
        stats = sync_mgr.get_stats()
        self.assertEqual(stats['synced'], 0)
        self.assertEqual(stats['circuit_breaker_state'], 'closed')
    
    def test_offline_to_online_transition(self):
        """Test transition from offline to online"""
        resilience = OfflineResilienceManager(
            db_path=f"{tempfile.mkdtemp()}/resilience.db"
        )
        
        # Go offline
        resilience.start_offline_period("Connection lost")
        time.sleep(0.1)
        
        # Check health
        health = resilience.check_queue_health()
        self.assertIsNotNone(health)
        
        # Come back online
        resilience.end_offline_period(synced_items=5)
        
        # Check statistics
        stats = resilience.get_offline_statistics(hours=1)
        self.assertEqual(stats['offline_periods'], 1)

# ===== RUN TESTS =====

if __name__ == '__main__':
    print("\n" + "="*60)
    print("GOTG PACS - Battle-Ready Validation Test Suite")
    print("="*60 + "\n")
    
    # Configure test runner
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCircuitBreaker))
    suite.addTests(loader.loadTestsFromTestCase(TestExponentialBackoff))
    suite.addTests(loader.loadTestsFromTestCase(TestDataIntegrity))
    suite.addTests(loader.loadTestsFromTestCase(TestLoadManager))
    suite.addTests(loader.loadTestsFromTestCase(TestEnhancedSyncManager))
    
    try:
        suite.addTests(loader.loadTestsFromTestCase(TestHealthDashboard))
    except:
        print("⚠️  Skipping health dashboard tests (module not available)")
    
    try:
        suite.addTests(loader.loadTestsFromTestCase(TestOfflineResilience))
    except:
        print("⚠️  Skipping offline resilience tests (module not available)")
    
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*60)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED")
        print(f"   Ran {result.testsRun} tests successfully")
        print("\n🎉 SYSTEM IS BATTLE-READY FOR DEPLOYMENT")
    else:
        print("❌ SOME TESTS FAILED")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
        print("\n⚠️  REVIEW FAILURES BEFORE DEPLOYMENT")
    print("="*60 + "\n")
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)
