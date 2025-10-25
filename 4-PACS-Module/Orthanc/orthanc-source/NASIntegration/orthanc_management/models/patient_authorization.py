"""
Orthanc Management Models - Patient Authorization
Manual access control for doctors to access specific patient studies
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import json

from ..database.manager import Base
from ..database.schema import DatabaseCompatibleMixin, generate_id, get_timestamp_default


class PatientAuthorization(Base, DatabaseCompatibleMixin):
    """
    Patient Authorization Model
    Manages manual access control for doctors to access specific patient studies
    """
    __tablename__ = 'patient_authorizations'
    
    # Primary key
    id = Column(String(50), primary_key=True, default=generate_id)
    
    # Authorization data
    doctor_id = Column(String(50), ForeignKey('referring_doctors.id'), nullable=False, index=True)
    patient_id = Column(String(50), nullable=False, index=True)
    study_instance_uid = Column(String(100), nullable=True, index=True)
    
    # Access control
    access_level = Column(String(20), nullable=False, default='view_only')
    granted_by = Column(String(50), nullable=False)  # Admin user who granted access
    granted_at = Column(DateTime, nullable=False, default=get_timestamp_default)
    expires_at = Column(DateTime, nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    # Usage tracking
    access_count = Column(Integer, nullable=False, default=0)
    last_accessed = Column(DateTime, nullable=True)
    
    # Additional metadata
    notes = Column(String(500), nullable=True)
    access_reason = Column(String(200), nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, nullable=False, default=get_timestamp_default)
    updated_at = Column(DateTime, nullable=True, onupdate=get_timestamp_default)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(String(50), nullable=True)
    revoked_reason = Column(String(200), nullable=True)
    
    # Relationships
    doctor = relationship("ReferringDoctor", backref="authorizations")
    
    # Table constraints
    __table_args__ = (
        Index('idx_patient_auth_doctor_patient', 'doctor_id', 'patient_id'),
        Index('idx_patient_auth_active_expires', 'is_active', 'expires_at'),
        Index('idx_patient_auth_study_access', 'study_instance_uid', 'access_level'),
        Index('idx_patient_auth_granted_by_date', 'granted_by', 'granted_at'),
        UniqueConstraint('doctor_id', 'patient_id', 'study_instance_uid',
                        name='uq_patient_auth_doctor_patient_study'),
        CheckConstraint('access_level IN ("view_only", "download", "annotate", "report_access", "share", "full_access")',
                       name='ck_patient_auth_access_level'),
    )
    
    # Class constants
    ACCESS_LEVELS = {
        'view_only': 'View Only',
        'download': 'Download Images',
        'annotate': 'Add Annotations',
        'report_access': 'Access Reports',
        'share': 'Create Patient Shares',
        'full_access': 'Full Access'
    }
    
    def __repr__(self):
        return f"<PatientAuthorization(id='{self.id}', doctor='{self.doctor_id}', patient='{self.patient_id}')>"
    
    def __str__(self):
        return f"Authorization {self.id} - {self.access_level} for {self.patient_id}"
    
    def validate(self) -> list:
        """Validate authorization data and return list of errors"""
        errors = []
        
        # Required fields
        if not self.doctor_id or len(self.doctor_id.strip()) < 1:
            errors.append("Doctor ID is required")
        
        if not self.patient_id or len(self.patient_id.strip()) < 1:
            errors.append("Patient ID is required")
        
        if not self.granted_by or len(self.granted_by.strip()) < 1:
            errors.append("Granted by user ID is required")
        
        # Enum validations
        if self.access_level not in self.ACCESS_LEVELS:
            errors.append(f"Invalid access level. Must be one of: {list(self.ACCESS_LEVELS.keys())}")
        
        # Date validations
        if self.expires_at and self.expires_at <= datetime.utcnow():
            errors.append("Expiration date must be in the future")
        
        if self.revoked_at and not self.revoked_by:
            errors.append("Revoked by user is required when revoked date is set")
        
        # Length validations
        if self.notes and len(self.notes) > 500:
            errors.append("Notes must be 500 characters or less")
        
        if self.access_reason and len(self.access_reason) > 200:
            errors.append("Access reason must be 200 characters or less")
        
        return errors
    
    def get_access_level_display(self) -> str:
        """Get human-readable access level"""
        return self.ACCESS_LEVELS.get(self.access_level, self.access_level)
    
    def is_expired(self) -> bool:
        """Check if authorization has expired"""
        if not self.expires_at:
            return False
        return self.expires_at <= datetime.utcnow()
    
    def is_revoked(self) -> bool:
        """Check if authorization has been revoked"""
        return self.revoked_at is not None
    
    def is_valid(self) -> bool:
        """Check if authorization is currently valid"""
        return self.is_active and not self.is_expired() and not self.is_revoked()
    
    def days_until_expiry(self) -> int:
        """Get number of days until expiration (-1 if no expiration)"""
        if not self.expires_at:
            return -1
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)
    
    def extend_access(self, additional_days: int) -> bool:
        """Extend access period"""
        try:
            if not self.expires_at:
                self.expires_at = datetime.utcnow() + timedelta(days=additional_days)
            else:
                self.expires_at += timedelta(days=additional_days)
            self.updated_at = datetime.utcnow()
            return True
        except Exception:
            return False
    
    def revoke_access(self, revoked_by: str, reason: str = None) -> bool:
        """Revoke authorization"""
        try:
            self.is_active = False
            self.revoked_at = datetime.utcnow()
            self.revoked_by = revoked_by
            self.revoked_reason = reason
            self.updated_at = datetime.utcnow()
            return True
        except Exception:
            return False
    
    def record_access(self) -> bool:
        """Record that this authorization was accessed"""
        try:
            self.access_count += 1
            self.last_accessed = datetime.utcnow()
            return True
        except Exception:
            return False
    
    def can_access_level(self, required_level: str) -> bool:
        """Check if this authorization allows the required access level"""
        if not self.is_valid():
            return False
        
        level_hierarchy = [
            'view_only',
            'download', 
            'annotate',
            'report_access',
            'share',
            'full_access'
        ]
        
        try:
            current_index = level_hierarchy.index(self.access_level)
            required_index = level_hierarchy.index(required_level)
            return current_index >= required_index
        except ValueError:
            return False
    
    def get_access_summary(self) -> dict:
        """Get summary of access permissions"""
        return {
            'can_view': self.can_access_level('view_only'),
            'can_download': self.can_access_level('download'),
            'can_annotate': self.can_access_level('annotate'),
            'can_access_reports': self.can_access_level('report_access'),
            'can_share': self.can_access_level('share'),
            'has_full_access': self.can_access_level('full_access')
        }
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'doctor_id': self.doctor_id,
            'patient_id': self.patient_id,
            'study_instance_uid': self.study_instance_uid,
            'access_level': self.access_level,
            'access_level_display': self.get_access_level_display(),
            'granted_by': self.granted_by,
            'granted_at': self.granted_at.isoformat() if self.granted_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'is_valid': self.is_valid(),
            'is_expired': self.is_expired(),
            'is_revoked': self.is_revoked(),
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'days_until_expiry': self.days_until_expiry(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'access_summary': self.get_access_summary()
        }
        
        if include_sensitive:
            data.update({
                'notes': self.notes,
                'access_reason': self.access_reason,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None,
                'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
                'revoked_by': self.revoked_by,
                'revoked_reason': self.revoked_reason
            })
        
        # Include doctor information if available
        if self.doctor:
            data['doctor'] = {
                'id': self.doctor.id,
                'name': self.doctor.name,
                'hpcsa_number': self.doctor.hpcsa_number,
                'practice_name': self.doctor.practice_name
            }
        
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PatientAuthorization':
        """Create instance from dictionary"""
        auth = cls()
        
        # Map fields
        fields = [
            'doctor_id', 'patient_id', 'study_instance_uid', 'access_level',
            'granted_by', 'is_active', 'notes', 'access_reason',
            'revoked_by', 'revoked_reason'
        ]
        
        for field in fields:
            if field in data:
                setattr(auth, field, data[field])
        
        # Handle date fields
        date_fields = ['granted_at', 'expires_at', 'revoked_at']
        for field in date_fields:
            if field in data and data[field]:
                if isinstance(data[field], str):
                    setattr(auth, field, datetime.fromisoformat(data[field]))
                else:
                    setattr(auth, field, data[field])
        
        return auth
    
    @classmethod
    def create_bulk_authorization(cls, doctor_id: str, patient_ids: list, 
                                 access_level: str, granted_by: str,
                                 expires_in_days: int = 30,
                                 study_uids: list = None) -> list:
        """Create multiple authorizations at once"""
        authorizations = []
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days > 0 else None
        
        for patient_id in patient_ids:
            # If specific study UIDs provided, create one auth per study
            if study_uids:
                for study_uid in study_uids:
                    auth = cls(
                        doctor_id=doctor_id,
                        patient_id=patient_id,
                        study_instance_uid=study_uid,
                        access_level=access_level,
                        granted_by=granted_by,
                        expires_at=expires_at
                    )
                    authorizations.append(auth)
            else:
                # Create general patient access
                auth = cls(
                    doctor_id=doctor_id,
                    patient_id=patient_id,
                    access_level=access_level,
                    granted_by=granted_by,
                    expires_at=expires_at
                )
                authorizations.append(auth)
        
        return authorizations
