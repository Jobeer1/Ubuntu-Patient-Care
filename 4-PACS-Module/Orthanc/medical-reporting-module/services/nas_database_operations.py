"""
NAS Database Operations Service
Handles all database connections and patient indexing operations
"""

import sqlite3
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Database paths - Updated to use correct patient database
NAS_DB_PATH = r"\\TRUENAS\Medical_Images\medical_index.db"
try:
    from backend.metadata_db import get_metadata_db_path
    LOCAL_DB_PATH = get_metadata_db_path()
except Exception:
    LOCAL_DB_PATH = r"C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc\orthanc-source\NASIntegration\nas_patient_index.db"

def get_database_connection(use_nas=False):
    """Get database connection with fallback to local"""
    try:
        if use_nas and os.path.exists(NAS_DB_PATH):
            conn = sqlite3.connect(NAS_DB_PATH, timeout=30)
            logger.info("🗄️ Connected to NAS database")
            return conn
        else:
            conn = sqlite3.connect(LOCAL_DB_PATH, timeout=30)
            logger.info("🗄️ Connected to local database")
            return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

def search_patients_in_database(search_terms, limit=50):
    """Search for patients in the database"""
    try:
        with get_database_connection(use_nas=True) as conn:
            cursor = conn.cursor()
            
            # Build search query
            where_conditions = []
            params = []
            
            for field, value in search_terms.items():
                if value and field in ['patient_id', 'patient_name', 'study_date']:
                    where_conditions.append(f"{field} LIKE ?")
                    params.append(f"%{value}%")
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            query = f"""
                SELECT DISTINCT patient_id, patient_name, study_date, folder_path, 
                       COUNT(*) as file_count
                FROM patient_studies 
                WHERE {where_clause}
                GROUP BY patient_id, study_date
                ORDER BY study_date DESC
                LIMIT ?
            """
            
            params.append(limit)
            cursor.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'patient_id': row[0],
                    'patient_name': row[1],
                    'study_date': row[2],
                    'folder_path': row[3],
                    'file_count': row[4],
                    'source': 'database'
                })
            
            logger.info(f"🔍 Found {len(results)} patients in database")
            return results
            
    except Exception as e:
        logger.error(f"Database search error: {e}")
        return []

def get_medical_shares():
    """Get all medical sharing records"""
    try:
        with get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT share_id, patient_info, access_code, created_at, expires_at, 
                       accessed_at, access_count, orthanc_study_uid
                FROM medical_shares
                ORDER BY created_at DESC
            """)
            
            shares = []
            for row in cursor.fetchall():
                shares.append({
                    'share_id': row[0],
                    'patient_info': row[1],
                    'access_code': row[2],
                    'created_at': row[3],
                    'expires_at': row[4],
                    'accessed_at': row[5],
                    'access_count': row[6],
                    'orthanc_study_uid': row[7]
                })
            
            return shares
            
    except Exception as e:
        logger.error(f"Error getting medical shares: {e}")
        return []

def create_medical_share(share_data):
    """Create a new medical sharing record"""
    try:
        with get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO medical_shares 
                (share_id, patient_info, access_code, created_at, expires_at, orthanc_study_uid)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                share_data['share_id'],
                share_data['patient_info'],
                share_data['access_code'],
                share_data['created_at'],
                share_data['expires_at'],
                share_data.get('orthanc_study_uid')
            ))
            conn.commit()
            logger.info(f"📤 Created medical share: {share_data['share_id']}")
            return True
            
    except Exception as e:
        logger.error(f"Error creating medical share: {e}")
        return False

def update_share_access(share_id):
    """Update share access tracking"""
    try:
        with get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE medical_shares 
                SET accessed_at = ?, access_count = access_count + 1
                WHERE share_id = ?
            """, (datetime.now().isoformat(), share_id))
            conn.commit()
            return True
            
    except Exception as e:
        logger.error(f"Error updating share access: {e}")
        return False

def get_indexing_status():
    """Get current patient indexing status"""
    try:
        with get_database_connection(use_nas=True) as conn:
            cursor = conn.cursor()
            
            # Get total patients
            cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_studies")
            total_patients = cursor.fetchone()[0] or 0
            
            # Get last update time
            cursor.execute("SELECT MAX(created_at) FROM patient_studies")
            last_update = cursor.fetchone()[0]
            
            return {
                'total_patients': total_patients,
                'last_update': last_update,
                'is_running': False,
                'progress': 100 if total_patients > 0 else 0
            }
            
    except Exception as e:
        logger.error(f"Error getting indexing status: {e}")
        return {
            'total_patients': 0,
            'is_running': False,
            'progress': 0,
            'error': str(e)
        }

def initialize_medical_shares_table():
    """Initialize the medical shares table if it doesn't exist"""
    try:
        with get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS medical_shares (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    share_id TEXT UNIQUE NOT NULL,
                    patient_info TEXT NOT NULL,
                    access_code TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    accessed_at TEXT,
                    access_count INTEGER DEFAULT 0,
                    orthanc_study_uid TEXT
                )
            """)
            conn.commit()
            logger.info("📊 Medical shares table initialized")
            
    except Exception as e:
        logger.error(f"Error initializing medical shares table: {e}")

# Initialize table on import
initialize_medical_shares_table()