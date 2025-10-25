#!/usr/bin/env python3
"""
Direct DICOM Import Script for Felix Maxwell
============================================
This script directly imports Felix Maxwell's DICOM files from Z:\639380-20250922-* into Orthanc
"""

import os
import sys
import requests
import glob
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def import_felix_maxwell_dicoms():
    """Import Felix Maxwell's DICOM files directly to Orthanc"""
    
    # Configuration
    orthanc_url = "http://localhost:8042"
    felix_folder_pattern = "Z:\\639380-20250922-*"
    
    try:
        # Find Felix Maxwell's folder
        felix_folders = glob.glob(felix_folder_pattern)
        
        if not felix_folders:
            logger.error(f"❌ No folders found matching pattern: {felix_folder_pattern}")
            return False
        
        felix_folder = felix_folders[0]
        logger.info(f"📁 Found Felix Maxwell's folder: {felix_folder}")
        
        # Find all DICOM files in the folder
        dicom_files = []
        for root, dirs, files in os.walk(felix_folder):
            for file in files:
                file_path = os.path.join(root, file)
                # DICOM files often have no extension or various extensions
                dicom_files.append(file_path)
        
        logger.info(f"🔍 Found {len(dicom_files)} files in Felix Maxwell's folder")
        
        if not dicom_files:
            logger.error("❌ No files found in Felix Maxwell's folder")
            return False
        
        # Import each file to Orthanc
        imported_count = 0
        failed_count = 0
        
        for i, file_path in enumerate(dicom_files, 1):
            try:
                logger.info(f"📤 Importing file {i}/{len(dicom_files)}: {os.path.basename(file_path)}")
                
                # Read file content
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                # Import to Orthanc
                response = requests.post(
                    f"{orthanc_url}/instances",
                    data=file_content,
                    headers={'Content-Type': 'application/dicom'},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    instance_id = result.get('ID', 'Unknown')
                    logger.info(f"✅ Successfully imported: {instance_id}")
                    imported_count += 1
                else:
                    logger.error(f"❌ Failed to import {file_path}: {response.status_code} - {response.text}")
                    failed_count += 1
                
            except Exception as e:
                logger.error(f"❌ Error importing {file_path}: {e}")
                failed_count += 1
        
        # Summary
        logger.info(f"\n🎉 IMPORT COMPLETE:")
        logger.info(f"✅ Successfully imported: {imported_count} files")
        logger.info(f"❌ Failed imports: {failed_count} files")
        logger.info(f"📊 Success rate: {(imported_count / len(dicom_files)) * 100:.1f}%")
        
        return imported_count > 0
        
    except Exception as e:
        logger.error(f"❌ Fatal error during import: {e}")
        return False

def verify_import():
    """Verify that Felix Maxwell's data is now in Orthanc"""
    try:
        orthanc_url = "http://localhost:8042"
        
        # Get all patients
        response = requests.get(f"{orthanc_url}/patients", timeout=10)
        if response.status_code != 200:
            logger.error(f"❌ Failed to get patients from Orthanc: {response.status_code}")
            return False
        
        patients = response.json()
        logger.info(f"🔍 Orthanc now has {len(patients)} patient(s)")
        
        # Check each patient for Felix Maxwell
        felix_found = False
        for patient_id in patients:
            try:
                patient_response = requests.get(f"{orthanc_url}/patients/{patient_id}", timeout=5)
                if patient_response.status_code == 200:
                    patient_data = patient_response.json()
                    tags = patient_data.get('MainDicomTags', {})
                    patient_name = tags.get('PatientName', '')
                    patient_birth = tags.get('PatientBirthDate', '')
                    
                    logger.info(f"👤 Patient: {patient_name} (DOB: {patient_birth})")
                    
                    # Check if this matches Felix Maxwell
                    if 'FELIX' in patient_name.upper() and 'MAXWELL' in patient_name.upper():
                        felix_found = True
                        logger.info(f"🎉 FOUND FELIX MAXWELL: {patient_name}")
                        
                        # Check birth date
                        if patient_birth == '19610203':  # 03/02/1961
                            logger.info(f"✅ Birth date matches: {patient_birth}")
                        else:
                            logger.warning(f"⚠️ Birth date mismatch: expected 19610203, got {patient_birth}")
                        
                        # Get studies
                        studies = patient_data.get('Studies', [])
                        logger.info(f"📋 Felix Maxwell has {len(studies)} study/studies")
                        
            except Exception as e:
                logger.error(f"❌ Error checking patient {patient_id}: {e}")
        
        if felix_found:
            logger.info("🎉 SUCCESS: Felix Maxwell's data is now in Orthanc!")
            return True
        else:
            logger.error("❌ Felix Maxwell not found in Orthanc")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error verifying import: {e}")
        return False

def main():
    """Main function"""
    logger.info("🇿🇦 Felix Maxwell DICOM Import Tool")
    logger.info("=" * 50)
    
    # Check if Orthanc is running
    try:
        response = requests.get("http://localhost:8042/system", timeout=5)
        if response.status_code == 200:
            logger.info("✅ Orthanc server is running")
        else:
            logger.error("❌ Orthanc server is not responding correctly")
            return
    except:
        logger.error("❌ Cannot connect to Orthanc server")
        return
    
    # Import Felix Maxwell's DICOM files
    logger.info("\n🚀 Starting Felix Maxwell DICOM import...")
    if import_felix_maxwell_dicoms():
        logger.info("\n🔍 Verifying import...")
        if verify_import():
            logger.info("\n🎉 MISSION ACCOMPLISHED! Felix Maxwell's data is now available in the system.")
        else:
            logger.error("\n❌ Import verification failed")
    else:
        logger.error("\n❌ Import failed")

if __name__ == "__main__":
    main()