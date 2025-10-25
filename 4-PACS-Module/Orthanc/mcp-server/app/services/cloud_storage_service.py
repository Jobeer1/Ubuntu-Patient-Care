"""Cloud Storage Service for Google Drive and OneDrive"""
import os
import io
from typing import Optional, Dict, List
import httpx
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from msal import ConfidentialClientApplication

class CloudStorageService:
    """Service for uploading files to Google Drive and OneDrive"""
    
    @staticmethod
    async def upload_to_google_drive(
        refresh_token: str,
        file_content: bytes,
        filename: str,
        mime_type: str = "application/dicom"
    ) -> Dict:
        """Upload file directly to user's Google Drive"""
        try:
            # Create credentials from refresh token
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                scopes=["https://www.googleapis.com/auth/drive.file"]
            )
            
            # Build Drive service
            service = build('drive', 'v3', credentials=credentials)
            
            # Create file metadata
            file_metadata = {
                'name': filename,
                'mimeType': mime_type
            }
            
            # Upload file
            media = MediaIoBaseUpload(
                io.BytesIO(file_content),
                mimetype=mime_type,
                resumable=True
            )
            
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()
            
            return {
                "success": True,
                "file_id": file.get('id'),
                "file_name": file.get('name'),
                "web_link": file.get('webViewLink'),
                "provider": "google_drive"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": "google_drive"
            }
    
    @staticmethod
    async def upload_to_onedrive(
        refresh_token: str,
        file_content: bytes,
        filename: str
    ) -> Dict:
        """Upload file directly to user's OneDrive"""
        try:
            # Get access token from refresh token
            app = ConfidentialClientApplication(
                client_id=os.getenv("MICROSOFT_CLIENT_ID"),
                client_credential=os.getenv("MICROSOFT_CLIENT_SECRET"),
                authority=f"https://login.microsoftonline.com/{os.getenv('MICROSOFT_TENANT_ID')}"
            )
            
            result = app.acquire_token_by_refresh_token(
                refresh_token,
                scopes=["https://graph.microsoft.com/Files.ReadWrite"]
            )
            
            if "access_token" not in result:
                raise Exception("Failed to get access token")
            
            access_token = result["access_token"]
            
            # Upload to OneDrive
            upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{filename}:/content"
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    upload_url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/octet-stream"
                    },
                    content=file_content
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    return {
                        "success": True,
                        "file_id": data.get("id"),
                        "file_name": data.get("name"),
                        "web_link": data.get("webUrl"),
                        "provider": "onedrive"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Upload failed: {response.text}",
                        "provider": "onedrive"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": "onedrive"
            }
    
    @staticmethod
    async def batch_upload_to_google_drive(
        refresh_token: str,
        files: List[Dict]  # [{"content": bytes, "filename": str, "mime_type": str}]
    ) -> List[Dict]:
        """Upload multiple files to Google Drive"""
        results = []
        for file_data in files:
            result = await CloudStorageService.upload_to_google_drive(
                refresh_token=refresh_token,
                file_content=file_data["content"],
                filename=file_data["filename"],
                mime_type=file_data.get("mime_type", "application/dicom")
            )
            results.append(result)
        return results
    
    @staticmethod
    async def batch_upload_to_onedrive(
        refresh_token: str,
        files: List[Dict]  # [{"content": bytes, "filename": str}]
    ) -> List[Dict]:
        """Upload multiple files to OneDrive"""
        results = []
        for file_data in files:
            result = await CloudStorageService.upload_to_onedrive(
                refresh_token=refresh_token,
                file_content=file_data["content"],
                filename=file_data["filename"]
            )
            results.append(result)
        return results
