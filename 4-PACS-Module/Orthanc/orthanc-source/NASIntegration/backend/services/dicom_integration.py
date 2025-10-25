"""
DICOM Integration Service
Handles Orthanc integration and DICOM file operations
"""

import logging
import os
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

def upload_patient_to_orthanc(patient_data):
    """Upload patient DICOM files to Orthanc and return Study UID"""
    try:
        if not patient_data or not patient_data.get('folder_path'):
            raise Exception("No patient data or folder path provided")
        
        folder_path = patient_data['folder_path']
        orthanc_url = "http://localhost:8042"
        
        logger.info(f"📤 Uploading patient files from: {folder_path}")
        
        # Find DICOM files in the patient folder
        dicom_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.dcm', '.dicom', '.ima')) or not '.' in file:
                    dicom_files.append(os.path.join(root, file))
        
        if not dicom_files:
            raise Exception(f"No DICOM files found in {folder_path}")
        
        logger.info(f"📁 Found {len(dicom_files)} DICOM files to upload")
        
        study_uid = None
        uploaded_count = 0
        
        # Upload each DICOM file
        for dicom_file in dicom_files[:50]:  # Limit to first 50 files for performance
            try:
                with open(dicom_file, 'rb') as f:
                    files = {'file': f}
                    response = requests.post(f"{orthanc_url}/instances", files=files, timeout=30)
                    
                    if response.status_code == 200:
                        uploaded_count += 1
                        instance_data = response.json()
                        
                        # Get Study UID from the first successful upload
                        if not study_uid and 'ParentStudy' in instance_data:
                            study_response = requests.get(f"{orthanc_url}/studies/{instance_data['ParentStudy']}")
                            if study_response.status_code == 200:
                                study_info = study_response.json()
                                study_uid = study_info['MainDicomTags']['StudyInstanceUID']
                                logger.info(f"✅ Got Study UID: {study_uid}")
                                
                    elif response.status_code == 409:
                        # File already exists in Orthanc - this is okay
                        logger.debug(f"File already exists: {os.path.basename(dicom_file)}")
                    else:
                        logger.warning(f"Upload failed for {dicom_file}: {response.status_code}")
                        
            except Exception as e:
                logger.error(f"Error uploading {dicom_file}: {e}")
                continue
        
        logger.info(f"✅ Uploaded {uploaded_count} DICOM files to Orthanc")
        
        if not study_uid:
            # Try to find existing study by patient name/ID
            study_uid = find_existing_study_in_orthanc(patient_data)
        
        if not study_uid:
            raise Exception("Failed to get Study UID after upload")
        
        return study_uid
        
    except Exception as e:
        logger.error(f"Orthanc upload error: {e}")
        raise

def find_existing_study_in_orthanc(patient_data):
    """Find existing study in Orthanc by patient information"""
    try:
        orthanc_url = "http://localhost:8042"
        
        studies_response = requests.get(f"{orthanc_url}/studies")
        if studies_response.status_code == 200:
            studies = studies_response.json()
            
            for study in studies[-10:]:  # Check last 10 studies
                study_info_response = requests.get(f"{orthanc_url}/studies/{study}")
                if study_info_response.status_code == 200:
                    study_info = study_info_response.json()
                    patient_name = study_info['PatientMainDicomTags'].get('PatientName', '')
                    patient_id = study_info['PatientMainDicomTags'].get('PatientID', '')
                    
                    # Match by patient name or ID
                    if (patient_data.get('patient_name', '').upper() in patient_name.upper() or
                        patient_data.get('patient_name', '').replace(' ', '^') in patient_name or
                        patient_data.get('patient_id', '') == patient_id):
                        study_uid = study_info['MainDicomTags']['StudyInstanceUID']
                        logger.info(f"✅ Found existing Study UID: {study_uid}")
                        return study_uid
                        
        return None
        
    except Exception as e:
        logger.error(f"Error finding existing study: {e}")
        return None

def get_study_info_from_orthanc(study_uid):
    """Get study information from Orthanc"""
    try:
        orthanc_url = "http://localhost:8042"
        response = requests.get(f"{orthanc_url}/studies/{study_uid}")
        
        if response.status_code == 200:
            return response.json()
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting study info: {e}")
        return None

def get_patient_name_from_study(study_uid):
    """Get patient name from Orthanc study"""
    try:
        study = get_study_info_from_orthanc(study_uid)
        if study:
            patient_name = study.get('PatientMainDicomTags', {}).get('PatientName', 'Medical Patient')
            return patient_name.replace('^', ' ')  # Convert DICOM format to readable
        
        return 'Medical Patient'
        
    except Exception as e:
        logger.error(f"Error getting patient name: {e}")
        return 'Medical Patient'

def check_orthanc_connection():
    """Check if Orthanc is accessible"""
    try:
        response = requests.get("http://localhost:8042/system", timeout=5)
        return response.status_code == 200
    except:
        return False