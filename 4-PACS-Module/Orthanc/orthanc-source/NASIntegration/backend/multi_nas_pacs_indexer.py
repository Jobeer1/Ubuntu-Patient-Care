#!/usr/bin/env python3
"""
Enterprise Multi-NAS PACS Indexing System
==========================================

Unified SQL database for fast image location across multiple NAS devices:
- NAS #1: Pure DICOM files (CT scans)  
- NAS #2: Firebird database + JPEG2000 lossless
- NAS #3: Firebird database + JPEG2000 lossless

Features:
- Single SQL index for all image locations
- Incremental updates for new procedures
- Sub-second doctor search across all NAS devices
- Support for DICOM, JPEG2000, and database formats
- Real-time procedure indexing
"""

import os
import sqlite3
import logging
import pydicom
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import hashlib

# Firebird database support
try:
    import fdb  # Firebird database connector
    FIREBIRD_AVAILABLE = True
except ImportError:
    FIREBIRD_AVAILABLE = False
    logging.warning("⚠️ Firebird connector not available. Install with: pip install fdb")

# JPEG2000 support  
try:
    import glymur  # JPEG2000 support
    JPEG2000_AVAILABLE = True
except ImportError:
    JPEG2000_AVAILABLE = False
    logging.warning("⚠️ JPEG2000 support not available. Install with: pip install glymur")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MultiNASPACSIndexer:
    """Enterprise PACS indexer for multiple NAS devices with different formats"""
    
    def __init__(self, db_path: str = "enterprise_pacs_index.db"):
        self.db_path = db_path
        self.nas_configs = {}
        self.is_indexing = False
        self.incremental_mode = False
        self.last_update_times = {}
        
        # Threading for concurrent NAS processing
        self.indexing_threads = []
        self.progress_callbacks = []
        
        # Statistics tracking
        self.stats = {
            'total_patients': 0,
            'total_studies': 0,
            'total_series': 0,
            'total_instances': 0,
            'nas_stats': {},
            'errors': 0,
            'start_time': None,
            'end_time': None,
            'last_incremental_update': None
        }
    
    def add_nas_device(self, nas_id: str, config: Dict):
        """
        Add a NAS device configuration
        
        Args:
            nas_id: Unique identifier for the NAS device
            config: Configuration dictionary with:
                - type: 'dicom', 'firebird_jpeg2000'
                - path: Base path to NAS device
                - firebird_db: Path to Firebird database (if applicable)
                - firebird_host: Firebird server host (if applicable)
                - firebird_user: Database username
                - firebird_password: Database password
                - description: Human-readable description
        """
        self.nas_configs[nas_id] = config
        logger.info(f"✅ Added NAS device: {nas_id} ({config.get('description', 'Unknown')})")
    
    def init_enterprise_database(self):
        """Initialize the enterprise PACS database with comprehensive schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # NAS devices table - track all configured NAS devices
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nas_devices (
                nas_id TEXT PRIMARY KEY,
                device_type TEXT NOT NULL,
                base_path TEXT NOT NULL,
                firebird_db TEXT,
                firebird_host TEXT,
                description TEXT,
                status TEXT DEFAULT 'active',
                last_indexed TIMESTAMP,
                total_patients INTEGER DEFAULT 0,
                total_studies INTEGER DEFAULT 0,
                total_instances INTEGER DEFAULT 0,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Enhanced patients table with NAS source tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                patient_id TEXT,
                nas_id TEXT,
                patient_name TEXT NOT NULL,
                patient_birth_date TEXT,
                patient_sex TEXT,
                patient_age TEXT,
                medical_aid TEXT,
                referring_doctor TEXT,
                indexed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_path TEXT NOT NULL,
                PRIMARY KEY (patient_id, nas_id),
                FOREIGN KEY (nas_id) REFERENCES nas_devices (nas_id)
            )
        ''')
        
        # Enhanced studies table with format tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS studies (
                study_instance_uid TEXT,
                nas_id TEXT,
                patient_id TEXT NOT NULL,
                study_date TEXT,
                study_time TEXT,
                study_description TEXT,
                modality TEXT,
                accession_number TEXT,
                study_id TEXT,
                source_path TEXT NOT NULL,
                image_format TEXT, -- 'DICOM', 'JPEG2000', etc.
                compression_type TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (study_instance_uid, nas_id),
                FOREIGN KEY (patient_id, nas_id) REFERENCES patients (patient_id, nas_id)
            )
        ''')
        
        # Enhanced series table with compression info
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS series (
                series_instance_uid TEXT,
                nas_id TEXT,
                study_instance_uid TEXT NOT NULL,
                series_number INTEGER,
                series_description TEXT,
                modality TEXT,
                body_part TEXT,
                series_date TEXT,
                series_time TEXT,
                source_path TEXT NOT NULL,
                image_format TEXT,
                compression_ratio REAL,
                instance_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (series_instance_uid, nas_id),
                FOREIGN KEY (study_instance_uid, nas_id) REFERENCES studies (study_instance_uid, nas_id)
            )
        ''')
        
        # Enhanced instances table with file location tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS instances (
                sop_instance_uid TEXT,
                nas_id TEXT,
                series_instance_uid TEXT NOT NULL,
                instance_number INTEGER,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                file_format TEXT, -- 'DCM', 'JP2', 'JPEG', etc.
                compression_type TEXT,
                image_width INTEGER,
                image_height INTEGER,
                bits_per_pixel INTEGER,
                acquisition_date TEXT,
                acquisition_time TEXT,
                slice_location REAL,
                file_hash TEXT, -- For change detection
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (sop_instance_uid, nas_id),
                FOREIGN KEY (series_instance_uid, nas_id) REFERENCES series (series_instance_uid, nas_id)
            )
        ''')
        
        # Incremental update tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS update_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nas_id TEXT NOT NULL,
                update_type TEXT NOT NULL, -- 'full', 'incremental'
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                files_processed INTEGER DEFAULT 0,
                patients_updated INTEGER DEFAULT 0,
                studies_updated INTEGER DEFAULT 0,
                errors INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running', -- 'running', 'completed', 'failed'
                FOREIGN KEY (nas_id) REFERENCES nas_devices (nas_id)
            )
        ''')
        
        # Create comprehensive indexes for fast searching
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_patient_name ON patients (patient_name)',
            'CREATE INDEX IF NOT EXISTS idx_patient_id ON patients (patient_id)',
            'CREATE INDEX IF NOT EXISTS idx_patient_nas ON patients (nas_id)',
            'CREATE INDEX IF NOT EXISTS idx_study_date ON studies (study_date)',
            'CREATE INDEX IF NOT EXISTS idx_study_modality ON studies (modality)',
            'CREATE INDEX IF NOT EXISTS idx_study_accession ON studies (accession_number)',
            'CREATE INDEX IF NOT EXISTS idx_study_nas ON studies (nas_id)',
            'CREATE INDEX IF NOT EXISTS idx_instance_path ON instances (file_path)',
            'CREATE INDEX IF NOT EXISTS idx_instance_hash ON instances (file_hash)',
            'CREATE INDEX IF NOT EXISTS idx_last_updated ON instances (last_updated)',
            'CREATE INDEX IF NOT EXISTS idx_update_log_nas ON update_log (nas_id, start_time)'
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        conn.commit()
        conn.close()
        logger.info("✅ Enterprise PACS database initialized with multi-NAS schema")
    
    def extract_dicom_metadata(self, file_path: Path, nas_id: str) -> Optional[Dict]:
        """Extract metadata from DICOM file"""
        try:
            ds = pydicom.dcmread(str(file_path), stop_before_pixels=True)
            
            # Calculate file hash for change detection
            file_hash = self._calculate_file_hash(file_path)
            
            # Extract comprehensive metadata
            metadata = {
                'patient': {
                    'patient_id': str(getattr(ds, 'PatientID', '')),
                    'patient_name': str(getattr(ds, 'PatientName', 'Unknown')).replace('^', ' '),
                    'patient_birth_date': str(getattr(ds, 'PatientBirthDate', '')),
                    'patient_sex': str(getattr(ds, 'PatientSex', '')),
                    'patient_age': str(getattr(ds, 'PatientAge', '')),
                    'medical_aid': str(getattr(ds, 'InstitutionName', getattr(ds, 'ReferringPhysicianName', 'DIRECT TO PATIENT'))),
                    'referring_doctor': str(getattr(ds, 'ReferringPhysicianName', ''))
                },
                'study': {
                    'study_instance_uid': str(getattr(ds, 'StudyInstanceUID', '')),
                    'study_date': str(getattr(ds, 'StudyDate', '')),
                    'study_time': str(getattr(ds, 'StudyTime', '')),
                    'study_description': str(getattr(ds, 'StudyDescription', '')),
                    'modality': str(getattr(ds, 'Modality', '')),
                    'accession_number': str(getattr(ds, 'AccessionNumber', '')),
                    'study_id': str(getattr(ds, 'StudyID', ''))
                },
                'series': {
                    'series_instance_uid': str(getattr(ds, 'SeriesInstanceUID', '')),
                    'series_number': getattr(ds, 'SeriesNumber', 0),
                    'series_description': str(getattr(ds, 'SeriesDescription', '')),
                    'modality': str(getattr(ds, 'Modality', '')),
                    'body_part': str(getattr(ds, 'BodyPartExamined', '')),
                    'series_date': str(getattr(ds, 'SeriesDate', '')),
                    'series_time': str(getattr(ds, 'SeriesTime', ''))
                },
                'instance': {
                    'sop_instance_uid': str(getattr(ds, 'SOPInstanceUID', '')),
                    'instance_number': getattr(ds, 'InstanceNumber', 0),
                    'acquisition_date': str(getattr(ds, 'AcquisitionDate', '')),
                    'acquisition_time': str(getattr(ds, 'AcquisitionTime', '')),
                    'slice_location': getattr(ds, 'SliceLocation', None),
                    'image_width': getattr(ds, 'Columns', None),
                    'image_height': getattr(ds, 'Rows', None),
                    'bits_per_pixel': getattr(ds, 'BitsAllocated', None)
                },
                'file_info': {
                    'file_path': str(file_path),
                    'file_size': file_path.stat().st_size,
                    'file_format': 'DCM',
                    'compression_type': 'DICOM',
                    'file_hash': file_hash,
                    'nas_id': nas_id
                }
            }
            
            return metadata
            
        except Exception as e:
            logger.warning(f"Failed to read DICOM metadata from {file_path}: {e}")
            return None
    
    def extract_firebird_metadata(self, nas_id: str) -> List[Dict]:
        """Extract metadata from Firebird database"""
        if not FIREBIRD_AVAILABLE:
            logger.error("❌ Firebird support not available")
            return []
        
        config = self.nas_configs.get(nas_id)
        if not config:
            logger.error(f"❌ NAS config not found: {nas_id}")
            return []
        
        try:
            # Connect to Firebird database
            conn = fdb.connect(
                database=config['firebird_db'],
                host=config.get('firebird_host', 'localhost'),
                user=config['firebird_user'],
                password=config['firebird_password']
            )
            
            cursor = conn.cursor()
            
            # Query patient and study information
            # Note: Adjust SQL based on your actual Firebird schema
            sql = """
                SELECT DISTINCT
                    p.patient_id,
                    p.patient_name,
                    p.birth_date,
                    p.sex,
                    s.study_uid,
                    s.study_date,
                    s.study_description,
                    s.modality,
                    sr.series_uid,
                    sr.series_description,
                    i.file_path,
                    i.file_format,
                    i.compression_ratio
                FROM patients p
                JOIN studies s ON p.patient_id = s.patient_id
                JOIN series sr ON s.study_uid = sr.study_uid  
                JOIN instances i ON sr.series_uid = i.series_uid
                WHERE s.study_date >= ?
                ORDER BY p.patient_name, s.study_date
            """
            
            # Get recent studies (last 30 days for incremental)
            cutoff_date = datetime.now() - timedelta(days=30)
            cursor.execute(sql, (cutoff_date.strftime('%Y%m%d'),))
            
            results = []
            for row in cursor.fetchall():
                metadata = {
                    'patient': {
                        'patient_id': row[0],
                        'patient_name': row[1],
                        'patient_birth_date': row[2],
                        'patient_sex': row[3],
                        'medical_aid': 'Medical Aid',
                        'referring_doctor': ''
                    },
                    'study': {
                        'study_instance_uid': row[4],
                        'study_date': row[5],
                        'study_description': row[6],
                        'modality': row[7]
                    },
                    'series': {
                        'series_instance_uid': row[8],
                        'series_description': row[9]
                    },
                    'instance': {
                        'sop_instance_uid': f"{row[8]}_{hash(row[10])}",
                        'instance_number': 1
                    },
                    'file_info': {
                        'file_path': row[10],
                        'file_format': row[11] or 'JP2',
                        'compression_type': 'JPEG2000',
                        'compression_ratio': row[12],
                        'nas_id': nas_id
                    }
                }
                results.append(metadata)
            
            conn.close()
            logger.info(f"✅ Extracted {len(results)} records from Firebird database: {nas_id}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to extract from Firebird database {nas_id}: {e}")
            return []
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file for change detection"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def index_nas_device(self, nas_id: str, incremental: bool = False):
        """Index a specific NAS device"""
        config = self.nas_configs.get(nas_id)
        if not config:
            logger.error(f"❌ NAS device not configured: {nas_id}")
            return
        
        logger.info(f"🔍 {'Incremental' if incremental else 'Full'} indexing of NAS: {nas_id}")
        
        # Log update start
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO update_log (nas_id, update_type, start_time)
            VALUES (?, ?, ?)
        ''', (nas_id, 'incremental' if incremental else 'full', datetime.now()))
        
        update_log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        try:
            if config['type'] == 'dicom':
                self._index_dicom_nas(nas_id, incremental, update_log_id)
            elif config['type'] == 'firebird_jpeg2000':
                self._index_firebird_nas(nas_id, incremental, update_log_id)
            else:
                logger.error(f"❌ Unknown NAS type: {config['type']}")
                
        except Exception as e:
            logger.error(f"❌ Failed to index NAS {nas_id}: {e}")
            
            # Mark update as failed
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE update_log 
                SET status = 'failed', end_time = ?
                WHERE id = ?
            ''', (datetime.now(), update_log_id))
            conn.commit()
            conn.close()
    
    def _index_dicom_nas(self, nas_id: str, incremental: bool, update_log_id: int):
        """Index DICOM-based NAS device"""
        config = self.nas_configs[nas_id]
        nas_path = Path(config['path'])
        
        if not nas_path.exists():
            logger.error(f"❌ NAS path not accessible: {nas_path}")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get last update time for incremental indexing
        cutoff_time = None
        if incremental:
            cursor.execute('''
                SELECT MAX(last_updated) FROM instances WHERE nas_id = ?
            ''', (nas_id,))
            result = cursor.fetchone()
            if result[0]:
                cutoff_time = datetime.fromisoformat(result[0])
                logger.info(f"📅 Incremental update since: {cutoff_time}")
        
        processed_files = 0
        
        # Scan for DICOM files
        for root, dirs, files in os.walk(nas_path):
            root_path = Path(root)
            
            # Skip if incremental and folder not modified recently
            if incremental and cutoff_time:
                folder_mtime = datetime.fromtimestamp(root_path.stat().st_mtime)
                if folder_mtime < cutoff_time:
                    continue
            
            dicom_files = [f for f in files if f.lower().endswith(('.dcm', '.dicom', '.ima', '.img')) or '.' not in f]
            
            for file_name in dicom_files:
                file_path = root_path / file_name
                
                # Skip if incremental and file not modified recently
                if incremental and cutoff_time:
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime < cutoff_time:
                        continue
                
                # Extract metadata
                metadata = self.extract_dicom_metadata(file_path, nas_id)
                if not metadata:
                    continue
                
                # Insert/update database
                self._upsert_metadata(cursor, metadata, nas_id)
                
                processed_files += 1
                
                if processed_files % 100 == 0:
                    conn.commit()
                    logger.info(f"💾 Processed {processed_files} files from {nas_id}")
                    
                    # Update progress log
                    cursor.execute('''
                        UPDATE update_log 
                        SET files_processed = ?
                        WHERE id = ?
                    ''', (processed_files, update_log_id))
                    conn.commit()
        
        # Final commit and update log
        conn.commit()
        cursor.execute('''
            UPDATE update_log 
            SET status = 'completed', end_time = ?, files_processed = ?
            WHERE id = ?
        ''', (datetime.now(), processed_files, update_log_id))
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Completed {nas_id} indexing: {processed_files} files processed")
    
    def _index_firebird_nas(self, nas_id: str, incremental: bool, update_log_id: int):
        """Index Firebird/JPEG2000 based NAS device"""
        records = self.extract_firebird_metadata(nas_id)
        
        if not records:
            logger.warning(f"⚠️ No records found for NAS: {nas_id}")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        processed = 0
        for metadata in records:
            self._upsert_metadata(cursor, metadata, nas_id)
            processed += 1
            
            if processed % 50 == 0:
                conn.commit()
                logger.info(f"💾 Processed {processed} records from {nas_id}")
        
        # Final commit and update log
        conn.commit()
        cursor.execute('''
            UPDATE update_log 
            SET status = 'completed', end_time = ?, files_processed = ?
            WHERE id = ?
        ''', (datetime.now(), processed, update_log_id))
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Completed {nas_id} Firebird indexing: {processed} records processed")
    
    def _upsert_metadata(self, cursor, metadata: Dict, nas_id: str):
        """Insert or update metadata in database"""
        try:
            # Upsert patient
            cursor.execute('''
                INSERT OR REPLACE INTO patients 
                (patient_id, nas_id, patient_name, patient_birth_date, patient_sex, 
                 patient_age, medical_aid, referring_doctor, source_path, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metadata['patient']['patient_id'], nas_id,
                metadata['patient']['patient_name'],
                metadata['patient']['patient_birth_date'],
                metadata['patient']['patient_sex'],
                metadata['patient']['patient_age'],
                metadata['patient']['medical_aid'],
                metadata['patient']['referring_doctor'],
                metadata['file_info']['file_path'],
                datetime.now()
            ))
            
            # Upsert study
            cursor.execute('''
                INSERT OR REPLACE INTO studies 
                (study_instance_uid, nas_id, patient_id, study_date, study_time,
                 study_description, modality, accession_number, study_id, 
                 source_path, image_format, compression_type, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metadata['study']['study_instance_uid'], nas_id,
                metadata['patient']['patient_id'],
                metadata['study']['study_date'],
                metadata['study']['study_time'],
                metadata['study']['study_description'],
                metadata['study']['modality'],
                metadata['study']['accession_number'],
                metadata['study']['study_id'],
                metadata['file_info']['file_path'],
                metadata['file_info']['file_format'],
                metadata['file_info']['compression_type'],
                datetime.now()
            ))
            
            # Upsert series
            cursor.execute('''
                INSERT OR REPLACE INTO series 
                (series_instance_uid, nas_id, study_instance_uid, series_number,
                 series_description, modality, body_part, series_date, series_time,
                 source_path, image_format, compression_ratio, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metadata['series']['series_instance_uid'], nas_id,
                metadata['study']['study_instance_uid'],
                metadata['series']['series_number'],
                metadata['series']['series_description'],
                metadata['series']['modality'],
                metadata['series']['body_part'],
                metadata['series']['series_date'],
                metadata['series']['series_time'],
                metadata['file_info']['file_path'],
                metadata['file_info']['file_format'],
                metadata['file_info'].get('compression_ratio'),
                datetime.now()
            ))
            
            # Upsert instance
            cursor.execute('''
                INSERT OR REPLACE INTO instances 
                (sop_instance_uid, nas_id, series_instance_uid, instance_number,
                 file_path, file_size, file_format, compression_type,
                 image_width, image_height, bits_per_pixel,
                 acquisition_date, acquisition_time, slice_location, 
                 file_hash, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metadata['instance']['sop_instance_uid'], nas_id,
                metadata['series']['series_instance_uid'],
                metadata['instance']['instance_number'],
                metadata['file_info']['file_path'],
                metadata['file_info']['file_size'],
                metadata['file_info']['file_format'],
                metadata['file_info']['compression_type'],
                metadata['instance'].get('image_width'),
                metadata['instance'].get('image_height'),
                metadata['instance'].get('bits_per_pixel'),
                metadata['instance']['acquisition_date'],
                metadata['instance']['acquisition_time'],
                metadata['instance']['slice_location'],
                metadata['file_info'].get('file_hash'),
                datetime.now()
            ))
            
        except Exception as e:
            logger.error(f"❌ Failed to upsert metadata: {e}")
    
    def search_patients_across_nas(self, query: str = "", modality: str = "", 
                                 study_date: str = "", nas_filter: str = "") -> List[Dict]:
        """Search patients across all NAS devices"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build comprehensive search query
        sql = '''
            SELECT DISTINCT 
                p.patient_id, p.nas_id, p.patient_name, p.patient_birth_date, 
                p.patient_sex, p.medical_aid, p.referring_doctor, p.source_path,
                nd.description as nas_description,
                COUNT(DISTINCT s.study_instance_uid) as study_count,
                COUNT(DISTINCT i.sop_instance_uid) as image_count,
                GROUP_CONCAT(DISTINCT s.modality) as modalities,
                GROUP_CONCAT(DISTINCT i.file_format) as formats
            FROM patients p
            LEFT JOIN studies s ON p.patient_id = s.patient_id AND p.nas_id = s.nas_id
            LEFT JOIN instances i ON s.study_instance_uid = i.series_instance_uid AND s.nas_id = i.nas_id
            LEFT JOIN nas_devices nd ON p.nas_id = nd.nas_id
            WHERE 1=1
        '''
        params = []
        
        if query:
            sql += " AND (p.patient_name LIKE ? OR p.patient_id LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        
        if modality:
            sql += " AND s.modality = ?"
            params.append(modality)
        
        if study_date:
            sql += " AND s.study_date = ?"
            params.append(study_date.replace('-', ''))
        
        if nas_filter:
            sql += " AND p.nas_id = ?"
            params.append(nas_filter)
        
        sql += " GROUP BY p.patient_id, p.nas_id ORDER BY p.patient_name"
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
        
        patients = []
        for row in results:
            patients.append({
                'patient_id': row[0],
                'nas_id': row[1],
                'name': row[2],
                'birth_date': row[3],
                'sex': row[4],
                'medical_aid': row[5],
                'referring_doctor': row[6],
                'source_path': row[7],
                'nas_description': row[8],
                'study_count': row[9],
                'image_count': row[10],
                'modalities': row[11],
                'formats': row[12]
            })
        
        return patients
    
    def get_image_locations(self, patient_id: str, nas_id: str = None) -> List[Dict]:
        """Get all image file locations for a patient across NAS devices"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = '''
            SELECT 
                i.file_path, i.file_format, i.compression_type,
                i.image_width, i.image_height, i.file_size,
                s.study_description, s.modality, s.study_date,
                sr.series_description, sr.series_number,
                i.nas_id, nd.description as nas_description
            FROM instances i
            JOIN series sr ON i.series_instance_uid = sr.series_instance_uid AND i.nas_id = sr.nas_id
            JOIN studies s ON sr.study_instance_uid = s.study_instance_uid AND sr.nas_id = s.nas_id
            JOIN patients p ON s.patient_id = p.patient_id AND s.nas_id = p.nas_id
            JOIN nas_devices nd ON i.nas_id = nd.nas_id
            WHERE p.patient_id = ?
        '''
        params = [patient_id]
        
        if nas_id:
            sql += " AND i.nas_id = ?"
            params.append(nas_id)
        
        sql += " ORDER BY s.study_date DESC, sr.series_number, i.instance_number"
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
        
        images = []
        for row in results:
            images.append({
                'file_path': row[0],
                'file_format': row[1],
                'compression_type': row[2],
                'image_width': row[3],
                'image_height': row[4],
                'file_size': row[5],
                'study_description': row[6],
                'modality': row[7],
                'study_date': row[8],
                'series_description': row[9],
                'series_number': row[10],
                'nas_id': row[11],
                'nas_description': row[12]
            })
        
        return images
    
    def start_incremental_monitoring(self, interval_minutes: int = 15):
        """Start background thread for incremental updates"""
        def monitoring_loop():
            while True:
                try:
                    logger.info("🔄 Starting incremental update cycle...")
                    
                    for nas_id in self.nas_configs.keys():
                        self.index_nas_device(nas_id, incremental=True)
                    
                    self.stats['last_incremental_update'] = datetime.now()
                    logger.info(f"✅ Incremental update completed. Next in {interval_minutes} minutes.")
                    
                except Exception as e:
                    logger.error(f"❌ Incremental update failed: {e}")
                
                time.sleep(interval_minutes * 60)
        
        thread = threading.Thread(target=monitoring_loop, daemon=True)
        thread.start()
        logger.info(f"🚀 Started incremental monitoring (every {interval_minutes} minutes)")

# Configuration function for the three NAS devices
def setup_three_nas_config():
    """Setup configuration for your three NAS devices"""
    indexer = MultiNASPACSIndexer("enterprise_pacs_index.db")
    
    # NAS #1: DICOM CT Scans (currently connected)
    indexer.add_nas_device('nas_ct_dicom', {
        'type': 'dicom',
        'path': 'Z:',
        'description': 'CT DICOM NAS (Pure DICOM Files)'
    })
    
    # NAS #2: Firebird + JPEG2000 (configure when available)
    indexer.add_nas_device('nas_firebird_1', {
        'type': 'firebird_jpeg2000', 
        'path': 'Y:',  # Adjust path as needed
        'firebird_db': 'Y:/medical_db.fdb',  # Adjust database path
        'firebird_host': 'localhost',  # Adjust host
        'firebird_user': 'SYSDBA',  # Adjust credentials
        'firebird_password': 'password',  # Adjust credentials
        'description': 'Medical Images NAS #2 (Firebird + JPEG2000)'
    })
    
    # NAS #3: Firebird + JPEG2000 (configure when available)
    indexer.add_nas_device('nas_firebird_2', {
        'type': 'firebird_jpeg2000',
        'path': 'X:',  # Adjust path as needed
        'firebird_db': 'X:/medical_db.fdb',  # Adjust database path
        'firebird_host': 'localhost',  # Adjust host
        'firebird_user': 'SYSDBA',  # Adjust credentials
        'firebird_password': 'password',  # Adjust credentials
        'description': 'Medical Images NAS #3 (Firebird + JPEG2000)'
    })
    
    return indexer

if __name__ == "__main__":
    # Example usage
    indexer = setup_three_nas_config()
    indexer.init_enterprise_database()
    
    print("🏥 Multi-NAS PACS Indexer Initialized")
    print("🔧 Configure your Firebird database connections")
    print("🚀 Run full indexing: indexer.index_nas_device('nas_ct_dicom')")
    print("🔄 Start incremental monitoring: indexer.start_incremental_monitoring(15)")