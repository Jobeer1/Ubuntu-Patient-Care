"""
Synchronization Queue for Medical Reporting Module
Manages offline actions and synchronization with external systems
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import threading
import uuid

from config.offline_config import OfflineConfig

logger = logging.getLogger(__name__)

class SynchronizationQueue:
    """Queue for managing offline actions and synchronization"""
    
    def __init__(self):
        self.config = OfflineConfig()
        self.queue_db_path = self.config.OFFLINE_QUEUE_DB
        self._lock = threading.RLock()
        
        # Initialize queue database
        self._initialize_queue_db()
    
    def _initialize_queue_db(self):
        """Initialize synchronization queue database"""
        try:
            with sqlite3.connect(self.queue_db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS sync_queue (
                        id TEXT PRIMARY KEY,
                        item_type TEXT NOT NULL,
                        action TEXT NOT NULL,
                        data TEXT NOT NULL,
                        priority INTEGER DEFAULT 5,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        scheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        attempted_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        retry_count INTEGER DEFAULT 0,
                        max_retries INTEGER DEFAULT 3,
                        error_message TEXT,
                        dependencies TEXT
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS sync_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sync_item_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        message TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (sync_item_id) REFERENCES sync_queue (id)
                    )
                ''')
                
                # Create indexes for better performance
                conn.execute('CREATE INDEX IF NOT EXISTS idx_sync_status ON sync_queue(status)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_sync_priority ON sync_queue(priority, created_at)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_sync_type ON sync_queue(item_type)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_sync_scheduled ON sync_queue(scheduled_at)')
                
                conn.commit()
                logger.info("Synchronization queue database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize sync queue database: {e}")
            raise
    
    def add_item(self, item_type: str, action: str, data: Dict[str, Any], 
                 priority: int = 5, dependencies: List[str] = None, 
                 schedule_at: datetime = None) -> str:
        """Add item to synchronization queue"""
        try:
            with self._lock:
                item_id = str(uuid.uuid4())
                scheduled_at = schedule_at or datetime.utcnow()
                
                with sqlite3.connect(self.queue_db_path) as conn:
                    conn.execute('''
                        INSERT INTO sync_queue 
                        (id, item_type, action, data, priority, scheduled_at, dependencies)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item_id, item_type, action, json.dumps(data), 
                        priority, scheduled_at, 
                        json.dumps(dependencies) if dependencies else None
                    ))
                    conn.commit()
                
                self._log_event(item_id, 'queued', f'Added {item_type} action: {action}')
                logger.debug(f"Added sync item: {item_id} ({item_type}:{action})")
                return item_id
                
        except Exception as e:
            logger.error(f"Failed to add sync item: {e}")
            raise
    
    def get_pending_items(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get pending items from queue, ordered by priority and creation time"""
        try:
            with self._lock:
                with sqlite3.connect(self.queue_db_path) as conn:
                    cursor = conn.execute('''
                        SELECT id, item_type, action, data, priority, retry_count, dependencies
                        FROM sync_queue 
                        WHERE status = 'pending' 
                        AND scheduled_at <= CURRENT_TIMESTAMP
                        AND (retry_count < max_retries OR max_retries = -1)
                        ORDER BY priority ASC, created_at ASC
                        LIMIT ?
                    ''', (limit,))
                    
                    items = []
                    for row in cursor.fetchall():
                        item_id, item_type, action, data_json, priority, retry_count, dependencies_json = row
                        
                        # Check dependencies
                        if dependencies_json:
                            dependencies = json.loads(dependencies_json)
                            if not self._check_dependencies(dependencies):
                                continue  # Skip if dependencies not met
                        
                        items.append({
                            'id': item_id,
                            'type': item_type,
                            'action': action,
                            'data': json.loads(data_json),
                            'priority': priority,
                            'retry_count': retry_count
                        })
                    
                    logger.debug(f"Retrieved {len(items)} pending sync items")
                    return items
                    
        except Exception as e:
            logger.error(f"Failed to get pending sync items: {e}")
            return []
    
    def _check_dependencies(self, dependencies: List[str]) -> bool:
        """Check if all dependencies are completed"""
        try:
            with sqlite3.connect(self.queue_db_path) as conn:
                for dep_id in dependencies:
                    cursor = conn.execute('''
                        SELECT status FROM sync_queue WHERE id = ?
                    ''', (dep_id,))
                    
                    row = cursor.fetchone()
                    if not row or row[0] != 'completed':
                        return False
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to check dependencies: {e}")
            return False
    
    def mark_processing(self, item_id: str) -> bool:
        """Mark item as being processed"""
        try:
            with self._lock:
                with sqlite3.connect(self.queue_db_path) as conn:
                    cursor = conn.execute('''
                        UPDATE sync_queue 
                        SET status = 'processing', attempted_at = CURRENT_TIMESTAMP,
                            retry_count = retry_count + 1
                        WHERE id = ? AND status = 'pending'
                    ''', (item_id,))
                    
                    if cursor.rowcount > 0:
                        conn.commit()
                        self._log_event(item_id, 'processing', 'Started processing')
                        return True
                    
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to mark item as processing: {e}")
            return False
    
    def mark_completed(self, item_id: str, result_data: Dict[str, Any] = None) -> bool:
        """Mark item as completed"""
        try:
            with self._lock:
                with sqlite3.connect(self.queue_db_path) as conn:
                    # Update item status
                    conn.execute('''
                        UPDATE sync_queue 
                        SET status = 'completed', completed_at = CURRENT_TIMESTAMP,
                            error_message = NULL
                        WHERE id = ?
                    ''', (item_id,))
                    
                    # If result data provided, store it
                    if result_data:
                        conn.execute('''
                            UPDATE sync_queue 
                            SET data = json_set(data, '$.sync_result', ?)
                            WHERE id = ?
                        ''', (json.dumps(result_data), item_id))
                    
                    conn.commit()
                
                self._log_event(item_id, 'completed', 'Successfully completed')
                logger.debug(f"Marked sync item as completed: {item_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to mark item as completed: {e}")
            return False
    
    def mark_failed(self, item_id: str, error_message: str = None) -> bool:
        """Mark item as failed"""
        try:
            with self._lock:
                with sqlite3.connect(self.queue_db_path) as conn:
                    # Check if we should retry or mark as failed
                    cursor = conn.execute('''
                        SELECT retry_count, max_retries FROM sync_queue WHERE id = ?
                    ''', (item_id,))
                    
                    row = cursor.fetchone()
                    if not row:
                        return False
                    
                    retry_count, max_retries = row
                    
                    if max_retries == -1 or retry_count < max_retries:
                        # Reset to pending for retry
                        status = 'pending'
                        # Exponential backoff for retry scheduling
                        retry_delay = min(300, 30 * (2 ** retry_count))  # Max 5 minutes
                        scheduled_at = datetime.utcnow() + timedelta(seconds=retry_delay)
                        
                        conn.execute('''
                            UPDATE sync_queue 
                            SET status = ?, error_message = ?, scheduled_at = ?
                            WHERE id = ?
                        ''', (status, error_message, scheduled_at, item_id))
                        
                        self._log_event(item_id, 'retry_scheduled', 
                                      f'Scheduled for retry in {retry_delay}s: {error_message}')
                    else:
                        # Mark as permanently failed
                        conn.execute('''
                            UPDATE sync_queue 
                            SET status = 'failed', error_message = ?
                            WHERE id = ?
                        ''', (error_message, item_id))
                        
                        self._log_event(item_id, 'failed', f'Permanently failed: {error_message}')
                    
                    conn.commit()
                
                logger.debug(f"Marked sync item as failed: {item_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to mark item as failed: {e}")
            return False
    
    def cancel_item(self, item_id: str) -> bool:
        """Cancel a pending sync item"""
        try:
            with self._lock:
                with sqlite3.connect(self.queue_db_path) as conn:
                    cursor = conn.execute('''
                        UPDATE sync_queue 
                        SET status = 'cancelled'
                        WHERE id = ? AND status IN ('pending', 'processing')
                    ''', (item_id,))
                    
                    if cursor.rowcount > 0:
                        conn.commit()
                        self._log_event(item_id, 'cancelled', 'Item cancelled by user')
                        logger.debug(f"Cancelled sync item: {item_id}")
                        return True
                    
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to cancel sync item: {e}")
            return False
    
    def get_item_status(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific sync item"""
        try:
            with self._lock:
                with sqlite3.connect(self.queue_db_path) as conn:
                    cursor = conn.execute('''
                        SELECT item_type, action, status, created_at, completed_at, 
                               retry_count, max_retries, error_message
                        FROM sync_queue WHERE id = ?
                    ''', (item_id,))
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    return {
                        'id': item_id,
                        'type': row[0],
                        'action': row[1],
                        'status': row[2],
                        'created_at': row[3],
                        'completed_at': row[4],
                        'retry_count': row[5],
                        'max_retries': row[6],
                        'error_message': row[7]
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get item status: {e}")
            return None
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get synchronization queue statistics"""
        try:
            with self._lock:
                with sqlite3.connect(self.queue_db_path) as conn:
                    # Count by status
                    cursor = conn.execute('''
                        SELECT status, COUNT(*) FROM sync_queue GROUP BY status
                    ''')
                    status_counts = dict(cursor.fetchall())
                    
                    # Count by type
                    cursor = conn.execute('''
                        SELECT item_type, COUNT(*) FROM sync_queue 
                        WHERE status IN ('pending', 'processing')
                        GROUP BY item_type
                    ''')
                    type_counts = dict(cursor.fetchall())
                    
                    # Get oldest pending item
                    cursor = conn.execute('''
                        SELECT MIN(created_at) FROM sync_queue WHERE status = 'pending'
                    ''')
                    oldest_pending = cursor.fetchone()[0]
                    
                    return {
                        'status_counts': status_counts,
                        'type_counts': type_counts,
                        'oldest_pending': oldest_pending,
                        'total_items': sum(status_counts.values())
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {'error': str(e)}
    
    def get_pending_count(self) -> int:
        """Get count of pending items"""
        try:
            with self._lock:
                with sqlite3.connect(self.queue_db_path) as conn:
                    cursor = conn.execute('''
                        SELECT COUNT(*) FROM sync_queue WHERE status = 'pending'
                    ''')
                    return cursor.fetchone()[0]
                    
        except Exception as e:
            logger.error(f"Failed to get pending count: {e}")
            return 0
    
    def get_last_sync_time(self) -> Optional[str]:
        """Get timestamp of last successful sync"""
        try:
            with self._lock:
                with sqlite3.connect(self.queue_db_path) as conn:
                    cursor = conn.execute('''
                        SELECT MAX(completed_at) FROM sync_queue WHERE status = 'completed'
                    ''')
                    result = cursor.fetchone()[0]
                    return result
                    
        except Exception as e:
            logger.error(f"Failed to get last sync time: {e}")
            return None
    
    def cleanup_completed_items(self, days_old: int) -> int:
        """Clean up old completed sync items"""
        try:
            with self._lock:
                cutoff_date = datetime.utcnow() - timedelta(days=days_old)
                
                with sqlite3.connect(self.queue_db_path) as conn:
                    # Clean completed items
                    cursor = conn.execute('''
                        DELETE FROM sync_queue 
                        WHERE status IN ('completed', 'cancelled', 'failed')
                        AND completed_at < ?
                    ''', (cutoff_date,))
                    
                    cleaned_count = cursor.rowcount
                    
                    # Clean orphaned log entries
                    conn.execute('''
                        DELETE FROM sync_log 
                        WHERE sync_item_id NOT IN (SELECT id FROM sync_queue)
                    ''')
                    
                    conn.commit()
                    
                    logger.info(f"Cleaned up {cleaned_count} old sync queue items")
                    return cleaned_count
                    
        except Exception as e:
            logger.error(f"Failed to cleanup sync queue: {e}")
            return 0
    
    def _log_event(self, sync_item_id: str, event_type: str, message: str):
        """Log sync event"""
        try:
            with sqlite3.connect(self.queue_db_path) as conn:
                conn.execute('''
                    INSERT INTO sync_log (sync_item_id, event_type, message)
                    VALUES (?, ?, ?)
                ''', (sync_item_id, event_type, message))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to log sync event: {e}")
    
    def get_item_log(self, item_id: str) -> List[Dict[str, Any]]:
        """Get log entries for a sync item"""
        try:
            with self._lock:
                with sqlite3.connect(self.queue_db_path) as conn:
                    cursor = conn.execute('''
                        SELECT event_type, message, timestamp FROM sync_log 
                        WHERE sync_item_id = ? ORDER BY timestamp DESC
                    ''', (item_id,))
                    
                    return [
                        {
                            'event_type': row[0],
                            'message': row[1],
                            'timestamp': row[2]
                        }
                        for row in cursor.fetchall()
                    ]
                    
        except Exception as e:
            logger.error(f"Failed to get item log: {e}")
            return []
    
    def clear_queue(self, status_filter: str = None) -> int:
        """Clear sync queue items"""
        try:
            with self._lock:
                with sqlite3.connect(self.queue_db_path) as conn:
                    if status_filter:
                        cursor = conn.execute('''
                            DELETE FROM sync_queue WHERE status = ?
                        ''', (status_filter,))
                    else:
                        cursor = conn.execute('DELETE FROM sync_queue')
                    
                    cleared_count = cursor.rowcount
                    
                    # Clear related log entries
                    conn.execute('DELETE FROM sync_log')
                    
                    conn.commit()
                    
                    logger.info(f"Cleared {cleared_count} sync queue items")
                    return cleared_count
                    
        except Exception as e:
            logger.error(f"Failed to clear sync queue: {e}")
            return 0