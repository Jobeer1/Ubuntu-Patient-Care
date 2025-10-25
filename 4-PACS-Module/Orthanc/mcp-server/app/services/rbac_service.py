"""Role-Based Access Control Service"""
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from app.models import User, Role, UserPermission
from datetime import datetime

class RBACService:
    """Service for managing role-based access control"""
    
    # Default role permissions
    ROLE_PERMISSIONS = {
        "Patient": {
            "can_view_images": True,
            "can_view_reports": True,
            "can_export_to_cloud": True,
            "modules": ["my-images", "my-reports"]
        },
        "Referring Doctor": {
            "can_view_images": True,
            "can_view_reports": True,
            "can_view_patients": True,
            "can_export_to_cloud": True,
            "can_share_studies": True,
            "modules": ["patients", "images", "reports"]
        },
        "Radiologist": {
            "can_view_images": True,
            "can_view_reports": True,
            "can_create_reports": True,
            "can_edit_reports": True,
            "can_approve_reports": True,
            "can_view_patients": True,
            "can_export_to_cloud": True,
            "can_share_studies": True,
            "modules": ["worklist", "reporting", "images", "patients"]
        },
        "Technician": {
            "can_view_images": True,
            "can_upload_images": True,
            "can_edit_images": True,
            "can_view_patients": True,
            "can_create_patients": True,
            "can_edit_patients": True,
            "modules": ["acquisition", "patients", "images"]
        },
        "Admin": {
            "can_view_images": True,
            "can_upload_images": True,
            "can_edit_images": True,
            "can_delete_images": True,
            "can_view_reports": True,
            "can_create_reports": True,
            "can_edit_reports": True,
            "can_approve_reports": True,
            "can_view_patients": True,
            "can_create_patients": True,
            "can_edit_patients": True,
            "can_manage_users": True,
            "can_manage_roles": True,
            "can_view_audit_logs": True,
            "can_export_to_cloud": True,
            "can_share_studies": True,
            "modules": ["admin", "users", "audit", "worklist", "reporting", "images", "patients"]
        }
    }
    
    @staticmethod
    def get_user_permissions(user: User) -> Dict:
        """Get all permissions for a user (role + individual overrides)"""
        base_permissions = RBACService.ROLE_PERMISSIONS.get(user.role, {})
        return base_permissions
    
    @staticmethod
    def get_accessible_modules(user: User) -> List[str]:
        """Get list of modules user can access"""
        permissions = RBACService.get_user_permissions(user)
        return permissions.get("modules", [])
    
    @staticmethod
    def can_access_patient_data(db: Session, user: User, patient_id: str) -> bool:
        """Check if user can access specific patient's data"""
        # Patients can only view their own data
        if user.role == "Patient":
            return user.patient_id == patient_id
        
        # Referring doctors can view their patients' data
        if user.role == "Referring Doctor":
            patient = db.query(User).filter(
                User.patient_id == patient_id,
                User.referring_doctor_id == user.id
            ).first()
            return patient is not None
        
        # Radiologists, Technicians, and Admins can view all patients
        if user.role in ["Radiologist", "Technician", "Admin"]:
            return True
        
        return False
    
    @staticmethod
    def can_access_study(db: Session, user: User, study_patient_id: str) -> bool:
        """Check if user can access a specific study"""
        return RBACService.can_access_patient_data(db, user, study_patient_id)
    
    @staticmethod
    def grant_permission(
        db: Session,
        user_id: int,
        permission_type: str,
        resource_id: Optional[str] = None,
        granted_by: Optional[int] = None,
        expires_at: Optional[datetime] = None
    ) -> UserPermission:
        """Grant specific permission to a user"""
        permission = UserPermission(
            user_id=user_id,
            permission_type=permission_type,
            resource_id=resource_id,
            granted_by=granted_by,
            expires_at=expires_at
        )
        db.add(permission)
        db.commit()
        db.refresh(permission)
        return permission
    
    @staticmethod
    def revoke_permission(db: Session, permission_id: int) -> bool:
        """Revoke a specific permission"""
        permission = db.query(UserPermission).filter(UserPermission.id == permission_id).first()
        if permission:
            db.delete(permission)
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_user_specific_permissions(db: Session, user_id: int) -> List[UserPermission]:
        """Get all specific permissions granted to a user"""
        return db.query(UserPermission).filter(
            UserPermission.user_id == user_id
        ).all()
    
    @staticmethod
    def initialize_default_roles(db: Session):
        """Initialize default roles in database"""
        for role_name, permissions in RBACService.ROLE_PERMISSIONS.items():
            existing_role = db.query(Role).filter(Role.name == role_name).first()
            if not existing_role:
                role = Role(
                    name=role_name,
                    description=f"Default {role_name} role",
                    can_view_images=permissions.get("can_view_images", False),
                    can_upload_images=permissions.get("can_upload_images", False),
                    can_edit_images=permissions.get("can_edit_images", False),
                    can_delete_images=permissions.get("can_delete_images", False),
                    can_view_reports=permissions.get("can_view_reports", False),
                    can_create_reports=permissions.get("can_create_reports", False),
                    can_edit_reports=permissions.get("can_edit_reports", False),
                    can_approve_reports=permissions.get("can_approve_reports", False),
                    can_view_patients=permissions.get("can_view_patients", False),
                    can_create_patients=permissions.get("can_create_patients", False),
                    can_edit_patients=permissions.get("can_edit_patients", False),
                    can_manage_users=permissions.get("can_manage_users", False),
                    can_manage_roles=permissions.get("can_manage_roles", False),
                    can_view_audit_logs=permissions.get("can_view_audit_logs", False),
                    can_export_to_cloud=permissions.get("can_export_to_cloud", False),
                    can_share_studies=permissions.get("can_share_studies", False)
                )
                db.add(role)
        db.commit()
    
    @staticmethod
    def get_all_roles() -> Dict[str, List[str]]:
        """Get all available roles and their modules"""
        roles_dict = {}
        for role_name, permissions in RBACService.ROLE_PERMISSIONS.items():
            roles_dict[role_name] = permissions.get("modules", [])
        return roles_dict
    
    @staticmethod
    def get_modules_for_role(role_name: str) -> Optional[List[str]]:
        """Get modules accessible by a specific role"""
        if role_name not in RBACService.ROLE_PERMISSIONS:
            return None
        return RBACService.ROLE_PERMISSIONS[role_name].get("modules", [])
