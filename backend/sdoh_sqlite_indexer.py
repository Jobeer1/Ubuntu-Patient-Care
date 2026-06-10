"""
SDOH SQLite-backed Patient Index
Reads from SQLite database instead of JSON
No more duplicate DICOM slices - one entry per series!
"""

from __future__ import annotations

import os
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from health_graph_schema import HealthGraphSchema

class SDOHSQLiteIndexer:
    """
    SQLite-backed indexer for SDOH documents
    Replaces JSON file operations with fast SQLite queries
    """
    
    def __init__(self, db_path: str = None):
        """Initialize SQLite indexer"""
        if db_path is None:
            # Default to vault folder
            db_path = r'C:\Users\Admin\.openclaw\vault\index\master_health_graph.db'
        
        self.db_path = db_path
        self.db = None
        self.lock = threading.RLock()
        self._load_db()
    
    def _load_db(self) -> None:
        """Load or create database"""
        try:
            if os.path.exists(self.db_path):
                self.db = HealthGraphSchema(self.db_path)
            else:
                # Create empty database
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                self.db = HealthGraphSchema(self.db_path)
        except Exception as e:
            print(f"Warning: Could not load SQLite: {e}")
            self.db = None
    
    # =====================================================================
    # Query Methods (for SDOH Agent)
    # =====================================================================
    
    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient record"""
        if not self.db:
            return None
        
        with self.lock:
            patient = self.db.get_patient(patient_id)
            if patient:
                # Add studies and series count
                studies = self.db.get_patient_studies(patient_id)
                series = self.db.get_patient_series(patient_id)
                patient['studies_count'] = len(studies)
                patient['series_count'] = len(series)
            return patient
    
    def get_patient_studies(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all studies for patient"""
        if not self.db:
            return []
        
        with self.lock:
            return self.db.get_patient_studies(patient_id)
    
    def get_patient_series(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all series for patient (deduped!)"""
        if not self.db:
            return []
        
        with self.lock:
            return self.db.get_patient_series(patient_id)
    
    def search_patients(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search patients by name or ID"""
        if not self.db:
            return []
        
        with self.lock:
            return self.db.search_patients(query, limit)
    
    def search_studies(self, modality: str = None, body_part: str = None,
                      start_date: str = None, end_date: str = None,
                      limit: int = 100) -> List[Dict[str, Any]]:
        """Search studies by criteria"""
        if not self.db:
            return []
        
        with self.lock:
            return self.db.search_studies(modality, body_part, start_date, end_date, limit)
    
    def search_keywords(self, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search by keyword"""
        if not self.db:
            return []
        
        with self.lock:
            return self.db.search_by_keyword(keyword, limit)
    
    def get_metadata(self, patient_id: str, key: str = None) -> List[Dict[str, Any]]:
        """Get patient metadata"""
        if not self.db:
            return []
        
        with self.lock:
            return self.db.get_metadata(patient_id, key)
    
    def get_findings(self, patient_id: str, study_uid: str = None) -> List[Dict[str, Any]]:
        """Get clinical findings"""
        if not self.db:
            return []
        
        with self.lock:
            return self.db.get_findings(patient_id, study_uid)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        if not self.db:
            return {}
        
        with self.lock:
            return self.db.get_stats()
    
    # =====================================================================
    # Write Methods (for metadata extraction and indexing)
    # =====================================================================
    
    def add_patient(self, patient_id: str, patient_data: Dict[str, Any]) -> bool:
        """Add or update patient"""
        if not self.db:
            return False
        
        with self.lock:
            try:
                self.db.insert_patient(patient_id, patient_data)
                return True
            except Exception as e:
                print(f"Error adding patient: {e}")
                return False
    
    def add_study(self, study_data: Dict[str, Any]) -> bool:
        """Add study"""
        if not self.db:
            return False
        
        with self.lock:
            try:
                self.db.insert_study(study_data)
                return True
            except Exception as e:
                print(f"Error adding study: {e}")
                return False
    
    def add_series(self, series_data: Dict[str, Any]) -> bool:
        """Add series (groups DICOM slices)"""
        if not self.db:
            return False
        
        with self.lock:
            try:
                self.db.insert_series(series_data)
                return True
            except Exception as e:
                print(f"Error adding series: {e}")
                return False
    
    def add_file(self, file_data: Dict[str, Any]) -> bool:
        """Add file reference"""
        if not self.db:
            return False
        
        with self.lock:
            try:
                self.db.insert_file(file_data)
                return True
            except Exception as e:
                print(f"Error adding file: {e}")
                return False
    
    def add_metadata(self, patient_id: str, key: str, value: Any) -> bool:
        """Add metadata entry"""
        if not self.db:
            return False
        
        with self.lock:
            try:
                self.db.insert_metadata(patient_id, key, value)
                return True
            except Exception as e:
                print(f"Error adding metadata: {e}")
                return False
    
    def add_finding(self, finding_data: Dict[str, Any]) -> bool:
        """Add clinical finding (extracted from DICOM/reports)"""
        if not self.db:
            return False
        
        with self.lock:
            try:
                self.db.insert_finding(finding_data)
                return True
            except Exception as e:
                print(f"Error adding finding: {e}")
                return False
    
    def add_keyword(self, patient_id: str, keyword: str, context: str = '') -> bool:
        """Add search keyword"""
        if not self.db:
            return False
        
        with self.lock:
            try:
                self.db.add_search_keyword(patient_id, keyword, context)
                return True
            except Exception as e:
                print(f"Error adding keyword: {e}")
                return False
    
    # =====================================================================
    # Index Scanning
    # =====================================================================
    
    def index_dicom_file(self, file_path: str, metadata: Dict[str, Any]) -> bool:
        """Index a DICOM file"""
        try:
            patient_id = metadata.get('patient_id')
            study_uid = metadata.get('study_uid')
            series_uid = metadata.get('series_uid')
            
            if not all([patient_id, study_uid, series_uid]):
                return False
            
            # Add patient
            self.add_patient(patient_id, metadata)
            
            # Add study
            study_data = {k: v for k, v in metadata.items() 
                         if k in ['patient_id', 'study_uid', 'accession_number',
                                 'study_date', 'study_time', 'study_description',
                                 'referring_physician', 'modality', 'body_part',
                                 'body_part_normalized']}
            self.add_study(study_data)
            
            # Add series (ONE entry groups all slices)
            series_data = {k: v for k, v in metadata.items()
                          if k in ['study_uid', 'patient_id', 'series_uid',
                                  'series_description', 'series_number', 'series_time',
                                  'modality', 'manufacturer']}
            self.add_series(series_data)
            
            # Add file reference
            file_data = {
                'patient_id': patient_id,
                'study_uid': study_uid,
                'series_uid': series_uid,
                'file_path': file_path,
                'file_type': 'dicom'
            }
            self.add_file(file_data)
            
            # Add keywords
            keywords = metadata.get('relevance_keywords', [])
            if isinstance(keywords, str):
                keywords = keywords.split()
            for kw in keywords:
                self.add_keyword(patient_id, kw)
            
            return True
        
        except Exception as e:
            print(f"Error indexing DICOM: {e}")
            return False
    
    def index_firebird_data(self, patient_id: str, firebird_record: Dict[str, Any]) -> bool:
        """Index data extracted from Firebird database"""
        try:
            # Add patient
            self.add_patient(patient_id, firebird_record)
            
            # Add metadata from Firebird
            for key, value in firebird_record.items():
                if value and key != 'patient_id':
                    self.add_metadata(patient_id, key, value)
            
            # Add keywords from description
            if 'description' in firebird_record:
                desc = firebird_record['description']
                keywords = desc.lower().split()
                for kw in keywords[:10]:  # Limit keywords
                    self.add_keyword(patient_id, kw, desc[:100])
            
            return True
        
        except Exception as e:
            print(f"Error indexing Firebird data: {e}")
            return False
    
    def index_external_database(self, patient_id: str, db_record: Dict[str, Any]) -> bool:
        """Index data from external databases"""
        try:
            # Add patient
            self.add_patient(patient_id, db_record)
            
            # Add metadata
            for key, value in db_record.items():
                if value and key != 'patient_id':
                    self.add_metadata(patient_id, key, value)
            
            # Add findings
            if 'findings' in db_record:
                for finding in db_record['findings']:
                    finding['patient_id'] = patient_id
                    self.add_finding(finding)
            
            return True
        
        except Exception as e:
            print(f"Error indexing external database: {e}")
            return False
    
    def close(self) -> None:
        """Close database"""
        if self.db:
            self.db.close()
    
    def __del__(self):
        self.close()
