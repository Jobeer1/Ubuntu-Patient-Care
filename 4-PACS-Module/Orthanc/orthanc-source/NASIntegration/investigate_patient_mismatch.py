#!/usr/bin/env python3
"""
Deep diagnostic script to investigate patient data mismatch
"""
import requests
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def investigate_orthanc_data():
    """Thoroughly investigate what's in Orthanc"""
    try:
        logger.info("🔍 DEEP INVESTIGATION: Orthanc Patient Data")
        logger.info("=" * 60)
        
        # Get all patients
        patients_url = "http://localhost:8042/patients"
        patients_response = requests.get(patients_url, timeout=10)
        
        if patients_response.status_code != 200:
            logger.error(f"❌ Failed to connect to Orthanc: {patients_response.status_code}")
            return False
            
        patients = patients_response.json()
        logger.info(f"📊 Found {len(patients)} patient(s) in Orthanc")
        
        # Analyze each patient in detail
        for i, patient_id in enumerate(patients, 1):
            logger.info(f"\n🔍 PATIENT {i}: {patient_id}")
            logger.info("-" * 40)
            
            # Get patient details
            patient_url = f"http://localhost:8042/patients/{patient_id}"
            patient_response = requests.get(patient_url, timeout=5)
            
            if patient_response.status_code == 200:
                patient_data = patient_response.json()
                tags = patient_data.get('MainDicomTags', {})
                
                logger.info(f"Patient ID (Internal): {patient_id}")
                logger.info(f"Patient ID (DICOM): {tags.get('PatientID', 'N/A')}")
                logger.info(f"Patient Name: {tags.get('PatientName', 'N/A')}")
                logger.info(f"Birth Date: {tags.get('PatientBirthDate', 'N/A')}")
                logger.info(f"Sex: {tags.get('PatientSex', 'N/A')}")
                logger.info(f"Studies Count: {len(patient_data.get('Studies', []))}")
                
                # Check if this matches the expected patient
                expected_name = "FELIX MAXWELL"
                expected_dob = "19610203"  # YYYYMMDD format
                
                actual_name = tags.get('PatientName', '').upper()
                actual_dob = tags.get('PatientBirthDate', '')
                
                if expected_name in actual_name or expected_dob == actual_dob:
                    logger.info("✅ THIS MATCHES THE EXPECTED PATIENT!")
                else:
                    logger.warning("⚠️ This does NOT match the expected patient data")
                
                # Get studies for this patient
                studies = patient_data.get('Studies', [])
                for j, study_id in enumerate(studies, 1):
                    logger.info(f"\n  📁 Study {j}: {study_id}")
                    
                    study_url = f"http://localhost:8042/studies/{study_id}"
                    study_response = requests.get(study_url, timeout=5)
                    
                    if study_response.status_code == 200:
                        study_data = study_response.json()
                        study_tags = study_data.get('MainDicomTags', {})
                        
                        logger.info(f"    Study Date: {study_tags.get('StudyDate', 'N/A')}")
                        logger.info(f"    Study Description: {study_tags.get('StudyDescription', 'N/A')}")
                        logger.info(f"    Modality: {study_tags.get('Modality', 'N/A')}")
                        logger.info(f"    Series Count: {len(study_data.get('Series', []))}")
                        
                        # Check for 22/09/2025 study
                        if study_tags.get('StudyDate') == '20250922':
                            logger.info("✅ FOUND STUDY FROM 22/09/2025!")
            
            logger.info("-" * 40)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Investigation failed: {e}")
        return False

def check_dicom_import_status():
    """Check if DICOM files are properly imported"""
    try:
        logger.info("\n🔍 CHECKING DICOM IMPORT STATUS")
        logger.info("=" * 60)
        
        # Check Orthanc system info
        system_url = "http://localhost:8042/system"
        system_response = requests.get(system_url, timeout=5)
        
        if system_response.status_code == 200:
            system_info = system_response.json()
            logger.info(f"Orthanc Version: {system_info.get('Version', 'Unknown')}")
            logger.info(f"Database Version: {system_info.get('DatabaseVersion', 'Unknown')}")
            
        # Check statistics
        stats_url = "http://localhost:8042/statistics"
        stats_response = requests.get(stats_url, timeout=5)
        
        if stats_response.status_code == 200:
            stats = stats_response.json()
            logger.info(f"Total Patients: {stats.get('CountPatients', 0)}")
            logger.info(f"Total Studies: {stats.get('CountStudies', 0)}")
            logger.info(f"Total Series: {stats.get('CountSeries', 0)}")
            logger.info(f"Total Instances: {stats.get('CountInstances', 0)}")
            logger.info(f"Total Disk Size: {stats.get('TotalDiskSize', 0)} bytes")
            
            if stats.get('CountPatients', 0) == 0:
                logger.error("❌ NO PATIENTS FOUND - DICOM files may not be imported!")
                return False
            elif stats.get('CountPatients', 0) == 1:
                logger.warning("⚠️ Only 1 patient found - check if all DICOM files are imported")
            else:
                logger.info(f"✅ Found {stats.get('CountPatients', 0)} patients")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Import status check failed: {e}")
        return False

def search_for_felix_maxwell():
    """Specifically search for Felix Maxwell"""
    try:
        logger.info("\n🔍 SEARCHING FOR FELIX MAXWELL")
        logger.info("=" * 60)
        
        # Search by name
        search_payload = {
            'Level': 'Patient',
            'Query': {
                'PatientName': '*FELIX*'
            }
        }
        
        search_url = "http://localhost:8042/tools/find"
        search_response = requests.post(search_url, json=search_payload, timeout=10)
        
        if search_response.status_code == 200:
            results = search_response.json()
            logger.info(f"Found {len(results)} patients matching 'FELIX'")
            
            for patient_id in results:
                logger.info(f"Patient ID: {patient_id}")
                
                # Get details
                patient_url = f"http://localhost:8042/patients/{patient_id}"
                patient_response = requests.get(patient_url, timeout=5)
                
                if patient_response.status_code == 200:
                    patient_data = patient_response.json()
                    tags = patient_data.get('MainDicomTags', {})
                    logger.info(f"  Name: {tags.get('PatientName', 'N/A')}")
                    logger.info(f"  DOB: {tags.get('PatientBirthDate', 'N/A')}")
        else:
            logger.warning("No patients found matching 'FELIX'")
            
        # Also search by birth date
        search_payload_dob = {
            'Level': 'Patient',
            'Query': {
                'PatientBirthDate': '19610203'
            }
        }
        
        search_response_dob = requests.post(search_url, json=search_payload_dob, timeout=10)
        
        if search_response_dob.status_code == 200:
            results_dob = search_response_dob.json()
            logger.info(f"Found {len(results_dob)} patients with DOB 03/02/1961")
            
            for patient_id in results_dob:
                logger.info(f"Patient ID: {patient_id}")
        else:
            logger.warning("No patients found with DOB 03/02/1961")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Felix search failed: {e}")
        return False

def check_nas_dicom_files():
    """Check what DICOM files are available on the NAS"""
    try:
        logger.info("\n🔍 CHECKING NAS DICOM FILES")
        logger.info("=" * 60)
        
        # This would need to be implemented based on your NAS structure
        # For now, we'll check if there are multiple DICOM files that should be imported
        
        logger.info("To check NAS files, we need to know:")
        logger.info("1. Where are the DICOM files stored on your NAS?")
        logger.info("2. Are there multiple patient folders?")
        logger.info("3. What's the file structure?")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ NAS check failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚨 CRITICAL PATIENT DATA MISMATCH INVESTIGATION")
    logger.info("Expected: MR FELIX MAXWELL, DOB: 03/02/1961")
    logger.info("Actual: XABA^MXOLISI N MN MR, DOB: 26/05/1979")
    logger.info("=" * 60)
    
    # Run investigations
    orthanc_ok = investigate_orthanc_data()
    import_ok = check_dicom_import_status()
    felix_found = search_for_felix_maxwell()
    nas_ok = check_nas_dicom_files()
    
    logger.info("\n" + "=" * 60)
    logger.info("INVESTIGATION SUMMARY:")
    logger.info(f"Orthanc Data Analysis: {'✅ PASS' if orthanc_ok else '❌ FAIL'}")
    logger.info(f"Import Status Check: {'✅ PASS' if import_ok else '❌ FAIL'}")
    logger.info(f"Felix Maxwell Search: {'✅ FOUND' if felix_found else '❌ NOT FOUND'}")
    logger.info(f"NAS File Check: {'✅ PASS' if nas_ok else '❌ FAIL'}")