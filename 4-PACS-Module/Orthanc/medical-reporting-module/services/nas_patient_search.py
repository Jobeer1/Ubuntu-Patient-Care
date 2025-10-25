"""
NAS Patient Search Service
Comprehensive patient search across NAS database, Orthanc, and direct folder scanning
"""

import os
import logging
import requests
from pathlib import Path
from .nas_database_operations import search_patients_in_database

logger = logging.getLogger(__name__)

# NAS configuration
NAS_BASE_PATH = r"\\TRUENAS\Medical_Images\Patients"
ORTHANC_URL = "http://localhost:8042"

def search_patient_comprehensive(search_data):
    """
    Comprehensive patient search using three-tier approach:
    1. NAS database search
    2. Orthanc PACS search
    3. Direct folder scanning
    """
    try:
        results = {
            'success': True,
            'patients': [],
            'total_found': 0,
            'sources_searched': []
        }
        
        # Extract search parameters
        patient_id = search_data.get('patient_id', '').strip()
        patient_name = search_data.get('patient_name', '').strip()
        study_date = search_data.get('study_date', '').strip()
        
        logger.info(f"🔍 Starting comprehensive search: ID={patient_id}, Name={patient_name}, Date={study_date}")
        
        # 1. Search NAS database first
        try:
            db_results = search_patients_in_database({
                'patient_id': patient_id,
                'patient_name': patient_name,
                'study_date': study_date
            })
            results['patients'].extend(db_results)
            results['sources_searched'].append('nas_database')
            logger.info(f"📊 Database search found {len(db_results)} patients")
        except Exception as e:
            logger.error(f"Database search failed: {e}")
        
        # 2. Search Orthanc PACS
        try:
            orthanc_results = search_orthanc_patients(patient_id, patient_name, study_date)
            # Merge results, avoiding duplicates
            for orthanc_patient in orthanc_results:
                if not any(p.get('patient_id') == orthanc_patient.get('patient_id') 
                          for p in results['patients']):
                    results['patients'].append(orthanc_patient)
            results['sources_searched'].append('orthanc_pacs')
            logger.info(f"🏥 Orthanc search found {len(orthanc_results)} patients")
        except Exception as e:
            logger.error(f"Orthanc search failed: {e}")
        
        # 3. Direct folder search as fallback
        if len(results['patients']) < 10:  # Only if we need more results
            try:
                folder_results = search_nas_folders_direct(patient_id, patient_name)
                # Merge results, avoiding duplicates
                for folder_patient in folder_results:
                    if not any(p.get('folder_path') == folder_patient.get('folder_path') 
                              for p in results['patients']):
                        results['patients'].append(folder_patient)
                results['sources_searched'].append('direct_folders')
                logger.info(f"📁 Direct folder search found {len(folder_results)} patients")
            except Exception as e:
                logger.error(f"Direct folder search failed: {e}")
        
        # Sort results by relevance and date
        results['patients'] = sort_search_results(results['patients'], patient_id, patient_name)
        results['total_found'] = len(results['patients'])
        
        logger.info(f"✅ Comprehensive search complete: {results['total_found']} patients found")
        return results
        
    except Exception as e:
        logger.error(f"Comprehensive search error: {e}")
        return {
            'success': False,
            'error': str(e),
            'patients': [],
            'total_found': 0
        }

def search_orthanc_patients(patient_id="", patient_name="", study_date=""):
    """Search for patients in Orthanc PACS"""
    try:
        # Build Orthanc query
        query = {}
        if patient_id:
            query['PatientID'] = f"*{patient_id}*"
        if patient_name:
            query['PatientName'] = f"*{patient_name}*"
        if study_date:
            query['StudyDate'] = study_date
        
        if not query:
            query = {'PatientName': '*'}  # Get all if no specific criteria
        
        # Query Orthanc
        response = requests.post(
            f"{ORTHANC_URL}/tools/find",
            json={
                "Level": "Patient",
                "Query": query,
                "Expand": True
            },
            timeout=10
        )
        
        if response.status_code == 200:
            orthanc_patients = response.json()
            results = []
            
            for patient in orthanc_patients:
                main_tags = patient.get('MainDicomTags', {})
                results.append({
                    'patient_id': main_tags.get('PatientID', 'Unknown'),
                    'patient_name': main_tags.get('PatientName', 'Unknown'),
                    'patient_birth_date': main_tags.get('PatientBirthDate', ''),
                    'patient_sex': main_tags.get('PatientSex', ''),
                    'orthanc_id': patient.get('ID', ''),
                    'study_count': len(patient.get('Studies', [])),
                    'source': 'orthanc'
                })
            
            return results
        else:
            logger.warning(f"Orthanc search failed: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"Orthanc search error: {e}")
        return []

def search_nas_folders_direct(patient_id="", patient_name=""):
    """Direct search of NAS folder structure"""
    try:
        if not os.path.exists(NAS_BASE_PATH):
            logger.warning(f"NAS path not accessible: {NAS_BASE_PATH}")
            return []
        
        results = []
        search_terms = []
        
        if patient_id:
            search_terms.append(patient_id.lower())
        if patient_name:
            search_terms.extend(patient_name.lower().split())
        
        # Scan patient folders
        for patient_folder in os.listdir(NAS_BASE_PATH):
            folder_path = os.path.join(NAS_BASE_PATH, patient_folder)
            
            if not os.path.isdir(folder_path):
                continue
            
            # Check if folder matches search terms
            folder_lower = patient_folder.lower()
            matches = not search_terms or any(term in folder_lower for term in search_terms)
            
            if matches:
                # Count DICOM files
                dicom_count = count_dicom_files(folder_path)
                
                if dicom_count > 0:
                    # Try to extract patient info from folder name
                    patient_info = parse_patient_folder_name(patient_folder)
                    
                    results.append({
                        'patient_id': patient_info.get('patient_id', patient_folder),
                        'patient_name': patient_info.get('patient_name', patient_folder),
                        'folder_path': folder_path,
                        'folder_name': patient_folder,
                        'file_count': dicom_count,
                        'source': 'direct_folder'
                    })
                    
                    if len(results) >= 20:  # Limit results
                        break
        
        return results
        
    except Exception as e:
        logger.error(f"Direct folder search error: {e}")
        return []

def count_dicom_files(folder_path):
    """Count DICOM files in a folder"""
    try:
        count = 0
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.dcm', '.dicom')) or '.' not in file:
                    count += 1
            if count > 100:  # Stop counting after 100 for performance
                break
        return count
    except:
        return 0

def parse_patient_folder_name(folder_name):
    """Try to extract patient ID and name from folder name"""
    try:
        # Common patterns: "ID_Name", "Name_ID", "ID - Name", etc.
        if '_' in folder_name:
            parts = folder_name.split('_', 1)
            if len(parts) == 2:
                # Determine which is ID and which is name
                if parts[0].isdigit() or len(parts[0]) < 10:
                    return {'patient_id': parts[0], 'patient_name': parts[1]}
                else:
                    return {'patient_id': parts[1], 'patient_name': parts[0]}
        
        if ' - ' in folder_name:
            parts = folder_name.split(' - ', 1)
            if len(parts) == 2:
                return {'patient_id': parts[0], 'patient_name': parts[1]}
        
        # Default: use folder name as both ID and name
        return {'patient_id': folder_name, 'patient_name': folder_name}
        
    except:
        return {'patient_id': folder_name, 'patient_name': folder_name}

def sort_search_results(patients, patient_id="", patient_name=""):
    """Sort search results by relevance"""
    try:
        def relevance_score(patient):
            score = 0
            p_id_raw = patient.get('patient_id')
            p_name_raw = patient.get('patient_name')
            p_id = (p_id_raw or '').lower()
            p_name = (p_name_raw or '').lower()
            
            # Exact matches get highest score
            if patient_id and patient_id.lower() == p_id:
                score += 100
            elif patient_id and patient_id.lower() in p_id:
                score += 50
            
            if patient_name and (patient_name or '').lower() == p_name:
                score += 100
            elif patient_name and (patient_name or '').lower() in p_name:
                score += 50
            
            # Prefer database sources
            if patient.get('source') == 'database':
                score += 20
            elif patient.get('source') == 'orthanc':
                score += 15
            
            return score
        
        return sorted(patients, key=relevance_score, reverse=True)
        
    except Exception as e:
        logger.error(f"Error sorting results: {e}")
        return patients