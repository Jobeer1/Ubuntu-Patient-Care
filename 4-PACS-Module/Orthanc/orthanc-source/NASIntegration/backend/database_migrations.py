#!/usr/bin/env python3
"""
🇿🇦 SA Medical Reporting - Database Migrations

Handles database schema updates for the typist workflow system.
Extends existing reporting database with queue management and learning loop tables.
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Tuple

logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Handles database migrations for typist workflow"""
    
    def __init__(self, db_path: str = "reporting.db"):
        self.db_path = db_path
    
    def run_all_migrations(self) -> bool:
        """Run all pending migrations"""
        try:
            migrations = [
                self._migration_001_add_queue_fields,
                self._migration_002_create_correction_logs,
                self._migration_003_create_sa_vocabulary,
                self._migration_004_create_performance_metrics,
                self._migration_005_add_indexes
            ]
            
            for migration in migrations:
                if not migration():
                    return False
            
            logger.info("✅ All database migrations completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False
    
    def _migration_001_add_queue_fields(self) -> bool:
        """Add queue management fields to dictation_sessions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if columns already exist
            cursor.execute("PRAGMA table_info(dictation_sessions)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Add new columns if they don't exist
            new_columns = [
                ("priority", "TEXT DEFAULT 'routine'"),
                ("claimed_by", "TEXT"),
                ("claimed_at", "TEXT"),
                ("correction_start_time", "TEXT"),
                ("correction_end_time", "TEXT"),
                ("qa_status", "TEXT DEFAULT 'pending'"),
                ("qa_reviewer", "TEXT"),
                ("qa_notes", "TEXT")
            ]
            
            for column_name, column_def in new_columns:
                if column_name not in columns:
                    cursor.execute(f"ALTER TABLE dictation_sessions ADD COLUMN {column_name} {column_def}")
                    logger.info(f"✅ Added column {column_name} to dictation_sessions")
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration 001 failed: {e}")
            return False
    
    def _migration_002_create_correction_logs(self) -> bool:
        """Create detailed correction logging table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS correction_logs (
                    log_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    original_text TEXT NOT NULL,
                    corrected_text TEXT NOT NULL,
                    correction_type TEXT,
                    confidence_score REAL,
                    typist_id TEXT NOT NULL,
                    timestamp TEXT DEFAULT (datetime('now')),
                    context TEXT,
                    FOREIGN KEY (session_id) REFERENCES dictation_sessions(session_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Created correction_logs table")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration 002 failed: {e}")
            return False
    
    def _migration_003_create_sa_vocabulary(self) -> bool:
        """Create SA medical vocabulary table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sa_medical_vocabulary (
                    term_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term TEXT NOT NULL,
                    language TEXT NOT NULL,
                    category TEXT,
                    frequency INTEGER DEFAULT 1,
                    last_used TEXT DEFAULT (datetime('now')),
                    UNIQUE(term, language)
                )
            ''')
            
            # Insert initial SA medical terms
            initial_terms = [
                ("tuberculosis", "en", "condition"),
                ("TB", "en", "condition"),
                ("pneumonia", "en", "condition"),
                ("fracture", "en", "condition"),
                ("hypertension", "en", "condition"),
                ("diabetes", "en", "condition"),
                ("HIV", "en", "condition"),
                ("AIDS", "en", "condition"),
                ("chest", "en", "anatomy"),
                ("abdomen", "en", "anatomy"),
                ("pelvis", "en", "anatomy"),
                ("spine", "en", "anatomy"),
                ("tuberkulose", "af", "condition"),
                ("longontsteking", "af", "condition"),
                ("breuk", "af", "condition"),
                ("hipertensie", "af", "condition"),
                ("bors", "af", "anatomy"),
                ("buik", "af", "anatomy"),
                ("isifo sefuba", "zu", "condition"),
                ("inyumoniya", "zu", "condition"),
                ("isifuba", "zu", "anatomy"),
                ("isisu", "zu", "anatomy")
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO sa_medical_vocabulary (term, language, category)
                VALUES (?, ?, ?)
            ''', initial_terms)
            
            conn.commit()
            conn.close()
            logger.info("✅ Created sa_medical_vocabulary table with initial terms")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration 003 failed: {e}")
            return False    

    def _migration_004_create_performance_metrics(self) -> bool:
        """Create STT performance metrics table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stt_performance_metrics (
                    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_version TEXT,
                    accuracy_rate REAL,
                    error_types TEXT,
                    measurement_date TEXT DEFAULT (datetime('now')),
                    sample_size INTEGER,
                    language TEXT DEFAULT 'en-ZA'
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Created stt_performance_metrics table")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration 004 failed: {e}")
            return False
    
    def _migration_005_add_indexes(self) -> bool:
        """Add performance indexes for queue operations"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_session_priority ON dictation_sessions(priority)",
                "CREATE INDEX IF NOT EXISTS idx_session_claimed ON dictation_sessions(claimed_by, claimed_at)",
                "CREATE INDEX IF NOT EXISTS idx_session_qa_status ON dictation_sessions(qa_status)",
                "CREATE INDEX IF NOT EXISTS idx_correction_session ON correction_logs(session_id)",
                "CREATE INDEX IF NOT EXISTS idx_correction_typist ON correction_logs(typist_id)",
                "CREATE INDEX IF NOT EXISTS idx_vocabulary_term ON sa_medical_vocabulary(term, language)",
                "CREATE INDEX IF NOT EXISTS idx_vocabulary_category ON sa_medical_vocabulary(category, language)",
                "CREATE INDEX IF NOT EXISTS idx_metrics_date ON stt_performance_metrics(measurement_date)"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            conn.commit()
            conn.close()
            logger.info("✅ Created performance indexes")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration 005 failed: {e}")
            return False
    
    def check_migration_status(self) -> dict:
        """Check which migrations have been applied"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            status = {}
            
            # Check if queue fields exist
            cursor.execute("PRAGMA table_info(dictation_sessions)")
            columns = [row[1] for row in cursor.fetchall()]
            status['queue_fields'] = 'priority' in columns
            
            # Check if correction_logs table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='correction_logs'")
            status['correction_logs'] = cursor.fetchone() is not None
            
            # Check if sa_medical_vocabulary table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sa_medical_vocabulary'")
            status['sa_vocabulary'] = cursor.fetchone() is not None
            
            # Check if stt_performance_metrics table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stt_performance_metrics'")
            status['performance_metrics'] = cursor.fetchone() is not None
            
            conn.close()
            return status
            
        except Exception as e:
            logger.error(f"❌ Error checking migration status: {e}")
            return {}

# Global migrator instance
db_migrator = DatabaseMigrator()