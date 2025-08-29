"""
Orthanc Management Models - Referring Doctor
HPCSA registered medical professionals with access control
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import re

from ..database.manager import Base
from ..database.schema import DatabaseCompatibleMixin, generate_id, get_timestamp_default


class ReferringDoctor(Base, DatabaseCompatibleMixin):
    """
    Referring Doctor Model
    Represents HPCSA registered medical professionals who can access patient data
    """
    __tablename__ = 'referring_doctors'
    
    # Primary key
    id = Column(String(50), primary_key=True, default=generate_id)
    
    # Personal Information
    name = Column(String(100), nullable=False, index=True)
    hpcsa_number = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(100), nullable=True, index=True)
    phone = Column(String(20), nullable=True)
    
    # Practice Information
    practice_name = Column(String(100), nullable=True)
    specialization = Column(String(50), nullable=True)
    facility_type = Column(String(50), nullable=True)  # private_practice, clinic, hospital
    province = Column(String(50), nullable=True)
    
    # Access Control
    access_level = Column(String(20), nullable=False, default='view_only')
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    # Additional metadata
    notes = Column(Text, nullable=True)
    emergency_contact = Column(String(100), nullable=True)
    
    # Audit Fields
    created_at = Column(DateTime, nullable=False, default=get_timestamp_default)
    updated_at = Column(DateTime, nullable=True, onupdate=get_timestamp_default)
    last_access = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    
    # Relationships
    referrals = relationship("PatientReferral", back_populates="referring_doctor", cascade="all, delete-orphan")
    # authorizations = relationship("PatientAuthorization", back_populates="doctor", cascade="all, delete-orphan")
    
    # Class constants
    ACCESS_LEVELS = {
        'view_only': 'View Only',
        'download': 'Download Images',
        'annotate': 'Add Annotations',
        'report_access': 'Access Reports',
        'share': 'Create Patient Shares',
        'full_access': 'Full Access'
    }
    
    FACILITY_TYPES = {
        'private_practice': 'Private Practice',
        'clinic': 'Clinic',
        'hospital': 'Hospital',
        'academic': 'Academic Institution',
        'other': 'Other'
    }
    
    PROVINCES = {
        'ec': 'Eastern Cape',
        'fs': 'Free State',
        'gp': 'Gauteng',
        'kzn': 'KwaZulu-Natal',
        'lp': 'Limpopo',
        'mp': 'Mpumalanga',
        'nc': 'Northern Cape',
        'nw': 'North West',
        'wc': 'Western Cape'
    }
    
    def __repr__(self):
        return f"<ReferringDoctor(id='{self.id}', name='{self.name}', hpcsa='{self.hpcsa_number}')>"
    
    def __str__(self):
        return f"Dr. {self.name} ({self.hpcsa_number})"
    
    @classmethod
    def validate_hpcsa_number(cls, hpcsa_number: str) -> bool:
        """
        Validate HPCSA number format
        Format: MP123456 or similar (2 letters + 6 digits)
        """
        if not hpcsa_number:
            return False
        
        # HPCSA format: 2 letters + 6 digits
        pattern = r'^[A-Z]{2}\d{6}$'
        return bool(re.match(pattern, hpcsa_number.upper()))
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validate email format"""
        if not email:
            return True  # Email is optional
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @classmethod
    def validate_phone(cls, phone: str) -> bool:
        """Validate South African phone number"""
        if not phone:
            return True  # Phone is optional
        
        # Remove all non-digits
        digits_only = re.sub(r'\D', '', phone)
        
        # South African numbers: 10 digits starting with 0, or 11 digits starting with 27
        if len(digits_only) == 10 and digits_only.startswith('0'):
            return True
        elif len(digits_only) == 11 and digits_only.startswith('27'):
            return True
        
        return False
    
    def validate(self) -> list:
        """Validate all doctor data and return list of errors"""
        errors = []
        
        # Required fields
        if not self.name or len(self.name.strip()) < 2:
            errors.append("Name is required and must be at least 2 characters")
        
        if not self.hpcsa_number:
            errors.append("HPCSA number is required")
        elif not self.validate_hpcsa_number(self.hpcsa_number):
            errors.append("Invalid HPCSA number format (expected: XX123456)")
        
        # Optional field validation
        if self.email and not self.validate_email(self.email):
            errors.append("Invalid email format")
        
        if self.phone and not self.validate_phone(self.phone):
            errors.append("Invalid phone number format")
        
        # Enum validations
        if self.access_level not in self.ACCESS_LEVELS:
            errors.append(f"Invalid access level. Must be one of: {list(self.ACCESS_LEVELS.keys())}")
        
        if self.facility_type and self.facility_type not in self.FACILITY_TYPES:
            errors.append(f"Invalid facility type. Must be one of: {list(self.FACILITY_TYPES.keys())}")
        
        if self.province and self.province not in self.PROVINCES:
            errors.append(f"Invalid province. Must be one of: {list(self.PROVINCES.keys())}")
        
        return errors
    
    def get_access_level_display(self) -> str:
        """Get human-readable access level"""
        return self.ACCESS_LEVELS.get(self.access_level, self.access_level)
    
    def get_facility_type_display(self) -> str:
        """Get human-readable facility type"""
        return self.FACILITY_TYPES.get(self.facility_type, self.facility_type)
    
    def get_province_display(self) -> str:
        """Get human-readable province name"""
        return self.PROVINCES.get(self.province, self.province)
    
    def can_access_level(self, required_level: str) -> bool:
        """Check if doctor has required access level or higher"""
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
    
    def update_last_access(self, ip_address: str = None):
        """Update last access timestamp and IP"""
        self.last_access = datetime.utcnow()
        if ip_address:
            self.last_login_ip = ip_address
    
    def get_referral_count(self) -> int:
        """Get count of referrals by this doctor"""
        return len(self.referrals) if self.referrals else 0
    
    def get_active_authorizations_count(self) -> int:
        """Get count of active authorizations"""
        # TODO: Implement when PatientAuthorization model is created
        return 0
        # if not self.authorizations:
        #     return 0
        # 
        # from datetime import datetime
        # current_time = datetime.utcnow()
        # 
        # return sum(1 for auth in self.authorizations 
        #           if auth.is_active and 
        #           (auth.expires_at is None or auth.expires_at > current_time))
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'name': self.name,
            'hpcsa_number': self.hpcsa_number,
            'practice_name': self.practice_name,
            'specialization': self.specialization,
            'facility_type': self.facility_type,
            'facility_type_display': self.get_facility_type_display(),
            'province': self.province,
            'province_display': self.get_province_display(),
            'access_level': self.access_level,
            'access_level_display': self.get_access_level_display(),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_access': self.last_access.isoformat() if self.last_access else None,
            'referral_count': self.get_referral_count(),
            'active_authorizations': self.get_active_authorizations_count()
        }
        
        if include_sensitive:
            data.update({
                'email': self.email,
                'phone': self.phone,
                'notes': self.notes,
                'emergency_contact': self.emergency_contact,
                'last_login_ip': self.last_login_ip,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            })
        
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ReferringDoctor':
        """Create instance from dictionary"""
        doctor = cls()
        
        # Map fields
        fields = [
            'name', 'hpcsa_number', 'email', 'phone', 'practice_name',
            'specialization', 'facility_type', 'province', 'access_level',
            'is_active', 'notes', 'emergency_contact'
        ]
        
        for field in fields:
            if field in data:
                setattr(doctor, field, data[field])
        
        return doctor
