"""
Orthanc Management API - Patient Authorization Router
CRUD operations for patient authorizations with POPIA compliance
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import logging

from orthanc_management.api.auth import User
from orthanc_management.api.routers.auth import get_current_active_user, get_auth_manager
from orthanc_management.managers.authorization_manager import AuthorizationManager
from orthanc_management.models.patient_authorization import PatientAuthorization
from orthanc_management.database.manager import DatabaseManager

logger = logging.getLogger(__name__)

# Pydantic models for request/response
class AuthorizationCreate(BaseModel):
    patient_id: str = Field(..., max_length=255)
    patient_name: str = Field(..., min_length=2, max_length=255)
    patient_email: Optional[EmailStr] = None
    patient_phone: Optional[str] = Field(None, max_length=20)
    patient_id_number: Optional[str] = Field(None, max_length=20)
    doctor_id: str = Field(..., max_length=36)
    study_instance_uid: str = Field(..., max_length=255)
    series_instance_uid: Optional[str] = Field(None, max_length=255)
    authorization_type: str = Field(..., max_length=50)
    purpose: str = Field(..., max_length=500)
    consent_given: bool = Field(default=True)
    consent_date: Optional[date] = None
    expiry_date: Optional[date] = None
    access_level: str = Field(default="read", max_length=20)
    restrictions: Optional[str] = Field(None, max_length=1000)
    emergency_access: bool = Field(default=False)
    notes: Optional[str] = Field(None, max_length=1000)

class AuthorizationUpdate(BaseModel):
    patient_name: Optional[str] = Field(None, min_length=2, max_length=255)
    patient_email: Optional[EmailStr] = None
    patient_phone: Optional[str] = Field(None, max_length=20)
    authorization_type: Optional[str] = Field(None, max_length=50)
    purpose: Optional[str] = Field(None, max_length=500)
    consent_given: Optional[bool] = None
    consent_date: Optional[date] = None
    expiry_date: Optional[date] = None
    access_level: Optional[str] = Field(None, max_length=20)
    restrictions: Optional[str] = Field(None, max_length=1000)
    emergency_access: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None

class AuthorizationResponse(BaseModel):
    id: str
    patient_id: str
    patient_name: str
    patient_email: Optional[str]
    patient_phone: Optional[str]
    patient_id_number: Optional[str]
    doctor_id: str
    doctor_name: Optional[str]
    study_instance_uid: str
    series_instance_uid: Optional[str]
    authorization_type: str
    purpose: str
    consent_given: bool
    consent_date: Optional[str]
    expiry_date: Optional[str]
    access_level: str
    restrictions: Optional[str]
    emergency_access: bool
    notes: Optional[str]
    is_active: bool
    is_expired: bool
    access_count: int
    last_accessed: Optional[str]
    created_at: str
    updated_at: str

class AuthorizationListResponse(BaseModel):
    authorizations: List[AuthorizationResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class AuthorizationStatsResponse(BaseModel):
    total_authorizations: int
    active_authorizations: int
    expired_authorizations: int
    pending_expiry: int
    by_type: Dict[str, int]
    by_access_level: Dict[str, int]
    emergency_access_count: int
    recent_activity: List[Dict[str, Any]]

class ConsentForm(BaseModel):
    patient_id: str
    patient_name: str
    doctor_id: str
    study_instance_uid: str
    purpose: str
    consent_text: str
    patient_signature: Optional[str] = None
    witness_signature: Optional[str] = None
    consent_date: date

# Router instance
router = APIRouter(prefix="/authorizations", tags=["Patient Authorizations"])

# Dependency to get database session
def get_db():
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

# Dependency to get authorization manager
def get_authorization_manager(db = Depends(get_db)):
    return AuthorizationManager(db)


@router.post("/", response_model=AuthorizationResponse)
async def create_authorization(
    auth_data: AuthorizationCreate,
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthorizationManager = Depends(get_authorization_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Create a new patient authorization
    Requires 'write' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "write")
        
        # Create authorization
        authorization = auth_manager.create_authorization(auth_data.dict())
        
        logger.info(f"Authorization created by {current_user.username}: {authorization.patient_name}")
        
        return AuthorizationResponse(**authorization.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create authorization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create authorization"
        )


@router.get("/", response_model=AuthorizationListResponse)
async def list_authorizations(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    doctor_id: Optional[str] = Query(None, description="Filter by doctor ID"),
    authorization_type: Optional[str] = Query(None, description="Filter by authorization type"),
    access_level: Optional[str] = Query(None, description="Filter by access level"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    include_expired: bool = Query(False, description="Include expired authorizations"),
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthorizationManager = Depends(get_authorization_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    List patient authorizations with pagination and filtering
    Requires 'read' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "read")
        
        # Build filters
        filters = {}
        if patient_id:
            filters["patient_id"] = patient_id
        if doctor_id:
            filters["doctor_id"] = doctor_id
        if authorization_type:
            filters["authorization_type"] = authorization_type
        if access_level:
            filters["access_level"] = access_level
        if is_active is not None:
            filters["is_active"] = is_active
        if not include_expired:
            filters["exclude_expired"] = True
        
        # Get authorizations
        result = auth_manager.get_authorizations_paginated(
            page=page,
            per_page=per_page,
            filters=filters
        )
        
        return AuthorizationListResponse(
            authorizations=[AuthorizationResponse(**auth.to_dict()) for auth in result["authorizations"]],
            total=result["total"],
            page=page,
            per_page=per_page,
            total_pages=result["total_pages"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list authorizations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve authorizations"
        )


@router.get("/stats", response_model=AuthorizationStatsResponse)
async def get_authorization_stats(
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthorizationManager = Depends(get_authorization_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Get authorization statistics and analytics
    Requires 'read' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "read")
        
        # Get statistics
        stats = auth_manager.get_authorization_statistics()
        
        return AuthorizationStatsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get authorization stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve authorization statistics"
        )


@router.get("/{authorization_id}", response_model=AuthorizationResponse)
async def get_authorization(
    authorization_id: str,
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthorizationManager = Depends(get_authorization_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Get authorization by ID
    Requires 'read' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "read")
        
        # Get authorization
        authorization = auth_manager.get_authorization(authorization_id)
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Authorization not found"
            )
        
        return AuthorizationResponse(**authorization.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get authorization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve authorization"
        )


@router.put("/{authorization_id}", response_model=AuthorizationResponse)
async def update_authorization(
    authorization_id: str,
    auth_data: AuthorizationUpdate,
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthorizationManager = Depends(get_authorization_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Update authorization by ID
    Requires 'write' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "write")
        
        # Filter out None values
        update_data = {k: v for k, v in auth_data.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided"
            )
        
        # Update authorization
        authorization = auth_manager.update_authorization(authorization_id, update_data)
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Authorization not found"
            )
        
        logger.info(f"Authorization updated by {current_user.username}: {authorization.patient_name}")
        
        return AuthorizationResponse(**authorization.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update authorization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update authorization"
        )


@router.delete("/{authorization_id}")
async def revoke_authorization(
    authorization_id: str,
    reason: str = Query(..., description="Reason for revocation"),
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthorizationManager = Depends(get_authorization_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Revoke authorization by ID
    Requires 'delete' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "delete")
        
        # Revoke authorization
        success = auth_manager.revoke_authorization(authorization_id, reason)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Authorization not found"
            )
        
        logger.info(f"Authorization revoked by {current_user.username}: {authorization_id} - {reason}")
        
        return {"message": "Authorization revoked successfully", "reason": reason}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke authorization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke authorization"
        )


@router.post("/{authorization_id}/extend")
async def extend_authorization(
    authorization_id: str,
    new_expiry_date: date = Query(..., description="New expiry date"),
    reason: str = Query(..., description="Reason for extension"),
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthorizationManager = Depends(get_authorization_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Extend authorization expiry date
    Requires 'write' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "write")
        
        # Extend authorization
        authorization = auth_manager.extend_authorization(authorization_id, new_expiry_date, reason)
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Authorization not found"
            )
        
        logger.info(f"Authorization extended by {current_user.username}: {authorization_id} until {new_expiry_date}")
        
        return {
            "message": "Authorization extended successfully",
            "authorization_id": authorization_id,
            "new_expiry_date": new_expiry_date.isoformat(),
            "reason": reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extend authorization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extend authorization"
        )


@router.post("/validate-access")
async def validate_access(
    patient_id: str = Query(..., description="Patient ID"),
    study_instance_uid: str = Query(..., description="Study Instance UID"),
    access_type: str = Query("read", description="Type of access requested"),
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthorizationManager = Depends(get_authorization_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Validate access to patient data
    Requires 'read' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "read")
        
        # Validate access
        access_result = auth_manager.validate_access(patient_id, study_instance_uid, access_type)
        
        return {
            "access_granted": access_result["granted"],
            "authorization_id": access_result.get("authorization_id"),
            "access_level": access_result.get("access_level"),
            "restrictions": access_result.get("restrictions"),
            "expiry_date": access_result.get("expiry_date"),
            "reason": access_result.get("reason")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate access"
        )


@router.get("/patient/{patient_id}")
async def get_patient_authorizations(
    patient_id: str,
    include_expired: bool = Query(False, description="Include expired authorizations"),
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthorizationManager = Depends(get_authorization_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Get all authorizations for a specific patient
    Requires 'read' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "read")
        
        # Get patient authorizations
        authorizations = auth_manager.get_patient_authorizations(patient_id, include_expired)
        
        return {
            "patient_id": patient_id,
            "authorizations": [AuthorizationResponse(**auth.to_dict()) for auth in authorizations],
            "total": len(authorizations)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get patient authorizations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve patient authorizations"
        )


@router.post("/consent-form")
async def generate_consent_form(
    consent_data: ConsentForm,
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthorizationManager = Depends(get_authorization_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Generate POPIA-compliant consent form
    Requires 'write' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "write")
        
        # Generate consent form
        consent_form = auth_manager.generate_consent_form(consent_data.dict())
        
        logger.info(f"Consent form generated by {current_user.username} for patient: {consent_data.patient_name}")
        
        return {
            "consent_form_id": consent_form["id"],
            "consent_form_html": consent_form["html"],
            "consent_form_pdf": consent_form.get("pdf_path"),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate consent form: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate consent form"
        )


@router.get("/expiring-soon")
async def get_expiring_authorizations(
    days_ahead: int = Query(7, ge=1, le=30, description="Days ahead to check for expiry"),
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthorizationManager = Depends(get_authorization_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Get authorizations expiring soon
    Requires 'read' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "read")
        
        # Get expiring authorizations
        expiring_auths = auth_manager.get_expiring_authorizations(days_ahead)
        
        return {
            "days_ahead": days_ahead,
            "expiring_authorizations": [AuthorizationResponse(**auth.to_dict()) for auth in expiring_auths],
            "total": len(expiring_auths)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get expiring authorizations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve expiring authorizations"
        )


@router.get("/audit-trail/{authorization_id}")
async def get_authorization_audit_trail(
    authorization_id: str,
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthorizationManager = Depends(get_authorization_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Get audit trail for specific authorization (POPIA compliance)
    Requires 'read' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "read")
        
        # Get audit trail
        audit_trail = auth_manager.get_authorization_audit_trail(authorization_id)
        
        return {
            "authorization_id": authorization_id,
            "audit_trail": audit_trail,
            "total_events": len(audit_trail)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit trail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit trail"
        )
