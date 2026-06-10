"""
Lightweight Health Graph SQLite Schema
Optimized for SDOH agent queries and fast metadata indexing
Database output location in vault folder: master_health_graph.db
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional

class HealthGraphSchema:
    """Lightweight SQLite schema for patient health data - deduped by series"""
    
    SCHEMA_VERSION = 2
    
    def __init__(self, db_path: str):
        """Initialize lightweight database"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # Performance optimizations
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=-64000")
        self.init_schema()
    
    def init_schema(self) -> None:
        """Create optimized schema for lightweight operations"""
        cursor = self.conn.cursor()
        
        # 1. PATIENTS - Core patient records (ONE entry per patient)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT UNIQUE NOT NULL,
                patient_name TEXT,
                dob TEXT,
                patient_age TEXT,
                patient_sex TEXT,
                institution TEXT,
                first_indexed TEXT DEFAULT CURRENT_TIMESTAMP,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                total_studies INTEGER DEFAULT 0,
                total_files INTEGER DEFAULT 0
            )
        ''')
        
        # 2. STUDIES - Clinical studies (ONE entry per unique study_uid)
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
                total_files INTEGER DEFAULT 0,
                indexed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
                UNIQUE(patient_id, study_uid)
            )
        ''')
        
        # 3. SERIES - Groups of images (ONE entry per unique series_uid - NO MORE DUPLICATE SLICES!)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS series (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                study_uid TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                series_uid TEXT UNIQUE,
                series_description TEXT,
                series_number TEXT,
                series_time TEXT,
                modality TEXT,
                manufacturer TEXT,
                file_count INTEGER DEFAULT 0,
                indexed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (study_uid) REFERENCES studies(study_uid),
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
                UNIQUE(study_uid, series_uid)
            )
        ''')
        
        # 4. FILES - Individual files (reference only, prevents duplicate slices)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                study_uid TEXT,
                series_uid TEXT,
                file_path TEXT UNIQUE NOT NULL,
                file_type TEXT,
                indexed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
                FOREIGN KEY (study_uid) REFERENCES studies(study_uid),
                FOREIGN KEY (series_uid) REFERENCES series(series_uid)
            )
        ''')
        
        # 5. METADATA - Fast query index for patient info
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                value_type TEXT,
                indexed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
                UNIQUE(patient_id, key)
            )
        ''')
        
        # 6. FINDINGS - Clinical findings extracted from reports/DICOM
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                study_uid TEXT,
                finding_type TEXT,
                finding_text TEXT,
                confidence REAL,
                extraction_date TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
                FOREIGN KEY (study_uid) REFERENCES studies(study_uid)
            )
        ''')
        
        # 7. SEARCH_INDEX - Fast keyword search
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                keyword TEXT NOT NULL,
                context TEXT,
                indexed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            )
        ''')
        
        # Create efficient indexes
        self._create_indexes(cursor)
        self.conn.commit()
    
    def _create_indexes(self, cursor) -> None:
        """Create lightweight indexes for fast queries"""
        indexes = [
            ("idx_patient_id", "patients", "patient_id"),
            ("idx_studies_patient", "studies", "patient_id"),
            ("idx_studies_date", "studies", "study_date"),
            ("idx_studies_modality", "studies", "modality"),
            ("idx_studies_uid", "studies", "study_uid"),
            ("idx_series_study", "series", "study_uid"),
            ("idx_series_uid", "series", "series_uid"),
            ("idx_files_patient", "files", "patient_id"),
            ("idx_files_study", "files", "study_uid"),
            ("idx_files_series", "files", "series_uid"),
            ("idx_metadata_patient", "metadata", "patient_id"),
            ("idx_metadata_key", "metadata", "key"),
            ("idx_findings_patient", "findings", "patient_id"),
            ("idx_search_keyword", "search_index", "keyword"),
        ]
        
        for index_name, table, column in indexes:
            try:
                cursor.execute(f'''
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON {table}({column})
                ''')
            except:
                pass
    
    def insert_patient(self, patient_id: str, patient_data: Dict[str, Any]) -> int:
        """Insert or update patient record"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO patients
            (patient_id, patient_name, dob, patient_age, patient_sex, institution, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            patient_id,
            patient_data.get('patient_name'),
            patient_data.get('dob'),
            patient_data.get('patient_age'),
            patient_data.get('patient_sex'),
            patient_data.get('institution'),
            datetime.now().isoformat()
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_study(self, study_data: Dict[str, Any]) -> int:
        """Insert or update study record (ONE per unique study_uid)"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO studies
            (patient_id, study_uid, accession_number, study_date, study_time,
             study_description, referring_physician, modality, body_part,
             body_part_normalized, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            study_data.get('patient_id'),
            study_data.get('study_uid'),
            study_data.get('accession_number'),
            study_data.get('study_date'),
            study_data.get('study_time'),
            study_data.get('study_description'),
            study_data.get('referring_physician'),
            study_data.get('modality'),
            study_data.get('body_part'),
            study_data.get('body_part_normalized'),
            datetime.now().isoformat()
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_series(self, series_data: Dict[str, Any]) -> int:
        """Insert series record (ONE per unique series_uid - groups CT slices)"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO series
            (study_uid, patient_id, series_uid, series_description, series_number,
             series_time, modality, manufacturer, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            series_data.get('study_uid'),
            series_data.get('patient_id'),
            series_data.get('series_uid'),
            series_data.get('series_description'),
            series_data.get('series_number'),
            series_data.get('series_time'),
            series_data.get('modality'),
            series_data.get('manufacturer'),
            datetime.now().isoformat()
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_file(self, file_data: Dict[str, Any]) -> int:
        """Insert file reference (multiple per series, no duplicates by UNIQUE constraint)"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO files
            (patient_id, study_uid, series_uid, file_path, file_type, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            file_data.get('patient_id'),
            file_data.get('study_uid'),
            file_data.get('series_uid'),
            file_data.get('file_path'),
            file_data.get('file_type'),
            datetime.now().isoformat()
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_metadata(self, patient_id: str, key: str, value: Any, value_type: str = 'text') -> None:
        """Insert searchable metadata"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO metadata
            (patient_id, key, value, value_type, indexed_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            patient_id,
            key,
            str(value),
            value_type,
            datetime.now().isoformat()
        ))
        
        self.conn.commit()
    
    def insert_finding(self, finding_data: Dict[str, Any]) -> int:
        """Insert clinical finding extracted from DICOM/reports"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO findings
            (patient_id, study_uid, finding_type, finding_text, confidence, extraction_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            finding_data.get('patient_id'),
            finding_data.get('study_uid'),
            finding_data.get('finding_type'),
            finding_data.get('finding_text'),
            finding_data.get('confidence', 0.0),
            datetime.now().isoformat()
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def add_search_keyword(self, patient_id: str, keyword: str, context: str = '') -> None:
        """Add searchable keyword for quick SDOH queries"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO search_index
            (patient_id, keyword, context, indexed_at)
            VALUES (?, ?, ?, ?)
        ''', (
            patient_id,
            keyword.lower(),
            context,
            datetime.now().isoformat()
        ))
        
        self.conn.commit()
    
    # =====================================================================
    # QUERY METHODS - For SDOH Agent
    # =====================================================================
    
    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient record"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM patients WHERE patient_id = ?', (patient_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_patient_studies(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all studies for patient"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM studies WHERE patient_id = ?
            ORDER BY study_date DESC
        ''', (patient_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_patient_series(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all series for patient (deduped!)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT s.* FROM series s
            JOIN studies st ON s.study_uid = st.study_uid
            WHERE st.patient_id = ?
            ORDER BY s.indexed_at DESC
        ''', (patient_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def search_patients(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fast patient search by name or ID"""
        cursor = self.conn.cursor()
        q = f'%{query}%'
        cursor.execute('''
            SELECT * FROM patients
            WHERE patient_id LIKE ? OR patient_name LIKE ?
            ORDER BY last_updated DESC
            LIMIT ?
        ''', (q, q, limit))
        return [dict(row) for row in cursor.fetchall()]
    
    def search_studies(self, modality: str = None, body_part: str = None,
                      start_date: str = None, end_date: str = None,
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
    
    def search_by_keyword(self, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search patients by keyword"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT p.* FROM patients p
            JOIN search_index si ON p.patient_id = si.patient_id
            WHERE si.keyword LIKE ?
            ORDER BY p.last_updated DESC
            LIMIT ?
        ''', (f'%{keyword.lower()}%', limit))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_metadata(self, patient_id: str, key: str = None) -> List[Dict[str, Any]]:
        """Get patient metadata"""
        cursor = self.conn.cursor()
        if key:
            cursor.execute('''
                SELECT * FROM metadata WHERE patient_id = ? AND key = ?
            ''', (patient_id, key))
        else:
            cursor.execute('''
                SELECT * FROM metadata WHERE patient_id = ?
            ''', (patient_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_findings(self, patient_id: str, study_uid: str = None) -> List[Dict[str, Any]]:
        """Get clinical findings for patient"""
        cursor = self.conn.cursor()
        if study_uid:
            cursor.execute('''
                SELECT * FROM findings WHERE patient_id = ? AND study_uid = ?
                ORDER BY extraction_date DESC
            ''', (patient_id, study_uid))
        else:
            cursor.execute('''
                SELECT * FROM findings WHERE patient_id = ?
                ORDER BY extraction_date DESC
            ''', (patient_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM patients')
        patients = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM studies')
        studies = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM series')
        series = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM files')
        files = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(DISTINCT modality) as count FROM studies')
        modalities = cursor.fetchone()['count']
        
        return {
            'patients': patients,
            'studies': studies,
            'series': series,
            'files': files,
            'modalities': modalities
        }
    
    def update_patient_counts(self, patient_id: str) -> None:
        """Update patient study/file counts"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            UPDATE patients SET total_studies = (
                SELECT COUNT(DISTINCT study_uid) FROM studies WHERE patient_id = ?
            ), total_files = (
                SELECT COUNT(*) FROM files WHERE patient_id = ?
            ), last_updated = ? WHERE patient_id = ?
        ''', (patient_id, patient_id, datetime.now().isoformat(), patient_id))
        
        self.conn.commit()
    
    def close(self) -> None:
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
