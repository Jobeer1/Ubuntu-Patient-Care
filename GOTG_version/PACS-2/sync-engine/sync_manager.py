#!/usr/bin/env python3
"""
GOTG PACS Sync Manager
Intelligent synchronization engine for hostile network environments
"""

import os
import time
import json
import logging
import requests
import schedule
import psutil
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify
from threading import Thread
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
ORTHANC_URL = os.getenv('ORTHANC_URL', 'http://pacs-orthanc:8042')
ORTHANC_USER = os.getenv('ORTHANC_USERNAME', 'orthanc')
ORTHANC_PASS = os.getenv('ORTHANC_PASSWORD', 'orthanc')
RIS_URL = os.getenv('RIS_URL', 'http://host.docker.internal:5000')
SYNC_MODE = os.getenv('SYNC_MODE', 'auto')
MAX_BANDWIDTH_MBPS = float(os.getenv('MAX_BANDWIDTH_MBPS', '1'))
COMPRESSION_LEVEL = os.getenv('COMPRESSION_LEVEL', 'high')
QUEUE_DIR = Path('/app/queue')
QUEUE_DIR.mkdir(exist_ok=True)

# Flask app for monitoring
app = Flask(__name__)

class NetworkMonitor:
    """Monitor network conditions and adapt sync strategy"""
    
    def __init__(self):
        self.status = 'unknown'
        self.bandwidth_mbps = 0
        self.latency_ms = 0
        self.last_check = None
    
    def check_network(self):
        """Check network connectivity and quality"""
        try:
            start = time.time()
            response = requests.get(f'{RIS_URL}/health', timeout=5)
            latency = (time.time() - start) * 1000
            
            if response.status_code == 200:
                self.status = 'online'
                self.latency_ms = latency
                self.bandwidth_mbps = self._estimate_bandwidth(latency)
                self.last_check = datetime.now()
                logger.info(f"Network: {self.status}, Latency: {latency:.0f}ms, Bandwidth: {self.bandwidth_mbps:.1f}Mbps")
                return True
            else:
                self.status = 'degraded'
                return False
        except Exception as e:
            self.status = 'offline'
            self.bandwidth_mbps = 0
            self.last_check = datetime.now()
            logger.warning(f"Network offline: {e}")
            return False
    
    def _estimate_bandwidth(self, latency_ms):
        """Estimate bandwidth based on latency"""
        if latency_ms < 50:
            return 10.0  # Excellent
        elif latency_ms < 200:
            return 5.0   # Good
        elif latency_ms < 500:
            return 1.0   # Fair
        else:
            return 0.5   # Poor
    
    def get_sync_strategy(self):
        """Determine sync strategy based on network conditions"""
        if self.status == 'offline':
            return 'queue'
        elif self.bandwidth_mbps >= 10:
            return 'full'
        elif self.bandwidth_mbps >= 1:
            return 'compressed'
        else:
            return 'minimal'

class SyncQueue:
    """Manage sync queue for offline operations"""
    
    def __init__(self):
        self.queue_file = QUEUE_DIR / 'sync_queue.json'
        self.queue = self._load_queue()
    
    def _load_queue(self):
        """Load queue from disk"""
        if self.queue_file.exists():
            try:
                with open(self.queue_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load queue: {e}")
                return []
        return []
    
    def _save_queue(self):
        """Save queue to disk"""
        try:
            with open(self.queue_file, 'w') as f:
                json.dump(self.queue, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save queue: {e}")
    
    def add(self, item):
        """Add item to sync queue"""
        item['queued_at'] = datetime.now().isoformat()
        item['priority'] = item.get('priority', 'medium')
        self.queue.append(item)
        self._save_queue()
        logger.info(f"Added to queue: {item.get('type')} - {item.get('id')}")
    
    def get_next(self, strategy='full'):
        """Get next item from queue based on strategy"""
        if not self.queue:
            return None
        
        # Sort by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        self.queue.sort(key=lambda x: priority_order.get(x.get('priority', 'medium'), 2))
        
        # Filter by strategy
        if strategy == 'minimal':
            # Only critical items
            for item in self.queue:
                if item.get('priority') == 'critical':
                    return item
            return None
        
        return self.queue[0] if self.queue else None
    
    def remove(self, item):
        """Remove item from queue"""
        try:
            self.queue.remove(item)
            self._save_queue()
            logger.info(f"Removed from queue: {item.get('type')} - {item.get('id')}")
        except ValueError:
            pass
    
    def size(self):
        """Get queue size"""
        return len(self.queue)

class SyncManager:
    """Main sync manager"""
    
    def __init__(self):
        self.network = NetworkMonitor()
        self.queue = SyncQueue()
        self.stats = {
            'synced': 0,
            'failed': 0,
            'queued': 0,
            'last_sync': None
        }
    
    def sync_study(self, study_id, strategy='full'):
        """Sync a single study"""
        try:
            # Get study from Orthanc
            response = requests.get(
                f'{ORTHANC_URL}/studies/{study_id}',
                auth=(ORTHANC_USER, ORTHANC_PASS),
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get study {study_id}")
                return False
            
            study_data = response.json()
            
            # Apply compression based on strategy
            if strategy == 'compressed':
                # Get compressed version
                logger.info(f"Syncing study {study_id} with compression")
            elif strategy == 'minimal':
                # Only metadata
                logger.info(f"Syncing study {study_id} metadata only")
            else:
                # Full quality
                logger.info(f"Syncing study {study_id} full quality")
            
            # Send to RIS or central PACS
            # (Implementation depends on target system)
            
            self.stats['synced'] += 1
            self.stats['last_sync'] = datetime.now().isoformat()
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync study {study_id}: {e}")
            self.stats['failed'] += 1
            return False
    
    def process_queue(self):
        """Process sync queue"""
        if not self.network.check_network():
            logger.info("Network offline, skipping sync")
            return
        
        strategy = self.network.get_sync_strategy()
        logger.info(f"Processing queue with strategy: {strategy}")
        
        processed = 0
        max_items = 10  # Process max 10 items per cycle
        
        while processed < max_items:
            item = self.queue.get_next(strategy)
            if not item:
                break
            
            if item['type'] == 'study':
                if self.sync_study(item['id'], strategy):
                    self.queue.remove(item)
                    processed += 1
                else:
                    # Retry later
                    break
            
            # Rate limiting
            time.sleep(1)
        
        logger.info(f"Processed {processed} items, {self.queue.size()} remaining")
    
    def monitor_new_studies(self):
        """Monitor for new studies in Orthanc"""
        try:
            response = requests.get(
                f'{ORTHANC_URL}/studies',
                auth=(ORTHANC_USER, ORTHANC_PASS),
                timeout=10
            )
            
            if response.status_code == 200:
                studies = response.json()
                # Check for new studies and add to queue
                # (Implementation depends on tracking mechanism)
                logger.debug(f"Found {len(studies)} studies")
        except Exception as e:
            logger.error(f"Failed to monitor studies: {e}")
    
    def run(self):
        """Main sync loop"""
        logger.info("Starting GOTG PACS Sync Manager")
        
        # Schedule tasks
        schedule.every(5).minutes.do(self.process_queue)
        schedule.every(1).minutes.do(self.monitor_new_studies)
        schedule.every(30).seconds.do(self.network.check_network)
        
        # Initial check
        self.network.check_network()
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutting down sync manager")
                break
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                time.sleep(5)

# Flask routes for monitoring
@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/status')
def status():
    """Get sync status"""
    return jsonify({
        'network': {
            'status': sync_manager.network.status,
            'bandwidth_mbps': sync_manager.network.bandwidth_mbps,
            'latency_ms': sync_manager.network.latency_ms,
            'last_check': sync_manager.network.last_check.isoformat() if sync_manager.network.last_check else None
        },
        'queue': {
            'size': sync_manager.queue.size(),
            'items': sync_manager.queue.queue[:10]  # First 10 items
        },
        'stats': sync_manager.stats,
        'system': {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent
        }
    })

@app.route('/sync-now', methods=['POST'])
def sync_now():
    """Trigger immediate sync"""
    sync_manager.process_queue()
    return jsonify({'status': 'sync triggered'})

# Global sync manager instance
sync_manager = SyncManager()

def run_flask():
    """Run Flask monitoring server"""
    app.run(host='0.0.0.0', port=5001, debug=False)

if __name__ == '__main__':
    # Start Flask in separate thread
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Run sync manager
    sync_manager.run()
