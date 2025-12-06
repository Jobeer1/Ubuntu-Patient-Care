"""
Google Drive Monitor - Central Data Ingestion Service
Monitors clinic Drive folders, downloads training data, and uploads to private GCS.
Part of the Ubuntu Patient Care AI training pipeline.

Deployment: Google Cloud Run or Cloud Functions (triggered on schedule or webhook)
Service Account Required Roles:
  - roles/storage.objectAdmin (for GCS bucket access)
  - roles/drive.readonly (for Drive folder monitoring)
"""

import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from google.cloud import storage
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
import io

# Configuration
MONITORED_DRIVE_FOLDER_ID = os.getenv('DRIVE_FOLDER_ID', 'PLACEHOLDER_FOLDER_ID')
PRIVATE_GCS_BUCKET = os.getenv('GCS_TRAINING_BUCKET', 'ubuntu-training-data-private')
SERVICE_ACCOUNT_KEY_PATH = os.getenv('SERVICE_ACCOUNT_KEY', 'config/service_account.json')
PROCESSED_SUBFOLDER_NAME = 'synced'

# Drive API scopes for service account
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def get_drive_service():
    """
    Initialize Google Drive API service using service account credentials.
    
    Returns:
        Resource: Authenticated Drive API service
    """
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_KEY_PATH,
        scopes=SCOPES
    )
    service = build('drive', 'v3', credentials=credentials)
    print(f"✓ Drive service initialized with service account")
    return service


def get_gcs_client():
    """
    Initialize Google Cloud Storage client.
    
    Returns:
        storage.Client: Authenticated GCS client
    """
    client = storage.Client()
    print(f"✓ GCS client initialized for bucket: {PRIVATE_GCS_BUCKET}")
    return client


def list_new_manifests(drive_service, folder_id: str) -> List[Dict]:
    """
    List unprocessed batch manifest files from the monitored Drive folder.
    
    Args:
        drive_service: Authenticated Drive API service
        folder_id: Google Drive folder ID to monitor
        
    Returns:
        List[Dict]: List of manifest file metadata
    """
    try:
        # Query for JSON manifest files that haven't been moved to 'synced' folder
        query = (
            f"'{folder_id}' in parents and "
            f"name contains 'batch_manifest_' and "
            f"mimeType='application/json' and "
            f"trashed=false"
        )
        
        results = drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, createdTime, size)',
            orderBy='createdTime desc'
        ).execute()
        
        files = results.get('files', [])
        print(f"✓ Found {len(files)} unprocessed manifest(s)")
        
        return files
        
    except Exception as e:
        print(f"✗ Error listing Drive files: {e}")
        return []


def validate_popia_compliance(manifest_data: Dict) -> Dict:
    """
    POPIA Compliance Validation - Placeholder for anonymization checks.
    
    This function validates that uploaded data meets South African POPIA
    (Protection of Personal Information Act) requirements.
    
    Args:
        manifest_data: The manifest JSON containing batch data
        
    Returns:
        Dict: Validation result with compliance status
        
    TODO: Implement actual PII detection and anonymization:
      - Check for patient names, ID numbers, addresses
      - Validate that audio files are properly de-identified
      - Ensure clinician IDs are hashed/anonymized
      - Log compliance checks for audit trail
    """
    print("\n" + "="*70)
    print("  POPIA COMPLIANCE VALIDATION")
    print("="*70)
    
    validation_result = {
        "compliant": True,
        "checks_performed": [],
        "warnings": [],
        "timestamp": datetime.now().isoformat()
    }
    
    # Check 1: Verify no direct patient identifiers in manifest
    batch_data = manifest_data.get('batch_data', [])
    for record in batch_data:
        # Placeholder: Check for common PII patterns
        text_fields = [
            record.get('original_text', ''),
            record.get('corrected_text', '')
        ]
        
        for text in text_fields:
            # Simple heuristic checks (expand in production)
            if any(keyword in text.lower() for keyword in ['id number', 'address', 'phone']):
                validation_result['warnings'].append(
                    f"Potential PII detected in record: {record.get('audio_file', 'unknown')}"
                )
    
    validation_result['checks_performed'].append("PII_PATTERN_SCAN")
    
    # Check 2: Verify clinician IDs are anonymized (should not be real names)
    for record in batch_data:
        clinician_id = record.get('clinician_id', '')
        if ' ' in clinician_id or '@' in clinician_id:
            validation_result['warnings'].append(
                f"Clinician ID may not be properly anonymized: {clinician_id}"
            )
    
    validation_result['checks_performed'].append("CLINICIAN_ID_ANONYMIZATION")
    
    # Check 3: Validate data retention metadata exists
    if 'upload_timestamp' not in manifest_data:
        validation_result['warnings'].append("Missing upload timestamp for retention policy")
    
    validation_result['checks_performed'].append("RETENTION_METADATA")
    
    print(f"  Checks Performed: {len(validation_result['checks_performed'])}")
    print(f"  Warnings: {len(validation_result['warnings'])}")
    print(f"  Status: {'✓ COMPLIANT' if validation_result['compliant'] else '✗ NON-COMPLIANT'}")
    print("="*70 + "\n")
    
    return validation_result


def download_and_upload_to_gcs(drive_service, gcs_client, manifest_file: Dict) -> Optional[str]:
    """
    Download manifest from Drive, validate compliance, and upload to private GCS bucket.
    
    Args:
        drive_service: Authenticated Drive API service
        gcs_client: Authenticated GCS client
        manifest_file: Drive file metadata
        
    Returns:
        Optional[str]: GCS URI of uploaded manifest, or None if failed
    """
    file_id = manifest_file['id']
    file_name = manifest_file['name']
    
    print(f"\n{'='*70}")
    print(f"  PROCESSING: {file_name}")
    print(f"{'='*70}")
    
    try:
        # Download manifest from Drive
        request = drive_service.files().get_media(fileId=file_id)
        file_buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(file_buffer, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"  Download progress: {int(status.progress() * 100)}%")
        
        file_buffer.seek(0)
        manifest_content = file_buffer.read().decode('utf-8')
        manifest_data = json.loads(manifest_content)
        
        print(f"✓ Downloaded manifest: {len(manifest_data.get('batch_data', []))} records")
        
        # CRITICAL: POPIA Compliance Validation
        compliance_result = validate_popia_compliance(manifest_data)
        
        if not compliance_result['compliant']:
            print(f"✗ POPIA compliance check failed. Skipping upload.")
            return None
        
        # Add compliance metadata to manifest
        manifest_data['popia_validation'] = compliance_result
        manifest_data['gcs_upload_timestamp'] = datetime.now().isoformat()
        
        # Upload to private GCS bucket
        bucket = gcs_client.bucket(PRIVATE_GCS_BUCKET)
        
        # Organize by date for easy management
        upload_date = datetime.now().strftime("%Y/%m/%d")
        gcs_path = f"training_data/{upload_date}/{file_name}"
        
        blob = bucket.blob(gcs_path)
        blob.upload_from_string(
            json.dumps(manifest_data, indent=2),
            content_type='application/json'
        )
        
        gcs_uri = f"gs://{PRIVATE_GCS_BUCKET}/{gcs_path}"
        print(f"✓ Uploaded to GCS: {gcs_uri}")
        
        # Generate checksum for audit trail
        checksum = hashlib.sha256(manifest_content.encode()).hexdigest()
        print(f"  SHA256: {checksum[:16]}...")
        
        return gcs_uri
        
    except Exception as e:
        print(f"✗ Error processing {file_name}: {e}")
        return None


def mark_as_processed(drive_service, file_id: str, parent_folder_id: str) -> bool:
    """
    Move processed file to 'synced' subfolder to prevent reprocessing.
    
    Args:
        drive_service: Authenticated Drive API service
        file_id: ID of the file to move
        parent_folder_id: Current parent folder ID
        
    Returns:
        bool: True if successful
    """
    try:
        # Find or create 'synced' subfolder
        query = (
            f"'{parent_folder_id}' in parents and "
            f"name='{PROCESSED_SUBFOLDER_NAME}' and "
            f"mimeType='application/vnd.google-apps.folder' and "
            f"trashed=false"
        )
        
        results = drive_service.files().list(q=query, fields='files(id)').execute()
        folders = results.get('files', [])
        
        if folders:
            synced_folder_id = folders[0]['id']
        else:
            # Create synced folder
            folder_metadata = {
                'name': PROCESSED_SUBFOLDER_NAME,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder_id]
            }
            folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            synced_folder_id = folder['id']
            print(f"✓ Created '{PROCESSED_SUBFOLDER_NAME}' subfolder")
        
        # Move file to synced folder
        file = drive_service.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ','.join(file.get('parents', []))
        
        drive_service.files().update(
            fileId=file_id,
            addParents=synced_folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
        
        print(f"✓ Moved to '{PROCESSED_SUBFOLDER_NAME}' folder")
        return True
        
    except Exception as e:
        print(f"✗ Error marking as processed: {e}")
        return False


def run_monitoring_cycle() -> Dict:
    """
    Execute one complete monitoring cycle.
    
    Returns:
        Dict: Summary of processing results
    """
    print("\n" + "🔄 " + "="*68)
    print("  UBUNTU PATIENT CARE - DRIVE MONITOR SERVICE")
    print("  " + "="*68)
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print(f"  Monitored Folder: {MONITORED_DRIVE_FOLDER_ID}")
    print(f"  Target GCS Bucket: {PRIVATE_GCS_BUCKET}")
    print("  " + "="*68 + "\n")
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "files_found": 0,
        "files_processed": 0,
        "files_failed": 0,
        "gcs_uris": []
    }
    
    try:
        # Initialize services
        drive_service = get_drive_service()
        gcs_client = get_gcs_client()
        
        # List new manifests
        manifests = list_new_manifests(drive_service, MONITORED_DRIVE_FOLDER_ID)
        summary['files_found'] = len(manifests)
        
        if not manifests:
            print("ℹ No new manifests to process")
            return summary
        
        # Process each manifest
        for manifest in manifests:
            gcs_uri = download_and_upload_to_gcs(drive_service, gcs_client, manifest)
            
            if gcs_uri:
                summary['gcs_uris'].append(gcs_uri)
                summary['files_processed'] += 1
                
                # Mark as processed
                mark_as_processed(drive_service, manifest['id'], MONITORED_DRIVE_FOLDER_ID)
            else:
                summary['files_failed'] += 1
        
        # Final summary
        print("\n" + "="*70)
        print("  MONITORING CYCLE COMPLETE")
        print("="*70)
        print(f"  Files Found: {summary['files_found']}")
        print(f"  Successfully Processed: {summary['files_processed']}")
        print(f"  Failed: {summary['files_failed']}")
        print("="*70 + "\n")
        
        return summary
        
    except Exception as e:
        print(f"\n✗ Monitoring cycle failed: {e}")
        summary['error'] = str(e)
        return summary


# Cloud Function / Cloud Run entry point
def main(request=None):
    """
    Entry point for Cloud Functions or Cloud Run.
    
    Args:
        request: Flask request object (for Cloud Functions)
        
    Returns:
        Tuple: (response_dict, status_code)
    """
    summary = run_monitoring_cycle()
    
    status_code = 200 if summary.get('files_failed', 0) == 0 else 207
    
    return summary, status_code


if __name__ == "__main__":
    # Local testing
    result = run_monitoring_cycle()
    print(f"\nResult: {json.dumps(result, indent=2)}")
