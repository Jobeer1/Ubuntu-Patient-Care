#!/usr/bin/env python3
"""
Create DICOM file for Felix Maxwell to match the medical report
"""
import os
import sys
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_felix_maxwell_dicom():
    """Create a DICOM file for Felix Maxwell matching the report"""
    try:
        # Try to import pydicom
        try:
            import pydicom
            from pydicom.dataset import Dataset, FileDataset
            from pydicom.uid import ExplicitVRLittleEndian, generate_uid
        except ImportError:
            logger.error("❌ pydicom not installed. Installing it now...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pydicom"])
            import pydicom
            from pydicom.dataset import Dataset, FileDataset
            from pydicom.uid import ExplicitVRLittleEndian, generate_uid
        
        logger.info("🏥 Creating DICOM file for Felix Maxwell...")
        
        # Create the file meta information dataset
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.1"  # CT Image Storage
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.ImplementationClassUID = "1.2.840.113619.6.5"
        file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        
        # Create the main dataset
        ds = FileDataset(
            filename="felix_maxwell_ct_scan.dcm",
            dataset={},
            file_meta=file_meta,
            preamble=b"\0" * 128
        )
        
        # Patient Information
        ds.PatientName = "MAXWELL^FELIX"
        ds.PatientID = "N0044905"
        ds.PatientBirthDate = "19610203"  # 03/02/1961 in DICOM format
        ds.PatientSex = "M"
        
        # Study Information
        ds.StudyDate = "20250922"  # 22/09/2025
        ds.StudyTime = "120000"    # 12:00:00
        ds.StudyDescription = "MEDICAL EXAMINATION"
        ds.StudyInstanceUID = generate_uid()
        ds.StudyID = "1"
        ds.AccessionNumber = "N0044905"
        
        # Series Information
        ds.SeriesDate = "20250922"
        ds.SeriesTime = "120000"
        ds.SeriesDescription = "CT SCAN"
        ds.SeriesInstanceUID = generate_uid()
        ds.SeriesNumber = "1"
        ds.Modality = "CT"
        
        # Instance Information
        ds.InstanceNumber = "1"
        ds.SOPInstanceUID = generate_uid()
        ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.1"
        
        # Image Information
        ds.ImageType = ["ORIGINAL", "PRIMARY", "AXIAL"]
        ds.Rows = 512
        ds.Columns = 512
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 0
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        
        # Referring Physician
        ds.ReferringPhysicianName = "CHARLTON^G^DR"
        
        # Institution
        ds.InstitutionName = "UBUNTU PATIENT CARE"
        ds.InstitutionAddress = "SOUTH AFRICA"
        
        # Create pixel data (simple gradient for demonstration)
        import numpy as np
        pixel_array = np.zeros((512, 512), dtype=np.uint16)
        
        # Create a simple pattern to simulate medical image
        for i in range(512):
            for j in range(512):
                # Create circular pattern
                center_x, center_y = 256, 256
                distance = ((i - center_x) ** 2 + (j - center_y) ** 2) ** 0.5
                if distance < 200:
                    pixel_array[i, j] = int(32768 + distance * 100)
                else:
                    pixel_array[i, j] = 1000
        
        ds.PixelData = pixel_array.tobytes()
        
        # Set proper file paths
        orthanc_storage = "C:\\Users\\Admin\\Desktop\\ELC\\Ubuntu-Patient-Care\\Orthanc\\orthanc-source\\NASIntegration\\backend\\orthanc-storage"
        dicom_folder = "C:\\Users\\Admin\\Desktop\\ELC\\Ubuntu-Patient-Care\\Orthanc\\dicom_files"
        
        # Create directories if they don't exist
        os.makedirs(dicom_folder, exist_ok=True)
        
        # Save the DICOM file
        dicom_path = os.path.join(dicom_folder, "felix_maxwell_ct_scan.dcm")
        ds.save_as(dicom_path)
        
        logger.info(f"✅ DICOM file created: {dicom_path}")
        logger.info(f"Patient: {ds.PatientName}")
        logger.info(f"Patient ID: {ds.PatientID}")
        logger.info(f"Birth Date: {ds.PatientBirthDate}")
        logger.info(f"Study Date: {ds.StudyDate}")
        logger.info(f"Modality: {ds.Modality}")
        
        return dicom_path
        
    except Exception as e:
        logger.error(f"❌ Failed to create DICOM file: {e}")
        return None

def upload_to_orthanc(dicom_path):
    """Upload the DICOM file to Orthanc"""
    try:
        import requests
        
        logger.info("📤 Uploading DICOM file to Orthanc...")
        
        orthanc_url = "http://localhost:8042/instances"
        
        # Read the DICOM file
        with open(dicom_path, 'rb') as f:
            dicom_data = f.read()
        
        # Upload to Orthanc
        response = requests.post(
            orthanc_url,
            data=dicom_data,
            headers={'Content-Type': 'application/dicom'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ DICOM uploaded successfully!")
            logger.info(f"Instance ID: {result.get('ID', 'Unknown')}")
            logger.info(f"Patient ID: {result.get('ParentPatient', 'Unknown')}")
            return True
        else:
            logger.error(f"❌ Upload failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Upload error: {e}")
        return False

def verify_patient_data():
    """Verify that Felix Maxwell is now in Orthanc"""
    try:
        import requests
        
        logger.info("🔍 Verifying patient data in Orthanc...")
        
        # Get all patients
        patients_url = "http://localhost:8042/patients"
        patients_response = requests.get(patients_url, timeout=10)
        
        if patients_response.status_code == 200:
            patients = patients_response.json()
            logger.info(f"Total patients in Orthanc: {len(patients)}")
            
            # Search for Felix Maxwell
            for patient_id in patients:
                patient_url = f"http://localhost:8042/patients/{patient_id}"
                patient_response = requests.get(patient_url, timeout=5)
                
                if patient_response.status_code == 200:
                    patient_data = patient_response.json()
                    tags = patient_data.get('MainDicomTags', {})
                    
                    patient_name = tags.get('PatientName', '')
                    patient_dicom_id = tags.get('PatientID', '')
                    birth_date = tags.get('PatientBirthDate', '')
                    
                    logger.info(f"Patient: {patient_name} (ID: {patient_dicom_id}, DOB: {birth_date})")
                    
                    if "FELIX" in patient_name.upper() or "MAXWELL" in patient_name.upper():
                        logger.info("✅ FELIX MAXWELL FOUND!")
                        return True
            
            logger.warning("⚠️ Felix Maxwell not found in patient list")
            return False
        else:
            logger.error(f"❌ Failed to get patients: {patients_response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🏥 FELIX MAXWELL DICOM CREATOR")
    logger.info("Creating DICOM file to match medical report")
    logger.info("=" * 50)
    
    # Create the DICOM file
    dicom_path = create_felix_maxwell_dicom()
    
    if dicom_path:
        logger.info("\n" + "=" * 50)
        
        # Upload to Orthanc
        upload_success = upload_to_orthanc(dicom_path)
        
        if upload_success:
            logger.info("\n" + "=" * 50)
            
            # Verify the data
            verify_success = verify_patient_data()
            
            if verify_success:
                logger.info("\n🎉 SUCCESS! Felix Maxwell is now in the system!")
                logger.info("You can now search for the patient in the web interface.")
            else:
                logger.error("\n❌ Verification failed - patient may not have been imported correctly")
        else:
            logger.error("\n❌ Upload failed - DICOM file was not imported to Orthanc")
    else:
        logger.error("\n❌ Failed to create DICOM file")