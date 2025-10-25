"""
Orthanc Management Models - Patient Share
Secure patient link sharing for direct patient access
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, Index, CheckConstraint
from datetime import datetime, timedelta
import json
import secrets
import hashlib

from ..database.manager import Base
from ..database.schema import DatabaseCompatibleMixin, generate_id, get_timestamp_default


class PatientShare(Base, DatabaseCompatibleMixin):
    """
    Patient Share Model
    Manages secure, time-limited links for patients to access their own medical images
    """
    __tablename__ = 'patient_shares'
    
    # Primary key
    id = Column(String(50), primary_key=True, default=generate_id)
    
    # Patient information
    patient_id = Column(String(50), nullable=False, index=True)
    patient_name = Column(String(100), nullable=True)
    patient_email = Column(String(100), nullable=True)
    patient_phone = Column(String(20), nullable=True)
    
    # Share data
    study_uids = Column(Text, nullable=False)  # JSON array of study UIDs
    share_token = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    
    # Metadata
    created_by = Column(String(50), nullable=False)  # Admin user who created the share
    created_at = Column(DateTime, nullable=False, default=get_timestamp_default)
    expires_at = Column(DateTime, nullable=True, index=True)
    
    # Usage control
    max_downloads = Column(Integer, nullable=False, default=10)
    download_count = Column(Integer, nullable=False, default=0)
    access_count = Column(Integer, nullable=False, default=0)
    last_accessed = Column(DateTime, nullable=True)
    
    # Status and configuration
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    mobile_optimized = Column(Boolean, nullable=False, default=True)
    allow_download = Column(Boolean, nullable=False, default=True)
    require_password = Column(Boolean, nullable=False, default=False)
    
    # Communication tracking
    email_sent = Column(Boolean, nullable=False, default=False)
    sms_sent = Column(Boolean, nullable=False, default=False)
    notification_count = Column(Integer, nullable=False, default=0)
    last_notification = Column(DateTime, nullable=True)
    
    # Additional metadata
    share_title = Column(String(200), nullable=True)
    share_description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    
    # Table constraints
    __table_args__ = (
        Index('idx_patient_shares_patient_active', 'patient_id', 'is_active'),
        Index('idx_patient_shares_expires_active', 'expires_at', 'is_active'),
        Index('idx_patient_shares_created_by', 'created_by'),
        Index('idx_patient_shares_token_active', 'share_token', 'is_active'),
        CheckConstraint('max_downloads >= 0', name='ck_patient_shares_max_downloads'),
        CheckConstraint('download_count >= 0', name='ck_patient_shares_download_count'),
        CheckConstraint('access_count >= 0', name='ck_patient_shares_access_count'),
        CheckConstraint('notification_count >= 0', name='ck_patient_shares_notification_count'),
    )
    
    def __repr__(self):
        return f"<PatientShare(id='{self.id}', patient='{self.patient_id}', token='{self.share_token[:8]}...')>"
    
    def __str__(self):
        return f"Patient Share {self.id} - {self.patient_name or self.patient_id}"
    
    @classmethod
    def generate_secure_token(cls) -> str:
        """Generate cryptographically secure share token"""
        return secrets.token_urlsafe(32)
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.share_token:
            self.share_token = self.generate_secure_token()
    
    def validate(self) -> list:
        """Validate share data and return list of errors"""
        errors = []
        
        # Required fields
        if not self.patient_id or len(self.patient_id.strip()) < 1:
            errors.append("Patient ID is required")
        
        if not self.study_uids:
            errors.append("Study UIDs are required")
        else:
            # Validate JSON format
            try:
                uids = json.loads(self.study_uids)
                if not isinstance(uids, list) or len(uids) == 0:
                    errors.append("Study UIDs must be a non-empty list")
            except (json.JSONDecodeError, TypeError):
                errors.append("Study UIDs must be valid JSON")
        
        if not self.created_by or len(self.created_by.strip()) < 1:
            errors.append("Created by user ID is required")
        
        if not self.share_token:
            errors.append("Share token is required")
        
        # Date validations
        if self.expires_at and self.expires_at <= datetime.utcnow():
            errors.append("Expiration date must be in the future")
        
        # Email validation
        if self.patient_email:
            import re
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(pattern, self.patient_email):
                errors.append("Invalid email format")
        
        # Phone validation (South African format)
        if self.patient_phone:
            import re
            digits_only = re.sub(r'\D', '', self.patient_phone)
            if not (len(digits_only) == 10 and digits_only.startswith('0')) and \
               not (len(digits_only) == 11 and digits_only.startswith('27')):
                errors.append("Invalid phone number format")
        
        # Numeric validations
        if self.max_downloads < 0:
            errors.append("Max downloads cannot be negative")
        
        if self.download_count < 0:
            errors.append("Download count cannot be negative")
        
        if self.access_count < 0:
            errors.append("Access count cannot be negative")
        
        # Logic validations
        if self.require_password and not self.password_hash:
            errors.append("Password hash is required when password is required")
        
        return errors
    
    def get_study_uids(self) -> list:
        """Get study UIDs as list"""
        if not self.study_uids:
            return []
        try:
            return json.loads(self.study_uids)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_study_uids(self, uids: list):
        """Set study UIDs from list"""
        try:
            self.study_uids = json.dumps(uids)
        except (TypeError, ValueError):
            self.study_uids = "[]"
    
    def add_study_uid(self, uid: str):
        """Add a study UID to the share"""
        uids = self.get_study_uids()
        if uid not in uids:
            uids.append(uid)
            self.set_study_uids(uids)
    
    def remove_study_uid(self, uid: str):
        """Remove a study UID from the share"""
        uids = self.get_study_uids()
        if uid in uids:
            uids.remove(uid)
            self.set_study_uids(uids)
    
    def is_expired(self) -> bool:
        """Check if share has expired"""
        if not self.expires_at:
            return False
        return self.expires_at <= datetime.utcnow()
    
    def is_download_limit_reached(self) -> bool:
        """Check if download limit has been reached"""
        return self.download_count >= self.max_downloads
    
    def is_accessible(self) -> bool:
        """Check if share is currently accessible"""
        return (self.is_active and 
                not self.is_expired() and 
                not self.is_download_limit_reached())
    
    def days_until_expiry(self) -> int:
        """Get number of days until expiration (-1 if no expiration)"""
        if not self.expires_at:
            return -1
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)
    
    def check_password(self, password: str) -> bool:
        """Check if provided password matches"""
        if not self.require_password:
            return True
        if not self.password_hash:
            return False
        return self.password_hash == self.hash_password(password)
    
    def set_password(self, password: str):
        """Set password for the share"""
        if password:
            self.password_hash = self.hash_password(password)
            self.require_password = True
        else:
            self.password_hash = None
            self.require_password = False
    
    def record_access(self) -> bool:
        """Record that this share was accessed"""
        try:
            self.access_count += 1
            self.last_accessed = datetime.utcnow()
            return True
        except Exception:
            return False
    
    def record_download(self) -> bool:
        """Record a download"""
        try:
            if self.download_count < self.max_downloads:
                self.download_count += 1
                self.last_accessed = datetime.utcnow()
                return True
            return False
        except Exception:
            return False
    
    def extend_expiry(self, additional_days: int) -> bool:
        """Extend expiration date"""
        try:
            if not self.expires_at:
                self.expires_at = datetime.utcnow() + timedelta(days=additional_days)
            else:
                self.expires_at += timedelta(days=additional_days)
            return True
        except Exception:
            return False
    
    def deactivate(self) -> bool:
        """Deactivate the share"""
        try:
            self.is_active = False
            return True
        except Exception:
            return False
    
    def get_access_url(self, base_url: str = "https://your-domain.com") -> str:
        """Generate full access URL for the share"""
        return f"{base_url}/patient-access/{self.share_token}"
    
    def mark_notification_sent(self, notification_type: str = 'email') -> bool:
        """Mark notification as sent"""
        try:
            if notification_type == 'email':
                self.email_sent = True
            elif notification_type == 'sms':
                self.sms_sent = True
            
            self.notification_count += 1
            self.last_notification = datetime.utcnow()
            return True
        except Exception:
            return False
    
    def get_usage_stats(self) -> dict:
        """Get usage statistics"""
        return {
            'total_accesses': self.access_count,
            'total_downloads': self.download_count,
            'downloads_remaining': max(0, self.max_downloads - self.download_count),
            'download_percentage': (self.download_count / self.max_downloads * 100) if self.max_downloads > 0 else 0,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'days_since_creation': (datetime.utcnow() - self.created_at).days if self.created_at else 0,
            'days_until_expiry': self.days_until_expiry(),
            'notifications_sent': self.notification_count
        }
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'patient_id': self.patient_id,
            'patient_name': self.patient_name,
            'share_token': self.share_token if include_sensitive else f"{self.share_token[:8]}...",
            'study_uids': self.get_study_uids(),
            'study_count': len(self.get_study_uids()),
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'is_accessible': self.is_accessible(),
            'is_expired': self.is_expired(),
            'mobile_optimized': self.mobile_optimized,
            'allow_download': self.allow_download,
            'require_password': self.require_password,
            'usage_stats': self.get_usage_stats(),
            'share_title': self.share_title,
            'share_description': self.share_description
        }
        
        if include_sensitive:
            data.update({
                'patient_email': self.patient_email,
                'patient_phone': self.patient_phone,
                'password_hash': self.password_hash,
                'max_downloads': self.max_downloads,
                'download_count': self.download_count,
                'access_count': self.access_count,
                'email_sent': self.email_sent,
                'sms_sent': self.sms_sent,
                'notification_count': self.notification_count,
                'last_notification': self.last_notification.isoformat() if self.last_notification else None,
                'instructions': self.instructions
            })
        
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PatientShare':
        """Create instance from dictionary"""
        share = cls()
        
        # Map fields
        fields = [
            'patient_id', 'patient_name', 'patient_email', 'patient_phone',
            'created_by', 'is_active', 'mobile_optimized', 'allow_download',
            'require_password', 'max_downloads', 'share_title', 'share_description',
            'instructions'
        ]
        
        for field in fields:
            if field in data:
                setattr(share, field, data[field])
        
        # Handle study UIDs
        if 'study_uids' in data:
            if isinstance(data['study_uids'], list):
                share.set_study_uids(data['study_uids'])
            else:
                share.study_uids = data['study_uids']
        
        # Handle dates
        date_fields = ['expires_at']
        for field in date_fields:
            if field in data and data[field]:
                if isinstance(data[field], str):
                    setattr(share, field, datetime.fromisoformat(data[field]))
                else:
                    setattr(share, field, data[field])
        
        # Handle password
        if 'password' in data and data['password']:
            share.set_password(data['password'])
        
        return share
    
    @classmethod
    def create_patient_share(cls, patient_id: str, study_uids: list, created_by: str,
                           expires_in_days: int = 7, max_downloads: int = 10,
                           patient_email: str = None, patient_phone: str = None,
                           password: str = None, **kwargs) -> 'PatientShare':
        """Factory method to create a patient share with common settings"""
        share = cls(
            patient_id=patient_id,
            created_by=created_by,
            patient_email=patient_email,
            patient_phone=patient_phone,
            max_downloads=max_downloads,
            **kwargs
        )
        
        # Set study UIDs
        share.set_study_uids(study_uids)
        
        # Set expiration
        if expires_in_days > 0:
            share.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Set password if provided
        if password:
            share.set_password(password)
        
        return share
