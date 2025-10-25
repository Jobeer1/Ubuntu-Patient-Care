"""
User Studies API Routes
Endpoints for users to access their studies and patient information

This module provides REST API endpoints for:
- Getting user's accessible studies
- Getting user's accessible patients (for doctors)
- Filtering and pagination
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.services import get_pacs_connector, get_access_control_service
import logging

router = APIRouter(prefix="/access", tags=["user_studies"])
logger = logging.getLogger(__name__)


class StudyResponse(BaseModel):
    id: int
    patient_id: str
    patient_name: Optional[str]
    study_date: Optional[str]
    study_description: Optional[str]
    modality: Optional[str]
    dicom_file_count: Optional[int]


class PatientResponse(BaseModel):
    patient_id: str
    patient_name: Optional[str]
    patient_birth_date: Optional[str]
    patient_sex: Optional[str]
    study_count: Optional[int]
    last_study_date: Optional[str]


@router.get("/my-studies", response_model=List[StudyResponse])
async def my_studies(
    request: Request,
    user_id: int = Query(..., description="User ID"),
    limit: int = Query(100, description="Maximum number of studies to return")
):
    """
    Get studies accessible to the user
    
    Returns list of studies based on user's role and access permissions.
    """
    try:
        db = get_db()
        
        # Get user role
        cursor = db.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        user_role = user[0]
        
        # Get accessible studies using access control service
        pacs = get_pacs_connector()
        access_control = get_access_control_service(pacs, db)
        studies = access_control.get_user_studies(user_id, user_role, limit=limit)
        
        logger.info(f"User {user_id} ({user_role}) retrieved {len(studies)} studies")
        
        # Convert to response model
        return [StudyResponse(**study) for study in studies]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user studies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-patients", response_model=List[PatientResponse])
async def my_patients(
    request: Request,
    user_id: int = Query(..., description="User ID")
):
    """
    Get patients accessible to the user
    
    For doctors: returns assigned patients
    For patients: returns self + family members
    For admin/radiologist: returns recent patients
    """
    try:
        db = get_db()
        
        # Get user role
        cursor = db.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        user_role = user[0]
        
        # Get accessible patients
        pacs = get_pacs_connector()
        access_control = get_access_control_service(pacs, db)
        accessible_patient_ids = access_control.get_accessible_patients(user_id, user_role)
        
        # If wildcard (admin/radiologist), get recent patients
        if '*' in accessible_patient_ids:
            patients, _ = pacs.get_patient_list(offset=0, limit=100)
        else:
            # Get patient info for each accessible patient
            patients = []
            for patient_id in accessible_patient_ids:
                patient_info = pacs.get_patient_info(patient_id)
                if patient_info:
                    patients.append(patient_info)
        
        logger.info(f"User {user_id} ({user_role}) retrieved {len(patients)} patients")
        
        # Convert to response model
        return [PatientResponse(**patient) for patient in patients]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user patients: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_access_summary(
    user_id: int = Query(..., description="User ID")
):
    """
    Get summary of user's access permissions
    
    Returns comprehensive summary including:
    - User role
    - Full access flag
    - Accessible patient count
    - Role-specific details
    """
    try:
        db = get_db()
        
        # Get user role
        cursor = db.execute("SELECT role, name, email FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        user_role, user_name, user_email = user
        
        # Get access summary
        pacs = get_pacs_connector()
        access_control = get_access_control_service(pacs, db)
        summary = access_control.get_access_summary(user_id, user_role)
        
        # Add user details
        summary['user_name'] = user_name
        summary['user_email'] = user_email
        
        logger.info(f"Access summary for user {user_id}: {summary['accessible_patient_count']} patients")
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting access summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
