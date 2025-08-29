"""
Offline-first configuration for Medical Reporting Module
"""

import os
from datetime import timedelta

class OfflineConfig:
    """Configuration for offline functionality"""
    
    # Offline storage paths
    OFFLINE_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'offline_data')
    OFFLINE_QUEUE_DB = os.path.join(OFFLINE_DATA_DIR, 'offline_queue.db')
    OFFLINE_CACHE_DB = os.path.join(OFFLINE_DATA_DIR, 'offline_cache.db')
    
    # Sync configuration
    SYNC_INTERVAL_SECONDS = 30  # Check for connectivity every 30 seconds
    SYNC_BATCH_SIZE = 50  # Process 50 items per sync batch
    SYNC_TIMEOUT_SECONDS = 300  # 5 minute timeout for sync operations
    
    # Cache configuration
    CACHE_RETENTION_DAYS = 30  # Keep cached data for 30 days
    MAX_OFFLINE_REPORTS = 1000  # Maximum number of reports to cache offline
    CACHE_CLEANUP_INTERVAL = timedelta(hours=6)  # Clean cache every 6 hours
    
    # Conflict resolution
    CONFLICT_RESOLUTION_STRATEGY = 'user_prompt'  # Options: 'user_prompt', 'latest_wins', 'merge'
    AUTO_RESOLVE_MINOR_CONFLICTS = True
    
    # Network detection
    CONNECTIVITY_CHECK_URLS = [
        'http://localhost:8042/system',  # Orthanc server
        'http://localhost:5000/health',  # SA Medical System
        'https://www.google.com',        # Internet connectivity
    ]
    CONNECTIVITY_TIMEOUT = 5  # seconds
    
    # Offline capabilities
    OFFLINE_FEATURES = {
        'report_creation': True,
        'report_editing': True,
        'voice_dictation': True,
        'template_access': True,
        'image_viewing': True,
        'layout_customization': True,
    }
    
    # Data priorities for sync
    SYNC_PRIORITIES = {
        'reports': 1,          # Highest priority
        'voice_recordings': 2,
        'templates': 3,
        'layouts': 4,
        'cache_updates': 5,    # Lowest priority
    }