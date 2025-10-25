"""Cloud storage routes for Google Drive and OneDrive"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.database import get_db
from app.services import JWTService, UserService, AuditService
from app.services.cloud_storage_service import CloudStorageService
from app.services.rbac_service import RBACService
import httpx

router = APIRouter(prefix="/cloud", tags=["cloud-storage"])

class UploadRequest(BaseModel):
    study_id: str
    patient_id: str
    instance_ids: List[str]
    provider: str  # "google_drive" or "onedrive"

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Get current authenticated user"""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = JWTService.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = UserService.get_user_by_id(db, payload.get("user_id"))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

@router.post("/upload")
async def upload_to_cloud(
    upload_req: UploadRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Upload DICOM images directly to user's cloud storage"""
    try:
        # Check permissions
        permissions = RBACService.get_user_permissions(current_user)
        if not permissions.get("can_export_to_cloud"):
            raise HTTPException(status_code=403, detail="No permission to export to cloud")
        
        # Check if user can access this patient's data
        if not RBACService.can_access_patient_data(db, current_user, upload_req.patient_id):
            raise HTTPException(status_code=403, detail="No access to this patient's data")
        
        # Get refresh token based on provider
        if upload_req.provider == "google_drive":
            refresh_token = current_user.google_refresh_token
            if not refresh_token:
                raise HTTPException(
                    status_code=400,
                    detail="Google Drive not connected. Please sign in with Google first."
                )
        elif upload_req.provider == "onedrive":
            refresh_token = current_user.microsoft_refresh_token
            if not refresh_token:
                raise HTTPException(
                    status_code=400,
                    detail="OneDrive not connected. Please sign in with Microsoft first."
                )
        else:
            raise HTTPException(status_code=400, detail="Invalid provider")
        
        # Fetch DICOM files from PACS
        from config.settings import settings
        files_to_upload = []
        
        async with httpx.AsyncClient() as client:
            for instance_id in upload_req.instance_ids:
                # Fetch DICOM file from Orthanc
                response = await client.get(
                    f"{settings.PACS_ORTHANC_URL}/instances/{instance_id}/file"
                )
                
                if response.status_code == 200:
                    files_to_upload.append({
                        "content": response.content,
                        "filename": f"{upload_req.study_id}_{instance_id}.dcm",
                        "mime_type": "application/dicom"
                    })
        
        if not files_to_upload:
            raise HTTPException(status_code=404, detail="No files found to upload")
        
        # Upload to cloud storage
        if upload_req.provider == "google_drive":
            results = await CloudStorageService.batch_upload_to_google_drive(
                refresh_token=refresh_token,
                files=files_to_upload
            )
        else:
            results = await CloudStorageService.batch_upload_to_onedrive(
                refresh_token=refresh_token,
                files=files_to_upload
            )
        
        # Log the export
        AuditService.log_event(
            db=db,
            user_id=current_user.id,
            user_email=current_user.email,
            action=f"export_to_{upload_req.provider}",
            resource=f"study:{upload_req.study_id}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            success=all(r.get("success") for r in results)
        )
        
        return {
            "success": True,
            "provider": upload_req.provider,
            "uploaded_count": len([r for r in results if r.get("success")]),
            "failed_count": len([r for r in results if not r.get("success")]),
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/status")
async def cloud_storage_status(
    current_user = Depends(get_current_user)
):
    """Check which cloud storage providers are connected"""
    return {
        "google_drive_connected": bool(current_user.google_refresh_token),
        "onedrive_connected": bool(current_user.microsoft_refresh_token),
        "can_export": RBACService.get_user_permissions(current_user).get("can_export_to_cloud", False)
    }

@router.post("/disconnect/{provider}")
async def disconnect_cloud_storage(
    provider: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Disconnect cloud storage provider"""
    if provider == "google_drive":
        UserService.update_google_token(db, current_user.id, None)
    elif provider == "onedrive":
        UserService.update_microsoft_token(db, current_user.id, None)
    else:
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    return {"success": True, "message": f"{provider} disconnected"}
