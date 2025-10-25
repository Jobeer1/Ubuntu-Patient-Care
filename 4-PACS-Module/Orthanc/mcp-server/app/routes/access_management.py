"""
Access Management API Routes
Admin endpoints for managing patient access relationships

This module provides REST API endpoints for:
- Creating patient relationships (user → patient mapping)
- Assigning doctors to patients
- Granting family access
- Checking access permissions
- Revoking access
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional
from app.database import get_db
from app.services import get_pacs_connector, get_access_control_service
import logging
import sqlite3

router = APIRouter(prefix="/access", tags=["access_management"])
logger = logging.getLogger(__name__)


class PatientRelationshipCreate(BaseModel):
    patient_id: str = Field(..., description="Patient identifier in PACS")
    user_id: int = Field(..., description="User id to grant access to")
    access_level: str = Field("read", description="Access level: read|download")
    expires_at: Optional[str] = Field(None, description="Optional ISO expiry date")


class DoctorAssignmentCreate(BaseModel):
    doctor_user_id: int
    patient_id: str
    assignment_type: Optional[str] = "primary"


class FamilyAccessCreate(BaseModel):
    parent_user_id: int
    child_patient_id: str
    relationship: Optional[str] = "parent"
    expires_at: Optional[str] = None


@router.post("/patient-relationship")
async def create_patient_relationship(payload: PatientRelationshipCreate, request: Request):
    """
    Create a patient relationship (grant user access to their patient record)
    
    Admin only endpoint.
    """
    try:
        # Get current user from request (should be admin)
        # TODO: Add proper authentication middleware
        admin_user_id = 1  # Placeholder
        
        # Get database connection
        db = get_db()
        
        # Verify patient exists in PACS
        pacs = get_pacs_connector()
        if not pacs.verify_patient_exists(payload.patient_id):
            raise HTTPException(status_code=404, detail=f"Patient {payload.patient_id} not found in PACS")
        
        # Create relationship
        cursor = db.execute("""
            INSERT INTO patient_relationships 
            (user_id, patient_identifier, relationship_type, access_level, created_by, expires_at, is_active)
            VALUES (?, ?, 'self', ?, ?, ?, 1)
        """, (payload.user_id, payload.patient_id, payload.access_level, admin_user_id, payload.expires_at))
        
        db.commit()
        relationship_id = cursor.lastrowid
        
        logger.info(f"Patient relationship created: user {payload.user_id} → patient {payload.patient_id}")
        
        return {
            "success": True,
            "message": "Patient relationship created successfully",
            "data": {
                "id": relationship_id,
                "user_id": payload.user_id,
                "patient_id": payload.patient_id,
                "access_level": payload.access_level
            }
        }
        
    except sqlite3.IntegrityError as e:
        logger.error(f"Integrity error creating relationship: {e}")
        raise HTTPException(status_code=400, detail="Relationship already exists or invalid user_id")
    except Exception as e:
        logger.error(f"Error creating patient relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/doctor-assignment")
async def create_doctor_assignment(payload: DoctorAssignmentCreate, request: Request):
    """
    Assign a referring doctor to a patient
    
    Admin only endpoint.
    """
    try:
        admin_user_id = 1  # Placeholder
        db = get_db()
        
        # Verify patient exists
        pacs = get_pacs_connector()
        if not pacs.verify_patient_exists(payload.patient_id):
            raise HTTPException(status_code=404, detail=f"Patient {payload.patient_id} not found in PACS")
        
        # Verify doctor user exists and has correct role
        cursor = db.execute("SELECT role FROM users WHERE id = ?", (payload.doctor_user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {payload.doctor_user_id} not found")
        if user[0] != 'Referring Doctor':
            raise HTTPException(status_code=400, detail=f"User {payload.doctor_user_id} is not a Referring Doctor")
        
        # Create assignment
        cursor = db.execute("""
            INSERT INTO doctor_patient_assignments 
            (doctor_user_id, patient_identifier, assignment_type, assigned_by, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, (payload.doctor_user_id, payload.patient_id, payload.assignment_type, admin_user_id))
        
        db.commit()
        assignment_id = cursor.lastrowid
        
        logger.info(f"Doctor assignment created: doctor {payload.doctor_user_id} → patient {payload.patient_id}")
        
        return {
            "success": True,
            "message": "Doctor assignment created successfully",
            "data": {
                "id": assignment_id,
                "doctor_user_id": payload.doctor_user_id,
                "patient_id": payload.patient_id,
                "assignment_type": payload.assignment_type
            }
        }
        
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Assignment already exists")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating doctor assignment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/family-access")
async def create_family_access(payload: FamilyAccessCreate, request: Request):
    """
    Grant family access (parent/guardian to child's records)
    
    Admin only endpoint. Requires admin verification.
    """
    try:
        admin_user_id = 1  # Placeholder
        db = get_db()
        
        # Verify child patient exists
        pacs = get_pacs_connector()
        if not pacs.verify_patient_exists(payload.child_patient_id):
            raise HTTPException(status_code=404, detail=f"Patient {payload.child_patient_id} not found in PACS")
        
        # Verify parent user exists
        cursor = db.execute("SELECT id FROM users WHERE id = ?", (payload.parent_user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"User {payload.parent_user_id} not found")
        
        # Create family access (verified by admin)
        cursor = db.execute("""
            INSERT INTO family_access 
            (parent_user_id, child_patient_identifier, relationship, verified, verified_by, verified_at, expires_at, is_active)
            VALUES (?, ?, ?, 1, ?, datetime('now'), ?, 1)
        """, (payload.parent_user_id, payload.child_patient_id, payload.relationship, admin_user_id, payload.expires_at))
        
        db.commit()
        access_id = cursor.lastrowid
        
        logger.info(f"Family access created: parent {payload.parent_user_id} → child {payload.child_patient_id}")
        
        return {
            "success": True,
            "message": "Family access granted successfully",
            "data": {
                "id": access_id,
                "parent_user_id": payload.parent_user_id,
                "child_patient_id": payload.child_patient_id,
                "relationship": payload.relationship,
                "verified": True
            }
        }
        
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Family access already exists")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating family access: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/patients")
async def get_user_patients(user_id: int):
    """
    Get list of patient IDs accessible to a user
    
    Returns list of patient IDs based on user's role and assignments.
    """
    try:
        db = get_db()
        
        # Get user role
        cursor = db.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        user_role = user[0]
        
        # Get accessible patients using access control service
        pacs = get_pacs_connector()
        access_control = get_access_control_service(pacs, db)
        accessible_patients = access_control.get_accessible_patients(user_id, user_role)
        
        # Get patient count
        patient_count = access_control.get_accessible_patient_count(user_id, user_role)
        
        logger.info(f"User {user_id} ({user_role}) has access to {patient_count} patients")
        
        return {
            "user_id": user_id,
            "user_role": user_role,
            "has_full_access": '*' in accessible_patients,
            "accessible_patients": accessible_patients if '*' not in accessible_patients else [],
            "patient_count": patient_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user patients: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check")
async def check_access(user_id: Optional[int] = None, patient_id: Optional[str] = None):
    """
    Check whether a user has access to a specific patient
    
    Used by PACS backend to validate access before serving images.
    """
    if not user_id or not patient_id:
        raise HTTPException(status_code=400, detail="user_id and patient_id are required")
    
    try:
        db = get_db()
        
        # Get user role
        cursor = db.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        user_role = user[0]
        
        # Check access using access control service
        pacs = get_pacs_connector()
        access_control = get_access_control_service(pacs, db)
        has_access = access_control.can_access_patient(user_id, user_role, patient_id)
        
        # Log access attempt
        access_control.log_access_attempt(
            user_id=user_id,
            patient_id=patient_id,
            access_type='check',
            granted=has_access
        )
        
        logger.info(f"Access check: user {user_id} → patient {patient_id}: {'GRANTED' if has_access else 'DENIED'}")
        
        return {
            "user_id": user_id,
            "patient_id": patient_id,
            "has_access": has_access,
            "user_role": user_role
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking access: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/revoke")
async def revoke_access(user_id: int, patient_id: str):
    """
    Revoke access relationship
    
    Admin only endpoint. Deactivates all access relationships for user→patient.
    """
    try:
        db = get_db()
        
        # Deactivate patient relationships
        cursor = db.execute("""
            UPDATE patient_relationships 
            SET is_active = 0 
            WHERE user_id = ? AND patient_identifier = ?
        """, (user_id, patient_id))
        
        relationships_revoked = cursor.rowcount
        
        # Deactivate doctor assignments
        cursor = db.execute("""
            UPDATE doctor_patient_assignments 
            SET is_active = 0 
            WHERE doctor_user_id = ? AND patient_identifier = ?
        """, (user_id, patient_id))
        
        assignments_revoked = cursor.rowcount
        
        # Deactivate family access
        cursor = db.execute("""
            UPDATE family_access 
            SET is_active = 0 
            WHERE parent_user_id = ? AND child_patient_identifier = ?
        """, (user_id, patient_id))
        
        family_revoked = cursor.rowcount
        
        db.commit()
        
        total_revoked = relationships_revoked + assignments_revoked + family_revoked
        
        logger.info(f"Access revoked: user {user_id} → patient {patient_id} ({total_revoked} relationships)")
        
        return {
            "success": True,
            "message": f"Access revoked successfully ({total_revoked} relationships)",
            "user_id": user_id,
            "patient_id": patient_id,
            "revoked_count": total_revoked
        }
        
    except Exception as e:
        logger.error(f"Error revoking access: {e}")
        raise HTTPException(status_code=500, detail=str(e))
