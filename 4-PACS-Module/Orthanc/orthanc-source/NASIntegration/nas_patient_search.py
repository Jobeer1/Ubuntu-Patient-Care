#!/usr/bin/env python3
"""
Enhanced NAS Patient Search using SQLite Index
Integrates with Ubuntu Patient Care NAS indexing system
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

logger = logging.getLogger(__name__)

class NASPatientSearch:
    """
    Fast patient search using pre-built SQLite index
    Provides PACS-like functionality without physical file import
    """
    
    def __init__(self, index_db_path: str = None):
        # Prefer explicit path, then metadata helper, then legacy filename
        if index_db_path:
            self.index_db_path = index_db_path
        else:
            try:
                from backend.metadata_db import get_metadata_db_path
                self.index_db_path = get_metadata_db_path()
            except Exception:
                try:
                    from metadata_db import get_metadata_db_path
                    self.index_db_path = get_metadata_db_path()
                except Exception:
                    self.index_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'nas_patient_index.db'))
        self.available = self.check_index_availability()
    
    def check_index_availability(self) -> bool:
        """Check if the patient index database exists and is usable"""
        try:
            if not Path(self.index_db_path).exists():
                logger.warning(f"Patient index database not found: {self.index_db_path}")
                return False
            
            with sqlite3.connect(self.index_db_path) as conn:
                cursor = conn.cursor()
                # Check both old and new table structures
                try:
                    cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_studies")
                    patient_count = cursor.fetchone()[0]
                    logger.info(f"✅ Patient index available with {patient_count} unique patients")
                except:
                    # Fallback to old table if new one doesn't exist
                    cursor.execute("SELECT COUNT(*) FROM patients")
                    patient_count = cursor.fetchone()[0]
                    logger.info(f"✅ Patient index available with {patient_count} patients (legacy)")
                
                return patient_count > 0
                
        except Exception as e:
            logger.error(f"Error checking index availability: {e}")
            return False
    
    def search_patients(self, patient_id="", patient_name="", study_date="", modality="", limit=50) -> Dict:
        """
        Search patients using the NAS index
        Returns results in format compatible with existing frontend
        """
        if not self.available:
            logger.warning("Patient index not available, returning empty results")
            return {
                'success': False,
                'patients': [],
                'total_found': 0,
                'message': 'Patient index not available. Please run indexing first.',
                'error': 'index_not_available'
            }
        
        try:
            with sqlite3.connect(self.index_db_path) as conn:
                cursor = conn.cursor()
                
                # Build search conditions
                where_conditions = []
                params = []
                
                if patient_id:
                    where_conditions.append("(p.patient_id LIKE ? OR p.patient_name LIKE ?)")
                    params.extend([f"%{patient_id}%", f"%{patient_id}%"])
                
                if patient_name:
                    where_conditions.append("p.patient_name LIKE ?")
                    params.append(f"%{patient_name}%")
                
                if study_date:
                    # Handle different date formats
                    clean_date = study_date.replace('-', '').replace('/', '')
                    where_conditions.append("s.study_date LIKE ?")
                    params.append(f"%{clean_date}%")
                
                if modality:
                    where_conditions.append("s.modality = ?")
                    params.append(modality)
                
                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
                
                # Main query to get patients with their studies
                query = f'''
                    SELECT DISTINCT
                        p.patient_id,
                        p.patient_name,
                        p.patient_birth_date,
                        p.patient_sex,
                        p.patient_age,
                        p.folder_path as patient_folder,
                        COUNT(DISTINCT s.study_instance_uid) as total_studies,
                        COUNT(DISTINCT ser.series_instance_uid) as total_series,
                        COUNT(DISTINCT f.file_id) as total_instances,
                        MIN(s.study_date) as first_study_date,
                        MAX(s.study_date) as last_study_date
                    FROM patients p
                    LEFT JOIN studies s ON p.patient_id = s.patient_id
                    LEFT JOIN series ser ON s.study_instance_uid = ser.study_instance_uid
                    LEFT JOIN dicom_files f ON ser.series_instance_uid = f.series_instance_uid
                    WHERE {where_clause}
                    GROUP BY p.patient_id, p.patient_name, p.patient_birth_date, p.patient_sex
                    ORDER BY p.patient_name
                    LIMIT ?
                '''
                
                params.append(limit)
                cursor.execute(query, params)
                
                # Convert results to frontend format
                patients = []
                for row in cursor.fetchall():
                    patient_id, patient_name, birth_date, sex, age, folder_path, \
                    study_count, series_count, instance_count, first_study, last_study = row
                    
                    # Get studies for this patient
                    studies = self.get_patient_studies(cursor, patient_id, modality)
                    
                    # Format patient data
                    patient_data = {
                        'patient_id': patient_id or 'N/A',
                        'name': patient_name or 'Unknown',
                        'birth_date': self.format_date(birth_date),
                        'sex': sex or 'U',
                        'age': age or '',
                        'studies': studies,
                        'total_studies': study_count or 0,
                        'total_series': series_count or 0,
                        'total_instances': instance_count or 0,
                        'first_study_date': self.format_date(first_study),
                        'last_study_date': self.format_date(last_study),
                        'folder_path': folder_path or '',
                        'source': 'NAS Index'
                    }
                    
                    patients.append(patient_data)
                
                return {
                    'success': True,
                    'patients': patients,
                    'total_found': len(patients),
                    'search_criteria': {
                        'patient_id': patient_id,
                        'patient_name': patient_name,
                        'study_date': study_date,
                        'modality': modality
                    },
                    'message': f'Found {len(patients)} patient(s) in NAS index',
                    'source': 'nas_index'
                }
                
        except Exception as e:
            logger.error(f"Error searching patients: {e}")
            return {
                'success': False,
                'patients': [],
                'total_found': 0,
                'message': f'Search failed: {str(e)}',
                'error': str(e)
            }
    
    def get_patient_studies(self, cursor: sqlite3.Cursor, patient_id: str, modality_filter="") -> List[Dict]:
        """Get studies for a specific patient"""
        try:
            where_clause = "patient_id = ?"
            params = [patient_id]
            
            if modality_filter:
                where_clause += " AND modality = ?"
                params.append(modality_filter)
            
            query = f'''
                SELECT 
                    study_instance_uid,
                    study_id,
                    study_date,
                    study_time,
                    study_description,
                    modality,
                    accession_number,
                    referring_physician,
                    series_count,
                    instance_count,
                    folder_path
                FROM studies
                WHERE {where_clause}
                ORDER BY study_date DESC
            '''
            
            cursor.execute(query, params)
            
            studies = []
            for row in cursor.fetchall():
                study_uid, study_id, study_date, study_time, description, modality, \
                accession, referring_physician, series_count, instance_count, folder_path = row
                
                study_data = {
                    'study_id': study_uid,
                    'study_identifier': study_id or '',
                    'study_date': self.format_date(study_date),
                    'study_time': self.format_time(study_time),
                    'description': description or '',
                    'modality': modality or '',
                    'accession_number': accession or '',
                    'referring_physician': referring_physician or '',
                    'series_count': series_count or 0,
                    'instance_count': instance_count or 0,
                    'folder_path': folder_path or ''
                }
                
                studies.append(study_data)
            
            return studies
            
        except Exception as e:
            logger.error(f"Error getting studies for patient {patient_id}: {e}")
            return []
    
    def format_date(self, date_str: str) -> str:
        """Format DICOM date (YYYYMMDD) to readable format"""
        if not date_str or len(date_str) < 8:
            return date_str or ''
        
        try:
            # DICOM date format: YYYYMMDD
            year = date_str[:4]
            month = date_str[4:6]
            day = date_str[6:8]
            return f"{year}-{month}-{day}"
        except:
            return date_str
    
    def format_time(self, time_str: str) -> str:
        """Format DICOM time (HHMMSS) to readable format"""
        if not time_str or len(time_str) < 6:
            return time_str or ''
        
        try:
            # DICOM time format: HHMMSS
            hour = time_str[:2]
            minute = time_str[2:4]
            second = time_str[4:6]
            return f"{hour}:{minute}:{second}"
        except:
            return time_str
    
    def get_index_statistics(self) -> Dict:
        """Get statistics about the patient index"""
        if not self.available:
            return {'available': False, 'message': 'Index not available'}
        
        try:
            with sqlite3.connect(self.index_db_path) as conn:
                cursor = conn.cursor()
                
                # Check if we have the new lightweight schema
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='patient_studies'")
                has_lightweight_schema = cursor.fetchone() is not None
                
                if has_lightweight_schema:
                    # Use lightweight schema - count unique patients and studies
                    cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_studies")
                    patient_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM patient_studies")
                    study_count = cursor.fetchone()[0]
                    
                    # No series or files in lightweight schema
                    series_count = 0
                    file_count = 0
                else:
                    # Fallback to old schema if it exists
                    try:
                        cursor.execute("SELECT COUNT(*) FROM patients")
                        patient_count = cursor.fetchone()[0]
                        
                        cursor.execute("SELECT COUNT(*) FROM studies") 
                        study_count = cursor.fetchone()[0]
                        
                        cursor.execute("SELECT COUNT(*) FROM series")
                        series_count = cursor.fetchone()[0]
                        
                        cursor.execute("SELECT COUNT(*) FROM dicom_files")
                        file_count = cursor.fetchone()[0]
                    except sqlite3.OperationalError:
                        # Tables don't exist, return zero counts
                        patient_count = study_count = series_count = file_count = 0
                
                # Get indexing status (without errors column)
                cursor.execute('''
                    SELECT status, started_at, completed_at
                    FROM indexing_status 
                    ORDER BY id DESC LIMIT 1
                ''')
                
                status_row = cursor.fetchone()
                indexing_status = {}
                if status_row:
                    indexing_status = {
                        'status': status_row[0],
                        'started_at': status_row[1],
                        'completed_at': status_row[2]
                    }
                
                return {
                    'available': True,
                    'patient_count': patient_count,
                    'study_count': study_count,
                    'series_count': series_count,
                    'file_count': file_count,
                    'indexing_status': indexing_status,
                    'database_path': self.index_db_path
                }
                
        except Exception as e:
            logger.error(f"Error getting index statistics: {e}")
            return {'available': False, 'error': str(e)}

# Test function
def test_search():
    """Test the patient search functionality"""
    searcher = NASPatientSearch()
    
    if not searcher.available:
        print("❌ Patient index not available. Please run indexing first.")
        return
    
    # Test search
    print("🔍 Testing patient search...")
    
    # Search for all patients
    results = searcher.search_patients(limit=10)
    
    if results['success']:
        print(f"✅ Found {results['total_found']} patients")
        for i, patient in enumerate(results['patients'][:5], 1):
            print(f"   {i}. {patient['name']} (ID: {patient['patient_id']}) - {len(patient['studies'])} studies")
    else:
        print(f"❌ Search failed: {results['message']}")
    
    # Get statistics
    stats = searcher.get_index_statistics()
    print(f"\n📊 Index Statistics:")
    print(f"   Patients: {stats.get('patient_count', 0)}")
    print(f"   Studies: {stats.get('study_count', 0)}")
    print(f"   Series: {stats.get('series_count', 0)}")
    print(f"   Files: {stats.get('file_count', 0)}")

if __name__ == "__main__":
    test_search()