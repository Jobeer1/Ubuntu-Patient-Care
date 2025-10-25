"""Database models"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)  # For local sign-in
    name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="Patient")
    hpcsa_number = Column(String, nullable=True)
    practice_number = Column(String, nullable=True)  # For referring doctors
    language_preference = Column(String, default="en-ZA")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # OAuth tokens for cloud storage
    google_refresh_token = Column(String, nullable=True)
    microsoft_refresh_token = Column(String, nullable=True)
    
    # Patient-specific fields
    patient_id = Column(String, nullable=True, index=True)  # For patients
    referring_doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Link patient to doctor
    
    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")
    context = relationship("UserContext", back_populates="user", uselist=False)
    permissions = relationship("UserPermission", back_populates="user", foreign_keys="[UserPermission.user_id]")
    patients = relationship("User", backref="referring_doctor", remote_side=[id], foreign_keys="[User.referring_doctor_id]")  # Doctor's patients

class Role(Base):
    """Role model with module permissions"""
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    
    # Module access permissions
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

class UserPermission(Base):
    """Individual user permission overrides"""
    __tablename__ = "user_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    permission_type = Column(String, nullable=False)  # e.g., "view_patient", "view_study"
    resource_id = Column(String, nullable=True)  # Specific patient_id or study_id
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="permissions", foreign_keys=[user_id])

class AuditLog(Base):
    """Audit log model"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_email = Column(String, nullable=False)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    success = Column(Boolean, default=True)
    failure_reason = Column(String, nullable=True)
    session_id = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")

class UserContext(Base):
    """User context model"""
    __tablename__ = "user_context"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    language = Column(String, default="en-ZA")
    dictation_model = Column(String, default="whisper-large-v3")
    report_templates = Column(Text, nullable=True)  # JSON string
    ui_preferences = Column(Text, nullable=True)  # JSON string
    
    # Relationships
    user = relationship("User", back_populates="context")

class PatientContext(Base):
    """Patient context model"""
    __tablename__ = "patient_context"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String, unique=True, nullable=False, index=True)
    medical_aid = Column(String, nullable=True)
    scheme = Column(String, nullable=True)
    billing_codes = Column(Text, nullable=True)  # JSON string
    popia_consent = Column(Boolean, default=False)
    consent_date = Column(DateTime, nullable=True)


class DicomStudy(Base):
    """DICOM Study metadata from Orthanc"""
    __tablename__ = "dicom_studies"
    
    id = Column(Integer, primary_key=True, index=True)
    orthanc_study_id = Column(String, unique=True, nullable=False, index=True)
    orthanc_patient_id = Column(String, nullable=False, index=True)
    patient_name = Column(String, nullable=True)
    patient_id_from_dicom = Column(String, nullable=True, index=True)
    study_description = Column(String, nullable=True)
    study_date = Column(DateTime, nullable=True, index=True)
    study_time = Column(String, nullable=True)
    modality = Column(String, nullable=True)  # CT, MR, US, XA, etc.
    institution_name = Column(String, nullable=True)
    referring_physician = Column(String, nullable=True)
    
    # Study metrics
    num_series = Column(Integer, default=0)
    num_instances = Column(Integer, default=0)
    total_size_mb = Column(Integer, default=0)
    
    # Metadata
    study_uid = Column(String, nullable=True, index=True)
    accession_number = Column(String, nullable=True, index=True)
    
    # System fields
    imported_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_accessed = Column(DateTime, nullable=True)
    
    # Relationships
    measurements = relationship("Measurement", back_populates="study")
    view_sessions = relationship("ViewSession", back_populates="study")


class Measurement(Base):
    """DICOM measurements (distance, area, volume, HU)"""
    __tablename__ = "measurements"
    
    id = Column(Integer, primary_key=True, index=True)
    study_id = Column(Integer, ForeignKey("dicom_studies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Measurement info
    measurement_type = Column(String, nullable=False)  # distance, area, angle, volume, hu
    label = Column(String, nullable=True)
    description = Column(String, nullable=True)
    
    # Measurement data (JSON structure varies by type)
    measurement_data = Column(JSON, nullable=False)  # Stores coordinates, values, etc.
    
    # Value in appropriate units
    value = Column(String, nullable=False)  # e.g., "45.2 mm", "1250 cm³", "340 HU"
    
    # Reference information
    series_index = Column(Integer, nullable=True)
    slice_index = Column(Integer, nullable=True)
    
    # System fields
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    study = relationship("DicomStudy", back_populates="measurements")
    user = relationship("User")


class ViewSession(Base):
    """DICOM viewer session tracking"""
    __tablename__ = "view_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    study_id = Column(Integer, ForeignKey("dicom_studies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Session info
    session_start = Column(DateTime, default=datetime.utcnow, index=True)
    session_end = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, default=0)
    
    # Viewer state snapshot
    last_slice_index = Column(Integer, default=0)
    last_mpr_position = Column(JSON, nullable=True)  # Stores axial, sagittal, coronal positions
    zoom_level = Column(String, default="1.0")
    window_level = Column(Integer, default=40)
    window_width = Column(Integer, default=400)
    
    # Activity flags
    measurements_created = Column(Integer, default=0)
    exports_performed = Column(Integer, default=0)
    
    # Relationships
    study = relationship("DicomStudy", back_populates="view_sessions")
    user = relationship("User")
