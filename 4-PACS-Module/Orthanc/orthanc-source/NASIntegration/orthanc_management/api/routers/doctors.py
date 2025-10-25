"""
Orthanc Management API - Doctors Router
CRUD operations for referring doctors with South African healthcare compliance
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from orthanc_management.api.auth import User
from orthanc_management.api.routers.auth import get_current_active_user, get_auth_manager
from orthanc_management.managers.doctor_manager import DoctorManager
from orthanc_management.models.referring_doctor import ReferringDoctor
from orthanc_management.database.manager import DatabaseManager

logger = logging.getLogger(__name__)

# Pydantic models for request/response
class DoctorCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(..., max_length=20)
    hpcsa_number: str = Field(..., max_length=20)
    practice_number: Optional[str] = Field(None, max_length=20)
    specialization: Optional[str] = Field(None, max_length=100)
    institution: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    province: Optional[str] = Field(None, max_length=50)
    postal_code: Optional[str] = Field(None, max_length=10)
    emergency_contact: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = Field(None, max_length=1000)
    is_active: bool = Field(default=True)

class DoctorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    practice_number: Optional[str] = Field(None, max_length=20)
    specialization: Optional[str] = Field(None, max_length=100)
    institution: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    province: Optional[str] = Field(None, max_length=50)
    postal_code: Optional[str] = Field(None, max_length=10)
    emergency_contact: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None

class DoctorResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    hpcsa_number: str
    practice_number: Optional[str]
    specialization: Optional[str]
    institution: Optional[str]
    department: Optional[str]
    address: Optional[str]
    city: Optional[str]
    province: Optional[str]
    postal_code: Optional[str]
    emergency_contact: Optional[str]
    notes: Optional[str]
    is_active: bool
    referral_count: int
    last_referral_date: Optional[str]
    created_at: str
    updated_at: str

class DoctorListResponse(BaseModel):
    doctors: List[DoctorResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class DoctorStatsResponse(BaseModel):
    total_doctors: int
    active_doctors: int
    inactive_doctors: int
    by_specialization: Dict[str, int]
    by_province: Dict[str, int]
    top_referring_doctors: List[Dict[str, Any]]

# Router instance
router = APIRouter(prefix="/doctors", tags=["Doctors"])

# Dependency to get database session
def get_db():
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

# Dependency to get doctor manager
def get_doctor_manager(db = Depends(get_db)):
    return DoctorManager(db)


@router.post("/", response_model=DoctorResponse)
async def create_doctor(
    doctor_data: DoctorCreate,
    current_user: User = Depends(get_current_active_user),
    doctor_manager: DoctorManager = Depends(get_doctor_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Create a new referring doctor
    Requires 'write' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "write")
        
        # Create doctor
        doctor = doctor_manager.create_doctor(doctor_data.dict())
        
        logger.info(f"Doctor created by {current_user.username}: {doctor.name}")
        
        return DoctorResponse(**doctor.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create doctor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create doctor"
        )


@router.get("/", response_model=DoctorListResponse)
async def list_doctors(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name, email, or HPCSA number"),
    specialization: Optional[str] = Query(None, description="Filter by specialization"),
    province: Optional[str] = Query(None, description="Filter by province"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_active_user),
    doctor_manager: DoctorManager = Depends(get_doctor_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    List referring doctors with pagination and filtering
    Requires 'read' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "read")
        
        # Build filters
        filters = {}
        if search:
            filters["search"] = search
        if specialization:
            filters["specialization"] = specialization
        if province:
            filters["province"] = province
        if is_active is not None:
            filters["is_active"] = is_active
        
        # Get doctors
        result = doctor_manager.get_doctors_paginated(
            page=page,
            per_page=per_page,
            filters=filters
        )
        
        return DoctorListResponse(
            doctors=[DoctorResponse(**doctor.to_dict()) for doctor in result["doctors"]],
            total=result["total"],
            page=page,
            per_page=per_page,
            total_pages=result["total_pages"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list doctors: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve doctors"
        )


@router.get("/stats", response_model=DoctorStatsResponse)
async def get_doctor_stats(
    current_user: User = Depends(get_current_active_user),
    doctor_manager: DoctorManager = Depends(get_doctor_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Get doctor statistics and analytics
    Requires 'read' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "read")
        
        # Get statistics
        stats = doctor_manager.get_doctor_statistics()
        
        return DoctorStatsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get doctor stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve doctor statistics"
        )


@router.get("/{doctor_id}", response_model=DoctorResponse)
async def get_doctor(
    doctor_id: str,
    current_user: User = Depends(get_current_active_user),
    doctor_manager: DoctorManager = Depends(get_doctor_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Get doctor by ID
    Requires 'read' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "read")
        
        # Get doctor
        doctor = doctor_manager.get_doctor(doctor_id)
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found"
            )
        
        return DoctorResponse(**doctor.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get doctor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve doctor"
        )


@router.put("/{doctor_id}", response_model=DoctorResponse)
async def update_doctor(
    doctor_id: str,
    doctor_data: DoctorUpdate,
    current_user: User = Depends(get_current_active_user),
    doctor_manager: DoctorManager = Depends(get_doctor_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Update doctor by ID
    Requires 'write' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "write")
        
        # Filter out None values
        update_data = {k: v for k, v in doctor_data.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided"
            )
        
        # Update doctor
        doctor = doctor_manager.update_doctor(doctor_id, update_data)
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found"
            )
        
        logger.info(f"Doctor updated by {current_user.username}: {doctor.name}")
        
        return DoctorResponse(**doctor.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update doctor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update doctor"
        )


@router.delete("/{doctor_id}")
async def delete_doctor(
    doctor_id: str,
    current_user: User = Depends(get_current_active_user),
    doctor_manager: DoctorManager = Depends(get_doctor_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Delete doctor by ID (soft delete)
    Requires 'delete' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "delete")
        
        # Delete doctor (soft delete by setting is_active=False)
        success = doctor_manager.delete_doctor(doctor_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found"
            )
        
        logger.info(f"Doctor deleted by {current_user.username}: {doctor_id}")
        
        return {"message": "Doctor deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete doctor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete doctor"
        )


@router.get("/{doctor_id}/referrals")
async def get_doctor_referrals(
    doctor_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    doctor_manager: DoctorManager = Depends(get_doctor_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Get referrals made by a specific doctor
    Requires 'read' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "read")
        
        # Get doctor referrals
        referrals = doctor_manager.get_doctor_referrals(
            doctor_id=doctor_id,
            page=page,
            per_page=per_page
        )
        
        return referrals
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get doctor referrals: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve doctor referrals"
        )


@router.post("/{doctor_id}/verify-hpcsa")
async def verify_hpcsa_number(
    doctor_id: str,
    current_user: User = Depends(get_current_active_user),
    doctor_manager: DoctorManager = Depends(get_doctor_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Verify doctor's HPCSA number (South African compliance)
    Requires 'write' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "write")
        
        # Get doctor
        doctor = doctor_manager.get_doctor(doctor_id)
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found"
            )
        
        # Verify HPCSA number
        verification_result = doctor_manager.verify_hpcsa_number(doctor.hpcsa_number)
        
        logger.info(f"HPCSA verification requested by {current_user.username} for doctor: {doctor.name}")
        
        return {
            "doctor_id": doctor_id,
            "hpcsa_number": doctor.hpcsa_number,
            "verification_status": verification_result["status"],
            "verification_details": verification_result.get("details"),
            "verified_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify HPCSA number: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify HPCSA number"
        )


@router.get("/search/by-hpcsa/{hpcsa_number}", response_model=DoctorResponse)
async def search_doctor_by_hpcsa(
    hpcsa_number: str,
    current_user: User = Depends(get_current_active_user),
    doctor_manager: DoctorManager = Depends(get_doctor_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Search doctor by HPCSA number
    Requires 'read' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "read")
        
        # Search doctor by HPCSA number
        doctor = doctor_manager.get_doctor_by_hpcsa(hpcsa_number)
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found with this HPCSA number"
            )
        
        return DoctorResponse(**doctor.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search doctor by HPCSA: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search doctor"
        )


@router.get("/export/csv")
async def export_doctors_csv(
    specialization: Optional[str] = Query(None, description="Filter by specialization"),
    province: Optional[str] = Query(None, description="Filter by province"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_active_user),
    doctor_manager: DoctorManager = Depends(get_doctor_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Export doctors data as CSV
    Requires 'read' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "read")
        
        # Build filters
        filters = {}
        if specialization:
            filters["specialization"] = specialization
        if province:
            filters["province"] = province
        if is_active is not None:
            filters["is_active"] = is_active
        
        # Export to CSV
        csv_data = doctor_manager.export_doctors_csv(filters)
        
        logger.info(f"Doctors CSV export requested by {current_user.username}")
        
        from fastapi.responses import Response
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=doctors_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export doctors CSV: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export doctors data"
        )
