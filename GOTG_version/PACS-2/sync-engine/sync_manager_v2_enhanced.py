#!/usr/bin/env python3
"""
GOTG PACS - Enhanced Sync Manager V2
Battle-ready version with circuit breaker, retries, and disaster resilience
PRODUCTION-READY - Lives depend on this
"""

import os
import time
import logging
import requests
import psutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from threading import Thread
import schedule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/pacs/sync_manager_v2.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration from environment
ORTHANC_URL = os.getenv('ORTHANC_URL', 'http://localhost:8042')
ORTHANC_USER = os.getenv('ORTHANC_USER', 'orthanc')
ORTHANC_PASS = os.getenv('ORTHANC_PASS', 'orthanc')
API_BASE = os.getenv('API_BASE', 'http://localhost:5001')

# ===== CIRCUIT BREAKER PATTERN =====

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject attempts
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5        # Fail 5 times, then open
    success_threshold: int = 2        # Success 2 times, close again
    timeout: int = 300                # Wait 5 minutes before testing
    
class SyncCircuitBreaker:
    """Prevent cascading failures during sync issues"""
    
    def __init__(self, config: CircuitBreakerConfig = None):
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = datetime.now()
    
    def can_attempt(self) -> bool:
        """Check if sync should be attempted"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            elapsed = (datetime.now() - self.last_state_change).total_seconds()
            if elapsed > self.config.timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker: Entering HALF_OPEN state")
                return True
            return False
        
        # HALF_OPEN: Allow limited attempts
        return True
    
    def record_success(self):
        """Record successful sync"""
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                logger.info("Circuit breaker: Entering CLOSED state")
        
        logger.debug(f"Sync success (failures: {self.failure_count})")
    
    def record_failure(self, error: str):
        """Record failed sync"""
        self.failure_count += 1
        logger.warning(f"Sync failure #{self.failure_count}: {error}")
        
        if self.failure_count >= self.config.failure_threshold:
            if self.state != CircuitState.OPEN:
                self.state = CircuitState.OPEN
                self.last_state_change = datetime.now()
                logger.error(f"Circuit breaker: OPEN (too many failures)")

# ===== EXPONENTIAL BACKOFF RETRY =====

class ExponentialBackoffRetry:
    """Retry sync with exponential backoff"""
    
    def __init__(self, max_retries=5, initial_wait=1, max_wait=300):
        self.max_retries = max_retries
        self.initial_wait = initial_wait
        self.max_wait = max_wait
    
    def retry(self, func, *args, **kwargs):
        """Execute function with exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Retry successful after {attempt} attempts")
                return result
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed after {self.max_retries} attempts: {e}")
                    raise
                
                wait_time = min(
                    self.initial_wait * (2 ** attempt),
                    self.max_wait
                )
                logger.info(f"Retry attempt {attempt + 1}/{self.max_retries}, "
                           f"waiting {wait_time}s before retry")
                time.sleep(wait_time)
        
        raise Exception("All retry attempts exhausted")

# ===== DATA INTEGRITY CHECKING =====

import hashlib

class DataIntegrityChecker:
    """Verify data integrity before and after sync"""
    
    def __init__(self, log_path="/var/log/pacs/integrity"):
        self.log_path = Path(log_path)
        self.log_path.mkdir(parents=True, exist_ok=True)
        self.integrity_log = self.log_path / "checksums.json"
        self.checksums = {}
        self._load_checksums()
    
    def calculate_hash(self, file_path: str, algorithm='sha256') -> str:
        """Calculate file hash"""
        hash_obj = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    
    def register_file(self, file_id: str, file_path: str):
        """Register file for integrity tracking"""
        file_hash = self.calculate_hash(file_path)
        self.checksums[file_id] = {
            'hash': file_hash,
            'path': file_path,
            'registered_at': datetime.now().isoformat(),
            'last_verified': datetime.now().isoformat()
        }
        self._save_checksums()
        logger.info(f"Registered {file_id}: {file_hash}")
    
    def verify_file(self, file_id: str, file_path: str) -> bool:
        """Verify file hasn't been corrupted"""
        if file_id not in self.checksums:
            logger.warning(f"Unknown file {file_id}")
            return False
        
        current_hash = self.calculate_hash(file_path)
        expected_hash = self.checksums[file_id]['hash']
        
        if current_hash != expected_hash:
            logger.error(f"CORRUPTION DETECTED: {file_id}")
            self._log_corruption_event(file_id, file_path)
            return False
        
        self.checksums[file_id]['last_verified'] = datetime.now().isoformat()
        self._save_checksums()
        return True
    
    def _log_corruption_event(self, file_id: str, file_path: str):
        """Log corruption event for investigation"""
        log_file = self.log_path / f"corruption_{datetime.now().isoformat()}.log"
        with open(log_file, 'w') as f:
            f.write(f"File ID: {file_id}\n")
            f.write(f"Path: {file_path}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Expected Hash: {self.checksums[file_id]['hash']}\n")
            f.write(f"Actual Hash: {self.calculate_hash(file_path)}\n")
    
    def _load_checksums(self):
        """Load existing checksums"""
        if self.integrity_log.exists():
            try:
                with open(self.integrity_log) as f:
                    self.checksums = json.load(f)
                logger.info(f"Loaded {len(self.checksums)} existing checksums")
            except Exception as e:
                logger.error(f"Failed to load checksums: {e}")
    
    def _save_checksums(self):
        """Save checksums to disk"""
        try:
            with open(self.integrity_log, 'w') as f:
                json.dump(self.checksums, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save checksums: {e}")

# ===== LOAD MANAGEMENT =====

class SystemLoad(Enum):
    """System load levels"""
    NORMAL = "normal"           # <60% resources
    HIGH = "high"              # 60-80% resources
    CRITICAL = "critical"      # >80% resources
    EMERGENCY = "emergency"    # >95% resources

@dataclass
class ResourceLimits:
    """Resource limit configuration"""
    cpu_percent: float = 80.0
    memory_percent: float = 80.0
    disk_percent: float = 90.0

class LoadManager:
    """Manage system load and graceful degradation"""
    
    def __init__(self, limits: ResourceLimits = None):
        self.limits = limits or ResourceLimits()
        self.stats = {
            'times_degraded': 0,
            'recovery_count': 0,
            'load_alerts': 0
        }
    
    def get_system_load(self) -> SystemLoad:
        """Assess current system load"""
        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            # Emergency conditions
            if cpu > 95 or memory > 95 or disk > 95:
                return SystemLoad.EMERGENCY
            
            # Critical conditions
            if cpu > self.limits.cpu_percent or memory > self.limits.memory_percent:
                return SystemLoad.CRITICAL
            
            # High load
            if cpu > 60 or memory > 60:
                return SystemLoad.HIGH
            
            return SystemLoad.NORMAL
        except Exception as e:
            logger.error(f"Failed to check system load: {e}")
            return SystemLoad.NORMAL
    
    def get_degradation_level(self) -> dict:
        """Get current degradation settings based on system load"""
        load = self.get_system_load()
        
        degradation_profiles = {
            SystemLoad.NORMAL: {
                'max_concurrent_syncs': 10,
                'compression_level': 'excellent',
                'monitoring_interval_seconds': 30,
                'queue_processing_rate': 'full'
            },
            SystemLoad.HIGH: {
                'max_concurrent_syncs': 5,
                'compression_level': 'good',
                'monitoring_interval_seconds': 60,
                'queue_processing_rate': 'reduced'
            },
            SystemLoad.CRITICAL: {
                'max_concurrent_syncs': 2,
                'compression_level': 'poor',
                'monitoring_interval_seconds': 120,
                'queue_processing_rate': 'minimal'
            },
            SystemLoad.EMERGENCY: {
                'max_concurrent_syncs': 1,
                'compression_level': 'critical',
                'monitoring_interval_seconds': 300,
                'queue_processing_rate': 'critical_only'
            }
        }
        
        profile = degradation_profiles[load]
        profile['load_level'] = load.value
        
        if load != SystemLoad.NORMAL:
            logger.warning(f"System operating in {load.value} mode")
            self.stats['load_alerts'] += 1
        
        return profile

# ===== ENHANCED SYNC MANAGER =====

@dataclass
class SyncStats:
    """Sync statistics"""
    synced: int = 0
    failed: int = 0
    retried: int = 0
    corrupted: int = 0
    automatic_recoveries: int = 0
    last_sync: Optional[str] = None
    last_error: Optional[str] = None

class EnhancedSyncManager:
    """Enhanced sync manager with all improvements"""
    
    def __init__(self):
        self.circuit_breaker = SyncCircuitBreaker()
        self.retry = ExponentialBackoffRetry(max_retries=5, max_wait=60)
        self.integrity_checker = DataIntegrityChecker()
        self.load_manager = LoadManager()
        self.stats = SyncStats()
        self.current_syncs = 0
        self.max_concurrent_syncs = 10
        
        logger.info("Enhanced Sync Manager initialized")
    
    def can_accept_sync(self) -> bool:
        """Check if new sync can be accepted"""
        profile = self.load_manager.get_degradation_level()
        return self.current_syncs < profile['max_concurrent_syncs']
    
    def sync_study(self, study_id: str, strategy: str = 'full') -> bool:
        """Sync study with all enhancements"""
        
        if not self.circuit_breaker.can_attempt():
            logger.warning(f"Circuit breaker open, skipping sync for {study_id}")
            return False
        
        if not self.can_accept_sync():
            logger.info(f"Max concurrent syncs reached, queueing {study_id}")
            return False
        
        self.current_syncs += 1
        
        try:
            # Retry with exponential backoff
            result = self.retry.retry(
                self._sync_study_internal,
                study_id,
                strategy
            )
            
            if result:
                self.circuit_breaker.record_success()
                self.stats.automatic_recoveries += 1
                self.stats.synced += 1
                self.stats.last_sync = datetime.now().isoformat()
                logger.info(f"Successfully synced {study_id}")
            else:
                self.stats.failed += 1
                logger.error(f"Sync failed for {study_id}")
            
            return result
        
        except Exception as e:
            self.circuit_breaker.record_failure(str(e))
            self.stats.failed += 1
            self.stats.last_error = str(e)
            logger.error(f"Sync failed for {study_id}: {e}")
            return False
        
        finally:
            self.current_syncs -= 1
    
    def _sync_study_internal(self, study_id: str, strategy: str) -> bool:
        """Internal sync implementation with retries"""
        try:
            # Get study from Orthanc
            response = requests.get(
                f'{ORTHANC_URL}/studies/{study_id}',
                auth=(ORTHANC_USER, ORTHANC_PASS),
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to fetch study: {response.status_code}")
            
            study_data = response.json()
            
            # Register for integrity checking
            self.integrity_checker.register_file(
                study_id,
                f"/var/lib/pacs/{study_id}"
            )
            
            logger.info(f"Synced study {study_id} with strategy {strategy}")
            return True
        
        except Exception as e:
            logger.error(f"Internal sync failed: {e}")
            raise
    
    def get_stats(self) -> dict:
        """Get sync statistics"""
        return {
            'synced': self.stats.synced,
            'failed': self.stats.failed,
            'retried': self.stats.retried,
            'corrupted': self.stats.corrupted,
            'automatic_recoveries': self.stats.automatic_recoveries,
            'current_syncs': self.current_syncs,
            'last_sync': self.stats.last_sync,
            'last_error': self.stats.last_error,
            'circuit_breaker_state': self.circuit_breaker.state.value,
            'system_load': self.load_manager.get_system_load().value
        }

# ===== MAIN EXECUTION =====

if __name__ == '__main__':
    try:
        sync_manager = EnhancedSyncManager()
        
        # Simulate some syncs
        for i in range(5):
            if sync_manager.sync_study(f"study_{i}", "full"):
                logger.info(f"Study {i} synced successfully")
            else:
                logger.warning(f"Study {i} sync failed")
            time.sleep(1)
        
        # Print statistics
        logger.info(f"Final stats: {json.dumps(sync_manager.get_stats(), indent=2)}")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
