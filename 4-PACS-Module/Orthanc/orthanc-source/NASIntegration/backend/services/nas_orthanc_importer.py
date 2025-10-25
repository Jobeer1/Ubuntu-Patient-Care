"""
NAS to Orthanc Auto-Import Service
Automatically imports NAS DICOM patients into Orthanc PACS
"""

import os
import sys
import time
import sqlite3
import logging
import requests
from pathlib import Path
from typing import List, Dict, Optional
import threading

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
ORTHANC_URL = os.environ.get('ORTHANC_URL', 'http://localhost:8042')
ORTHANC_USER = os.environ.get('ORTHANC_USERNAME', 'orthanc')
ORTHANC_PASS = os.environ.get('ORTHANC_PASSWORD', 'orthanc')
try:
    from backend.metadata_db import get_metadata_db_path
    NAS_DB_PATH = get_metadata_db_path()
except Exception:
    try:
        from metadata_db import get_metadata_db_path
        NAS_DB_PATH = get_metadata_db_path()
    except Exception:
        NAS_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'nas_patient_index.db'))
IMPORT_BATCH_SIZE = 10  # Import 10 patients at a time
IMPORT_INTERVAL = 300  # Check every 5 minutes
MAX_IMPORT_PER_RUN = 50  # Maximum patients to import per run
ALLOW_UPLOAD_TO_ORTHANC = os.environ.get('ALLOW_UPLOAD_TO_ORTHANC', 'false').lower() in ('1','true','yes')


class NASOrthancImporter:
    """Service that imports NAS patients into Orthanc PACS"""
    
    def __init__(self):
        self.orthanc_url = ORTHANC_URL
        self.orthanc_auth = (ORTHANC_USER, ORTHANC_PASS)
        # Prefer the orthanc full index if it exists to avoid duplicate indexing
        base = os.path.dirname(os.path.abspath(__file__))
        orthanc_index_path = os.path.join(base, '..', 'orthanc-index', 'index')
        orthanc_index_path = os.path.normpath(orthanc_index_path)

        # Use safe metadata DB (not Orthanc internal index file)
        safe_metadata = NAS_DB_PATH
        self.db_path = safe_metadata
        logger.info(f"🔎 NAS Importer using metadata DB: {self.db_path}")
        self.running = False
        self.import_thread = None
        
    def check_orthanc_connection(self) -> bool:
        """Check if Orthanc is accessible"""
        try:
            response = requests.get(f"{self.orthanc_url}/system", auth=self.orthanc_auth, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Orthanc connection failed: {e}")
            return False
    
    def get_orthanc_patients(self) -> set:
        """Get list of patient IDs already in Orthanc"""
        try:
            response = requests.get(f"{self.orthanc_url}/patients", auth=self.orthanc_auth, timeout=10)
            if response.status_code != 200:
                return set()
            
            patient_ids = []
            for patient_orthanc_id in response.json():
                # Get patient details
                patient_resp = requests.get(
                    f"{self.orthanc_url}/patients/{patient_orthanc_id}",
                    auth=self.orthanc_auth,
                    timeout=5
                )
                if patient_resp.status_code == 200:
                    patient_data = patient_resp.json()
                    main_tags = patient_data.get('MainDicomTags', {})
                    patient_id = main_tags.get('PatientID')
                    if patient_id:
                        patient_ids.append(patient_id)
            
            logger.info(f"📊 Orthanc currently has {len(patient_ids)} patients")
            return set(patient_ids)
        except Exception as e:
            logger.error(f"Failed to get Orthanc patients: {e}")
            return set()
    
    def get_nas_patients_to_import(self, orthanc_patient_ids: set, limit: int = 50) -> List[Dict]:
        """Get NAS patients that are not yet in Orthanc"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()

            patients = []

            # If this DB contains a lightweight patient_studies table, use it
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='patient_studies'")
            if cursor.fetchone():
                cursor.execute('''
                    SELECT DISTINCT patient_id, patient_name, folder_path
                    FROM patient_studies
                    WHERE patient_id IS NOT NULL AND folder_path IS NOT NULL AND folder_path != ''
                    ORDER BY patient_id
                    LIMIT ?
                ''', (limit * 2,))

                for row in cursor.fetchall():
                    patient_id, patient_name, folder_path = row
                    if patient_id in orthanc_patient_ids:
                        continue
                    if not os.path.exists(folder_path):
                        continue
                    patients.append({'patient_id': patient_id, 'patient_name': patient_name, 'folder_path': folder_path})
                    if len(patients) >= limit:
                        break

                conn.close()
                return patients

            # Otherwise, assume this is the full Orthanc index and query MainDicomTags
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='MainDicomTags'")
            if cursor.fetchone():
                # Query distinct PatientID with a representative Source/Identifier path if available
                # MainDicomTags typically contains patient-level tags; DicomIdentifiers or Resources store file refs
                cursor.execute('''
                    SELECT DISTINCT m.PatientID, m.PatientName
                    FROM MainDicomTags m
                    WHERE m.PatientID IS NOT NULL
                    LIMIT ?
                ''', (limit * 2,))

                for row in cursor.fetchall():
                    patient_id, patient_name = row
                    if patient_id in orthanc_patient_ids:
                        continue

                    # Try to find a folder_path or resource pointing to files for this patient
                    folder_path = None
                    try:
                        cursor.execute('''
                            SELECT r.Uri FROM Resources r
                            JOIN DicomIdentifiers di ON di.ResourceId = r.Id
                            WHERE di.PatientID = ? LIMIT 1
                        ''', (patient_id,))
                        r = cursor.fetchone()
                        if r and r[0]:
                            folder_path = r[0]
                    except Exception:
                        folder_path = None

                    # If we couldn't get a folder path, leave it empty; importer will skip missing folders
                    if folder_path and not os.path.exists(folder_path):
                        folder_path = None

                    patients.append({'patient_id': patient_id, 'patient_name': patient_name, 'folder_path': folder_path})
                    if len(patients) >= limit:
                        break

                conn.close()
                return patients

            conn.close()
            return patients
            
        except Exception as e:
            logger.error(f"Failed to get NAS patients: {e}")
            return []
    
    def find_dicom_files(self, folder_path: str, max_files: int = 1000) -> List[str]:
        """Find DICOM files in folder"""
        dicom_files = []
        
        try:
            folder = Path(folder_path)
            if not folder.exists():
                return []
            
            # Search for DICOM files (no extension or .dcm extension)
            for root, dirs, files in os.walk(folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Check if it's a DICOM file
                    if file.lower().endswith('.dcm') or '.' not in file:
                        dicom_files.append(file_path)
                        
                        if len(dicom_files) >= max_files:
                            return dicom_files
            
            return dicom_files
            
        except Exception as e:
            logger.error(f"Error scanning folder {folder_path}: {e}")
            return []
    
    def upload_dicom_to_orthanc(self, dicom_file_path: str) -> bool:
        """Upload a single DICOM file to Orthanc"""
        # Uploads are disabled by default to preserve images on NAS only.
        if not ALLOW_UPLOAD_TO_ORTHANC:
            logger.info(f"Upload disabled by config. Skipping upload of {dicom_file_path}")
            return False

        try:
            with open(dicom_file_path, 'rb') as f:
                dicom_data = f.read()

            response = requests.post(
                f"{self.orthanc_url}/instances",
                auth=self.orthanc_auth,
                data=dicom_data,
                headers={'Content-Type': 'application/dicom'},
                timeout=30
            )

            return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Failed to upload {dicom_file_path}: {e}")
            return False
    
    def import_patient(self, patient: Dict) -> bool:
        """Import a single patient's DICOM files to Orthanc"""
        patient_id = patient['patient_id']
        patient_name = patient['patient_name']
        folder_path = patient['folder_path']
        
        logger.info(f"📤 Importing patient: {patient_name} (ID: {patient_id})")
        
        # Find DICOM files
        dicom_files = self.find_dicom_files(folder_path, max_files=500)
        
        if not dicom_files:
            logger.warning(f"⚠️  No DICOM files found for patient {patient_id}")
            return False
        
        logger.info(f"📁 Found {len(dicom_files)} DICOM files")
        
        # Upload files to Orthanc
        success_count = 0
        for i, dicom_file in enumerate(dicom_files):
            if self.upload_dicom_to_orthanc(dicom_file):
                success_count += 1
            
            # Log progress every 50 files
            if (i + 1) % 50 == 0:
                logger.info(f"   Progress: {i + 1}/{len(dicom_files)} files uploaded")
        
        success_rate = (success_count / len(dicom_files)) * 100 if dicom_files else 0
        logger.info(f"✅ Imported {success_count}/{len(dicom_files)} files ({success_rate:.1f}%)")
        
        return success_count > 0
    
    def run_import_cycle(self):
        """Run one import cycle"""
        logger.info("🔄 Starting import cycle...")
        
        # Check Orthanc connection
        if not self.check_orthanc_connection():
            logger.error("❌ Orthanc is not accessible. Skipping import.")
            return
        
        # Get patients already in Orthanc
        orthanc_patients = self.get_orthanc_patients()
        
        # Get NAS patients to import
        patients_to_import = self.get_nas_patients_to_import(orthanc_patients, MAX_IMPORT_PER_RUN)
        
        if not patients_to_import:
            logger.info("✨ All NAS patients are already in Orthanc!")
            return
        
        logger.info(f"📋 Found {len(patients_to_import)} patients to import")
        
        # Import patients
        imported_count = 0
        for patient in patients_to_import:
            if self.import_patient(patient):
                imported_count += 1
        
        logger.info(f"🎉 Import cycle complete: {imported_count}/{len(patients_to_import)} patients imported")
    
    def start_background_import(self):
        """Start background import service"""
        if self.running:
            logger.warning("Import service is already running")
            return
        
        self.running = True
        
        def import_loop():
            logger.info("🚀 NAS→Orthanc Auto-Import Service Started")
            backoff = IMPORT_INTERVAL
            consecutive_failures = 0
            while self.running:
                try:
                    self.run_import_cycle()
                    # Reset backoff after a successful cycle
                    backoff = IMPORT_INTERVAL
                    consecutive_failures = 0
                except Exception as e:
                    logger.error(f"Import cycle error: {e}")
                    consecutive_failures += 1
                    # Exponential backoff on repeated failures, cap at 1 hour
                    backoff = min(3600, IMPORT_INTERVAL * (2 ** (consecutive_failures - 1)))

                # Wait before next cycle
                if self.running:
                    logger.info(f"💤 Sleeping for {backoff} seconds...")
                    time.sleep(backoff)
        
        self.import_thread = threading.Thread(target=import_loop, daemon=True)
        self.import_thread.start()
        
        logger.info("✅ Background import service started")
    
    def stop_background_import(self):
        """Stop background import service"""
        if not self.running:
            return
        
        logger.info("🛑 Stopping import service...")
        self.running = False
        
        if self.import_thread:
            self.import_thread.join(timeout=5)
        
        logger.info("✅ Import service stopped")


# Global instance
_importer_instance = None

def get_importer() -> NASOrthancImporter:
    """Get or create importer instance"""
    global _importer_instance
    if _importer_instance is None:
        _importer_instance = NASOrthancImporter()
    return _importer_instance


if __name__ == '__main__':
    # Run as standalone script
    importer = NASOrthancImporter()
    
    print("🏥 NAS to Orthanc Import Service")
    print("=" * 50)
    print(f"Orthanc URL: {ORTHANC_URL}")
    print(f"NAS Database: {NAS_DB_PATH}")
    print(f"Batch Size: {IMPORT_BATCH_SIZE} patients")
    print(f"Import Interval: {IMPORT_INTERVAL} seconds")
    print("=" * 50)
    
    try:
        importer.start_background_import()
        
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        importer.stop_background_import()
        print("👋 Goodbye!")
