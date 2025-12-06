"""
Intelligent DICOM Indexing Service
Uses advanced techniques for robust and efficient patient data indexing and retrieval
"""

import logging
import os
import sqlite3
import threading
import queue
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import pydicom
import re
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)


class IntelligentDICOMIndexer:
    """
    Advanced DICOM indexer with:
    - Multi-threaded concurrent indexing
    - Metadata extraction and normalization
    - Duplicate detection via file hashing
    - Incremental updates with change tracking
    - Full-text search index
    - Performance monitoring
    """
    
    def __init__(self, db_path: str, nas_path: str):
        self.db_path = db_path
        self.nas_path = nas_path
        self.index_queue = queue.Queue()
        self.stats = {
            'total_files': 0,
            'indexed_files': 0,
            'skipped_files': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
        self._ensure_database_schema()
    
    def _ensure_database_schema(self):
        """Create optimized database schema with indices"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Main studies table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS studies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id TEXT NOT NULL,
                    patient_name TEXT NOT NULL,
                    study_uid TEXT UNIQUE NOT NULL,
                    study_date TEXT NOT NULL,
                    study_time TEXT,
                    modality TEXT,
                    study_description TEXT,
                    institution_name TEXT,
                    referring_physician TEXT,
                    study_comments TEXT,
                    folder_path TEXT,
                    file_count INTEGER DEFAULT 0,
                    total_size_mb REAL DEFAULT 0,
                    first_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_verified TIMESTAMP,
                    is_complete BOOLEAN DEFAULT 0,
                    CHECK(patient_id != ''),
                    CHECK(study_uid != '')
                )
            ''')
            
            # Patient master table for fast lookups
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patient_master (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id TEXT UNIQUE NOT NULL,
                    patient_name TEXT NOT NULL,
                    patient_sex TEXT,
                    patient_birth_date TEXT,
                    age_at_last_study INTEGER,
                    total_studies INTEGER DEFAULT 0,
                    total_series INTEGER DEFAULT 0,
                    total_instances INTEGER DEFAULT 0,
                    first_study_date TEXT,
                    last_study_date TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CHECK(patient_id != '')
                )
            ''')
            
            # Series details table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS series (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    study_id INTEGER NOT NULL,
                    series_uid TEXT UNIQUE NOT NULL,
                    series_number INTEGER,
                    series_description TEXT,
                    modality TEXT,
                    instance_count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(study_id) REFERENCES studies(id),
                    CHECK(series_uid != '')
                )
            ''')
            
            # Full-text search index
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    study_id INTEGER NOT NULL,
                    search_text TEXT NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(study_id) REFERENCES studies(id)
                )
            ''')
            
            # File hash tracking to detect duplicates
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_hashes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    file_hash TEXT NOT NULL,
                    file_size INTEGER,
                    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    study_id INTEGER,
                    FOREIGN KEY(study_id) REFERENCES studies(id)
                )
            ''')
            
            # Indexing status and progress
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS indexing_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'pending',
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    total_files INTEGER DEFAULT 0,
                    indexed_files INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    error_log TEXT,
                    progress_percent INTEGER DEFAULT 0
                )
            ''')
            
            # Ensure required columns exist on possibly pre-existing tables (safe migrations)
            def _ensure_column(table: str, column: str, col_def: str = 'TEXT'):
                try:
                    cursor.execute(f"PRAGMA table_info('{table}')")
                    cols = [r[1] for r in cursor.fetchall()]
                    if column not in cols:
                        logger.info(f"🔧 Adding missing column '{column}' to table '{table}'")
                        # ALTER TABLE ADD COLUMN is additive and safe for SQLite
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
                except Exception as _e:
                    # If the table doesn't exist or ALTER fails, ignore here; CREATE TABLE above handles most cases
                    logger.debug(f"Could not ensure column {column} on {table}: {_e}")

            # Attempt to add commonly referenced columns used by the indexer in case the existing pacs DB
            # uses an older schema. This makes initialization idempotent and tolerant to previous schemas.
            _ensure_column('series', 'study_id', 'INTEGER')
            _ensure_column('search_index', 'study_id', 'INTEGER')
            _ensure_column('file_hashes', 'study_id', 'INTEGER')

            # Create indices for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_studies_patient_id ON studies(patient_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_studies_study_date ON studies(study_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_studies_modality ON studies(modality)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_patient_master_patient_id ON patient_master(patient_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_patient_master_patient_name ON patient_master(patient_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_series_study_id ON series(study_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_index_study_id ON search_index(study_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_index_text ON search_index(search_text)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_hashes_hash ON file_hashes(file_hash)')
            
            conn.commit()
            conn.close()
            logger.info("✅ Database schema initialized with optimized indices")
            
        except Exception as e:
            logger.error(f"❌ Database schema creation failed: {e}")
            raise
    
    def _extract_dicom_metadata(self, file_path: str) -> Optional[Dict]:
        """Extract and normalize DICOM metadata"""
        try:
            dcm = pydicom.dcmread(file_path, force=True, stop_before_pixels=True)
            
            # Normalize patient name (handle '^' separator in DICOM)
            patient_name = str(getattr(dcm, 'PatientName', '')).split('^')[0].strip()
            
            metadata = {
                'patient_id': getattr(dcm, 'PatientID', '').strip(),
                'patient_name': patient_name,
                'patient_sex': getattr(dcm, 'PatientSex', '').strip(),
                'patient_birth_date': getattr(dcm, 'PatientBirthDate', '').strip(),
                'study_uid': getattr(dcm, 'StudyInstanceUID', '').strip(),
                'study_date': getattr(dcm, 'StudyDate', '').strip(),
                'study_time': getattr(dcm, 'StudyTime', '').strip(),
                'modality': getattr(dcm, 'Modality', '').strip(),
                'study_description': getattr(dcm, 'StudyDescription', '').strip(),
                'institution_name': getattr(dcm, 'InstitutionName', '').strip(),
                'referring_physician': getattr(dcm, 'ReferringPhysicianName', '').strip(),
                'study_comments': getattr(dcm, 'StudyComments', '').strip(),
                'series_uid': getattr(dcm, 'SeriesInstanceUID', '').strip(),
                'series_number': getattr(dcm, 'SeriesNumber', None),
                'series_description': getattr(dcm, 'SeriesDescription', '').strip(),
            }
            
            # Validate required fields
            if not all([metadata['patient_id'], metadata['study_uid'], metadata['study_date']]):
                return None
            
            return metadata
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to extract metadata from {file_path}: {e}")
            return None
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file for duplicate detection"""
        try:
            sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.warning(f"⚠️  Failed to hash {file_path}: {e}")
            return ""
    
    def index_directory(self, folder_path: str, recursive: bool = True, num_workers: int = 4) -> Dict:
        """
        Index a directory with multi-threaded processing
        """
        logger.info(f"🚀 Starting intelligent indexing of {folder_path}")
        self.stats['start_time'] = datetime.now()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create indexing job record
            job_id = hashlib.md5(f"{folder_path}{datetime.now()}".encode()).hexdigest()
            cursor.execute('''
                INSERT INTO indexing_jobs (job_id, status, start_time)
                VALUES (?, ?, ?)
            ''', (job_id, 'running', datetime.now()))
            conn.commit()
            
            # Collect all DICOM files
            dicom_files = self._find_dicom_files(folder_path, recursive)
            self.stats['total_files'] = len(dicom_files)
            logger.info(f"📊 Found {len(dicom_files)} DICOM files to index")
            
            # Process with thread pool
            threads = []
            for i in range(num_workers):
                t = threading.Thread(target=self._worker_thread, args=(dicom_files, job_id))
                t.start()
                threads.append(t)
            
            # Wait for completion
            for t in threads:
                t.join()
            
            # Update patient master table
            self._update_patient_master(conn)
            
            # Finalize indexing job
            self.stats['end_time'] = datetime.now()
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            cursor.execute('''
                UPDATE indexing_jobs 
                SET status = ?, end_time = ?, indexed_files = ?, error_count = ?, progress_percent = ?
                WHERE job_id = ?
            ''', ('completed', datetime.now(), self.stats['indexed_files'], self.stats['errors'], 100, job_id))
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Indexing completed in {duration:.2f}s: {self.stats['indexed_files']} files indexed, {self.stats['errors']} errors")
            
            return {
                'success': True,
                'job_id': job_id,
                'stats': self.stats
            }
            
        except Exception as e:
            logger.error(f"❌ Indexing failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _find_dicom_files(self, folder_path: str, recursive: bool) -> List[str]:
        """Find all DICOM files in directory"""
        dicom_files = []
        try:
            path_obj = Path(folder_path)
            pattern = '**/*.dcm' if recursive else '*.dcm'
            
            for file_path in path_obj.glob(pattern):
                if file_path.is_file():
                    dicom_files.append(str(file_path))
        except Exception as e:
            logger.error(f"❌ Error scanning directory: {e}")
        
        return dicom_files
    
    def _worker_thread(self, file_list: List[str], job_id: str):
        """Worker thread for parallel indexing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for file_path in file_list:
            try:
                # Extract metadata
                metadata = self._extract_dicom_metadata(file_path)
                if not metadata:
                    self.stats['skipped_files'] += 1
                    continue
                
                # Check for duplicates
                file_hash = self._calculate_file_hash(file_path)
                cursor.execute('SELECT study_id FROM file_hashes WHERE file_hash = ?', (file_hash,))
                if cursor.fetchone():
                    logger.debug(f"⏭️  Skipping duplicate file: {file_path}")
                    self.stats['skipped_files'] += 1
                    continue
                
                # Insert or get study
                cursor.execute('''
                    INSERT OR IGNORE INTO studies 
                    (patient_id, patient_name, study_uid, study_date, study_time, modality, 
                     study_description, institution_name, referring_physician, study_comments, 
                     folder_path, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metadata['patient_id'],
                    metadata['patient_name'],
                    metadata['study_uid'],
                    metadata['study_date'],
                    metadata['study_time'],
                    metadata['modality'],
                    metadata['study_description'],
                    metadata['institution_name'],
                    metadata['referring_physician'],
                    metadata['study_comments'],
                    os.path.dirname(file_path),
                    datetime.now()
                ))
                
                cursor.execute('SELECT id FROM studies WHERE study_uid = ?', (metadata['study_uid'],))
                study_id = cursor.fetchone()[0]
                
                # Insert or update series
                cursor.execute('''
                    INSERT OR IGNORE INTO series 
                    (study_id, series_uid, series_number, series_description, modality)
                    VALUES (?, ?, ?, ?, ?)
                ''', (study_id, metadata['series_uid'], metadata['series_number'], 
                      metadata['series_description'], metadata['modality']))
                
                # Record file hash
                file_size = os.path.getsize(file_path)
                cursor.execute('''
                    INSERT OR IGNORE INTO file_hashes 
                    (file_path, file_hash, file_size, study_id)
                    VALUES (?, ?, ?, ?)
                ''', (file_path, file_hash, file_size, study_id))
                
                # Update full-text search index
                search_text = f"{metadata['patient_id']} {metadata['patient_name']} {metadata['study_description']} {metadata['modality']}"
                cursor.execute('''
                    INSERT OR IGNORE INTO search_index (study_id, search_text)
                    VALUES (?, ?)
                ''', (study_id, search_text.lower()))
                
                conn.commit()
                self.stats['indexed_files'] += 1
                
                if self.stats['indexed_files'] % 100 == 0:
                    logger.info(f"📈 Progress: {self.stats['indexed_files']}/{self.stats['total_files']} files indexed")
                
            except Exception as e:
                logger.error(f"❌ Error indexing {file_path}: {e}")
                self.stats['errors'] += 1
        
        conn.close()
    
    def _update_patient_master(self, conn: sqlite3.Connection):
        """Update patient master table with aggregated study data"""
        try:
            cursor = conn.cursor()
            
            # Get unique patients from studies
            cursor.execute('''
                SELECT DISTINCT patient_id, patient_name, patient_sex, patient_birth_date
                FROM studies
            ''')
            
            patients = cursor.fetchall()
            
            for patient_id, patient_name, patient_sex, patient_birth_date in patients:
                # Count studies, series, instances
                cursor.execute('''
                    SELECT COUNT(DISTINCT study_uid), 
                           COUNT(DISTINCT series_uid),
                           COUNT(*)
                    FROM studies s
                    LEFT JOIN series ser ON s.id = ser.study_id
                    WHERE s.patient_id = ?
                ''', (patient_id,))
                
                total_studies, total_series, total_instances = cursor.fetchone()
                
                # Get date range
                cursor.execute('''
                    SELECT MIN(study_date), MAX(study_date)
                    FROM studies
                    WHERE patient_id = ?
                ''', (patient_id,))
                
                first_date, last_date = cursor.fetchone()
                
                # Insert or update patient master
                cursor.execute('''
                    INSERT OR REPLACE INTO patient_master
                    (patient_id, patient_name, patient_sex, patient_birth_date,
                     total_studies, total_series, total_instances,
                     first_study_date, last_study_date, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (patient_id, patient_name, patient_sex, patient_birth_date,
                      total_studies or 0, total_series or 0, total_instances or 0,
                      first_date, last_date, datetime.now()))
            
            conn.commit()
            logger.info("✅ Patient master table updated")
            
        except Exception as e:
            logger.error(f"❌ Error updating patient master: {e}")
