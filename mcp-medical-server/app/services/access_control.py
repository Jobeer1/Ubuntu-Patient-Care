"""Access Control Service"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import User

class AccessControlService:
    """Service for managing access control at patient/scheme level"""
    
    @staticmethod
    def get_accessible_patients(db: Session, user: User) -> List[str]:
        """Get list of patient IDs accessible to the user"""
        
        # Patients can only access themselves
        if user.role == "Patient":
            if user.patient_id:
                return [user.patient_id]
            return []
        
        # Referring doctors can access their assigned patients
        if user.role == "Referring Doctor":
            return AccessControlService._get_doctor_assigned_patients(db, user.id)
        
        # Radiologists and Technicians can see all patients
        if user.role in ["Radiologist", "Technician"]:
            all_patients = db.query(User).filter(User.role == "Patient").all()
            return [p.patient_id for p in all_patients if p.patient_id]
        
        # Admins can access all patients
        if user.role == "Admin":
            all_patients = db.query(User).filter(User.role == "Patient").all()
            return [p.patient_id for p in all_patients if p.patient_id]
        
        return []
    
    @staticmethod
    def can_access_patient(db: Session, user: User, patient_id: str) -> bool:
        """Check if user can access a specific patient"""
        
        # Patients can only access themselves
        if user.role == "Patient":
            return user.patient_id == patient_id
        
        # Referring doctors can access their assigned patients
        if user.role == "Referring Doctor":
            assigned_patients = AccessControlService._get_doctor_assigned_patients(db, user.id)
            return patient_id in assigned_patients
        
        # Radiologists, Technicians, and Admins can access any patient
        if user.role in ["Radiologist", "Technician", "Admin"]:
            return True
        
        return False
    
    @staticmethod
    def _get_doctor_assigned_patients(db: Session, doctor_id: int) -> List[str]:
        """Get patients assigned to a specific doctor"""
        assigned_patients = db.query(User).filter(
            User.referring_doctor_id == doctor_id,
            User.role == "Patient"
        ).all()
        
        return [p.patient_id for p in assigned_patients if p.patient_id]
    
    @staticmethod
    def _get_patient_self_access(user: User) -> List[str]:
        """Get self-access for patient (their own data)"""
        if user.patient_id:
            return [user.patient_id]
        return []
    
    @staticmethod
    def _get_family_access(db: Session, user: User) -> List[str]:
        """Get family member access (for patients viewing family member records)"""
        # This would implement family access permissions
        # For now, returning empty as it requires additional family relationships table
        return []
    
    @staticmethod
    def assign_patient_to_doctor(db: Session, patient: User, doctor: User) -> bool:
        """Assign a patient to a referring doctor"""
        if patient.role != "Patient" or doctor.role != "Referring Doctor":
            return False
        
        patient.referring_doctor_id = doctor.id
        db.commit()
        return True
    
    @staticmethod
    def revoke_doctor_access(db: Session, patient: User, doctor: User) -> bool:
        """Revoke a doctor's access to a patient"""
        if patient.referring_doctor_id == doctor.id:
            patient.referring_doctor_id = None
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_user_studies(db: Session, user: User) -> List[str]:
        """Get list of study IDs accessible to the user"""
        # This would integrate with ORTHANC/DICOM connector
        # Returns list of accessible study IDs
        # Placeholder implementation
        return []
    
    @staticmethod
    def can_access_study(db: Session, user: User, study_id: str, patient_id: str) -> bool:
        """Check if user can access a specific study"""
        return AccessControlService.can_access_patient(db, user, patient_id)
    
    @staticmethod
    def can_perform_action(db: Session, user: User, action: str, resource_id: Optional[str] = None) -> bool:
        """Check if user can perform an action"""
        from app.services.rbac_service import RBACService
        
        permissions = RBACService.get_user_permissions(user)
        return permissions.get(action, False)
