"""
PACS Database Connector
Connects MCP server to PACS metadata database for access control

This module provides read-only access to the PACS database to:
- Query patient information
- Retrieve study data
- Verify patient existence
- Search for patients

Database Schema (PACS):
- patient_studies: Main patient and study information
- studies: Detailed study information
- series: Series within studies
- instances: Individual DICOM instances
"""
import sqlite3
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class PACSConnector:
    """
    PACS Database Connector
    
    Provides read-only access to PACS metadata database for
    patient information and study queries.
    """
    
    def __init__(self, pacs_db_path: str):
        """
        Initialize PACS connector
        
        Args:
            pacs_db_path: Path to PACS metadata database
        """
        self.pacs_db_path = pacs_db_path
        self._verify_database()
    
    def _verify_database(self):
        """Verify PACS database exists and is accessible"""
        db_path = Path(self.pacs_db_path)
        if not db_path.exists():
            raise FileNotFoundError(f"PACS database not found: {self.pacs_db_path}")
        
        # Test connection
        try:
            conn = self.get_connection()
            conn.close()
            logger.info(f"✅ PACS database connected: {self.pacs_db_path}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to PACS database: {e}")
            raise
    
    def get_connection(self) -> sqlite3.Connection:
        """
        Get read-only connection to PACS database
        
        Returns:
            sqlite3.Connection: Database connection
        
        Raises:
            sqlite3.Error: If connection fails
        """
        try:
            # Open in read-only mode
            conn = sqlite3.connect(f"file:{self.pacs_db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to PACS database: {e}")
            raise
    
    def get_patient_studies(self, patient_id: str) -> List[Dict]:
        """
        Get all studies for a specific patient
        
        Args:
            patient_id: Patient ID or MRN
        
        Returns:
            List of study dictionaries with patient and study information
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    id,
                    patient_id,
                    patient_name,
                    patient_birth_date,
                    patient_sex,
                    study_date,
                    study_description,
                    modality,
                    folder_path,
                    dicom_file_count,
                    folder_size_mb,
                    last_indexed
                FROM patient_studies 
                WHERE patient_id = ?
                ORDER BY study_date DESC, last_indexed DESC
            """, (patient_id,))
            
            studies = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"Found {len(studies)} studies for patient {patient_id}")
            return studies
            
        except Exception as e:
            logger.error(f"Error fetching studies for patient {patient_id}: {e}")
            return []
        finally:
            conn.close()
    
    def get_patient_info(self, patient_id: str) -> Optional[Dict]:
        """
        Get patient information
        
        Args:
            patient_id: Patient ID or MRN
        
        Returns:
            Dictionary with patient information or None if not found
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    patient_id,
                    patient_name,
                    patient_birth_date,
                    patient_sex,
                    COUNT(*) as study_count,
                    MAX(study_date) as last_study_date,
                    SUM(dicom_file_count) as total_images,
                    SUM(folder_size_mb) as total_size_mb
                FROM patient_studies 
                WHERE patient_id = ?
                GROUP BY patient_id, patient_name, patient_birth_date, patient_sex
                LIMIT 1
            """, (patient_id,))
            
            row = cursor.fetchone()
            if row:
                patient_info = dict(row)
                logger.debug(f"Found patient info for {patient_id}")
                return patient_info
            else:
                logger.debug(f"Patient not found: {patient_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching patient info for {patient_id}: {e}")
            return None
        finally:
            conn.close()
    
    def search_patients(self, search_term: str, limit: int = 50) -> List[Dict]:
        """
        Search patients by name, ID, or MRN
        
        Args:
            search_term: Search query
            limit: Maximum number of results (default: 50)
        
        Returns:
            List of patient dictionaries
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            search_pattern = f"%{search_term}%"
            
            cursor.execute("""
                SELECT DISTINCT
                    patient_id,
                    patient_name,
                    patient_birth_date,
                    patient_sex,
                    COUNT(*) as study_count,
                    MAX(study_date) as last_study_date
                FROM patient_studies
                WHERE patient_name LIKE ? 
                   OR patient_id LIKE ?
                GROUP BY patient_id, patient_name, patient_birth_date, patient_sex
                ORDER BY last_study_date DESC
                LIMIT ?
            """, (search_pattern, search_pattern, limit))
            
            patients = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"Found {len(patients)} patients matching '{search_term}'")
            return patients
            
        except Exception as e:
            logger.error(f"Error searching patients with term '{search_term}': {e}")
            return []
        finally:
            conn.close()
    
    def verify_patient_exists(self, patient_id: str) -> bool:
        """
        Verify patient exists in PACS
        
        Args:
            patient_id: Patient ID or MRN
        
        Returns:
            True if patient exists, False otherwise
        """
        info = self.get_patient_info(patient_id)
        return info is not None
    
    def get_study_details(self, study_instance_uid: str) -> Optional[Dict]:
        """
        Get detailed study information
        
        Args:
            study_instance_uid: Study Instance UID
        
        Returns:
            Dictionary with study details or None if not found
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    study_instance_uid,
                    patient_id,
                    study_date,
                    study_time,
                    study_description,
                    modality,
                    accession_number,
                    study_id,
                    folder_path
                FROM studies 
                WHERE study_instance_uid = ?
                LIMIT 1
            """, (study_instance_uid,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"Error fetching study details for {study_instance_uid}: {e}")
            return None
        finally:
            conn.close()
    
    def get_patient_list(self, offset: int = 0, limit: int = 100) -> Tuple[List[Dict], int]:
        """
        Get paginated list of all patients
        
        Args:
            offset: Starting offset for pagination
            limit: Number of results per page
        
        Returns:
            Tuple of (patient list, total count)
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_studies")
            total_count = cursor.fetchone()[0]
            
            # Get paginated results
            cursor.execute("""
                SELECT DISTINCT
                    patient_id,
                    patient_name,
                    patient_birth_date,
                    patient_sex,
                    COUNT(*) as study_count,
                    MAX(study_date) as last_study_date
                FROM patient_studies
                GROUP BY patient_id, patient_name, patient_birth_date, patient_sex
                ORDER BY last_study_date DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            patients = [dict(row) for row in cursor.fetchall()]
            return patients, total_count
            
        except Exception as e:
            logger.error(f"Error fetching patient list: {e}")
            return [], 0
        finally:
            conn.close()
    
    def get_database_stats(self) -> Dict:
        """
        Get PACS database statistics
        
        Returns:
            Dictionary with database statistics
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            stats = {}
            
            # Patient count
            cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_studies")
            stats['total_patients'] = cursor.fetchone()[0]
            
            # Study count
            cursor.execute("SELECT COUNT(*) FROM studies")
            stats['total_studies'] = cursor.fetchone()[0]
            
            # Series count
            cursor.execute("SELECT COUNT(*) FROM series")
            stats['total_series'] = cursor.fetchone()[0]
            
            # Instance count
            cursor.execute("SELECT COUNT(*) FROM instances")
            stats['total_instances'] = cursor.fetchone()[0]
            
            # Total size
            cursor.execute("SELECT SUM(folder_size_mb) FROM patient_studies")
            stats['total_size_mb'] = cursor.fetchone()[0] or 0
            
            # Last indexed
            cursor.execute("SELECT MAX(last_indexed) FROM patient_studies")
            stats['last_indexed'] = cursor.fetchone()[0]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error fetching database stats: {e}")
            return {}
        finally:
            conn.close()


# Singleton instance
_pacs_connector = None

def get_pacs_connector(pacs_db_path: str = None) -> PACSConnector:
    """
    Get or create PACS connector singleton
    
    Args:
        pacs_db_path: Path to PACS database (required on first call)
    
    Returns:
        PACSConnector instance
    """
    global _pacs_connector
    
    if _pacs_connector is None:
        if pacs_db_path is None:
            # Try to get from config
            try:
                from app.database import get_db
                db = get_db()
                cursor = db.execute(
                    "SELECT config_value FROM pacs_connection_config WHERE config_key = 'pacs_db_path'"
                )
                row = cursor.fetchone()
                if row:
                    pacs_db_path = row[0]
            except:
                pass
        
        if pacs_db_path is None:
            raise ValueError("PACS database path not provided and not found in config")
        
        _pacs_connector = PACSConnector(pacs_db_path)
    
    return _pacs_connector
