#!/usr/bin/env python3
"""
🇿🇦 SA Medical Reporting - Typist Queue Manager

Manages the queue of dictation sessions awaiting typist review and correction.
Provides priority-based queue management, report claiming/releasing, and
performance tracking for South African healthcare workflows.
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import threading
import time

logger = logging.getLogger(__name__)

@dataclass
class QueueItem:
    """Represents an item in the typist queue"""
    session_id: str
    patient_name: str = ""
    patient_id: str = ""
    doctor_name: str = ""
    doctor_id: str = ""
    study_type: str = ""
    study_description: str = ""
    priority: str = "routine"  # urgent, routine, low
    created_date: str = ""
    audio_duration: float = 0.0
    estimated_work_time: float = 0.0
    claimed_by: str = ""
    claimed_at: str = ""
    status: str = "pending"  # pending, claimed, in_progress, completed
    language: str = "en-ZA"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'QueueItem':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class TypistStats:
    """Typist performance statistics"""
    typist_id: str
    reports_completed_today: int = 0
    reports_completed_week: int = 0
    average_completion_time: float = 0.0
    accuracy_rate: float = 0.0
    total_work_time: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

class TypistQueueManager:
    """
    Manages the typist queue for SA medical reporting
    """
    
    def __init__(self, db_path: str = "reporting.db"):
        self.db_path = db_path
        self.claim_timeout_minutes = 120  # 2 hours
        self.init_queue_tables()
        self.start_cleanup_thread()
    
    def init_queue_tables(self):
        """Initialize queue-specific database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Enhanced dictation sessions - add queue fields if not exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dictation_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    patient_id TEXT,
                    study_id TEXT,
                    image_ids TEXT,
                    audio_file_path TEXT,
                    audio_duration REAL,
                    raw_transcript TEXT,
                    corrected_transcript TEXT,
                    status TEXT DEFAULT 'recording',
                    language TEXT DEFAULT 'en-ZA',
                    created_date TEXT NOT NULL,
                    updated_date TEXT NOT NULL,
                    typist_id TEXT,
                    correction_notes TEXT,
                    priority TEXT DEFAULT 'routine',
                    claimed_by TEXT,
                    claimed_at TEXT,
                    correction_start_time TEXT,
                    correction_end_time TEXT,
                    qa_status TEXT DEFAULT 'pending',
                    qa_reviewer TEXT,
                    qa_notes TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Typist queue tables initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing queue tables: {e}")
            raise  
  
    def start_cleanup_thread(self):
        """Start background thread to clean up expired claims"""
        def cleanup_expired_claims():
            while True:
                try:
                    self.release_expired_claims()
                    time.sleep(300)  # Check every 5 minutes
                except Exception as e:
                    logger.error(f"❌ Cleanup thread error: {e}")
                    time.sleep(60)  # Wait 1 minute before retry
        
        thread = threading.Thread(target=cleanup_expired_claims, daemon=True)
        thread.start()
        logger.info("✅ Queue cleanup thread started")
    
    def get_pending_reports(self, typist_id: str = None, priority: str = None) -> List[QueueItem]:
        """Get pending reports in the typist queue"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Base query for transcribed sessions ready for typist review
            query = '''
                SELECT ds.session_id, ds.patient_id, ds.user_id as doctor_id, 
                       ds.study_id, ds.priority, ds.created_date, ds.audio_duration,
                       ds.claimed_by, ds.claimed_at, ds.status, ds.language,
                       ds.raw_transcript, ds.corrected_transcript
                FROM dictation_sessions ds
                WHERE ds.status = 'transcribed' 
                   OR (ds.status = 'claimed' AND ds.claimed_by IS NOT NULL)
            '''
            
            params = []
            
            # Filter by priority if specified
            if priority:
                query += ' AND ds.priority = ?'
                params.append(priority)
            
            # Filter by typist if specified (show their claimed reports)
            if typist_id:
                query += ' AND (ds.claimed_by IS NULL OR ds.claimed_by = ?)'
                params.append(typist_id)
            
            # Order by priority and creation date
            query += '''
                ORDER BY 
                    CASE ds.priority 
                        WHEN 'urgent' THEN 1 
                        WHEN 'routine' THEN 2 
                        WHEN 'low' THEN 3 
                        ELSE 4 
                    END,
                    ds.created_date ASC
            '''
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            queue_items = []
            for row in rows:
                # Estimate work time based on audio duration and complexity
                estimated_time = self._estimate_work_time(row[6], row[11], row[12])
                
                queue_item = QueueItem(
                    session_id=row[0],
                    patient_id=row[1],
                    doctor_id=row[2],
                    study_type=self._extract_study_type(row[3]),
                    priority=row[4] or 'routine',
                    created_date=row[5],
                    audio_duration=row[6] or 0.0,
                    estimated_work_time=estimated_time,
                    claimed_by=row[7] or '',
                    claimed_at=row[8] or '',
                    status='claimed' if row[7] else 'pending',
                    language=row[9] or 'en-ZA'
                )
                
                queue_items.append(queue_item)
            
            conn.close()
            return queue_items
            
        except Exception as e:
            logger.error(f"❌ Error getting pending reports: {e}")
            return []
    
    def claim_report(self, session_id: str, typist_id: str) -> Tuple[bool, str]:
        """Claim a report for a specific typist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if report is available for claiming
            cursor.execute('''
                SELECT claimed_by, claimed_at, status 
                FROM dictation_sessions 
                WHERE session_id = ?
            ''', (session_id,))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False, "Report not found"
            
            claimed_by, claimed_at, status = row
            
            # Check if already claimed by someone else
            if claimed_by and claimed_by != typist_id:
                # Check if claim has expired
                if claimed_at:
                    claimed_time = datetime.fromisoformat(claimed_at)
                    if datetime.now() - claimed_time < timedelta(minutes=self.claim_timeout_minutes):
                        conn.close()
                        return False, f"Report already claimed by {claimed_by}"
            
            # Claim the report
            now = datetime.now().isoformat()
            cursor.execute('''
                UPDATE dictation_sessions 
                SET claimed_by = ?, claimed_at = ?, status = 'claimed', 
                    correction_start_time = ?, updated_date = ?
                WHERE session_id = ?
            ''', (typist_id, now, now, now, session_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Report {session_id} claimed by {typist_id}")
            return True, "Report claimed successfully"
            
        except Exception as e:
            logger.error(f"❌ Error claiming report: {e}")
            return False, f"Failed to claim report: {str(e)}"
    
    def release_report(self, session_id: str, typist_id: str = None) -> Tuple[bool, str]:
        """Release a claimed report back to the queue"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verify ownership if typist_id provided
            if typist_id:
                cursor.execute('''
                    SELECT claimed_by FROM dictation_sessions WHERE session_id = ?
                ''', (session_id,))
                row = cursor.fetchone()
                
                if not row:
                    conn.close()
                    return False, "Report not found"
                
                if row[0] != typist_id:
                    conn.close()
                    return False, "Report not claimed by this typist"
            
            # Release the report
            cursor.execute('''
                UPDATE dictation_sessions 
                SET claimed_by = NULL, claimed_at = NULL, status = 'transcribed',
                    correction_start_time = NULL, updated_date = ?
                WHERE session_id = ?
            ''', (datetime.now().isoformat(), session_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Report {session_id} released back to queue")
            return True, "Report released successfully"
            
        except Exception as e:
            logger.error(f"❌ Error releasing report: {e}")
            return False, f"Failed to release report: {str(e)}"  
  
    def release_expired_claims(self):
        """Release claims that have expired"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find expired claims
            expiry_time = (datetime.now() - timedelta(minutes=self.claim_timeout_minutes)).isoformat()
            
            cursor.execute('''
                SELECT session_id, claimed_by FROM dictation_sessions 
                WHERE claimed_by IS NOT NULL 
                  AND claimed_at < ? 
                  AND status = 'claimed'
            ''', (expiry_time,))
            
            expired_claims = cursor.fetchall()
            
            if expired_claims:
                # Release expired claims
                cursor.execute('''
                    UPDATE dictation_sessions 
                    SET claimed_by = NULL, claimed_at = NULL, status = 'transcribed',
                        correction_start_time = NULL, updated_date = ?
                    WHERE claimed_by IS NOT NULL 
                      AND claimed_at < ? 
                      AND status = 'claimed'
                ''', (datetime.now().isoformat(), expiry_time))
                
                conn.commit()
                
                for session_id, typist_id in expired_claims:
                    logger.info(f"⏰ Released expired claim: {session_id} from {typist_id}")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error releasing expired claims: {e}")
    
    def get_queue_statistics(self) -> Dict[str, Any]:
        """Get queue statistics and metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total pending reports
            cursor.execute("SELECT COUNT(*) FROM dictation_sessions WHERE status = 'transcribed'")
            pending_count = cursor.fetchone()[0]
            
            # Reports by priority
            cursor.execute('''
                SELECT priority, COUNT(*) FROM dictation_sessions 
                WHERE status = 'transcribed' 
                GROUP BY priority
            ''')
            priority_counts = dict(cursor.fetchall())
            
            # Currently claimed reports
            cursor.execute("SELECT COUNT(*) FROM dictation_sessions WHERE status = 'claimed'")
            claimed_count = cursor.fetchone()[0]
            
            # Average wait time
            cursor.execute('''
                SELECT AVG(
                    (julianday('now') - julianday(created_date)) * 24 * 60
                ) FROM dictation_sessions 
                WHERE status = 'transcribed'
            ''')
            avg_wait_minutes = cursor.fetchone()[0] or 0
            
            # Completed today
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT COUNT(*) FROM dictation_sessions 
                WHERE status = 'corrected' 
                  AND date(updated_date) = ?
            ''', (today,))
            completed_today = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'pending_reports': pending_count,
                'claimed_reports': claimed_count,
                'priority_breakdown': {
                    'urgent': priority_counts.get('urgent', 0),
                    'routine': priority_counts.get('routine', 0),
                    'low': priority_counts.get('low', 0)
                },
                'average_wait_time_minutes': round(avg_wait_minutes, 1),
                'completed_today': completed_today,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting queue statistics: {e}")
            return {}
    
    def get_typist_statistics(self, typist_id: str) -> TypistStats:
        """Get performance statistics for a specific typist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Reports completed today
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT COUNT(*) FROM dictation_sessions 
                WHERE typist_id = ? AND status = 'corrected' 
                  AND date(updated_date) = ?
            ''', (typist_id, today))
            completed_today = cursor.fetchone()[0]
            
            # Reports completed this week
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute('''
                SELECT COUNT(*) FROM dictation_sessions 
                WHERE typist_id = ? AND status = 'corrected' 
                  AND updated_date >= ?
            ''', (typist_id, week_ago))
            completed_week = cursor.fetchone()[0]
            
            # Average completion time
            cursor.execute('''
                SELECT AVG(
                    (julianday(correction_end_time) - julianday(correction_start_time)) * 24 * 60
                ) FROM dictation_sessions 
                WHERE typist_id = ? AND correction_start_time IS NOT NULL 
                  AND correction_end_time IS NOT NULL
            ''', (typist_id,))
            avg_completion_time = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return TypistStats(
                typist_id=typist_id,
                reports_completed_today=completed_today,
                reports_completed_week=completed_week,
                average_completion_time=round(avg_completion_time, 1),
                accuracy_rate=95.0,  # TODO: Calculate from correction data
                total_work_time=avg_completion_time * completed_week
            )
            
        except Exception as e:
            logger.error(f"❌ Error getting typist statistics: {e}")
            return TypistStats(typist_id=typist_id)
    
    def prioritize_urgent_reports(self):
        """Mark reports as urgent based on criteria"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Mark old reports as urgent (older than 4 hours)
            urgent_threshold = (datetime.now() - timedelta(hours=4)).isoformat()
            
            cursor.execute('''
                UPDATE dictation_sessions 
                SET priority = 'urgent', updated_date = ?
                WHERE status = 'transcribed' 
                  AND priority != 'urgent'
                  AND created_date < ?
            ''', (datetime.now().isoformat(), urgent_threshold))
            
            updated_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if updated_count > 0:
                logger.info(f"⚡ Marked {updated_count} reports as urgent due to age")
            
        except Exception as e:
            logger.error(f"❌ Error prioritizing urgent reports: {e}")
    
    def _estimate_work_time(self, audio_duration: float, raw_transcript: str, 
                           corrected_transcript: str) -> float:
        """Estimate work time based on audio duration and transcript complexity"""
        if not audio_duration:
            return 5.0  # Default 5 minutes
        
        # Base time: 2x audio duration for transcription review
        base_time = audio_duration * 2
        
        # Add complexity factors
        if raw_transcript:
            # More complex if transcript is long
            word_count = len(raw_transcript.split())
            complexity_factor = min(word_count / 100, 2.0)  # Max 2x multiplier
            base_time *= (1 + complexity_factor * 0.5)
        
        # Convert to minutes and round
        return round(base_time / 60, 1)
    
    def _extract_study_type(self, study_id: str) -> str:
        """Extract study type from study ID or description"""
        if not study_id:
            return "Unknown Study"
        
        # Simple extraction - in real system would query PACS
        if "chest" in study_id.lower():
            return "Chest X-Ray"
        elif "ct" in study_id.lower():
            return "CT Scan"
        elif "mri" in study_id.lower():
            return "MRI Scan"
        else:
            return "Medical Study"

# Global instance
typist_queue_manager = TypistQueueManager()