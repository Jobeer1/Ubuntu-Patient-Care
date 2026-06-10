"""
SQLite-backed Health Graph Index Database
Converts 2GB JSON index into efficient SQLite with consolidation by patient
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

class HealthGraphDB:
    """SQLite database for consolidated patient health records"""
    
    SCHEMA_VERSION = 1
    
    def __init__(self, db_path: str):
        """Initialize database connection and schema"""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
    
    def _init_schema(self) -> None:
        """Create tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Patients table - one row per patient
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT UNIQUE NOT NULL,
                patient_name TEXT,
                dob TEXT,
                patient_age TEXT,
                patient_sex TEXT,
                institution TEXT,
                first_indexed TEXT,
                last_updated TEXT,
                total_studies INTEGER DEFAULT 0
            )
        ''')
        
        # Studies table - all studies for a patient
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS studies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                study_uid TEXT UNIQUE,
                accession_number TEXT,
                study_date TEXT,
                study_time TEXT,
                study_description TEXT,
                referring_physician TEXT,
                modality TEXT,
                body_part TEXT,
                body_part_normalized TEXT,
                series_count INTEGER DEFAULT 0,
                indexed_at TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            )
        ''')
        
        # Series table - individual series within studies
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS series (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                study_uid TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                series_description TEXT,
                series_time TEXT,
                modality TEXT,
                manufacturer TEXT,
                image_count INTEGER DEFAULT 0,
                FOREIGN KEY (study_uid) REFERENCES studies(study_uid),
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            )
        ''')
        
        # Files table - actual DICOM/JP2/PDF files
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                study_uid TEXT,
                series_id INTEGER,
                file_path TEXT UNIQUE NOT NULL,
                file_type TEXT,
                image_height INTEGER,
                image_width INTEGER,
                summary TEXT,
                indexed_at TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
                FOREIGN KEY (study_uid) REFERENCES studies(study_uid),
                FOREIGN KEY (series_id) REFERENCES series(id)
            )
        ''')
        
        # Keywords table for full-text search
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                FOREIGN KEY (file_id) REFERENCES files(id)
            )
        ''')
        
        # Create indexes for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patient_id ON patients(patient_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_studies_patient ON studies(patient_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_studies_date ON studies(study_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_studies_modality ON studies(modality)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_series_study ON series(study_uid)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_patient ON files(patient_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords(keyword)')
        
        self.conn.commit()
    
    def migrate_from_json(self, json_path: str, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Migrate from JSON index file to SQLite
        Consolidates multiple entries per patient into single patient record
        """
        if not os.path.exists(json_path):
            return {'success': False, 'error': f'JSON file not found: {json_path}'}
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                data = [data]
            
            total = len(data)
            patient_studies = {}  # Consolidate by patient
            
            # Group entries by patient_id
            for idx, entry in enumerate(data):
                if progress_callback:
                    progress_callback(idx + 1, total)
                
                patient_id = entry.get('patient_id', 'unknown')
                if patient_id not in patient_studies:
                    patient_studies[patient_id] = {
                        'patient': entry,
                        'files': []
                    }
                patient_studies[patient_id]['files'].append(entry)
            
            # Insert consolidated records
            for patient_id, patient_data in patient_studies.items():
                self._insert_patient_record(patient_data['patient'], patient_data['files'])
            
            self.conn.commit()
            return {
                'success': True,
                'patients_created': len(patient_studies),
                'records_processed': total,
                'message': f'Migrated {total} records into {len(patient_studies)} patient records'
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _insert_patient_record(self, first_entry: Dict[str, Any], all_files: List[Dict[str, Any]]) -> None:
        """Insert a patient and all their studies/files"""
        cursor = self.conn.cursor()
        
        patient_id = first_entry.get('patient_id')
        patient_name = first_entry.get('patient_name')
        dob = first_entry.get('dob')
        
        # Insert or update patient
        cursor.execute('''
            INSERT OR REPLACE INTO patients 
            (patient_id, patient_name, dob, patient_age, patient_sex, institution, 
             first_indexed, last_updated, total_studies)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            patient_id,
            patient_name,
            dob,
            first_entry.get('patient_age'),
            first_entry.get('patient_sex'),
            first_entry.get('institution'),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            len(set(f.get('study_uid') for f in all_files))
        ))
        
        # Group by study
        studies_by_uid = {}
        for file_entry in all_files:
            study_uid = file_entry.get('study_uid')
            if study_uid:
                if study_uid not in studies_by_uid:
                    studies_by_uid[study_uid] = []
                studies_by_uid[study_uid].append(file_entry)
        
        # Insert studies and files
        for study_uid, study_files in studies_by_uid.items():
            study_entry = study_files[0]
            
            cursor.execute('''
                INSERT OR REPLACE INTO studies
                (patient_id, study_uid, accession_number, study_date, study_time,
                 study_description, referring_physician, modality, body_part,
                 body_part_normalized, series_count, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient_id,
                study_uid,
                study_entry.get('accession_number'),
                study_entry.get('study_date'),
                study_entry.get('study_time'),
                study_entry.get('study_description'),
                study_entry.get('referring_physician'),
                study_entry.get('modality'),
                study_entry.get('body_part'),
                study_entry.get('body_part_normalized'),
                len(study_files),
                datetime.now().isoformat()
            ))
            
            # Insert files
            for file_entry in study_files:
                cursor.execute('''
                    INSERT OR REPLACE INTO files
                    (patient_id, study_uid, file_path, file_type, image_height, 
                     image_width, summary, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    patient_id,
                    study_uid,
                    file_entry.get('file_path'),
                    file_entry.get('file_type'),
                    file_entry.get('image_height'),
                    file_entry.get('image_width'),
                    file_entry.get('summary'),
                    file_entry.get('indexed_at')
                ))
                
                file_id = cursor.lastrowid
                
                # Insert keywords
                keywords = file_entry.get('relevance_keywords', [])
                if isinstance(keywords, str):
                    keywords = keywords.split()
                
                for keyword in keywords:
                    cursor.execute('''
                        INSERT INTO keywords (file_id, keyword)
                        VALUES (?, ?)
                    ''', (file_id, keyword.lower()))
    
    def search_patients(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for patients by name or ID"""
        cursor = self.conn.cursor()
        query_pattern = f'%{query}%'
        
        cursor.execute('''
            SELECT * FROM patients
            WHERE patient_id LIKE ? OR patient_name LIKE ?
            ORDER BY last_updated DESC
            LIMIT ?
        ''', (query_pattern, query_pattern, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_patient_studies(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all studies for a patient"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT * FROM studies
            WHERE patient_id = ?
            ORDER BY study_date DESC
        ''', (patient_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_patient_files(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all files for a patient"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT * FROM files
            WHERE patient_id = ?
            ORDER BY indexed_at DESC
        ''', (patient_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def search_studies(self, modality: Optional[str] = None, 
                      body_part: Optional[str] = None,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None,
                      limit: int = 100) -> List[Dict[str, Any]]:
        """Search studies by criteria"""
        cursor = self.conn.cursor()
        query = 'SELECT * FROM studies WHERE 1=1'
        params = []
        
        if modality:
            query += ' AND modality = ?'
            params.append(modality)
        if body_part:
            query += ' AND body_part_normalized = ?'
            params.append(body_part.lower())
        if start_date:
            query += ' AND study_date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND study_date <= ?'
            params.append(end_date)
        
        query += ' ORDER BY study_date DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def search_keywords(self, keywords: List[str], limit: int = 100) -> List[Dict[str, Any]]:
        """Search files by keywords"""
        cursor = self.conn.cursor()
        
        placeholders = ','.join('?' * len(keywords))
        keywords_lower = [k.lower() for k in keywords]
        
        cursor.execute(f'''
            SELECT DISTINCT f.* FROM files f
            JOIN keywords k ON f.id = k.file_id
            WHERE k.keyword IN ({placeholders})
            ORDER BY f.indexed_at DESC
            LIMIT ?
        ''', keywords_lower + [limit])
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM patients')
        patient_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM studies')
        study_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM files')
        file_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(DISTINCT modality) as count FROM studies')
        modality_count = cursor.fetchone()['count']
        
        cursor.execute('''
            SELECT modality, COUNT(*) as count
            FROM studies
            GROUP BY modality
            ORDER BY count DESC
        ''')
        modalities = {row['modality']: row['count'] for row in cursor.fetchall()}
        
        return {
            'patients': patient_count,
            'studies': study_count,
            'files': file_count,
            'modalities': modality_count,
            'modality_breakdown': modalities
        }
    
    def close(self) -> None:
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
