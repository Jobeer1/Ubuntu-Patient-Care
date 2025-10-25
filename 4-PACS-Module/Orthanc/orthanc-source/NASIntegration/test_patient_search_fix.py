#!/usr/bin/env python3
"""
Test script to verify the patient search fix is working
"""
import requests
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_patient_search():
    """Test the patient search endpoint"""
    try:
        # Test search endpoint
        url = "http://localhost:5000/api/nas/search/patient"
        
        # Test data
        test_data = {
            "patient_id": "",  # Empty search to get all patients
            "study_date": "",
            "modality": ""
        }
        
        # Need to authenticate first
        auth_url = "http://localhost:5000/api/auth/login"
        auth_data = {
            "username": "admin",
            "password": "admin",
            "user_type": "admin"
        }
        
        session = requests.Session()
        
        # Login
        logger.info("Logging in...")
        auth_response = session.post(auth_url, json=auth_data)
        
        if auth_response.status_code == 200:
            logger.info("✅ Login successful")
            
            # Test patient search
            logger.info("Testing patient search...")
            search_response = session.post(url, json=test_data)
            
            if search_response.status_code == 200:
                result = search_response.json()
                logger.info("✅ Patient search successful")
                logger.info(f"Found {result.get('total_found', 0)} patient(s)")
                
                # Print patient details
                for i, patient in enumerate(result.get('patients', []), 1):
                    logger.info(f"Patient {i}:")
                    logger.info(f"  - ID: {patient.get('patient_id', 'N/A')}")
                    logger.info(f"  - Name: {patient.get('name', 'N/A')}")
                    logger.info(f"  - Birth Date: {patient.get('birth_date', 'N/A')}")
                    logger.info(f"  - Sex: {patient.get('sex', 'N/A')}")
                    logger.info(f"  - Studies: {len(patient.get('studies', []))}")
                
                return True
            else:
                logger.error(f"❌ Patient search failed: {search_response.status_code}")
                logger.error(f"Response: {search_response.text}")
                return False
        else:
            logger.error(f"❌ Login failed: {auth_response.status_code}")
            logger.error(f"Response: {auth_response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return False

def test_orthanc_direct():
    """Test Orthanc API directly"""
    try:
        logger.info("Testing Orthanc API directly...")
        
        # Test Orthanc patients endpoint
        patients_url = "http://localhost:8042/patients"
        patients_response = requests.get(patients_url, timeout=5)
        
        if patients_response.status_code == 200:
            patients = patients_response.json()
            logger.info(f"✅ Orthanc has {len(patients)} patients")
            
            # Get details for first patient
            if patients:
                patient_id = patients[0]
                patient_url = f"http://localhost:8042/patients/{patient_id}"
                patient_response = requests.get(patient_url, timeout=5)
                
                if patient_response.status_code == 200:
                    patient_data = patient_response.json()
                    logger.info(f"✅ Patient details retrieved:")
                    logger.info(f"  - Patient ID: {patient_id}")
                    tags = patient_data.get('MainDicomTags', {})
                    logger.info(f"  - Name: {tags.get('PatientName', 'N/A')}")
                    logger.info(f"  - Birth Date: {tags.get('PatientBirthDate', 'N/A')}")
                    logger.info(f"  - Sex: {tags.get('PatientSex', 'N/A')}")
                    logger.info(f"  - Studies: {len(patient_data.get('Studies', []))}")
                    return True
                else:
                    logger.error(f"❌ Failed to get patient details: {patient_response.status_code}")
            else:
                logger.warning("⚠️ No patients found in Orthanc")
                return False
        else:
            logger.error(f"❌ Failed to get patients from Orthanc: {patients_response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Orthanc test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🔍 Testing Patient Search Fix")
    logger.info("=" * 50)
    
    # Test Orthanc directly first
    orthanc_ok = test_orthanc_direct()
    
    logger.info("\n" + "=" * 50)
    
    # Test our application endpoint
    app_ok = test_patient_search()
    
    logger.info("\n" + "=" * 50)
    logger.info("Test Summary:")
    logger.info(f"Orthanc Direct: {'✅ PASS' if orthanc_ok else '❌ FAIL'}")
    logger.info(f"App Endpoint: {'✅ PASS' if app_ok else '❌ FAIL'}")
    
    if orthanc_ok and app_ok:
        logger.info("🎉 All tests passed! Patient search is working.")
    else:
        logger.error("❌ Some tests failed. Check the logs above.")