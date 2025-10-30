"""
Database Operations Service
Handles all database interactions for the NAS integration system
"""

import sqlite3
import logging
import threading
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Database lock for thread safety
database_lock = threading.Lock()

def get_database_connection():
    """Get a thread-safe database connection"""
    try:
        with database_lock:
            # Prefer the canonical metadata DB used across the backend (pacs_metadata.db).
            # Fall back to the legacy per-service nas_patients.db if the helper is unavailable.
            try:
                from ..metadata_db import get_metadata_db_path
                db_path = Path(get_metadata_db_path())
            except Exception:
                db_path = Path(__file__).parent.parent / 'nas_patients.db'

            logger.debug(f"Opening NAS database at: {db_path}")
            conn = sqlite3.connect(str(db_path), timeout=30.0)
            # If the lightweight pacs_metadata.db uses 'patient_studies' only (no 'patients' table),
            # create a TEMP VIEW named 'patients' for compatibility with older queries.
            try:
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='patient_studies'")
                if cur.fetchone():
                    # If patient_studies exists, ensure we have a compatible patients view/table
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='patients'")
                    if cur.fetchone():
                        # Check if patients table has the required columns for search
                        cur.execute("PRAGMA table_info(patients)")
                        columns = [row[1] for row in cur.fetchall()]
                        required_columns = ['first_study_date', 'last_study_date', 'last_indexed', 'total_studies', 'total_instances']
                        if not all(col in columns for col in required_columns):
                            logger.info("Dropping incompatible patients table to create VIEW")
                            cur.execute("DROP TABLE patients")
                    
                    # Create the VIEW if it doesn't exist
                    cur.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='patients'")
                    if cur.fetchone():
                        logger.info("Dropping existing patients VIEW to recreate with date formatting")
                        cur.execute("DROP VIEW patients")
                    
                    logger.info("Creating VIEW 'patients' from 'patient_studies' for compatibility")
                    # Create a proper aggregated view that matches the expected patients table schema
                    # Use REPLACE(study_date, '-', '') to tolerate mixed formats (YYYYMMDD or YYYY-MM-DD)
                    cur.execute("""
                        CREATE VIEW patients AS
                        SELECT
                            patient_id,
                            MAX(patient_name) AS patient_name,
                            MAX(patient_birth_date) AS birth_date,
                            MAX(patient_sex) AS sex,
                            '' AS age,
                            MAX(folder_path) AS folder_path,
                            COUNT(*) AS total_studies,
                            0 AS total_series,
                            SUM(dicom_file_count) AS total_instances,
                            MIN(substr(TRIM(REPLACE(study_date,'-','')),1,4)||'-'||substr(TRIM(REPLACE(study_date,'-','')),5,2)||'-'||substr(TRIM(REPLACE(study_date,'-','')),7,2)) AS first_study_date,
                            MAX(substr(TRIM(REPLACE(study_date,'-','')),1,4)||'-'||substr(TRIM(REPLACE(study_date,'-','')),5,2)||'-'||substr(TRIM(REPLACE(study_date,'-','')),7,2)) AS last_study_date,
                            MAX(last_indexed) AS last_indexed,
                            MAX(last_indexed) AS created_at
                        FROM patient_studies
                        GROUP BY patient_id
                    """)
                    conn.commit()
            except Exception as e:
                # If anything fails here, continue — callers will handle missing tables
                logger.debug(f'Could not create compatibility view for patients: {e}')
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

def initialize_database():
    """Initialize the NAS patients database with all required tables"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Patients table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT UNIQUE NOT NULL,
            patient_name TEXT NOT NULL,
            birth_date TEXT,
            sex TEXT,
            age TEXT,
            folder_path TEXT NOT NULL,
            total_studies INTEGER DEFAULT 0,
            total_series INTEGER DEFAULT 0,
            total_instances INTEGER DEFAULT 0,
            first_study_date TEXT,
            last_study_date TEXT,
            last_indexed DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Medical shares table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS medical_shares (
            share_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            patient_name TEXT,
            access_code TEXT NOT NULL,
            doctor_name TEXT,
            doctor_email TEXT,
            recipient_type TEXT,
            created_date TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            message TEXT,
            download_count INTEGER DEFAULT 0,
            max_downloads INTEGER DEFAULT 10,
            allow_download BOOLEAN DEFAULT 1,
            is_active BOOLEAN DEFAULT 1,
            last_accessed TEXT,
            orthanc_study_uid TEXT
        )
        ''')
        
        # Indexing progress table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS indexing_progress (
            id INTEGER PRIMARY KEY,
            session_id TEXT UNIQUE,
            total_folders INTEGER,
            processed_folders INTEGER,
            current_folder TEXT,
            start_time TEXT,
            last_update TEXT,
            status TEXT DEFAULT 'running',
            errors_count INTEGER DEFAULT 0
        )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patient_name ON patients(patient_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patient_id ON patients(patient_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_indexed ON patients(last_indexed)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_share_expiry ON medical_shares(expiry_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_share_active ON medical_shares(is_active)')
        
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

def search_patients_in_database(search_params):
    """Search for patients in the database"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        patient_id = search_params.get('patient_id', '').strip()
        patient_name = search_params.get('patient_name', '').strip()
        study_date = search_params.get('study_date', '').strip()
        modality = search_params.get('modality', '').strip()
        query = search_params.get('query', '').strip()
        
        # Build the query dynamically
        conditions = []
        params = []
        
        # If a general `query` is provided, search both id and name with a single OR condition
        if query:
            qp = f'%{query}%'
            conditions.append("(patient_id LIKE ? OR patient_name LIKE ?)")
            params.extend([qp, qp])
        else:
            # If both fields provided and identical, treat as a single general query (OR)
            if patient_id and patient_name and patient_id == patient_name:
                qp = f'%{patient_id}%'
                conditions.append("(patient_id LIKE ? OR patient_name LIKE ?)")
                params.extend([qp, qp])
            else:
                if patient_id:
                    conditions.append("(patient_id LIKE ?)")
                    params.append(f'%{patient_id}%')

                if patient_name:
                    conditions.append("(patient_name LIKE ?)")
                    params.append(f'%{patient_name}%')
        
        if study_date:
            conditions.append("(first_study_date LIKE ? OR last_study_date LIKE ?)")
            params.extend([f'%{study_date}%', f'%{study_date}%'])
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f'''
        SELECT * FROM patients 
        WHERE ({where_clause})
        ORDER BY last_study_date DESC, last_indexed DESC 
        LIMIT 100
        '''
        
        logger.info(f"🔍 Executing query: {query}")
        logger.info(f"🔍 Query params: {params}")
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        logger.info(f"🔍 Query returned {len(rows)} rows")
        
        patients = []
        for row in rows:
            patient = {
                'patient_id': row['patient_id'],
                'patient_name': row['patient_name'],
                'patient_birth_date': row['birth_date'] or '',
                'patient_sex': row['sex'] or '',
                'age': row['age'] or '',
                'folder_path': row['folder_path'],
                'total_studies': row['total_studies'],
                'total_series': row['total_series'],
                'total_instances': row['total_instances'],
                'first_study_date': row['first_study_date'] or '',
                'last_study_date': row['last_study_date'] or '',
                'studies': [],  # Will be populated if needed
                # Compatibility fields used by UI
                'name': row['patient_name'],
                # Provide study_date in compact YYYYMMDD for the UI formatter
                'study_date': (row['first_study_date'] or row['last_study_date'] or '').replace('-', ''),
                'source': 'nas_index',
                'file_count': row['total_instances']
            }
            patients.append(patient)
        
        conn.close()
        logger.info(f"✅ NAS index found {len(patients)} patients")
        return patients
        
    except Exception as e:
        logger.error(f"Database search error: {e}")
        return []

def add_patient_to_database(patient_data):
    """Add a new patient to the database"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO patients 
        (patient_id, patient_name, birth_date, sex, age, folder_path, 
         total_studies, total_series, total_instances, first_study_date, last_study_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            patient_data.get('patient_id', ''),
            patient_data.get('patient_name', ''),
            patient_data.get('birth_date', ''),
            patient_data.get('sex', ''),
            patient_data.get('age', ''),
            patient_data.get('folder_path', ''),
            patient_data.get('total_studies', 0),
            patient_data.get('total_series', 0),
            patient_data.get('total_instances', 0),
            patient_data.get('first_study_date', ''),
            patient_data.get('last_study_date', '')
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Added patient to database: {patient_data.get('patient_name', 'Unknown')}")
        
    except Exception as e:
        logger.error(f"Error adding patient to database: {e}")
        raise

def get_indexing_status():
    """Get the current indexing status using lightweight schema"""
    try:
        # Import the correct indexing status from the indexing routes
        from routes.indexing import indexing_state
        import sqlite3
        
        # Check canonical metadata DB (prefer orthanc-index when available)
        db_path = None
        try:
            # Try to import the canonical metadata DB helper
            from ..metadata_db import get_metadata_db_path
            db_path = get_metadata_db_path()
        except Exception:
            try:
                from metadata_db import get_metadata_db_path
                db_path = get_metadata_db_path()
            except Exception:
                db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'nas_patient_index.db'))
        total_patients = 0

        if os.path.exists(db_path):
            try:
                with sqlite3.connect(db_path, timeout=5) as conn:
                    cursor = conn.cursor()
                    # Check if we have the new lightweight schema
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='patient_studies'")
                    if cursor.fetchone():
                        cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_studies")
                        count_result = cursor.fetchone()
                        if count_result:
                            total_patients = count_result[0]
            except Exception as e:
                logger.debug(f"Could not get patient count: {e}")
        
        # Use the current indexing state
        is_running = indexing_state.get('state') == 'indexing'
        progress = indexing_state.get('progress', 0)
        details = indexing_state.get('details', 'No indexing in progress')
        
        status = {
            'total_patients': total_patients,
            'is_running': is_running,
            'progress': progress,
            'current_folder': details,
            'errors_count': 0,
            'state': 'running' if is_running else 'idle',
            'details': details
        }
        
        logger.info(f"📊 Database service status: {status}")
        return status
        
    except Exception as e:
        logger.error(f"Error getting indexing status: {e}")
        return {
            'total_patients': 0,
            'is_running': False,
            'progress': 0,
            'current_folder': '',
            'errors_count': 0
        }

def create_medical_share(share_data):
    """Create a new medical share record"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO medical_shares 
        (share_id, patient_id, patient_name, access_code, doctor_name, doctor_email, 
         recipient_type, created_date, expiry_date, message, allow_download, max_downloads, orthanc_study_uid)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            share_data['share_id'],
            share_data['patient_id'],
            share_data.get('patient_name', ''),
            share_data['access_code'],
            share_data.get('doctor_name', ''),
            share_data.get('doctor_email', ''),
            share_data.get('recipient_type', 'doctor'),
            share_data['created_date'],
            share_data['expiry_date'],
            share_data.get('message', ''),
            share_data.get('allow_download', True),
            share_data.get('max_downloads', 10),
            share_data.get('orthanc_study_uid', '')
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Created medical share: {share_data['share_id']}")
        
    except Exception as e:
        logger.error(f"Error creating medical share: {e}")
        raise

def get_medical_share(share_id):
    """Get medical share by ID"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM medical_shares WHERE share_id = ? AND is_active = 1', (share_id,))
        share = cursor.fetchone()
        
        conn.close()
        
        if share:
            return dict(share)
        return None
        
    except Exception as e:
        logger.error(f"Error getting medical share: {e}")
        return None

def update_share_access(share_id):
    """Update share access timestamp"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE medical_shares 
        SET last_accessed = ? 
        WHERE share_id = ?
        ''', (datetime.now().isoformat(), share_id))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error updating share access: {e}")
        # Swallow the exception to avoid bringing down the service; caller can re-query
        return False
