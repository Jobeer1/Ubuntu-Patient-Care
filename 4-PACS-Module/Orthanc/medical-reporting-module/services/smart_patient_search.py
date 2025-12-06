"""
Smart Patient Search Autocomplete Service
Provides real-time suggestions as users type - like Google search
"""

import sqlite3
import logging
from typing import List, Dict, Any
import os

logger = logging.getLogger(__name__)

# Use the correct patient database
try:
    from backend.metadata_db import get_metadata_db_path
    LOCAL_DB_PATH = get_metadata_db_path()
except Exception:
    LOCAL_DB_PATH = r"C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc\orthanc-source\NASIntegration\nas_patient_index.db"

def get_smart_suggestions(query: str, suggestion_type: str = "all", limit: int = 10) -> Dict[str, Any]:
    """
    Get smart autocomplete suggestions as user types
    
    Args:
        query: What the user has typed so far
        suggestion_type: 'names', 'ids', 'dates', 'modalities', or 'all'
        limit: Maximum number of suggestions
        
    Returns:
        Dictionary with suggestions for different categories
    """
    
    if not query or len(query.strip()) < 1:
        return {
            'success': True,
            'suggestions': {
                'patient_names': [],
                'patient_ids': [],
                'study_dates': [],
                'modalities': []
            },
            'query': query
        }
    
    query = query.strip().lower()
    
    try:
        conn = sqlite3.connect(LOCAL_DB_PATH, timeout=30)
        cursor = conn.cursor()
        
        suggestions = {
            'patient_names': [],
            'patient_ids': [],
            'study_dates': [],
            'modalities': []
        }
        
        # 1. Patient Name Suggestions (fuzzy matching)
        if suggestion_type in ['names', 'all']:
            cursor.execute('''
                SELECT DISTINCT patient_name, COUNT(*) as study_count
                FROM patient_studies 
                WHERE LOWER(patient_name) LIKE ? 
                AND patient_name IS NOT NULL 
                AND patient_name != 'Anonymous Unknown'
                GROUP BY patient_name
                ORDER BY study_count DESC, patient_name
                LIMIT ?
            ''', (f'%{query}%', limit))
            
            name_results = cursor.fetchall()
            for name, count in name_results:
                suggestions['patient_names'].append({
                    'text': name,
                    'display': f"{name} ({count} studies)",
                    'type': 'patient_name',
                    'count': count
                })
        
        # 2. Patient ID Suggestions  
        if suggestion_type in ['ids', 'all']:
            cursor.execute('''
                SELECT DISTINCT patient_id, patient_name, COUNT(*) as study_count
                FROM patient_studies 
                WHERE LOWER(patient_id) LIKE ? 
                AND patient_id IS NOT NULL
                GROUP BY patient_id
                ORDER BY patient_id
                LIMIT ?
            ''', (f'%{query}%', limit))
            
            id_results = cursor.fetchall()
            for patient_id, name, count in id_results:
                display_name = name if name and name != 'Anonymous Unknown' else 'Unknown'
                suggestions['patient_ids'].append({
                    'text': patient_id,
                    'display': f"{patient_id} - {display_name} ({count} studies)",
                    'type': 'patient_id',
                    'count': count
                })
        
        # 3. Study Date Suggestions (smart date matching)
        if suggestion_type in ['dates', 'all']:
            # Handle different date formats the user might type
            date_patterns = []
            
            if query.isdigit():
                if len(query) == 4:  # Year like "2024"
                    date_patterns.append(f'{query}%')
                elif len(query) == 6:  # YYYYMM like "202409"
                    date_patterns.append(f'{query}%')
                elif len(query) == 8:  # YYYYMMDD like "20240915"
                    date_patterns.append(query)
                else:
                    date_patterns.append(f'%{query}%')
            else:
                date_patterns.append(f'%{query}%')
            
            for pattern in date_patterns:
                cursor.execute('''
                    SELECT DISTINCT study_date, COUNT(*) as study_count
                    FROM patient_studies 
                    WHERE study_date LIKE ? 
                    AND study_date IS NOT NULL
                    GROUP BY study_date
                    ORDER BY study_date DESC
                    LIMIT ?
                ''', (pattern, limit))
                
                date_results = cursor.fetchall()
                for study_date, count in date_results:
                    if study_date and len(study_date) >= 8:
                        # Format date nicely: 20240915 -> 2024-09-15
                        try:
                            formatted_date = f"{study_date[:4]}-{study_date[4:6]}-{study_date[6:8]}"
                            suggestions['study_dates'].append({
                                'text': study_date,
                                'display': f"{formatted_date} ({count} studies)",
                                'type': 'study_date',
                                'count': count,
                                'formatted': formatted_date
                            })
                        except:
                            suggestions['study_dates'].append({
                                'text': study_date,
                                'display': f"{study_date} ({count} studies)",
                                'type': 'study_date',
                                'count': count
                            })
                break  # Use first matching pattern
        
        # 4. Modality Suggestions
        if suggestion_type in ['modalities', 'all']:
            cursor.execute('''
                SELECT DISTINCT modality, COUNT(*) as study_count
                FROM patient_studies 
                WHERE LOWER(modality) LIKE ? 
                AND modality IS NOT NULL
                GROUP BY modality
                ORDER BY study_count DESC
                LIMIT ?
            ''', (f'%{query}%', limit))
            
            modality_results = cursor.fetchall()
            for modality, count in modality_results:
                suggestions['modalities'].append({
                    'text': modality,
                    'display': f"{modality} ({count} studies)",
                    'type': 'modality',
                    'count': count
                })
        
        conn.close()
        
        return {
            'success': True,
            'suggestions': suggestions,
            'query': query,
            'total_suggestions': sum(len(v) for v in suggestions.values())
        }
        
    except Exception as e:
        logger.error(f"Smart suggestions error: {e}")
        return {
            'success': False,
            'error': str(e),
            'suggestions': {
                'patient_names': [],
                'patient_ids': [],
                'study_dates': [],
                'modalities': []
            },
            'query': query
        }

def get_quick_stats() -> Dict[str, Any]:
    """Get quick database statistics for the UI"""
    try:
        conn = sqlite3.connect(LOCAL_DB_PATH, timeout=30)
        cursor = conn.cursor()
        
        # Total patients
        cursor.execute('SELECT COUNT(DISTINCT patient_id) FROM patient_studies')
        total_patients = cursor.fetchone()[0]
        
        # Total studies  
        cursor.execute('SELECT COUNT(*) FROM patient_studies')
        total_studies = cursor.fetchone()[0]
        
        # Date range
        cursor.execute('SELECT MIN(study_date), MAX(study_date) FROM patient_studies WHERE study_date IS NOT NULL')
        date_range = cursor.fetchone()
        
        # Top modalities
        cursor.execute('''
            SELECT modality, COUNT(*) 
            FROM patient_studies 
            WHERE modality IS NOT NULL 
            GROUP BY modality 
            ORDER BY COUNT(*) DESC 
            LIMIT 5
        ''')
        top_modalities = cursor.fetchall()
        
        conn.close()
        
        return {
            'success': True,
            'stats': {
                'total_patients': total_patients,
                'total_studies': total_studies,
                'date_range': {
                    'earliest': date_range[0] if date_range[0] else None,
                    'latest': date_range[1] if date_range[1] else None
                },
                'top_modalities': [{'name': mod, 'count': count} for mod, count in top_modalities]
            }
        }
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {
            'success': False,
            'error': str(e)
        }