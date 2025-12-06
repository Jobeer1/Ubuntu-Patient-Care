"""
Patient Search Service
Handles patient search across NAS database, Orthanc, and direct folder scanning
"""

import logging
import os
import time
from pathlib import Path
import pydicom
from .database_operations import search_patients_in_database

logger = logging.getLogger(__name__)


def _normalize_patient_record(rec: dict, source: str):
    """Ensure patient record contains UI-friendly fields used by templates.

    Returns a new dict with keys: patient_id, patient_name, study_date (YYYYMMDD),
    source, file_count, folder_path, patient_birth_date, patient_sex, age, total_studies,
    total_series, total_instances, first_study_date, last_study_date, studies
    """
    # Some sources use 'name' while DB uses 'patient_name'
    patient_name = rec.get('patient_name') or rec.get('name') or ''
    patient_id = rec.get('patient_id') or rec.get('id') or ''

    # Determine study_date: prefer first_study_date then last_study_date then study_date
    sd = rec.get('first_study_date') or rec.get('last_study_date') or rec.get('study_date') or ''
    # Normalize to compact YYYYMMDD for UI formatter (remove dashes)
    sd_compact = sd.replace('-', '') if isinstance(sd, str) else ''

    file_count = rec.get('file_count') or rec.get('total_instances') or rec.get('dicom_file_count') or 0

    return {
        'patient_id': patient_id,
        'patient_name': patient_name,
        'study_date': sd_compact,
        'source': source,
        'file_count': file_count,
        'folder_path': rec.get('folder_path', ''),
        'patient_birth_date': rec.get('patient_birth_date') or rec.get('birth_date') or rec.get('birthDate') or '',
        'patient_sex': rec.get('patient_sex') or rec.get('sex') or '',
        'age': rec.get('age', ''),
        'total_studies': rec.get('total_studies', 0),
        'total_series': rec.get('total_series', 0),
        'total_instances': rec.get('total_instances', 0),
        'first_study_date': rec.get('first_study_date') or rec.get('study_date') or '',
        'last_study_date': rec.get('last_study_date') or rec.get('study_date') or '',
        'studies': rec.get('studies', [])
    }

def search_patient_comprehensive(search_params):
    """
    Comprehensive patient search using three-tier approach:
    1. NAS database index (fastest)
    2. Orthanc PACS fallback
    3. Direct folder search (for unindexed patients)
    """
    logger.info(f"🔍 Starting comprehensive patient search")
    
    results = {
        'patients': [],
        'total_found': 0,
        'source': 'none',
        'search_criteria': search_params,
        'success': True,
        'message': ''
    }
    
    try:
        # Tier 1: NAS Database Search (fastest)
        logger.info("🗃️ Attempting NAS patient index search")
        nas_patients = search_patients_in_database(search_params)
        
        if nas_patients:
            # normalize records so UI fields are predictable
            normalized = [_normalize_patient_record(p, 'nas_index') for p in nas_patients]
            results['patients'] = normalized
            results['total_found'] = len(normalized)
            results['source'] = 'nas_index'
            # Check if any record has multiple studies to indicate aggregation was needed
            has_studies_array = any(p.get('studies') for p in normalized)
            results['message'] = f'Found {len(normalized)} patient(s) in NAS index' + (' (with studies)' if has_studies_array else '')
            logger.info(f"✅ NAS index search successful: {len(normalized)} patients")
            return results
        
        # Tier 2: Orthanc Search (if NAS index empty)
        logger.info("🏥 Attempting Orthanc PACS search")
        orthanc_patients = search_orthanc_patients(search_params)
        
        if orthanc_patients:
            normalized = [_normalize_patient_record(p, 'orthanc') for p in orthanc_patients]
            results['patients'] = normalized
            results['total_found'] = len(normalized)
            results['source'] = 'orthanc'
            results['message'] = f'Found {len(normalized)} patient(s) in Orthanc'
            logger.info(f"✅ Orthanc search successful: {len(normalized)} patients")
            return results
        
        # Tier 3: Direct Folder Search (last resort)
        logger.info("📁 Attempting direct folder search")
        folder_patients = search_folders_directly(search_params)
        
        if folder_patients:
            normalized = [_normalize_patient_record(p, 'direct_folder_search') for p in folder_patients]
            results['patients'] = normalized
            results['total_found'] = len(normalized)
            results['source'] = 'direct_folder_search'
            results['message'] = f'Found {len(normalized)} patient(s) via direct search'
            logger.info(f"✅ Direct folder search successful: {len(normalized)} patients")
            return results
        
        # No results found
        results['message'] = 'No patients found matching search criteria'
        logger.info("❌ No patients found in any search tier")
        
    except Exception as e:
        logger.error(f"Comprehensive search error: {e}")
        results['success'] = False
        results['message'] = f'Search error: {str(e)}'
    
    return results

def search_orthanc_patients(search_params):
    """Search for patients in Orthanc PACS"""
    try:
        import requests
        
        orthanc_url = "http://localhost:8042"
        
        # Get all patients from Orthanc
        response = requests.get(f"{orthanc_url}/patients", timeout=10)
        if response.status_code != 200:
            logger.warning("Could not connect to Orthanc")
            return []
        
        patient_ids = response.json()
        patients = []
        
        search_term = (search_params.get('patient_name', '') + 
                      search_params.get('patient_id', '')).lower()
        
        for patient_id in patient_ids[:50]:  # Limit to avoid timeout
            try:
                patient_response = requests.get(f"{orthanc_url}/patients/{patient_id}")
                if patient_response.status_code == 200:
                    patient_data = patient_response.json()
                    
                    patient_name = patient_data.get('MainDicomTags', {}).get('PatientName', '')
                    orthanc_patient_id = patient_data.get('MainDicomTags', {}).get('PatientID', '')
                    
                    # Check if matches search criteria
                    if (search_term in patient_name.lower() or 
                        search_term in orthanc_patient_id.lower()):
                        
                        patients.append({
                            'patient_id': orthanc_patient_id,
                            'name': patient_name.replace('^', ' '),
                            'birth_date': patient_data.get('MainDicomTags', {}).get('PatientBirthDate', ''),
                            'sex': patient_data.get('MainDicomTags', {}).get('PatientSex', ''),
                            'age': '',
                            'folder_path': f'orthanc://{patient_id}',
                            'total_studies': len(patient_data.get('Studies', [])),
                            'total_series': 0,
                            'total_instances': 0,
                            'first_study_date': '',
                            'last_study_date': '',
                            'studies': []
                        })
                        
            except Exception as e:
                logger.warning(f"Error processing Orthanc patient {patient_id}: {e}")
                continue
        
        logger.info(f"Found {len(patients)} patients in Orthanc")
        return patients
        
    except Exception as e:
        logger.error(f"Orthanc search error: {e}")
        return []

def search_folders_directly(search_params):
    """
    Direct folder search for patients not yet indexed
    Searches newest folders first for better performance on recent patients
    """
    try:
        from config.nas_configuration import get_active_nas_path
        nas_path = get_active_nas_path()
        fallback_path = "Z:\\"
        
        # Try UNC path first, then drive letter
        base_path = nas_path if os.path.exists(nas_path) else fallback_path
        
        if not os.path.exists(base_path):
            logger.error("NAS not accessible for direct search")
            return []
        
        logger.info(f"📁 Starting direct folder search in: {base_path}")
        
        # Get search criteria
        patient_id = search_params.get('patient_id', '').strip().lower()
        patient_name = search_params.get('patient_name', '').strip().lower()
        
        if not patient_id and not patient_name:
            logger.warning("No search criteria provided for direct search")
            return []
        
        patients = []
        folders_scanned = 0
        max_folders = 5000  # Increased limit for better coverage
        
        try:
            # Get all folders and sort by modification time (newest first)
            all_folders = []
            for item in os.listdir(base_path):
                folder_path = os.path.join(base_path, item)
                if os.path.isdir(folder_path):
                    try:
                        mod_time = os.path.getmtime(folder_path)
                        all_folders.append((mod_time, item, folder_path))
                    except:
                        continue
            
            # Sort by modification time - newest first
            all_folders.sort(reverse=True, key=lambda x: x[0])
            logger.info(f"📊 Found {len(all_folders)} folders, searching newest first...")
            
            for mod_time, folder_name, folder_path in all_folders[:max_folders]:
                folders_scanned += 1
                
                # Progress logging every 1000 folders
                if folders_scanned % 1000 == 0:
                    logger.info(f"📁 Scanned {folders_scanned} folders, found {len(patients)} patients")
                
                # Check if folder name matches search criteria
                folder_lower = folder_name.lower()
                
                if patient_id and patient_id in folder_lower:
                    patient = extract_patient_from_folder(folder_path, folder_name)
                    if patient:
                        patients.append(patient)
                        logger.info(f"✅ Found patient by ID: {patient['name']}")
                
                elif patient_name:
                    # Try to extract patient info and check name
                    patient = extract_patient_from_folder(folder_path, folder_name)
                    if (patient and patient_name in patient.get('name', '').lower()):
                        patients.append(patient)
                        logger.info(f"✅ Found patient by name: {patient['name']}")
                
                # Stop if we found enough results
                if len(patients) >= 10:
                    break
            
            logger.info(f"📁 Direct search completed: {folders_scanned} folders scanned, {len(patients)} patients found")
            
        except Exception as e:
            logger.error(f"Error during folder scanning: {e}")
        
        return patients
        
    except Exception as e:
        logger.error(f"Direct folder search error: {e}")
        return []

def extract_patient_from_folder(folder_path, folder_name):
    """Extract patient information from a DICOM folder"""
    try:
        # Look for DICOM files in the folder
        dicom_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files[:10]:  # Check first 10 files only
                if (file.lower().endswith(('.dcm', '.dicom', '.ima')) or 
                    ('.' not in file and len(file) > 5)):
                    dicom_files.append(os.path.join(root, file))
                    if len(dicom_files) >= 5:  # Only need a few files
                        break
            if dicom_files:
                break
        
        if not dicom_files:
            return None
        
        # Try to read DICOM metadata from the first valid file
        for dicom_file in dicom_files:
            try:
                with pydicom.dcmread(dicom_file, force=True) as ds:
                    patient_name = str(getattr(ds, 'PatientName', 'Unknown')).replace('^', ' ').strip()
                    patient_id = str(getattr(ds, 'PatientID', folder_name)).strip()
                    birth_date = str(getattr(ds, 'PatientBirthDate', '')).strip()
                    sex = str(getattr(ds, 'PatientSex', '')).strip()
                    
                    if patient_name and patient_name != 'Unknown':
                        return {
                            'patient_id': patient_id,
                            'name': patient_name,
                            'birth_date': birth_date,
                            'sex': sex,
                            'age': '',
                            'folder_path': folder_path,
                            'total_studies': 1,
                            'total_series': 0,
                            'total_instances': len(dicom_files),
                            'first_study_date': '',
                            'last_study_date': '',
                            'studies': []
                        }
                        
            except Exception as e:
                logger.debug(f"Could not read DICOM file {dicom_file}: {e}")
                continue
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting patient from folder {folder_path}: {e}")
        return None

def find_patient_by_id_or_name(identifier):
    """Find a patient by ID or name using comprehensive search"""
    try:
        # First try exact match in database
        search_params = {
            'patient_id': identifier,
            'patient_name': identifier
        }
        
        # Use the comprehensive search
        results = search_patient_comprehensive(search_params)
        
        if results['patients']:
            return results['patients'][0]  # Return first match
        
        return None
        
    except Exception as e:
        logger.error(f"Error finding patient {identifier}: {e}")
        return None


def get_smart_suggestions(query, suggestion_type='all', limit=15):
    """
    Get smart suggestions for autocomplete based on query
    Returns categorized suggestions for patient names, IDs, dates, and modalities
    """
    try:
        from .database_operations import get_database_connection
        
        # Build categorized suggestions to match frontend expectations
        results = {
            'success': True,
            'suggestions': {
                'patient_names': [],
                'patient_ids': [],
                'study_dates': [],
                'modalities': []
            }
        }
        
        if not query or len(query) < 1:
            return results
        
        conn = get_database_connection()
        if not conn:
            return results
        
        cursor = conn.cursor()
        query_pattern = f"%{query}%"

        # If the query is fully numeric, treat it as a DOB partial match and
        # only return birth-date based suggestions. Do NOT return patient_id suggestions.
        is_numeric = query.isdigit()
        if is_numeric:
            try:
                # Determine which birth-related column exists in the patients table
                birth_cols = ['birth_date', 'patient_birth_date', 'patient_birthdate', 'birthdate', 'dob']
                available_birth_cols = []
                try:
                    cursor.execute("PRAGMA table_info(patients)")
                    cols = [r[1] for r in cursor.fetchall()]
                    for bc in birth_cols:
                        if bc in cols:
                            available_birth_cols.append(bc)
                except Exception:
                    available_birth_cols = birth_cols

                pattern = f"%{query}%"
                matched = 0
                # Query matching birth columns using REPLACE to ignore dashes
                for bc in available_birth_cols:
                    try:
                        sql = f"SELECT DISTINCT patient_name, patient_id, {bc} FROM patients WHERE REPLACE({bc}, '-', '') LIKE ? AND {bc} != '' LIMIT ?"
                        cursor.execute(sql, (pattern, limit))
                        rows = cursor.fetchall()
                        for row in rows:
                            name = row[0] or ''
                            pid = row[1] or ''
                            bdate = row[2] or ''
                            bdisp = bdate
                            if bdate and len(bdate) == 8 and isinstance(bdate, str) and bdate.isdigit():
                                bdisp = f"{bdate[0:4]}-{bdate[4:6]}-{bdate[6:8]}"
                            results['suggestions']['patient_names'].append({
                                'text': name,
                                'count': 1,
                                # Do not surface patient_id when query is numeric (DOB search)
                                'display': f"{name} - {bdisp}"
                            })
                            matched += 1
                        if matched:
                            break
                    except Exception:
                        continue

                # Also provide matching birth dates as study_dates suggestions
                try:
                    for bc in available_birth_cols:
                        sql = f"SELECT DISTINCT {bc} FROM patients WHERE REPLACE({bc}, '-', '') LIKE ? AND {bc} != '' LIMIT ?"
                        cursor.execute(sql, (pattern, min(limit, 10)))
                        for row in cursor.fetchall():
                            sd = row[0]
                            formatted = sd
                            if sd and len(sd) == 8 and sd.isdigit():
                                formatted = f"{sd[0:4]}-{sd[4:6]}-{sd[6:8]}"
                            results['suggestions']['study_dates'].append({'text': sd, 'count': 1, 'formatted': formatted})
                        if results['suggestions']['study_dates']:
                            break
                except Exception:
                    pass

                conn.close()
                return results
            except Exception as e:
                logger.debug(f"Numeric DOB suggestion processing failed: {e}")
                conn.close()
                return results

        
        # Get patient name suggestions
        if suggestion_type in ['all', 'patient_name']:
            try:
                cursor.execute("""
                    SELECT DISTINCT patient_name, patient_id
                    FROM patients
                    WHERE patient_name LIKE ? AND patient_name != ''
                    ORDER BY patient_name
                    LIMIT ?
                """, (query_pattern, limit))
                
                for row in cursor.fetchall():
                    results['suggestions']['patient_names'].append({
                        'text': row[0],
                        'count': 1,
                        'display': f"{row[0]} - {row[1]}"
                    })
            except Exception as e:
                logger.error(f"Error getting patient name suggestions: {e}")
        
        # Get patient ID suggestions
        if suggestion_type in ['all', 'patient_id']:
            try:
                cursor.execute("""
                    SELECT DISTINCT patient_id, patient_name
                    FROM patients
                    WHERE patient_id LIKE ? AND patient_id != ''
                    ORDER BY patient_id
                    LIMIT ?
                """, (query_pattern, limit))
                
                for row in cursor.fetchall():
                    results['suggestions']['patient_ids'].append({
                        'text': row[0],
                        'count': 1,
                        'display': f"ID - {row[0]} - {row[1]}"
                    })
            except Exception as e:
                logger.error(f"Error getting patient ID suggestions: {e}")
        
        # Get patient birth date suggestions
        if suggestion_type in ['all', 'birth_date']:
            try:
                cursor.execute("""
                    SELECT DISTINCT birth_date, patient_name, patient_id
                    FROM patients
                    WHERE birth_date LIKE ? AND birth_date != ''
                    ORDER BY birth_date
                    LIMIT ?
                """, (query_pattern, min(limit, 10)))
                
                for row in cursor.fetchall():
                    results['suggestions']['study_dates'].append({
                        'text': row[0],
                        'count': 1,
                        'formatted': row[0]
                    })
            except Exception as e:
                logger.error(f"Error getting birth date suggestions: {e}")
        
        # Get study date suggestions (for date-based searches)
        if suggestion_type in ['all', 'study_date']:
            try:
                cursor.execute("""
                    SELECT DISTINCT study_date, COUNT(*) as count
                    FROM patient_studies
                    WHERE study_date LIKE ? AND study_date != ''
                    GROUP BY study_date
                    ORDER BY study_date DESC
                    LIMIT ?
                """, (query_pattern, min(limit, 10)))
                
                for row in cursor.fetchall():
                    # row[0] is study_date stored as YYYYMMDD or YYYY-MM-DD
                    sd = row[0]
                    # create a formatted version for display
                    formatted = sd
                    if sd and len(sd) == 8 and sd.isdigit():
                        formatted = f"{sd[0:4]}-{sd[4:6]}-{sd[6:8]}"
                    results['suggestions']['study_dates'].append({
                        'text': row[0],
                        'count': row[1],
                        'formatted': formatted
                    })
            except Exception as e:
                logger.error(f"Error getting study date suggestions: {e}")
        
        # Get modality suggestions
        if suggestion_type in ['all', 'modality']:
            try:
                cursor.execute("""
                    SELECT DISTINCT modality, COUNT(*) as count
                    FROM patient_studies
                    WHERE modality LIKE ? AND modality != ''
                    GROUP BY modality
                    ORDER BY count DESC
                    LIMIT ?
                """, (query_pattern, min(limit, 10)))
                
                for row in cursor.fetchall():
                    results['suggestions']['modalities'].append({
                        'text': row[0],
                        'count': row[1]
                    })
            except Exception as e:
                logger.error(f"Error getting modality suggestions: {e}")
        
        conn.close()
        return results
        
    except Exception as e:
        logger.error(f"Error getting smart suggestions: {e}")
        return {
            'success': False,
            'error': str(e),
            'suggestions': []
        }