"""
Intelligent DICOM Search Service
Advanced search with fuzzy matching, full-text search, and intelligent ranking
"""

import logging
import sqlite3
import re
from datetime import datetime
from typing import List, Dict, Optional
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

logger = logging.getLogger(__name__)


class IntelligentSearchService:
    """
    Advanced search engine with:
    - Fuzzy name matching for misspellings
    - Full-text search across multiple fields
    - Multi-field queries (patient ID, name, date, modality)
    - Intelligent result ranking
    - Phonetic matching for similar names
    - Smart date parsing
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.min_match_score = 70  # Fuzzy match threshold
    
    def search_patients(self, query: Dict[str, str], limit: int = 50) -> Dict:
        """
        Intelligent patient search with multiple strategies
        
        Args:
            query: Dict with keys like 'patient_name', 'patient_id', 'study_date', 'modality', 'free_text'
            limit: Maximum results to return
        
        Returns:
            Dict with matched patients and search metadata
        """
        logger.info(f"🔍 Intelligent search: {query}")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Determine search strategy based on query
            patients = self._execute_search_strategy(cursor, query, limit)
            
            # Rank and deduplicate results
            ranked_results = self._rank_results(patients, query)
            
            conn.close()
            
            return {
                'success': True,
                'patients': ranked_results,
                'total_found': len(ranked_results),
                'query': query,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            return {
                'success': False,
                'error': str(e),
                'patients': [],
                'total_found': 0
            }
    
    def _execute_search_strategy(self, cursor: sqlite3.Cursor, query: Dict, limit: int) -> List[Dict]:
        """Execute best search strategy based on query parameters"""
        
        # Strategy 1: Exact ID match (fastest)
        if 'patient_id' in query and query['patient_id']:
            patient_id = query['patient_id'].strip()
            results = self._search_by_patient_id(cursor, patient_id, limit)
            if results:
                return results
        
        # Strategy 2: Exact name match
        if 'patient_name' in query and query['patient_name']:
            patient_name = query['patient_name'].strip()
            results = self._search_by_exact_name(cursor, patient_name, limit)
            if results:
                return results
        
        # Strategy 3: Fuzzy name match (handles misspellings)
        if 'patient_name' in query and query['patient_name']:
            results = self._search_by_fuzzy_name(cursor, query['patient_name'], limit)
            if results:
                return results
        
        # Strategy 4: Combined fields with intelligent ranking
        if any(k in query and query[k] for k in ['patient_name', 'patient_id', 'study_date', 'modality']):
            return self._search_combined_fields(cursor, query, limit)
        
        # Strategy 5: Full-text search
        if 'free_text' in query and query['free_text']:
            return self._search_full_text(cursor, query['free_text'], limit)
        
        logger.warning("❌ No valid search criteria provided")
        return []
    
    def _search_by_patient_id(self, cursor: sqlite3.Cursor, patient_id: str, limit: int) -> List[Dict]:
        """Fast search by exact patient ID"""
        logger.info(f"🎯 Searching by exact patient ID: {patient_id}")
        
        cursor.execute('''
            SELECT pm.patient_id, pm.patient_name, pm.patient_sex, pm.patient_birth_date,
                   pm.total_studies, pm.total_series, pm.total_instances,
                   pm.first_study_date, pm.last_study_date,
                   s.study_uid, s.study_date, s.modality, s.study_description,
                   s.folder_path, COUNT(fh.file_path) as file_count
            FROM patient_master pm
            LEFT JOIN studies s ON pm.patient_id = s.patient_id
            LEFT JOIN file_hashes fh ON s.id = fh.study_id
            WHERE pm.patient_id LIKE ? OR s.patient_id LIKE ?
            GROUP BY s.study_uid
            ORDER BY s.study_date DESC
            LIMIT ?
        ''', (f'{patient_id}%', f'{patient_id}%', limit))
        
        return self._format_results(cursor.fetchall())
    
    def _search_by_exact_name(self, cursor: sqlite3.Cursor, patient_name: str, limit: int) -> List[Dict]:
        """Search by exact patient name"""
        logger.info(f"📛 Searching by exact name: {patient_name}")
        
        # Normalize name for comparison
        normalized_name = self._normalize_name(patient_name)
        
        cursor.execute('''
            SELECT pm.patient_id, pm.patient_name, pm.patient_sex, pm.patient_birth_date,
                   pm.total_studies, pm.total_series, pm.total_instances,
                   pm.first_study_date, pm.last_study_date,
                   s.study_uid, s.study_date, s.modality, s.study_description,
                   s.folder_path, COUNT(fh.file_path) as file_count
            FROM patient_master pm
            LEFT JOIN studies s ON pm.patient_id = s.patient_id
            LEFT JOIN file_hashes fh ON s.id = fh.study_id
            WHERE LOWER(REPLACE(pm.patient_name, '^', ' ')) LIKE ?
            GROUP BY s.study_uid
            ORDER BY s.study_date DESC
            LIMIT ?
        ''', (f'%{normalized_name}%', limit))
        
        return self._format_results(cursor.fetchall())
    
    def _search_by_fuzzy_name(self, cursor: sqlite3.Cursor, patient_name: str, limit: int) -> List[Dict]:
        """Fuzzy search for patient names (handles misspellings)"""
        logger.info(f"🔤 Searching by fuzzy name: {patient_name}")
        
        normalized_search = self._normalize_name(patient_name)
        
        # Get all patients
        cursor.execute('''
            SELECT pm.patient_id, pm.patient_name, pm.patient_sex, pm.patient_birth_date,
                   pm.total_studies, pm.total_series, pm.total_instances,
                   pm.first_study_date, pm.last_study_date
            FROM patient_master pm
        ''')
        
        all_patients = cursor.fetchall()
        
        # Fuzzy match patient names
        candidates = []
        for row in all_patients:
            patient_name_norm = self._normalize_name(row[1])
            score = fuzz.token_set_ratio(normalized_search, patient_name_norm)
            
            if score >= self.min_match_score:
                candidates.append((score, row[0], row))  # score, patient_id, full_row
        
        # Sort by score descending
        candidates.sort(key=lambda x: x[0], reverse=True)
        
        # Get studies for matched patients
        results = []
        for score, patient_id, patient_info in candidates[:limit]:
            cursor.execute('''
                SELECT pm.patient_id, pm.patient_name, pm.patient_sex, pm.patient_birth_date,
                       pm.total_studies, pm.total_series, pm.total_instances,
                       pm.first_study_date, pm.last_study_date,
                       s.study_uid, s.study_date, s.modality, s.study_description,
                       s.folder_path, COUNT(fh.file_path) as file_count
                FROM patient_master pm
                LEFT JOIN studies s ON pm.patient_id = s.patient_id
                LEFT JOIN file_hashes fh ON s.id = fh.study_id
                WHERE pm.patient_id = ?
                GROUP BY s.study_uid
                ORDER BY s.study_date DESC
            ''', (patient_id,))
            
            results.extend(self._format_results(cursor.fetchall(), match_score=score))
        
        return results[:limit]
    
    def _search_combined_fields(self, cursor: sqlite3.Cursor, query: Dict, limit: int) -> List[Dict]:
        """Search using multiple fields with intelligent filtering"""
        logger.info(f"🔎 Combined field search: {query}")
        
        # Build dynamic SQL query
        where_conditions = []
        params = []
        
        if query.get('patient_id'):
            where_conditions.append('s.patient_id LIKE ?')
            params.append(f"{query['patient_id']}%")
        
        if query.get('patient_name'):
            where_conditions.append('LOWER(REPLACE(pm.patient_name, "^", " ")) LIKE ?')
            params.append(f"%{self._normalize_name(query['patient_name'])}%")
        
        if query.get('study_date'):
            # Handle various date formats
            study_date = self._parse_date(query['study_date'])
            if study_date:
                where_conditions.append('s.study_date LIKE ?')
                params.append(f"{study_date}%")
        
        if query.get('modality'):
            where_conditions.append('s.modality = ?')
            params.append(query['modality'].upper())
        
        where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'
        params.append(limit)
        
        sql = f'''
            SELECT pm.patient_id, pm.patient_name, pm.patient_sex, pm.patient_birth_date,
                   pm.total_studies, pm.total_series, pm.total_instances,
                   pm.first_study_date, pm.last_study_date,
                   s.study_uid, s.study_date, s.modality, s.study_description,
                   s.folder_path, COUNT(fh.file_path) as file_count
            FROM patient_master pm
            LEFT JOIN studies s ON pm.patient_id = s.patient_id
            LEFT JOIN file_hashes fh ON s.id = fh.study_id
            WHERE {where_clause}
            GROUP BY s.study_uid
            ORDER BY s.study_date DESC
            LIMIT ?
        '''
        
        cursor.execute(sql, params)
        return self._format_results(cursor.fetchall())
    
    def _search_full_text(self, cursor: sqlite3.Cursor, search_text: str, limit: int) -> List[Dict]:
        """Full-text search across all indexed fields"""
        logger.info(f"📖 Full-text search: {search_text}")
        
        normalized_text = search_text.lower()
        
        cursor.execute('''
            SELECT DISTINCT pm.patient_id, pm.patient_name, pm.patient_sex, pm.patient_birth_date,
                   pm.total_studies, pm.total_series, pm.total_instances,
                   pm.first_study_date, pm.last_study_date,
                   s.study_uid, s.study_date, s.modality, s.study_description,
                   s.folder_path, COUNT(fh.file_path) as file_count
            FROM patient_master pm
            LEFT JOIN studies s ON pm.patient_id = s.patient_id
            LEFT JOIN file_hashes fh ON s.id = fh.study_id
            LEFT JOIN search_index si ON s.id = si.study_id
            WHERE si.search_text LIKE ?
               OR LOWER(pm.patient_name) LIKE ?
               OR LOWER(s.study_description) LIKE ?
               OR s.study_date LIKE ?
            GROUP BY s.study_uid
            ORDER BY s.study_date DESC
            LIMIT ?
        ''', (f'%{normalized_text}%', f'%{normalized_text}%', 
              f'%{normalized_text}%', f'%{normalized_text}%', limit))
        
        return self._format_results(cursor.fetchall())
    
    def _rank_results(self, patients: List[Dict], query: Dict) -> List[Dict]:
        """Rank search results by relevance"""
        if not patients:
            return []
        
        # Assign relevance scores
        for patient in patients:
            score = 0
            
            # Exact ID match gets highest score
            if query.get('patient_id') and query['patient_id'].lower() in patient['patient_id'].lower():
                score += 50
            
            # Name match
            if query.get('patient_name'):
                name_match = fuzz.token_set_ratio(
                    query['patient_name'].lower(),
                    patient['patient_name'].lower()
                )
                score += name_match / 2
            
            # Date match
            if query.get('study_date') and patient.get('study_date'):
                if str(query['study_date']).replace('-', '') in str(patient['study_date']).replace('-', ''):
                    score += 30
            
            # Modality match
            if query.get('modality') and patient.get('modality'):
                if query['modality'].upper() == patient['modality'].upper():
                    score += 20
            
            patient['relevance_score'] = min(score, 100)
        
        # Sort by relevance
        ranked = sorted(patients, key=lambda x: (x.get('relevance_score', 0), x.get('study_date', '')), reverse=True)
        return ranked
    
    def _format_results(self, rows: List[tuple], match_score: int = 100) -> List[Dict]:
        """Format database rows into result dictionaries"""
        results = []
        seen_studies = set()
        
        for row in rows:
            study_uid = row[9] if len(row) > 9 else None
            if study_uid in seen_studies:
                continue
            seen_studies.add(study_uid)
            
            result = {
                'patient_id': row[0],
                'patient_name': row[1],
                'patient_sex': row[2],
                'patient_birth_date': row[3],
                'total_studies': row[4],
                'total_series': row[5],
                'total_instances': row[6],
                'first_study_date': row[7],
                'last_study_date': row[8],
                'study_uid': row[9],
                'study_date': row[10],
                'modality': row[11],
                'study_description': row[12],
                'folder_path': row[13],
                'file_count': row[14] if len(row) > 14 else 0,
                'match_score': match_score
            }
            results.append(result)
        
        return results
    
    def _normalize_name(self, name: str) -> str:
        """Normalize patient name for comparison"""
        # Handle DICOM name format (Family^Given^Middle^Prefix^Suffix)
        name = name.replace('^', ' ')
        # Remove extra spaces and convert to lowercase
        name = ' '.join(name.split()).lower()
        # Remove special characters
        name = re.sub(r'[^a-z0-9\s]', '', name)
        return name
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse various date formats and return YYYYMMDD"""
        date_str = date_str.strip()
        
        try:
            # Already in YYYYMMDD format
            if len(date_str) == 8 and date_str.isdigit():
                return date_str
            
            # YYYY-MM-DD format
            if '-' in date_str:
                parts = date_str.split('-')
                if len(parts) == 3:
                    return f"{parts[0]}{parts[1]:0>2}{parts[2]:0>2}"
            
            # MM/DD/YYYY format
            if '/' in date_str:
                parts = date_str.split('/')
                if len(parts) == 3:
                    if len(parts[2]) == 4:  # MM/DD/YYYY
                        return f"{parts[2]}{parts[0]:0>2}{parts[1]:0>2}"
                    else:  # DD/MM/YY
                        return f"20{parts[2]}{parts[1]:0>2}{parts[0]:0>2}"
        
        except Exception as e:
            logger.warning(f"⚠️  Could not parse date {date_str}: {e}")
        
        return None
