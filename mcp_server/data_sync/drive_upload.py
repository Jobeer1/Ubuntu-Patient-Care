"""
Google Drive Sync Module for Ubuntu Patient Care
Handles secure upload of corrected transcription data to clinic-specific Drive folders.
Part of the Simple Sync / Hidden Vertex AI / Auditable Opus architecture.
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import pickle

# Define the OAuth scopes for Drive API access
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Configuration paths
CREDENTIALS_PATH = 'config/drive_credentials.json'
TOKEN_PATH = 'config/drive_token.pickle'


def get_drive_service():
    """
    Initialize and return the Google Drive API service.
    
    Handles OAuth 2.0 authentication flow:
    - Checks for existing saved token
    - Refreshes expired tokens
    - Initiates new OAuth flow if needed
    
    Returns:
        Resource: Authenticated Google Drive API service object
        
    Raises:
        FileNotFoundError: If credentials file is missing
        Exception: If authentication fails
    """
    creds = None
    
    # Check if we have a saved token
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    
    # If credentials are invalid or don't exist, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("✓ Refreshed expired OAuth token")
            except Exception as e:
                print(f"⚠ Token refresh failed: {e}")
                creds = None
        
        if not creds:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"OAuth credentials not found at {CREDENTIALS_PATH}. "
                    "Please download credentials from Google Cloud Console."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)
            print("✓ New OAuth token obtained")
        
        # Save the credentials for future use
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
    
    try:
        service = build('drive', 'v3', credentials=creds)
        print("✓ Google Drive API service initialized")
        return service
    except Exception as e:
        raise Exception(f"Failed to build Drive service: {e}")


def get_or_create_folder(service, folder_name: str = "Ubuntu Patient Care / Whisper Training Data") -> str:
    """
    Find or create the dedicated folder for training data uploads.
    
    Args:
        service: Authenticated Google Drive API service
        folder_name: Name of the folder to find or create
        
    Returns:
        str: The folder ID
        
    Raises:
        HttpError: If Drive API request fails
    """
    try:
        # Search for existing folder
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        folders = results.get('files', [])
        
        if folders:
            folder_id = folders[0]['id']
            print(f"✓ Found existing folder: {folder_name} (ID: {folder_id})")
            return folder_id
        
        # Create new folder if it doesn't exist
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        folder = service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()
        
        folder_id = folder.get('id')
        print(f"✓ Created new folder: {folder_name} (ID: {folder_id})")
        return folder_id
        
    except HttpError as error:
        raise Exception(f"Drive API error during folder operation: {error}")


def sync_training_data_to_drive(service, batch_data: List[Dict], folder_id: Optional[str] = None) -> Dict:
    """
    Package and upload corrected transcription data to Google Drive.
    
    This function:
    1. Generates a timestamped JSON manifest from batch_data
    2. Uploads the manifest to the clinic's Drive folder
    3. Returns upload metadata for audit trail
    
    Args:
        service: Authenticated Google Drive API service
        batch_data: List of dictionaries containing transcription corrections
        folder_id: Optional folder ID (will create default if not provided)
        
    Returns:
        Dict: Upload metadata including file_id, timestamp, and record count
        
    Example batch_data format:
        [
            {
                "audio_file": "consultation_001.wav",
                "original_text": "patient has high blood pressure",
                "corrected_text": "patient has hypertension",
                "correction_timestamp": "2025-11-17T10:30:00Z",
                "clinician_id": "dr_tom_rural_clinic_01"
            }
        ]
    """
    try:
        # Get or create folder if not provided
        if not folder_id:
            folder_id = get_or_create_folder(service)
        
        # Generate timestamped manifest filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        manifest_filename = f"batch_manifest_{timestamp}.json"
        manifest_path = f"temp/{manifest_filename}"
        
        # Ensure temp directory exists
        os.makedirs("temp", exist_ok=True)
        
        # Create manifest with metadata
        manifest = {
            "upload_timestamp": datetime.now().isoformat(),
            "record_count": len(batch_data),
            "data_type": "whisper_training_corrections",
            "version": "1.0",
            "batch_data": batch_data
        }
        
        # Write manifest to local file
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Generated manifest: {manifest_filename} ({len(batch_data)} records)")
        
        # Upload to Google Drive
        file_metadata = {
            'name': manifest_filename,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(
            manifest_path,
            mimetype='application/json',
            resumable=True
        )
        
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink'
        ).execute()
        
        file_id = uploaded_file.get('id')
        web_link = uploaded_file.get('webViewLink', 'N/A')
        
        print("\n" + "="*70)
        print("✓ TRAINING DATA SYNC COMPLETE")
        print("="*70)
        print(f"  Folder: Ubuntu Patient Care / Whisper Training Data")
        print(f"  File ID: {file_id}")
        print(f"  Records: {len(batch_data)}")
        print(f"  View: {web_link}")
        print("="*70 + "\n")
        
        # Clean up temp file
        if os.path.exists(manifest_path):
            os.remove(manifest_path)
        
        return {
            "success": True,
            "file_id": file_id,
            "filename": manifest_filename,
            "record_count": len(batch_data),
            "timestamp": timestamp,
            "web_link": web_link
        }
        
    except HttpError as error:
        raise Exception(f"Upload failed: {error}")
    except Exception as e:
        raise Exception(f"Sync error: {e}")


# Example usage and testing
if __name__ == "__main__":
    # Mock batch data for demonstration
    sample_batch = [
        {
            "audio_file": "consultation_001.wav",
            "original_text": "patient has high blood pressure",
            "corrected_text": "patient has hypertension",
            "correction_timestamp": "2025-11-17T10:30:00Z",
            "clinician_id": "dr_tom_rural_clinic_01"
        },
        {
            "audio_file": "consultation_002.wav",
            "original_text": "prescribe pain medication",
            "corrected_text": "prescribe analgesics",
            "correction_timestamp": "2025-11-17T10:35:00Z",
            "clinician_id": "dr_tom_rural_clinic_01"
        }
    ]
    
    try:
        print("Initializing Google Drive sync...")
        drive_service = get_drive_service()
        result = sync_training_data_to_drive(drive_service, sample_batch)
        print(f"✓ Upload successful: {result['filename']}")
    except Exception as e:
        print(f"✗ Error: {e}")
