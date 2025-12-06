"""
NAS DICOM Integration Service
Handles Orthanc PACS integration, Study UID management, and DICOM operations
"""

import os
import logging
import requests
import tempfile
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

ORTHANC_URL = "http://localhost:8042"

def check_orthanc_connection():
    """Check if Orthanc server is accessible"""
    try:
        response = requests.get(f"{ORTHANC_URL}/system", timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Orthanc connection failed: {e}")
        return False

def upload_dicom_to_orthanc(dicom_file_path):
    """Upload DICOM file to Orthanc and return Study UID"""
    try:
        if not os.path.exists(dicom_file_path):
            logger.error(f"DICOM file not found: {dicom_file_path}")
            return None
        
        # Read DICOM file
        with open(dicom_file_path, 'rb') as f:
            dicom_data = f.read()
        
        # Upload to Orthanc
        response = requests.post(
            f"{ORTHANC_URL}/instances",
            data=dicom_data,
            headers={'Content-Type': 'application/dicom'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            instance_id = result.get('ID')
            
            if instance_id:
                # Get study information
                study_info = get_study_info_from_instance(instance_id)
                if study_info:
                    logger.info(f"📤 DICOM uploaded successfully: {study_info['StudyInstanceUID']}")
                    return study_info['StudyInstanceUID']
        
        logger.error(f"Failed to upload DICOM: {response.status_code}")
        return None
        
    except Exception as e:
        logger.error(f"Error uploading DICOM: {e}")
        return None

def get_study_info_from_instance(instance_id):
    """Get study information from an Orthanc instance"""
    try:
        # Get instance details
        response = requests.get(f"{ORTHANC_URL}/instances/{instance_id}")
        if response.status_code != 200:
            return None
        
        instance_info = response.json()
        study_id = instance_info.get('ParentStudy')
        
        if study_id:
            # Get study details
            study_response = requests.get(f"{ORTHANC_URL}/studies/{study_id}")
            if study_response.status_code == 200:
                study_info = study_response.json()
                main_tags = study_info.get('MainDicomTags', {})
                
                return {
                    'StudyInstanceUID': main_tags.get('StudyInstanceUID'),
                    'StudyID': main_tags.get('StudyID'),
                    'StudyDate': main_tags.get('StudyDate'),
                    'StudyDescription': main_tags.get('StudyDescription', ''),
                    'PatientName': study_info.get('PatientMainDicomTags', {}).get('PatientName', ''),
                    'PatientID': study_info.get('PatientMainDicomTags', {}).get('PatientID', ''),
                    'orthanc_study_id': study_id
                }
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting study info: {e}")
        return None

def upload_patient_folder_to_orthanc(folder_path):
    """Upload all DICOM files in a patient folder to Orthanc"""
    try:
        if not os.path.exists(folder_path):
            logger.error(f"Patient folder not found: {folder_path}")
            return None
        
        study_uids = set()
        uploaded_count = 0
        
        # Find all DICOM files
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check if it's likely a DICOM file
                if (file.lower().endswith(('.dcm', '.dicom')) or 
                    ('.' not in file and os.path.getsize(file_path) > 1024)):
                    
                    study_uid = upload_dicom_to_orthanc(file_path)
                    if study_uid:
                        study_uids.add(study_uid)
                        uploaded_count += 1
                    
                    # Limit uploads to prevent overwhelming
                    if uploaded_count >= 50:
                        logger.warning(f"Upload limit reached: {uploaded_count} files")
                        break
            
            if uploaded_count >= 50:
                break
        
        logger.info(f"📤 Uploaded {uploaded_count} DICOM files, {len(study_uids)} unique studies")
        return list(study_uids)[0] if study_uids else None
        
    except Exception as e:
        logger.error(f"Error uploading patient folder: {e}")
        return None

def get_patient_name_from_study(study_uid):
    """Get patient name from Orthanc study UID"""
    try:
        # Find study by Study Instance UID
        response = requests.post(
            f"{ORTHANC_URL}/tools/find",
            json={
                "Level": "Study",
                "Query": {"StudyInstanceUID": study_uid},
                "Expand": True
            },
            timeout=10
        )
        
        if response.status_code == 200:
            studies = response.json()
            if studies:
                study = studies[0]
                patient_tags = study.get('PatientMainDicomTags', {})
                patient_name = patient_tags.get('PatientName', 'Unknown Patient')
                return patient_name
        
        return 'Unknown Patient'
        
    except Exception as e:
        logger.error(f"Error getting patient name: {e}")
        return 'Unknown Patient'

def create_orthanc_study_uid():
    """Create a new Study Instance UID (placeholder implementation)"""
    try:
        # In a real implementation, this would create a proper DICOM UID
        # For now, return a placeholder
        import uuid
        base_uid = "1.2.840.113619.2.176.2025"  # Example root UID
        unique_part = str(uuid.uuid4()).replace('-', '')[:12]
        return f"{base_uid}.{unique_part}"
        
    except Exception as e:
        logger.error(f"Error creating Study UID: {e}")
        return None

def get_orthanc_studies():
    """Get all studies from Orthanc"""
    try:
        response = requests.get(f"{ORTHANC_URL}/studies", timeout=10)
        if response.status_code == 200:
            studies = response.json()
            
            study_list = []
            for study_id in studies:
                # Get study details
                study_response = requests.get(f"{ORTHANC_URL}/studies/{study_id}")
                if study_response.status_code == 200:
                    study_info = study_response.json()
                    main_tags = study_info.get('MainDicomTags', {})
                    patient_tags = study_info.get('PatientMainDicomTags', {})
                    
                    study_list.append({
                        'orthanc_id': study_id,
                        'study_uid': main_tags.get('StudyInstanceUID', ''),
                        'study_date': main_tags.get('StudyDate', ''),
                        'study_description': main_tags.get('StudyDescription', ''),
                        'patient_name': patient_tags.get('PatientName', ''),
                        'patient_id': patient_tags.get('PatientID', ''),
                        'series_count': len(study_info.get('Series', []))
                    })
            
            return study_list
        
        return []
        
    except Exception as e:
        logger.error(f"Error getting Orthanc studies: {e}")
        return []

def download_study_from_orthanc(study_uid, output_path):
    """Download a complete study from Orthanc as ZIP"""
    try:
        # Find study by UID
        response = requests.post(
            f"{ORTHANC_URL}/tools/find",
            json={
                "Level": "Study",
                "Query": {"StudyInstanceUID": study_uid}
            },
            timeout=10
        )
        
        if response.status_code == 200:
            studies = response.json()
            if studies:
                study_id = studies[0]
                
                # Download study as ZIP
                zip_response = requests.get(
                    f"{ORTHANC_URL}/studies/{study_id}/archive",
                    timeout=60
                )
                
                if zip_response.status_code == 200:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(zip_response.content)
                    
                    logger.info(f"📦 Study downloaded: {study_uid}")
                    return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error downloading study: {e}")
        return False