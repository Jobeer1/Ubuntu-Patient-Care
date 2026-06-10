"""
Adapter layer to integrate HealthGraphDB with PatientDocumentIndexer
Provides a compatibility layer so existing code works with SQLite backend
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from health_graph_db import HealthGraphDB

class PatientIndexAdapter:
    """
    Adapter that provides the same interface as the old JSON-based
    PatientDocumentIndexer but uses SQLite backend
    """
    
    def __init__(self, db_path: str):
        """Initialize adapter with SQLite database"""
        self.db_path = db_path
        self.db = HealthGraphDB(db_path)
        self._cache = None
        self._cache_time = None
    
    def add_entry(self, entry: Dict[str, Any]) -> None:
        """
        Add or update a file entry in the database.
        This automatically consolidates by patient.
        """
        cursor = self.db.conn.cursor()
        patient_id = entry.get('patient_id')
        
        if not patient_id:
            return
        
        # Insert or update patient
        cursor.execute('''
            INSERT OR IGNORE INTO patients
            (patient_id, patient_name, dob, patient_age, patient_sex, institution, first_indexed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            patient_id,
            entry.get('patient_name'),
            entry.get('dob'),
            entry.get('patient_age'),
            entry.get('patient_sex'),
            entry.get('institution'),
            datetime.now().isoformat()
        ))
        
        # Update last_updated
        cursor.execute('''
            UPDATE patients SET last_updated = ? WHERE patient_id = ?
        ''', (datetime.now().isoformat(), patient_id))
        
        # Insert or update study
        study_uid = entry.get('study_uid')
        if study_uid:
            cursor.execute('''
                INSERT OR IGNORE INTO studies
                (patient_id, study_uid, accession_number, study_date, study_time,
                 study_description, referring_physician, modality, body_part,
                 body_part_normalized, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient_id,
                study_uid,
                entry.get('accession_number'),
                entry.get('study_date'),
                entry.get('study_time'),
                entry.get('study_description'),
                entry.get('referring_physician'),
                entry.get('modality'),
                entry.get('body_part'),
                entry.get('body_part_normalized'),
                datetime.now().isoformat()
            ))
        
        # Insert file
        cursor.execute('''
            INSERT OR REPLACE INTO files
            (patient_id, study_uid, file_path, file_type, image_height, 
             image_width, summary, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            patient_id,
            study_uid,
            entry.get('file_path'),
            entry.get('file_type'),
            entry.get('image_height'),
            entry.get('image_width'),
            entry.get('summary'),
            entry.get('indexed_at', datetime.now().isoformat())
        ))
        
        file_id = cursor.lastrowid
        
        # Insert keywords
        keywords = entry.get('relevance_keywords', [])
        if isinstance(keywords, str):
            keywords = keywords.split()
        
        for keyword in keywords:
            cursor.execute('''
                INSERT INTO keywords (file_id, keyword)
                VALUES (?, ?)
            ''', (file_id, keyword.lower()))
        
        self.db.conn.commit()
        self._cache = None  # Invalidate cache
    
    def search(
        self,
        modality: Optional[str] = None,
        body_part: Optional[str] = None,
        doc_type: Optional[str] = None,
        text_query: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search with same interface as original PatientDocumentIndexer.
        Returns files that match the criteria.
        """
        results = []
        
        # Build search parameters
        search_keywords = []
        if text_query:
            search_keywords = text_query.lower().split()
        
        # Search files based on criteria
        if modality or body_part or search_keywords:
            # Use database search
            if search_keywords:
                files = self.db.search_keywords(search_keywords, limit=1000)
            else:
                files = self.db.search_studies(
                    modality=modality,
                    body_part=body_part,
                    limit=1000
                )
            
            # Convert studies to files format
            for study in files if not search_keywords else []:
                result = self._study_to_file_entry(study)
                if result:
                    results.append(result)
        else:
            # Get all files if no filter
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT * FROM files LIMIT ?', (limit,))
            results = [dict(row) for row in cursor.fetchall()]
        
        # Sort by recency and return limited results
        results.sort(key=lambda x: x.get('indexed_at', '0'), reverse=True)
        return results[:limit]
    
    def search_for_visit(self, visit_description: str) -> Dict[str, Any]:
        """
        Search for documents relevant to a visit description.
        """
        text_lower = visit_description.lower()
        
        # Detect modality and body part from description
        modality = None
        body_part = None
        
        modality_terms = {
            'ct': 'CT', 'ct scan': 'CT', 'computed tomography': 'CT',
            'mri': 'MR', 'magnetic resonance': 'MR',
            'x-ray': 'CR', 'xray': 'CR', 'chest x-ray': 'CR',
            'ultrasound': 'US', 'us': 'US',
            'mammogram': 'MG', 'mammography': 'MG',
            'pet scan': 'PT', 'pet': 'PT',
            'fluoroscopy': 'RF', 'angiography': 'XA',
        }
        
        for term, code in modality_terms.items():
            if term in text_lower:
                modality = code
                break
        
        body_part_terms = {
            'chest': 'chest', 'thorax': 'chest', 'lung': 'chest',
            'abdomen': 'abdomen', 'liver': 'abdomen', 'kidney': 'abdomen',
            'brain': 'brain', 'head': 'brain', 'neuro': 'brain',
            'spine': 'spine', 'vertebra': 'spine', 'back': 'spine',
            'knee': 'extremity', 'leg': 'extremity', 'arm': 'extremity',
            'breast': 'breast', 'mammogram': 'breast',
        }
        
        for term, part in body_part_terms.items():
            if term in text_lower:
                body_part = part
                break
        
        # Search database
        relevant_files = self.search(
            modality=modality,
            body_part=body_part,
            text_query=visit_description,
            limit=20
        )
        
        return {
            'visit_description': visit_description,
            'detected_modality': modality,
            'detected_body_part': body_part,
            'relevant_files': relevant_files,
            'file_count': len(relevant_files),
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return self.db.get_stats()
    
    def _study_to_file_entry(self, study: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert study record to file entry format"""
        return {
            'patient_id': study.get('patient_id'),
            'study_uid': study.get('study_uid'),
            'study_date': study.get('study_date'),
            'study_description': study.get('study_description'),
            'modality': study.get('modality'),
            'body_part': study.get('body_part'),
            'body_part_normalized': study.get('body_part_normalized'),
            'indexed_at': study.get('indexed_at'),
        }
    
    def close(self) -> None:
        """Close database connection"""
        if self.db:
            self.db.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
