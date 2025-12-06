#!/usr/bin/env python3
"""
Enhanced NAS DICOM Indexer for Ubuntu Patient Care
Indexes 11TB of DICOM data from Z: drive into searchable database
Supports 9300+ patients without physical file import
"""

import os
import sys
import json
import sqlite3
import logging
import threading
import time
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
try:
    from backend.metadata_db import get_metadata_db_path
except Exception:
    try:
        from metadata_db import get_metadata_db_path
    except Exception:
        def get_metadata_db_path():
            # Fallback to safe canonical metadata DB inside backend/orthanc-index
            base = os.path.dirname(__file__)
            fallback = os.path.abspath(os.path.join(base, 'backend', 'orthanc-index', 'pacs_metadata.db'))
            return fallback
import hashlib

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import pydicom
    print("✅ PyDICOM loaded successfully")
except ImportError:
    print("❌ Missing pydicom. Install with: pip install pydicom")
    sys.exit(1)

class NASPatientIndexer:
    """
    High-performance DICOM indexer for large NAS volumes
    Creates searchable patient database without physical file import
    """
    
    # Global lock to prevent multiple indexing processes
    _global_indexing_lock = threading.Lock()
    
    def __init__(self, nas_path="Z:\\", db_path: str = None):
        self.nas_path = Path(nas_path)
        # Default to canonical metadata DB path (orthanc-index preferred)
        self.db_path = db_path or get_metadata_db_path()
        self.stats = {
            'folders_scanned': 0,
            'dicom_files_found': 0,
            'patients_indexed': 0,
            'studies_indexed': 0,
            'series_indexed': 0,
            'errors': 0,
            'start_time': None,
            'current_folder': '',
            'processing_rate': 0
        }
        self.running = False
        self.status_lock = threading.Lock()
        
    def init_database(self):
        """Initialize SQLite database for patient index"""
        logger.info("Initializing patient index database...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ❌ DISABLED: Create detailed tables (patients, studies, series)
        # These tables create complex relationships and can lead to database bloat
        # We use lightweight patient_studies table instead for all metadata
        
        # cursor.execute('''
        #     CREATE TABLE IF NOT EXISTS patients (
        #         patient_id TEXT PRIMARY KEY,
        #         patient_name TEXT,
        #         patient_birth_date TEXT,
        #         patient_sex TEXT,
        #         patient_age TEXT,
        #         first_study_date TEXT,
        #         last_study_date TEXT,
        #         total_studies INTEGER DEFAULT 0,
        #         total_series INTEGER DEFAULT 0,
        #         total_instances INTEGER DEFAULT 0,
        #         folder_path TEXT,
        #         last_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        #     )
        # ''')
        
        # cursor.execute('''
        #     CREATE TABLE IF NOT EXISTS studies (
        #         study_instance_uid TEXT PRIMARY KEY,
        #         patient_id TEXT,
        #         study_id TEXT,
        #         study_date TEXT,
        #         study_time TEXT,
        #         study_description TEXT,
        #         modality TEXT,
        #         series_count INTEGER DEFAULT 0,
        #         instance_count INTEGER DEFAULT 0,
        #         folder_path TEXT,
        #         accession_number TEXT,
        #         referring_physician TEXT,
        #         FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
        #     )
        # ''')
        
        # cursor.execute('''
        #     CREATE TABLE IF NOT EXISTS series (
        #         series_instance_uid TEXT PRIMARY KEY,
        #         study_instance_uid TEXT,
        #         patient_id TEXT,
        #         series_number TEXT,
        #         series_description TEXT,
        #         series_time TEXT,
        #         modality TEXT,
        #         instance_count INTEGER DEFAULT 0,
        #         folder_path TEXT,
        #         FOREIGN KEY (study_instance_uid) REFERENCES studies (study_instance_uid),
        #         FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
        #     )
        # ''')
        
        print("🚫 Detailed tables (patients/studies/series) creation DISABLED - using lightweight patient_studies instead")
        
        # ❌ DISABLED: Create file paths table for quick access
        # This table causes the database to grow to 1GB+ with millions of records
        # We only need patient/study/series metadata, not individual DICOM files
        # cursor.execute('''
        #     CREATE TABLE IF NOT EXISTS dicom_files (
        #         file_id INTEGER PRIMARY KEY AUTOINCREMENT,
        #         file_path TEXT UNIQUE,
        #         patient_id TEXT,
        #         study_instance_uid TEXT,
        #         series_instance_uid TEXT,
        #         sop_instance_uid TEXT,
        #         file_size INTEGER,
        #         file_hash TEXT,
        #         last_modified TIMESTAMP
        #     )
        # ''')
        print("🚫 DICOM files table creation DISABLED to prevent database bloat")
        
        # Create indexing status table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS indexing_status (
                id INTEGER PRIMARY KEY,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'running',
                folders_scanned INTEGER DEFAULT 0,
                files_processed INTEGER DEFAULT 0,
                patients_found INTEGER DEFAULT 0,
                errors INTEGER DEFAULT 0,
                current_folder TEXT
            )
        ''')
        
        # Create lightweight patient_studies table (replaces separate patients/studies/series tables)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patient_studies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                patient_name TEXT,
                patient_birth_date TEXT,
                patient_sex TEXT,
                study_date TEXT,
                study_description TEXT,
                modality TEXT,
                folder_path TEXT NOT NULL,
                dicom_file_count INTEGER DEFAULT 0,
                folder_size_mb REAL DEFAULT 0,
                last_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(patient_id, folder_path)
            )
        ''')
        print("✅ Lightweight patient_studies table created - stores only essential metadata")
        
        # ❌ DISABLED: Create indexes for disabled tables 
        # cursor.execute('CREATE INDEX IF NOT EXISTS idx_patients_name ON patients (patient_name)')
        # cursor.execute('CREATE INDEX IF NOT EXISTS idx_patients_birth_date ON patients (patient_birth_date)')
        # cursor.execute('CREATE INDEX IF NOT EXISTS idx_patients_first_study ON patients (first_study_date)')
        # cursor.execute('CREATE INDEX IF NOT EXISTS idx_studies_patient ON studies (patient_id)')
        # cursor.execute('CREATE INDEX IF NOT EXISTS idx_studies_date ON studies (study_date)')
        # cursor.execute('CREATE INDEX IF NOT EXISTS idx_studies_modality ON studies (modality)')
        # cursor.execute('CREATE INDEX IF NOT EXISTS idx_series_study ON series (study_instance_uid)')
        # cursor.execute('CREATE INDEX IF NOT EXISTS idx_series_patient ON series (patient_id)')
        # cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_patient ON dicom_files (patient_id)')
        # cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_study ON dicom_files (study_instance_uid)')
        # cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_series ON dicom_files (series_instance_uid)')
        
        # Create lightweight indexes for patient_studies table
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patient_studies_patient_id ON patient_studies (patient_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patient_studies_study_date ON patient_studies (study_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patient_studies_modality ON patient_studies (modality)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patient_studies_name ON patient_studies (patient_name)')
        print("✅ Lightweight patient_studies indexes created")
        
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized successfully")
    
    def scan_patient_folders(self) -> List[Path]:
        """Scan NAS for patient folders matching the pattern - PRIORITIZE NEWEST FIRST"""
        logger.info(f"🔍 Scanning NAS path: {self.nas_path}")
        
        if not self.nas_path.exists():
            logger.error(f"❌ NAS path does not exist: {self.nas_path}")
            return []
        
        patient_folders = []
        try:
            # Look for folders matching patient ID patterns
            for item in self.nas_path.iterdir():
                if item.is_dir():
                    folder_name = item.name
                    # Match patterns like: 639380-20250922-*, N0044905, etc.
                    if (('-' in folder_name and len(folder_name) >= 10) or 
                        (folder_name.startswith('N') and len(folder_name) >= 7) or
                        folder_name.isdigit()):
                        patient_folders.append(item)
                        self.stats['folders_scanned'] += 1
                        
                        if self.stats['folders_scanned'] % 100 == 0:
                            logger.info(f"Found {len(patient_folders)} patient folders, scanned {self.stats['folders_scanned']} total folders")
        
        except Exception as e:
            logger.error(f"❌ Error scanning NAS: {e}")
            self.stats['errors'] += 1
        
        # ⭐ CRITICAL FIX: Sort folders by modification time - NEWEST FIRST for clinical priority
        logger.info("🔄 Sorting patient folders by date - NEWEST PATIENTS FIRST for clinical priority...")
        try:
            patient_folders.sort(key=lambda folder: folder.stat().st_mtime, reverse=True)
            if patient_folders:
                newest = time.strftime('%Y-%m-%d %H:%M', time.localtime(patient_folders[0].stat().st_mtime))
                oldest = time.strftime('%Y-%m-%d %H:%M', time.localtime(patient_folders[-1].stat().st_mtime))
                logger.info(f"📅 Date range: NEWEST {newest} → oldest {oldest}")
                logger.info(f"⚡ INDEXING WILL START WITH THE MOST RECENT PATIENTS FIRST!")
        except Exception as e:
            logger.warning(f"⚠️ Could not sort by date, using original order: {e}")
        
        logger.info(f"✅ Found {len(patient_folders)} patient folders to index (NEWEST FIRST)")
        return patient_folders
    
    def extract_dicom_metadata(self, dicom_path: Path) -> Optional[Dict]:
        """Extract metadata from single DICOM file"""
        try:
            # Read DICOM header only (no pixel data)
            ds = pydicom.dcmread(str(dicom_path), stop_before_pixels=True)
            
            # Helper function to convert PersonName to string
            def convert_person_name(value):
                if hasattr(value, 'family_name') and hasattr(value, 'given_name'):
                    # It's a PersonName object
                    parts = []
                    if value.family_name:
                        parts.append(str(value.family_name))
                    if value.given_name:
                        parts.append(str(value.given_name))
                    return ' '.join(parts) if parts else str(value)
                else:
                    return str(value) if value else ''
            
            # Extract key metadata with proper PersonName handling
            metadata = {
                'patient_id': str(getattr(ds, 'PatientID', '')),
                'patient_name': convert_person_name(getattr(ds, 'PatientName', '')),
                'patient_birth_date': str(getattr(ds, 'PatientBirthDate', '')),
                'patient_sex': str(getattr(ds, 'PatientSex', '')),
                'patient_age': str(getattr(ds, 'PatientAge', '')),
                'study_instance_uid': str(getattr(ds, 'StudyInstanceUID', '')),
                'study_id': str(getattr(ds, 'StudyID', '')),
                'study_date': str(getattr(ds, 'StudyDate', '')),
                'study_time': str(getattr(ds, 'StudyTime', '')),
                'study_description': str(getattr(ds, 'StudyDescription', '')),
                'modality': str(getattr(ds, 'Modality', '')),
                'series_instance_uid': str(getattr(ds, 'SeriesInstanceUID', '')),
                'series_number': str(getattr(ds, 'SeriesNumber', '')),
                'series_description': str(getattr(ds, 'SeriesDescription', '')),
                'series_time': str(getattr(ds, 'SeriesTime', '')),
                'sop_instance_uid': str(getattr(ds, 'SOPInstanceUID', '')),
                'accession_number': str(getattr(ds, 'AccessionNumber', '')),
                'referring_physician': convert_person_name(getattr(ds, 'ReferringPhysicianName', '')),
                'file_path': str(dicom_path),
                'file_size': dicom_path.stat().st_size,
                'file_hash': self.calculate_file_hash(dicom_path)
            }
            
            return metadata
            
        except Exception as e:
            logger.debug(f"Error reading DICOM {dicom_path}: {e}")
            self.stats['errors'] += 1
            return None
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file for duplicate detection"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def index_patient_folder(self, patient_folder: Path) -> Dict:
        """Index all DICOM files in a patient folder"""
        folder_stats = {
            'patient_folder': str(patient_folder),
            'dicom_files': 0,
            'patients': set(),
            'studies': set(),
            'series': set(),
            'errors': 0
        }
        
        try:
            # Use WAL mode for better concurrency and timeout for locks
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute('PRAGMA journal_mode=WAL;')
                conn.execute('PRAGMA synchronous=NORMAL;')
                conn.execute('PRAGMA cache_size=10000;')
                conn.execute('PRAGMA temp_store=memory;')
                cursor = conn.cursor()
                
                # Check if this patient folder is already fully indexed
                cursor.execute('SELECT COUNT(*) FROM patient_studies WHERE folder_path LIKE ?', (f'%{patient_folder.name}%',))
                existing_patients = cursor.fetchone()[0]
                
                if existing_patients > 0:
                    logger.debug(f"⏭️ {patient_folder.name}: Already indexed ({existing_patients} studies) - skipping")
                    return folder_stats
        
                # Find all DICOM files in folder
                dicom_files = []
                for root, dirs, files in os.walk(patient_folder):
                    for file in files:
                        file_path = Path(root) / file
                        # Check if it's likely a DICOM file
                        if (file.lower().endswith(('.dcm', '.dicom', '.ima')) or 
                            '.' not in file or 
                            file.isdigit()):
                            dicom_files.append(file_path)

                logger.info(f"📁 {patient_folder.name}: Found {len(dicom_files)} potential DICOM files - PROCESSING FOR PACS")
                
                # Process ALL DICOM files for proper PACS functionality
                # Each file needs to be indexed for image sharing and fast retrieval
                batch_size = 100  # Larger batches for better performance
                processed_count = 0
                
                for i, dicom_file in enumerate(dicom_files):
                    try:
                        metadata = self.extract_dicom_metadata(dicom_file)
                        if metadata:
                            self.store_metadata(cursor, metadata)
                            folder_stats['dicom_files'] += 1
                            folder_stats['patients'].add(metadata['patient_id'])
                            folder_stats['studies'].add(metadata['study_instance_uid'])
                            folder_stats['series'].add(metadata['series_instance_uid'])
                            
                            self.stats['dicom_files_found'] += 1
                            processed_count += 1
                            
                            # Commit in batches for performance
                            if (i + 1) % batch_size == 0:
                                conn.commit()
                                # Show progress only for large folders to reduce log spam
                                if len(dicom_files) > 500:
                                    progress_percent = int(((i + 1) / len(dicom_files)) * 100)
                                    logger.info(f"   📊 {patient_folder.name}: {processed_count}/{len(dicom_files)} files indexed ({progress_percent}%)")
                                
                                # Update progress file during processing (every 100 files)
                                try:
                                    import json
                                    progress_data = {
                                        'current_folder': patient_folder.name,
                                        'files_processed': processed_count,
                                        'total_files': len(dicom_files),
                                        'current_patient': patient_folder.name,
                                        'phase': 'processing_files',
                                        'timestamp': time.time(),
                                        'progress_percent': progress_percent if len(dicom_files) > 500 else int((processed_count / len(dicom_files)) * 100)
                                    }
                                    
                                    with open('indexing_progress.json', 'w') as f:
                                        json.dump(progress_data, f)
                                    logger.debug(f"📊 Live progress: {processed_count}/{len(dicom_files)} files in {patient_folder.name}")
                                except Exception as e:
                                    logger.error(f"❌ Live progress update failed: {e}")
                        else:
                            folder_stats['errors'] += 1
                    except Exception as file_error:
                        logger.debug(f"❌ Error processing {dicom_file}: {file_error}")
                        folder_stats['errors'] += 1
                
                # Final commit for remaining files
                conn.commit()
                
                # Summary for this patient folder
                unique_patients = len(folder_stats['patients'])
                unique_studies = len(folder_stats['studies']) 
                logger.info(f"✅ {patient_folder.name}: Indexed {processed_count} files, {unique_patients} patients, {unique_studies} studies")
                
                # Update progress file after each patient folder completion
                try:
                    import json
                    progress_data = {
                        'current_folder': patient_folder.name,
                        'files_processed': processed_count,
                        'total_files': len(dicom_files),
                        'current_patient': patient_folder.name,
                        'phase': 'processing_files',
                        'timestamp': time.time()
                    }
                    
                    with open('indexing_progress.json', 'w') as f:
                        json.dump(progress_data, f)
                    logger.info(f"📝 Updated progress: {patient_folder.name} completed ({processed_count} files)")
                except Exception as e:
                    logger.error(f"❌ Progress file update failed: {e}")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Error indexing {patient_folder}: {e}")
            folder_stats['errors'] += 1
            self.stats['errors'] += 1
        
        # Update stats
        self.stats['patients_indexed'] += len(folder_stats['patients'])
        self.stats['studies_indexed'] += len(folder_stats['studies'])
        self.stats['series_indexed'] += len(folder_stats['series'])
        
        return folder_stats
    
    def store_metadata(self, cursor: sqlite3.Cursor, metadata: Dict):
        """Store DICOM metadata in database"""
        try:
            # Insert/update patient
            # ❌ DISABLED: Insert into detailed tables (prevents database bloat)
            # We use lightweight patient_studies table instead of separate patients/studies/series tables
            
            # cursor.execute('''
            #     INSERT OR REPLACE INTO patients 
            #     (patient_id, patient_name, patient_birth_date, patient_sex, patient_age, 
            #      first_study_date, folder_path)
            #     VALUES (?, ?, ?, ?, ?, ?, ?)
            # ''', (
            #     metadata['patient_id'],
            #     metadata['patient_name'],
            #     metadata['patient_birth_date'],
            #     metadata['patient_sex'],
            #     metadata['patient_age'],
            #     metadata['study_date'],
            #     os.path.dirname(metadata['file_path'])
            # ))
            
            # cursor.execute('''
            #     INSERT OR REPLACE INTO studies
            #     (study_instance_uid, patient_id, study_id, study_date, study_time,
            #      study_description, modality, folder_path, accession_number, referring_physician)
            #     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            # ''', (
            #     metadata['study_instance_uid'],
            #     metadata['patient_id'],
            #     metadata['study_id'],
            #     metadata['study_date'],
            #     metadata['study_time'],
            #     metadata['study_description'],
            #     metadata['modality'],
            #     os.path.dirname(metadata['file_path']),
            #     metadata['accession_number'],
            #     metadata['referring_physician']
            # ))
            
            # cursor.execute('''
            #     INSERT OR REPLACE INTO series
            #     (series_instance_uid, study_instance_uid, patient_id, series_number,
            #      series_description, series_time, modality, folder_path)
            #     VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            # ''', (
            #     metadata['series_instance_uid'],
            #     metadata['study_instance_uid'],
            #     metadata['patient_id'],
            #     metadata['series_number'],
            #     metadata['series_description'],
            #     metadata['series_time'],
            #     metadata['modality'],
            #     os.path.dirname(metadata['file_path'])
            # ))
            
            # ✅ LIGHTWEIGHT APPROACH: Insert into patient_studies table for PACS functionality
            # Each DICOM file gets indexed for proper image sharing and retrieval
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO patient_studies 
                    (patient_id, patient_name, patient_birth_date, patient_sex, 
                     study_date, study_description, modality, folder_path, 
                     dicom_file_count, folder_size_mb, last_indexed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (
                    metadata['patient_id'],
                    metadata['patient_name'],
                    metadata['patient_birth_date'],
                    metadata['patient_sex'],
                    metadata['study_date'],
                    metadata['study_description'],
                    metadata['modality'],
                    os.path.dirname(metadata['file_path']),
                    1,  # Each record represents one DICOM file
                    os.path.getsize(metadata['file_path']) / (1024 * 1024) if os.path.exists(metadata['file_path']) else 0
                ))
                logger.debug(f"✅ Stored: {metadata['patient_id']} - {metadata['study_date']}")
            except Exception as db_error:
                logger.error(f"❌ DATABASE INSERT FAILED: {db_error}")
                logger.error(f"   Patient: {metadata.get('patient_id', 'UNKNOWN')}")
                logger.error(f"   Study: {metadata.get('study_date', 'UNKNOWN')}")
                raise
            
        except Exception as e:
            logger.error(f"❌ Error storing DICOM metadata: {e}")
            raise
    
    def store_patient_metadata(self, cursor, metadata):
        """Store ONE record per patient folder - CRITICAL FIX for database bloat"""
        try:
            # Insert into patient_studies table - ONE record per patient folder
            cursor.execute('''
                INSERT OR REPLACE INTO patient_studies 
                (patient_id, patient_name, patient_birth_date, patient_sex, 
                 study_date, study_description, modality, folder_path, 
                 dicom_file_count, folder_size_mb, last_indexed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (
                metadata['patient_id'],
                metadata['patient_name'],
                metadata['patient_birth_date'],
                metadata['patient_sex'],
                metadata['study_date'],
                metadata['study_description'],
                metadata['modality'],
                metadata['folder_path'],
                metadata['dicom_file_count'],
                metadata['folder_size_mb']
            ))
            
        except Exception as e:
            logger.error(f"❌ Error storing patient metadata: {e}")
            raise
            # We only index patient/study/series metadata, not individual DICOM files
            # cursor.execute('''
            #     INSERT OR REPLACE INTO dicom_files
            #     (file_path, patient_id, study_instance_uid, series_instance_uid,
            #      sop_instance_uid, file_size, file_hash, last_modified)
            #     VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            # ''', (
            #     metadata['file_path'],
            #     metadata['patient_id'],
            #     metadata['study_instance_uid'],
            #     metadata['series_instance_uid'],
            #     metadata['sop_instance_uid'],
            #     metadata['file_size'],
            #     metadata['file_hash']
            # ))
            
            # Instead of storing individual files, just count them
            pass  # Skip individual file storage
            
        except Exception as e:
            logger.error(f"❌ Error storing metadata: {e}")
            raise
    
    def run_full_index(self, max_workers=1):  # Single-threaded to avoid database locks
        """Run complete indexing of NAS"""
        with self._global_indexing_lock:
            logger.info("🚀 Starting full NAS indexing...")
            self.running = True
            self.stats['start_time'] = time.time()
            
            # Initialize database
            self.init_database()
            
            # Get patient folders
            patient_folders = self.scan_patient_folders()
            
            if not patient_folders:
                logger.warning("⚠️ No patient folders found to index")
                return
            
            # Record indexing start
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO indexing_status 
                    (status, folders_scanned, current_folder)
                    VALUES ('running', ?, 'Starting...')
                ''', (len(patient_folders),))
                conn.commit()
            
            # Index folders sequentially to avoid database locks - OPTIMIZED VERSION
            logger.info(f"📊 Indexing {len(patient_folders)} patient folders sequentially...")
            
            # Pre-load existing patient IDs for faster processing
            logger.info("🔍 Pre-loading existing patient IDs for optimization...")
            existing_patient_ids = set()
            try:
                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT DISTINCT patient_id FROM patient_studies')
                    existing_patient_ids = {row[0] for row in cursor.fetchall()}
                logger.info(f"✅ Loaded {len(existing_patient_ids)} existing patient IDs")
            except Exception as e:
                logger.warning(f"Could not pre-load patient IDs: {e}")
            
            completed = 0
            new_patients_added = 0
            skipped_existing = 0
            
            for folder in patient_folders:
                try:
                    # Quick check if patient might already exist (optimization)
                    folder_name = folder.name
                    patient_id_prefix = folder_name.split('-')[0] if '-' in folder_name else folder_name
                    
                    # Skip if we can quickly determine patient exists
                    if existing_patient_ids and any(pid.startswith(patient_id_prefix) for pid in existing_patient_ids):
                        completed += 1
                        skipped_existing += 1
                        if completed % 500 == 0:  # Report every 500 folders for more frequent updates
                            progress_percent = completed/len(patient_folders)*100
                            logger.info(f"📈 Progress: {completed:,}/{len(patient_folders):,} patients scanned "
                                      f"({progress_percent:.1f}%) • NEW: {new_patients_added:,} • Already indexed: {skipped_existing:,}")
                        continue
                    
                    # Get current patient count before processing (for folders that might be new)
                    with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT COUNT(*) FROM patient_studies')
                        studies_before = cursor.fetchone()[0]
                    
                    result = self.index_patient_folder(folder)
                    completed += 1
                    
                    # Check if new studies were added
                    with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT COUNT(*) FROM patient_studies')
                        studies_after = cursor.fetchone()[0]
                    
                    if studies_after > studies_before:
                        new_patients_added += (studies_after - studies_before)
                        logger.info(f"✨ NEW: {folder.name} → Added {studies_after - studies_before} study(s) (Total: {studies_after:,})")
                        
                        # Add the new patient ID to our cache for future optimization
                        try:
                            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT patient_id FROM patient_studies ORDER BY last_indexed DESC LIMIT 1')
                                latest_patient = cursor.fetchone()
                                if latest_patient:
                                    existing_patient_ids.add(latest_patient[0])
                        except Exception as cache_error:
                            logger.debug(f"Cache update error: {cache_error}")
                    else:
                        skipped_existing += 1
                    
                    # Update progress
                    with self.status_lock:
                        self.stats['current_folder'] = folder.name
                        elapsed = time.time() - self.stats['start_time']
                        self.stats['processing_rate'] = completed / elapsed if elapsed > 0 else 0
                        self.stats['folders_completed'] = completed
                        self.stats['total_folders'] = len(patient_folders)
                        
                        # Save real-time progress for API access
                        try:
                            progress_data = {
                                'current_folder': folder.name,
                                'completed': completed,
                                'total': len(patient_folders),
                                'rate': completed / elapsed if elapsed > 0 else 0,
                                'elapsed': elapsed,
                                'start_time': self.stats['start_time'],
                                'dicom_files': self.stats['dicom_files_found'],
                                'timestamp': time.time()
                            }
                            
                            import json
                            with open('indexing_progress.json', 'w') as f:
                                json.dump(progress_data, f)
                            logger.info(f"📊 Progress file updated: {completed}/{len(patient_folders)} folders, current: {folder.name}")
                        except Exception as e:
                            logger.error(f"❌ Could not save progress file: {e}")
                    
                    if completed % 10 == 0:  # More frequent updates for PACS monitoring
                        progress_percent = completed/len(patient_folders)*100
                        elapsed = time.time() - self.stats['start_time']
                        rate = completed / elapsed if elapsed > 0 else 0
                        remaining = len(patient_folders) - completed
                        eta_minutes = int((remaining / rate) / 60) if rate > 0 else 0
                        
                        eta_text = ""
                        if eta_minutes > 60:
                            eta_hours = eta_minutes // 60
                            eta_minutes = eta_minutes % 60
                            eta_text = f" • ETA: ~{eta_hours}h {eta_minutes}m"
                        elif eta_minutes > 0:
                            eta_text = f" • ETA: ~{eta_minutes} minutes"
                        
                        # Get current total studies from database for accurate display
                        try:
                            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT COUNT(*) FROM patient_studies')
                                total_studies = cursor.fetchone()[0]
                        except:
                            total_studies = self.stats['dicom_files_found']
                        
                        logger.info(f"📊 PACS Indexing: {completed:,}/{len(patient_folders):,} folders • {total_studies:,} studies indexed • Rate: {rate:.1f}/sec{eta_text}")
                        
                        # Update database status
                        try:
                            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                                cursor = conn.cursor()
                                cursor.execute('''
                                    UPDATE indexing_status 
                                    SET files_processed = ?, patients_found = ?, 
                                        current_folder = ?, errors = ?
                                    WHERE id = (SELECT MAX(id) FROM indexing_status)
                                ''', (
                                    self.stats['dicom_files_found'],
                                    self.stats['patients_indexed'],
                                    self.stats['current_folder'],
                                    self.stats['errors']
                                ))
                                conn.commit()
                        except Exception as db_error:
                            logger.debug(f"Database status update error: {db_error}")
                            
                except Exception as e:
                    logger.error(f"❌ Error processing {folder}: {e}")
                    self.stats['errors'] += 1
            
            # Complete indexing
            self.running = False
            elapsed = time.time() - self.stats['start_time']
            
            # Update database status
            try:
                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE indexing_status 
                        SET status = 'completed', completed_at = datetime('now'),
                            files_processed = ?, patients_found = ?, errors = ?
                        WHERE id = (SELECT MAX(id) FROM indexing_status)
                    ''', (
                        self.stats['dicom_files_found'],
                        self.stats['patients_indexed'],
                        self.stats['errors']
                    ))
                    conn.commit()
            except Exception as db_error:
                logger.error(f"Final database update error: {db_error}")
            
            logger.info("🎉 INDEXING COMPLETED!")
            logger.info(f"📊 FINAL STATISTICS:")
            logger.info(f"   ⏱️  Time elapsed: {elapsed:.1f} seconds")
            logger.info(f"   📁 Folders scanned: {self.stats['folders_scanned']}")
            logger.info(f"   📄 DICOM files found: {self.stats['dicom_files_found']}")
            logger.info(f"   👤 Patients indexed: {self.stats['patients_indexed']}")
            logger.info(f"   📋 Studies indexed: {self.stats['studies_indexed']}")
            logger.info(f"   📊 Series indexed: {self.stats['series_indexed']}")
            logger.info(f"   ❌ Errors: {self.stats['errors']}")
            logger.info(f"   🚀 Processing rate: {self.stats['processing_rate']:.1f} folders/sec")
    
    def get_indexing_status(self) -> Dict:
        """Get current indexing status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM indexing_status 
                    ORDER BY id DESC LIMIT 1
                ''')
                row = cursor.fetchone()
                
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    status = dict(zip(columns, row))
                    status.update(self.stats)
                    return status
                else:
                    return self.stats
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return self.stats
    
    def search_patients(self, patient_name="", patient_id="", study_date="", limit=50) -> List[Dict]:
        """Search indexed patients"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build search query
                where_clauses = []
                params = []
                
                if patient_name:
                    where_clauses.append("patient_name LIKE ?")
                    params.append(f"%{patient_name}%")
                
                if patient_id:
                    where_clauses.append("patient_id LIKE ?")
                    params.append(f"%{patient_id}%")
                
                if study_date:
                    where_clauses.append("study_date LIKE ?")
                    params.append(f"%{study_date.replace('-', '')}%")
                
                where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                query = f'''
                    SELECT patient_id, patient_name, patient_birth_date, patient_sex,
                           study_date as first_study_date, study_description, modality,
                           folder_path, dicom_file_count as file_count, folder_size_mb,
                           last_indexed, COUNT(*) as study_count, 0 as series_count
                    FROM patient_studies
                    WHERE {where_clause}
                    GROUP BY patient_id
                    ORDER BY last_indexed DESC
                    LIMIT ?
                '''
                
                params.append(limit)
                cursor.execute(query, params)
                
                columns = [desc[0] for desc in cursor.description]
                patients = []
                
                for row in cursor.fetchall():
                    patient = dict(zip(columns, row))
                    patients.append(patient)
                
                return patients
                
        except Exception as e:
            logger.error(f"Error searching patients: {e}")
            return []

def main():
    """Main indexing function"""
    indexer = NASPatientIndexer()
    
    # Check if Z: drive is accessible
    if not Path("Z:\\").exists():
        logger.error("❌ Z: drive not accessible. Please ensure NAS is mounted.")
        return
    
    logger.info("🏥 Ubuntu Patient Care - NAS DICOM Indexer")
    logger.info("=" * 60)
    
    try:
        # Run full indexing
        indexer.run_full_index(max_workers=1)  # Single-threaded for database safety
        
        # Test search
        logger.info("\n🔍 Testing patient search...")
        patients = indexer.search_patients(limit=10)
        
        if patients:
            logger.info(f"✅ Search test successful - found {len(patients)} patients")
            for i, patient in enumerate(patients[:3], 1):
                logger.info(f"   {i}. {patient['patient_name']} (ID: {patient['patient_id']}) - {patient['study_count']} studies")
        else:
            logger.warning("⚠️ No patients found in search test")
    
    except KeyboardInterrupt:
        logger.info("\n⏹️ Indexing interrupted by user")
    except Exception as e:
        logger.error(f"❌ Indexing failed: {e}")
        raise

if __name__ == "__main__":
    main()