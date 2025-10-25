#!/usr/bin/env python3
"""
High-Performance PACS Indexer for 11TB NAS Drive
==================================================

This creates a fast metadata index of all DICOM files without duplicating storage.
Critical for doctor workflow - enables instant patient search and image access.

Key Features:
- Scans 9300+ patients on NAS drive
- Extracts DICOM metadata from headers
- Builds SQLite index with file paths
- Enables sub-second patient search
- Direct access to original DICOM files
"""

import os
import sqlite3
import logging
import pydicom
import json
from datetime import datetime
from pathlib import Path
import threading
from typing import Dict, List, Optional, Tuple
import time
from .metadata_db import get_metadata_db_path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PACSIndexer:
    """High-performance PACS indexer for NAS-based DICOM storage"""
    
    def __init__(self, nas_path: str = "Z:", db_path: str = None):
        self.nas_path = Path(nas_path)
        # Use canonical metadata DB when not explicitly provided
        self.db_path = db_path or get_metadata_db_path()
        self.stats = {
            'patients': 0,
            'studies': 0,
            'series': 0,
            'instances': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
        self.is_indexing = False
        self.progress_callback = None
        
    def init_database(self):
        """Initialize the PACS index database with optimized schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Patients table - core patient demographics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                patient_id TEXT PRIMARY KEY,
                patient_name TEXT NOT NULL,
                patient_birth_date TEXT,
                patient_sex TEXT,
                patient_age TEXT,
                medical_aid TEXT,
                referring_doctor TEXT,
                indexed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                folder_path TEXT NOT NULL
            )
        ''')
        
        # Studies table - study-level metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS studies (
                study_instance_uid TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                study_date TEXT,
                study_time TEXT,
                study_description TEXT,
                modality TEXT,
                accession_number TEXT,
                study_id TEXT,
                folder_path TEXT NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
            )
        ''')
        
        # Series table - series-level metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS series (
                series_instance_uid TEXT PRIMARY KEY,
                study_instance_uid TEXT NOT NULL,
                series_number INTEGER,
                series_description TEXT,
                modality TEXT,
                body_part TEXT,
                series_date TEXT,
                series_time TEXT,
                folder_path TEXT NOT NULL,
                instance_count INTEGER DEFAULT 0,
                FOREIGN KEY (study_instance_uid) REFERENCES studies (study_instance_uid)
            )
        ''')
        
        # Instances table - individual DICOM file metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS instances (
                sop_instance_uid TEXT PRIMARY KEY,
                series_instance_uid TEXT NOT NULL,
                instance_number INTEGER,
                file_path TEXT NOT NULL UNIQUE,
                file_size INTEGER,
                acquisition_date TEXT,
                acquisition_time TEXT,
                slice_location REAL,
                FOREIGN KEY (series_instance_uid) REFERENCES series (series_instance_uid)
            )
        ''')
        
        # Create indexes for fast searching
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patient_name ON patients (patient_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patient_id ON patients (patient_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_study_date ON studies (study_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_modality ON studies (modality)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_accession ON studies (accession_number)')
        
        conn.commit()
        conn.close()
        logger.info("✅ PACS database initialized with optimized schema")
    
    def extract_dicom_metadata(self, file_path: Path) -> Optional[Dict]:
        """Extract metadata from DICOM file header"""
        try:
            ds = pydicom.dcmread(str(file_path), stop_before_pixels=True)
            
            # Extract patient information
            patient_name = str(getattr(ds, 'PatientName', 'Unknown')).replace('^', ' ')
            patient_id = str(getattr(ds, 'PatientID', ''))
            patient_dob = str(getattr(ds, 'PatientBirthDate', ''))
            patient_sex = str(getattr(ds, 'PatientSex', ''))
            patient_age = str(getattr(ds, 'PatientAge', ''))
            
            # Extract study information
            study_uid = str(getattr(ds, 'StudyInstanceUID', ''))
            study_date = str(getattr(ds, 'StudyDate', ''))
            study_time = str(getattr(ds, 'StudyTime', ''))
            study_desc = str(getattr(ds, 'StudyDescription', ''))
            modality = str(getattr(ds, 'Modality', ''))
            accession = str(getattr(ds, 'AccessionNumber', ''))
            study_id = str(getattr(ds, 'StudyID', ''))
            
            # Extract series information
            series_uid = str(getattr(ds, 'SeriesInstanceUID', ''))
            series_number = getattr(ds, 'SeriesNumber', 0)
            series_desc = str(getattr(ds, 'SeriesDescription', ''))
            body_part = str(getattr(ds, 'BodyPartExamined', ''))
            series_date = str(getattr(ds, 'SeriesDate', ''))
            series_time = str(getattr(ds, 'SeriesTime', ''))
            
            # Extract instance information
            sop_uid = str(getattr(ds, 'SOPInstanceUID', ''))
            instance_number = getattr(ds, 'InstanceNumber', 0)
            acquisition_date = str(getattr(ds, 'AcquisitionDate', ''))
            acquisition_time = str(getattr(ds, 'AcquisitionTime', ''))
            slice_location = getattr(ds, 'SliceLocation', None)
            
            # Try to extract medical aid and referring doctor from various fields
            medical_aid = str(getattr(ds, 'InstitutionName', getattr(ds, 'ReferringPhysicianName', 'DIRECT TO PATIENT')))
            referring_doctor = str(getattr(ds, 'ReferringPhysicianName', ''))
            
            return {
                'patient': {
                    'patient_id': patient_id or f"AUTO_{hash(patient_name + patient_dob) % 100000:05d}",
                    'patient_name': patient_name,
                    'patient_birth_date': patient_dob,
                    'patient_sex': patient_sex,
                    'patient_age': patient_age,
                    'medical_aid': medical_aid,
                    'referring_doctor': referring_doctor
                },
                'study': {
                    'study_instance_uid': study_uid,
                    'study_date': study_date,
                    'study_time': study_time,
                    'study_description': study_desc,
                    'modality': modality,
                    'accession_number': accession,
                    'study_id': study_id
                },
                'series': {
                    'series_instance_uid': series_uid,
                    'series_number': series_number,
                    'series_description': series_desc,
                    'modality': modality,
                    'body_part': body_part,
                    'series_date': series_date,
                    'series_time': series_time
                },
                'instance': {
                    'sop_instance_uid': sop_uid,
                    'instance_number': instance_number,
                    'acquisition_date': acquisition_date,
                    'acquisition_time': acquisition_time,
                    'slice_location': slice_location
                }
            }
            
        except Exception as e:
            logger.warning(f"Failed to read DICOM metadata from {file_path}: {e}")
            return None
    
    def scan_nas_directory(self, progress_callback=None):
        """Scan the entire NAS directory for DICOM files and build index"""
        logger.info(f"🔍 Starting PACS indexing of {self.nas_path}")
        self.is_indexing = True
        self.stats['start_time'] = datetime.now()
        self.progress_callback = progress_callback
        
        # Initialize database
        self.init_database()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing data for fresh index
        cursor.execute('DELETE FROM instances')
        cursor.execute('DELETE FROM series')
        cursor.execute('DELETE FROM studies')
        cursor.execute('DELETE FROM patients')
        
        processed_files = 0
        patient_folders = set()
        
        try:
            # Scan all directories for DICOM files
            for root, dirs, files in os.walk(self.nas_path):
                root_path = Path(root)
                
                # Skip if no files in this directory
                if not files:
                    continue
                    
                # Look for DICOM files (common extensions)
                dicom_files = [f for f in files if f.lower().endswith(('.dcm', '.dicom', '.ima', '.img')) or '.' not in f]
                
                if not dicom_files:
                    continue
                
                logger.info(f"📁 Processing folder: {root_path}")
                
                # Process each DICOM file in this folder
                for file_name in dicom_files:
                    file_path = root_path / file_name
                    
                    if not file_path.is_file():
                        continue
                    
                    # Extract metadata
                    metadata = self.extract_dicom_metadata(file_path)
                    if not metadata:
                        self.stats['errors'] += 1
                        continue
                    
                    try:
                        # Insert patient data (ignore if exists)
                        cursor.execute('''
                            INSERT OR IGNORE INTO patients 
                            (patient_id, patient_name, patient_birth_date, patient_sex, 
                             patient_age, medical_aid, referring_doctor, folder_path)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            metadata['patient']['patient_id'],
                            metadata['patient']['patient_name'],
                            metadata['patient']['patient_birth_date'],
                            metadata['patient']['patient_sex'],
                            metadata['patient']['patient_age'],
                            metadata['patient']['medical_aid'],
                            metadata['patient']['referring_doctor'],
                            str(root_path)
                        ))
                        
                        # Insert study data (ignore if exists)
                        cursor.execute('''
                            INSERT OR IGNORE INTO studies 
                            (study_instance_uid, patient_id, study_date, study_time,
                             study_description, modality, accession_number, study_id, folder_path)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            metadata['study']['study_instance_uid'],
                            metadata['patient']['patient_id'],
                            metadata['study']['study_date'],
                            metadata['study']['study_time'],
                            metadata['study']['study_description'],
                            metadata['study']['modality'],
                            metadata['study']['accession_number'],
                            metadata['study']['study_id'],
                            str(root_path)
                        ))
                        
                        # Insert series data (ignore if exists)
                        cursor.execute('''
                            INSERT OR IGNORE INTO series 
                            (series_instance_uid, study_instance_uid, series_number,
                             series_description, modality, body_part, series_date, 
                             series_time, folder_path, instance_count)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                        ''', (
                            metadata['series']['series_instance_uid'],
                            metadata['study']['study_instance_uid'],
                            metadata['series']['series_number'],
                            metadata['series']['series_description'],
                            metadata['series']['modality'],
                            metadata['series']['body_part'],
                            metadata['series']['series_date'],
                            metadata['series']['series_time'],
                            str(root_path)
                        ))
                        
                        # Insert instance data
                        cursor.execute('''
                            INSERT OR REPLACE INTO instances 
                            (sop_instance_uid, series_instance_uid, instance_number,
                             file_path, file_size, acquisition_date, acquisition_time, slice_location)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            metadata['instance']['sop_instance_uid'],
                            metadata['series']['series_instance_uid'],
                            metadata['instance']['instance_number'],
                            str(file_path),
                            file_path.stat().st_size,
                            metadata['instance']['acquisition_date'],
                            metadata['instance']['acquisition_time'],
                            metadata['instance']['slice_location']
                        ))
                        
                        # Update series instance count
                        cursor.execute('''
                            UPDATE series 
                            SET instance_count = (
                                SELECT COUNT(*) FROM instances 
                                WHERE series_instance_uid = ?
                            )
                            WHERE series_instance_uid = ?
                        ''', (metadata['series']['series_instance_uid'], metadata['series']['series_instance_uid']))
                        
                        processed_files += 1
                        
                        # Commit every 100 files for performance
                        if processed_files % 100 == 0:
                            conn.commit()
                            logger.info(f"💾 Processed {processed_files} DICOM files...")
                            
                            if self.progress_callback:
                                self.progress_callback(processed_files)
                        
                    except Exception as e:
                        logger.error(f"Failed to insert metadata for {file_path}: {e}")
                        self.stats['errors'] += 1
        
        except Exception as e:
            logger.error(f"Critical error during indexing: {e}")
        
        finally:
            # Final commit and update statistics
            conn.commit()
            
            # Update final statistics
            cursor.execute('SELECT COUNT(DISTINCT patient_id) FROM patients')
            self.stats['patients'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT study_instance_uid) FROM studies')
            self.stats['studies'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT series_instance_uid) FROM series')
            self.stats['series'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM instances')
            self.stats['instances'] = cursor.fetchone()[0]
            
            conn.close()
            
            self.stats['end_time'] = datetime.now()
            self.is_indexing = False
            
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            logger.info("🎉 PACS Indexing Complete!")
            logger.info(f"📊 Statistics:")
            logger.info(f"   - Patients: {self.stats['patients']:,}")
            logger.info(f"   - Studies: {self.stats['studies']:,}")
            logger.info(f"   - Series: {self.stats['series']:,}")
            logger.info(f"   - Instances: {self.stats['instances']:,}")
            logger.info(f"   - Duration: {duration:.1f} seconds")
            logger.info(f"   - Speed: {self.stats['instances']/duration:.1f} files/second")
    
    def search_patients(self, query: str = "", modality: str = "", study_date: str = "") -> List[Dict]:
        """Fast patient search using the index"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build search query
        sql = '''
            SELECT DISTINCT 
                p.patient_id, p.patient_name, p.patient_birth_date, p.patient_sex,
                p.medical_aid, p.referring_doctor, p.folder_path,
                COUNT(DISTINCT s.study_instance_uid) as study_count
            FROM patients p
            LEFT JOIN studies s ON p.patient_id = s.patient_id
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
        
        sql += " GROUP BY p.patient_id ORDER BY p.patient_name"
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
        
        patients = []
        for row in results:
            patients.append({
                'patient_id': row[0],
                'name': row[1],
                'birth_date': row[2],
                'sex': row[3],
                'medical_aid': row[4],
                'referring_doctor': row[5],
                'folder_path': row[6],
                'study_count': row[7]
            })
        
        return patients
    
    def get_patient_studies(self, patient_id: str) -> List[Dict]:
        """Get all studies for a specific patient"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT study_instance_uid, study_date, study_time, study_description,
                   modality, accession_number, folder_path,
                   (SELECT COUNT(DISTINCT series_instance_uid) 
                    FROM series WHERE study_instance_uid = s.study_instance_uid) as series_count,
                   (SELECT COUNT(*) 
                    FROM instances i JOIN series se ON i.series_instance_uid = se.series_instance_uid
                    WHERE se.study_instance_uid = s.study_instance_uid) as instance_count
            FROM studies s
            WHERE patient_id = ?
            ORDER BY study_date DESC, study_time DESC
        ''', (patient_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        studies = []
        for row in results:
            studies.append({
                'study_instance_uid': row[0],
                'study_date': row[1],
                'study_time': row[2],
                'study_description': row[3],
                'modality': row[4],
                'accession_number': row[5],
                'folder_path': row[6],
                'series_count': row[7],
                'instance_count': row[8]
            })
        
        return studies
    
    def get_study_images(self, study_uid: str) -> List[Dict]:
        """Get all image files for a specific study"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT i.file_path, i.instance_number, i.sop_instance_uid,
                   se.series_description, se.series_number, se.modality
            FROM instances i
            JOIN series se ON i.series_instance_uid = se.series_instance_uid
            WHERE se.study_instance_uid = ?
            ORDER BY se.series_number, i.instance_number
        ''', (study_uid,))
        
        results = cursor.fetchall()
        conn.close()
        
        images = []
        for row in results:
            images.append({
                'file_path': row[0],
                'instance_number': row[1],
                'sop_instance_uid': row[2],
                'series_description': row[3],
                'series_number': row[4],
                'modality': row[5]
            })
        
        return images
    
    def get_indexing_status(self) -> Dict:
        """Get current indexing status and statistics"""
        return {
            'is_indexing': self.is_indexing,
            'stats': self.stats.copy(),
            'db_exists': os.path.exists(self.db_path)
        }

def start_indexing_thread(nas_path: str = "Z:", db_path: str = "pacs_index.db"):
    """Start indexing in a background thread"""
    indexer = PACSIndexer(nas_path, db_path)
    
    def progress_callback(processed_files):
        logger.info(f"📈 Progress: {processed_files} files processed")
    
    thread = threading.Thread(target=indexer.scan_nas_directory, args=(progress_callback,))
    thread.daemon = True
    thread.start()
    
    return indexer

if __name__ == "__main__":
    # Test the indexer
    indexer = PACSIndexer("Z:", "test_pacs_index.db")
    
    print("🏥 Ubuntu Patient Care - PACS Indexer")
    print("=" * 50)
    
    choice = input("Start full NAS indexing? (y/n): ").lower()
    if choice == 'y':
        indexer.scan_nas_directory()
        
        # Test search
        print("\n🔍 Testing patient search...")
        patients = indexer.search_patients("FELIX")
        for patient in patients:
            print(f"Found: {patient['name']} (ID: {patient['patient_id']})")