"""
Cache Service for Medical Reporting Module
Handles DICOM image and metadata caching for offline access
"""

import sqlite3
import json
import logging
import hashlib
import gzip
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import threading

from config.offline_config import OfflineConfig

logger = logging.getLogger(__name__)

class CacheService:
    """Service for caching DICOM images and metadata"""
    
    def __init__(self):
        self.config = OfflineConfig()
        self.cache_db_path = self.config.OFFLINE_CACHE_DB
        self._lock = threading.RLock()
        
        # Initialize cache database
        self._initialize_cache_db()
    
    def _initialize_cache_db(self):
        """Initialize cache database schema"""
        try:
            # Ensure cache directory exists
            import os
            cache_dir = os.path.dirname(self.cache_db_path)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir, exist_ok=True)
            
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS dicom_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        study_id TEXT NOT NULL,
                        series_id TEXT,
                        instance_id TEXT,
                        cache_key TEXT UNIQUE NOT NULL,
                        data_type TEXT NOT NULL,
                        data BLOB,
                        metadata TEXT,
                        size_bytes INTEGER,
                        checksum TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        priority INTEGER DEFAULT 5
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS report_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        report_id TEXT UNIQUE NOT NULL,
                        patient_id TEXT,
                        study_id TEXT,
                        report_data TEXT NOT NULL,
                        status TEXT DEFAULT 'draft',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        sync_status TEXT DEFAULT 'pending'
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS template_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        template_id TEXT UNIQUE NOT NULL,
                        template_name TEXT NOT NULL,
                        template_data TEXT NOT NULL,
                        category TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS layout_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        layout_id TEXT UNIQUE NOT NULL,
                        user_id TEXT NOT NULL,
                        layout_name TEXT NOT NULL,
                        layout_data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for better performance
                conn.execute('CREATE INDEX IF NOT EXISTS idx_dicom_study ON dicom_cache(study_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_dicom_cache_key ON dicom_cache(cache_key)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_dicom_accessed ON dicom_cache(accessed_at)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_report_study ON report_cache(study_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_report_patient ON report_cache(patient_id)')
                
                conn.commit()
                logger.info("Cache database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize cache database: {e}")
            raise
    
    def cache_dicom_image(self, study_id: str, series_id: str, instance_id: str, 
                         image_data: bytes, metadata: Dict[str, Any] = None) -> bool:
        """Cache DICOM image data"""
        try:
            with self._lock:
                cache_key = f"dicom_image_{study_id}_{series_id}_{instance_id}"
                
                # Compress image data
                compressed_data = gzip.compress(image_data)
                
                # Calculate checksum
                checksum = hashlib.sha256(image_data).hexdigest()
                
                # Set expiration
                expires_at = datetime.utcnow() + timedelta(days=self.config.CACHE_RETENTION_DAYS)
                
                with sqlite3.connect(self.cache_db_path) as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO dicom_cache 
                        (study_id, series_id, instance_id, cache_key, data_type, data, 
                         metadata, size_bytes, checksum, expires_at, priority)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        study_id, series_id, instance_id, cache_key, 'image',
                        compressed_data, json.dumps(metadata) if metadata else None,
                        len(image_data), checksum, expires_at, 1  # High priority for images
                    ))
                    conn.commit()
                
                logger.debug(f"Cached DICOM image: {cache_key}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to cache DICOM image: {e}")
            return False
    
    def get_cached_dicom_image(self, study_id: str, series_id: str, instance_id: str) -> Optional[Tuple[bytes, Dict[str, Any]]]:
        """Retrieve cached DICOM image"""
        try:
            with self._lock:
                cache_key = f"dicom_image_{study_id}_{series_id}_{instance_id}"
                
                with sqlite3.connect(self.cache_db_path) as conn:
                    cursor = conn.execute('''
                        SELECT data, metadata, checksum FROM dicom_cache 
                        WHERE cache_key = ? AND expires_at > CURRENT_TIMESTAMP
                    ''', (cache_key,))
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    # Update access time
                    conn.execute('''
                        UPDATE dicom_cache SET accessed_at = CURRENT_TIMESTAMP 
                        WHERE cache_key = ?
                    ''', (cache_key,))
                    conn.commit()
                    
                    # Decompress data
                    compressed_data, metadata_json, checksum = row
                    image_data = gzip.decompress(compressed_data)
                    
                    # Verify checksum
                    if hashlib.sha256(image_data).hexdigest() != checksum:
                        logger.error(f"Checksum mismatch for cached image: {cache_key}")
                        return None
                    
                    metadata = json.loads(metadata_json) if metadata_json else {}
                    
                    logger.debug(f"Retrieved cached DICOM image: {cache_key}")
                    return image_data, metadata
                    
        except Exception as e:
            logger.error(f"Failed to retrieve cached DICOM image: {e}")
            return None
    
    def cache_dicom_metadata(self, study_id: str, metadata: Dict[str, Any]) -> bool:
        """Cache DICOM study metadata"""
        try:
            with self._lock:
                cache_key = f"dicom_metadata_{study_id}"
                expires_at = datetime.utcnow() + timedelta(days=self.config.CACHE_RETENTION_DAYS)
                
                with sqlite3.connect(self.cache_db_path) as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO dicom_cache 
                        (study_id, cache_key, data_type, metadata, expires_at, priority)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        study_id, cache_key, 'metadata',
                        json.dumps(metadata), expires_at, 2  # Medium priority for metadata
                    ))
                    conn.commit()
                
                logger.debug(f"Cached DICOM metadata: {cache_key}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to cache DICOM metadata: {e}")
            return False
    
    def get_cached_dicom_metadata(self, study_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached DICOM metadata"""
        try:
            with self._lock:
                cache_key = f"dicom_metadata_{study_id}"
                
                with sqlite3.connect(self.cache_db_path) as conn:
                    cursor = conn.execute('''
                        SELECT metadata FROM dicom_cache 
                        WHERE cache_key = ? AND expires_at > CURRENT_TIMESTAMP
                    ''', (cache_key,))
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    # Update access time
                    conn.execute('''
                        UPDATE dicom_cache SET accessed_at = CURRENT_TIMESTAMP 
                        WHERE cache_key = ?
                    ''', (cache_key,))
                    conn.commit()
                    
                    metadata = json.loads(row[0])
                    logger.debug(f"Retrieved cached DICOM metadata: {cache_key}")
                    return metadata
                    
        except Exception as e:
            logger.error(f"Failed to retrieve cached DICOM metadata: {e}")
            return None
    
    def cache_report(self, report_id: str, report_data: Dict[str, Any]) -> bool:
        """Cache report data"""
        try:
            with self._lock:
                with sqlite3.connect(self.cache_db_path) as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO report_cache 
                        (report_id, patient_id, study_id, report_data, status, modified_at)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (
                        report_id,
                        report_data.get('patient_id'),
                        report_data.get('study_id'),
                        json.dumps(report_data),
                        report_data.get('status', 'draft')
                    ))
                    conn.commit()
                
                logger.debug(f"Cached report: {report_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to cache report: {e}")
            return False
    
    def get_cached_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached report"""
        try:
            with self._lock:
                with sqlite3.connect(self.cache_db_path) as conn:
                    cursor = conn.execute('''
                        SELECT report_data FROM report_cache WHERE report_id = ?
                    ''', (report_id,))
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    # Update access time
                    conn.execute('''
                        UPDATE report_cache SET accessed_at = CURRENT_TIMESTAMP 
                        WHERE report_id = ?
                    ''', (report_id,))
                    conn.commit()
                    
                    report_data = json.loads(row[0])
                    logger.debug(f"Retrieved cached report: {report_id}")
                    return report_data
                    
        except Exception as e:
            logger.error(f"Failed to retrieve cached report: {e}")
            return None
    
    def cache_template(self, template_id: str, template_data: Dict[str, Any]) -> bool:
        """Cache report template"""
        try:
            with self._lock:
                with sqlite3.connect(self.cache_db_path) as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO template_cache 
                        (template_id, template_name, template_data, category, modified_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (
                        template_id,
                        template_data.get('name', ''),
                        json.dumps(template_data),
                        template_data.get('category', 'general')
                    ))
                    conn.commit()
                
                logger.debug(f"Cached template: {template_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to cache template: {e}")
            return False
    
    def get_cached_templates(self, category: str = None) -> List[Dict[str, Any]]:
        """Retrieve cached templates"""
        try:
            with self._lock:
                with sqlite3.connect(self.cache_db_path) as conn:
                    if category:
                        cursor = conn.execute('''
                            SELECT template_id, template_data FROM template_cache 
                            WHERE category = ? ORDER BY template_name
                        ''', (category,))
                    else:
                        cursor = conn.execute('''
                            SELECT template_id, template_data FROM template_cache 
                            ORDER BY template_name
                        ''')
                    
                    templates = []
                    for row in cursor.fetchall():
                        template_id, template_data_json = row
                        template_data = json.loads(template_data_json)
                        template_data['id'] = template_id
                        templates.append(template_data)
                    
                    logger.debug(f"Retrieved {len(templates)} cached templates")
                    return templates
                    
        except Exception as e:
            logger.error(f"Failed to retrieve cached templates: {e}")
            return []
    
    def cache_layout(self, layout_id: str, user_id: str, layout_data: Dict[str, Any]) -> bool:
        """Cache user layout configuration"""
        try:
            with self._lock:
                with sqlite3.connect(self.cache_db_path) as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO layout_cache 
                        (layout_id, user_id, layout_name, layout_data, modified_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (
                        layout_id,
                        user_id,
                        layout_data.get('name', ''),
                        json.dumps(layout_data)
                    ))
                    conn.commit()
                
                logger.debug(f"Cached layout: {layout_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to cache layout: {e}")
            return False
    
    def get_cached_layouts(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve cached layouts for user"""
        try:
            with self._lock:
                with sqlite3.connect(self.cache_db_path) as conn:
                    cursor = conn.execute('''
                        SELECT layout_id, layout_data FROM layout_cache 
                        WHERE user_id = ? ORDER BY layout_name
                    ''', (user_id,))
                    
                    layouts = []
                    for row in cursor.fetchall():
                        layout_id, layout_data_json = row
                        layout_data = json.loads(layout_data_json)
                        layout_data['id'] = layout_id
                        layouts.append(layout_data)
                    
                    logger.debug(f"Retrieved {len(layouts)} cached layouts for user {user_id}")
                    return layouts
                    
        except Exception as e:
            logger.error(f"Failed to retrieve cached layouts: {e}")
            return []
    
    def get_cached_studies(self, patient_id: str = None) -> List[Dict[str, Any]]:
        """Get list of cached studies"""
        try:
            with self._lock:
                with sqlite3.connect(self.cache_db_path) as conn:
                    if patient_id:
                        cursor = conn.execute('''
                            SELECT DISTINCT study_id, metadata FROM dicom_cache 
                            WHERE data_type = 'metadata' AND metadata LIKE ?
                            ORDER BY created_at DESC
                        ''', (f'%"PatientID":"{patient_id}"%',))
                    else:
                        cursor = conn.execute('''
                            SELECT DISTINCT study_id, metadata FROM dicom_cache 
                            WHERE data_type = 'metadata'
                            ORDER BY created_at DESC
                        ''')
                    
                    studies = []
                    for row in cursor.fetchall():
                        study_id, metadata_json = row
                        if metadata_json:
                            metadata = json.loads(metadata_json)
                            studies.append({
                                'study_id': study_id,
                                'metadata': metadata
                            })
                    
                    logger.debug(f"Retrieved {len(studies)} cached studies")
                    return studies
                    
        except Exception as e:
            logger.error(f"Failed to retrieve cached studies: {e}")
            return []
    
    def cleanup_old_data(self, days_old: int) -> int:
        """Clean up old cached data"""
        try:
            with self._lock:
                cutoff_date = datetime.utcnow() - timedelta(days=days_old)
                
                with sqlite3.connect(self.cache_db_path) as conn:
                    # Clean expired DICOM cache
                    cursor = conn.execute('''
                        DELETE FROM dicom_cache 
                        WHERE expires_at < CURRENT_TIMESTAMP OR accessed_at < ?
                    ''', (cutoff_date,))
                    dicom_cleaned = cursor.rowcount
                    
                    # Clean old reports (keep recent ones)
                    cursor = conn.execute('''
                        DELETE FROM report_cache 
                        WHERE accessed_at < ? AND sync_status = 'synced'
                    ''', (cutoff_date,))
                    reports_cleaned = cursor.rowcount
                    
                    conn.commit()
                    
                    total_cleaned = dicom_cleaned + reports_cleaned
                    logger.info(f"Cleaned up {total_cleaned} old cache entries")
                    return total_cleaned
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old cache data: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            with self._lock:
                with sqlite3.connect(self.cache_db_path) as conn:
                    # DICOM cache stats
                    cursor = conn.execute('''
                        SELECT 
                            COUNT(*) as total_items,
                            SUM(size_bytes) as total_size,
                            COUNT(DISTINCT study_id) as unique_studies
                        FROM dicom_cache
                    ''')
                    dicom_stats = cursor.fetchone()
                    
                    # Report cache stats
                    cursor = conn.execute('SELECT COUNT(*) FROM report_cache')
                    report_count = cursor.fetchone()[0]
                    
                    # Template cache stats
                    cursor = conn.execute('SELECT COUNT(*) FROM template_cache')
                    template_count = cursor.fetchone()[0]
                    
                    # Layout cache stats
                    cursor = conn.execute('SELECT COUNT(*) FROM layout_cache')
                    layout_count = cursor.fetchone()[0]
                    
                    return {
                        'dicom_cache': {
                            'total_items': dicom_stats[0] or 0,
                            'total_size_bytes': dicom_stats[1] or 0,
                            'unique_studies': dicom_stats[2] or 0
                        },
                        'report_cache': {'count': report_count},
                        'template_cache': {'count': template_count},
                        'layout_cache': {'count': layout_count},
                        'last_updated': datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {'error': str(e)}
    
    def clear_cache(self, cache_type: str = 'all') -> bool:
        """Clear cache data"""
        try:
            with self._lock:
                with sqlite3.connect(self.cache_db_path) as conn:
                    if cache_type == 'all':
                        conn.execute('DELETE FROM dicom_cache')
                        conn.execute('DELETE FROM report_cache')
                        conn.execute('DELETE FROM template_cache')
                        conn.execute('DELETE FROM layout_cache')
                    elif cache_type == 'dicom':
                        conn.execute('DELETE FROM dicom_cache')
                    elif cache_type == 'reports':
                        conn.execute('DELETE FROM report_cache')
                    elif cache_type == 'templates':
                        conn.execute('DELETE FROM template_cache')
                    elif cache_type == 'layouts':
                        conn.execute('DELETE FROM layout_cache')
                    
                    conn.commit()
                    logger.info(f"Cleared {cache_type} cache")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False

# Global cache service instance (initialized on first use)
cache_service = None

def get_cache_service():
    """Get or create cache service instance"""
    global cache_service
    if cache_service is None:
        cache_service = CacheService()
    return cache_service

# Initialize cache service
cache_service = get_cache_service()