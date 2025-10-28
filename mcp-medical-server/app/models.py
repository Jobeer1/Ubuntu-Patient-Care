"""Database Models for Medical Schemes Server"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    role = Column(String(50), default="Patient", index=True)  # Patient, Doctor, Radiologist, Technician, Admin
    password_hash = Column(String(255), nullable=True)
    
    # OAuth tokens
    google_access_token = Column(Text, nullable=True)
    google_refresh_token = Column(Text, nullable=True)
    google_token_updated_at = Column(DateTime, nullable=True)
    
    microsoft_access_token = Column(Text, nullable=True)
    microsoft_refresh_token = Column(Text, nullable=True)
    microsoft_token_updated_at = Column(DateTime, nullable=True)
    
    # Patient-specific fields
    patient_id = Column(String(100), nullable=True, unique=True, index=True)
    medical_aid_number = Column(String(100), nullable=True)
    scheme_code = Column(String(50), nullable=True)
    
    # Doctor-specific fields
    referring_doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    license_number = Column(String(100), nullable=True)
    
    # Status and timestamps
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    permissions = relationship("UserPermission", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

class Role(Base):
    """Role model for RBAC"""
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Permission flags
    can_view_images = Column(Boolean, default=False)
    can_upload_images = Column(Boolean, default=False)
    can_edit_images = Column(Boolean, default=False)
    can_delete_images = Column(Boolean, default=False)
    can_view_reports = Column(Boolean, default=False)
    can_create_reports = Column(Boolean, default=False)
    can_edit_reports = Column(Boolean, default=False)
    can_approve_reports = Column(Boolean, default=False)
    can_view_patients = Column(Boolean, default=False)
    can_create_patients = Column(Boolean, default=False)
    can_edit_patients = Column(Boolean, default=False)
    can_manage_users = Column(Boolean, default=False)
    can_manage_roles = Column(Boolean, default=False)
    can_view_audit_logs = Column(Boolean, default=False)
    can_export_to_cloud = Column(Boolean, default=False)
    can_share_studies = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Role(id={self.id}, name={self.name})>"

class UserPermission(Base):
    """User-specific permission model (for granular overrides)"""
    __tablename__ = "user_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    permission_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(String(255), nullable=True, index=True)  # Can be patient_id, study_id, etc.
    
    granted_at = Column(DateTime, default=datetime.utcnow)
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="permissions", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<UserPermission(user_id={self.user_id}, permission={self.permission_type})>"

class AuditLog(Base):
    """Audit log model for tracking access and changes"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True, index=True)
    resource_id = Column(String(255), nullable=True, index=True)
    action = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    
    status = Column(String(20), default="success", index=True)  # success, denied, error
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    user = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<AuditLog(user_id={self.user_id}, event={self.event_type}, timestamp={self.timestamp})>"

class MedicalScheme(Base):
    """Medical Scheme/Medical Aid info (for reference)"""
    __tablename__ = "medical_schemes"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<MedicalScheme(code={self.code}, name={self.name})>"

class PreAuthRequest(Base):
    """Pre-authorization request model"""
    __tablename__ = "pre_auth_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(String(100), nullable=False, index=True)
    scheme_code = Column(String(50), ForeignKey("medical_schemes.code"))
    
    service_type = Column(String(100), nullable=False)
    provider_name = Column(String(255), nullable=True)
    amount = Column(Integer, nullable=False)  # In cents/cents equivalent
    
    status = Column(String(20), default="pending", index=True)  # pending, approved, denied
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    decided_at = Column(DateTime, nullable=True)
    decided_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<PreAuthRequest(id={self.id}, member_id={self.member_id}, status={self.status})>"
