"""
Orthanc Management API - Shares Router
Patient data sharing and secure link management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import logging

from orthanc_management.api.auth import User
from orthanc_management.api.routers.auth import get_current_active_user, get_auth_manager
from orthanc_management.database.manager import DatabaseManager

logger = logging.getLogger(__name__)

# Pydantic models
class ShareCreate(BaseModel):
    patient_id: str = Field(..., max_length=255)
    study_instance_uid: str = Field(..., max_length=255)
    recipient_email: EmailStr
    recipient_name: str = Field(..., max_length=255)
    access_level: str = Field(default="read", max_length=20)
    expiry_date: Optional[date] = None
    message: Optional[str] = Field(None, max_length=1000)
    password_protected: bool = Field(default=True)

class ShareResponse(BaseModel):
    id: str
    patient_id: str
    study_instance_uid: str
    recipient_email: str
    recipient_name: str
    access_level: str
    share_link: str
    expiry_date: Optional[str]
    password_protected: bool
    is_active: bool
    access_count: int
    last_accessed: Optional[str]
    created_at: str

# Router instance
router = APIRouter(prefix="/shares", tags=["Data Sharing"])

# Dependency to get database session
def get_db():
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()


@router.post("/", response_model=ShareResponse)
async def create_share(
    share_data: ShareCreate,
    current_user: User = Depends(get_current_active_user),
    auth_manager = Depends(get_auth_manager)
):
    """
    Create a secure share link for patient data
    Requires 'write' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "write")
        
        # Mock implementation
        share_id = f"share_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Share created by {current_user.username}: {share_data.recipient_email}")
        
        return ShareResponse(
            id=share_id,
            patient_id=share_data.patient_id,
            study_instance_uid=share_data.study_instance_uid,
            recipient_email=share_data.recipient_email,
            recipient_name=share_data.recipient_name,
            access_level=share_data.access_level,
            share_link=f"https://orthanc.example.com/share/{share_id}",
            expiry_date=share_data.expiry_date.isoformat() if share_data.expiry_date else None,
            password_protected=share_data.password_protected,
            is_active=True,
            access_count=0,
            last_accessed=None,
            created_at=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create share: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create share"
        )


@router.get("/")
async def list_shares(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    auth_manager = Depends(get_auth_manager)
):
    """
    List shares created by current user
    Requires 'read' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "read")
        
        # Mock implementation
        return {
            "shares": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "total_pages": 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list shares: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve shares"
        )
