"""
Orthanc Management Models - Patient Referral
Tracks patient referrals and workflow automation
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import json

from ..database.manager import Base
from ..database.schema import DatabaseCompatibleMixin, generate_id, get_timestamp_default


class PatientReferral(Base, DatabaseCompatibleMixin):
    """
    Patient Referral Model
    Tracks referrals from doctors and automates access workflow
    """
    __tablename__ = 'patient_referrals'
    
    # Primary key
    id = Column(String(50), primary_key=True, default=generate_id)
    
    # Core referral data
    patient_id = Column(String(50), nullable=False, index=True)
    referring_doctor_id = Column(String(50), ForeignKey('referring_doctors.id'), nullable=False, index=True)
    study_instance_uid = Column(String(100), nullable=True, index=True)
    
    # Referral details
    referral_date = Column(DateTime, nullable=False, default=get_timestamp_default, index=True)
    study_type = Column(String(100), nullable=True)
    clinical_indication = Column(Text, nullable=True)
    priority = Column(String(20), nullable=False, default='routine')
    
    # Patient information (cached for performance)
    patient_name = Column(String(100), nullable=True)
    patient_dob = Column(String(20), nullable=True)
    patient_gender = Column(String(10), nullable=True)
    
    # Access management
    access_granted = Column(Boolean, nullable=False, default=False)
    access_expires = Column(DateTime, nullable=True, index=True)
    notification_sent = Column(Boolean, nullable=False, default=False)
    patient_contacted = Column(Boolean, nullable=False, default=False)
    
    # Workflow tracking
    status = Column(String(20), nullable=False, default='pending')
    workflow_data = Column(Text, nullable=True)  # JSON data for workflow state
    
    # Audit fields
    created_at = Column(DateTime, nullable=False, default=get_timestamp_default)
    updated_at = Column(DateTime, nullable=True, onupdate=get_timestamp_default)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    referring_doctor = relationship("ReferringDoctor", back_populates="referrals")
    
    # Class constants
    PRIORITIES = {
        'routine': 'Routine',
        'urgent': 'Urgent',
        'emergency': 'Emergency'
    }
    
    STATUSES = {
        'pending': 'Pending',
        'processing': 'Processing',
        'completed': 'Completed',
        'failed': 'Failed',
        'expired': 'Expired'
    }
    
    STUDY_TYPES = {
        'xray': 'X-Ray',
        'ct': 'CT Scan',
        'mri': 'MRI',
        'ultrasound': 'Ultrasound',
        'mammography': 'Mammography',
        'nuclear': 'Nuclear Medicine',
        'pet': 'PET Scan',
        'angiography': 'Angiography',
        'other': 'Other'
    }
    
    def __repr__(self):
        return f"<PatientReferral(id='{self.id}', patient='{self.patient_id}', doctor='{self.referring_doctor_id}')>"
    
    def __str__(self):
        return f"Referral {self.id} - {self.patient_name or self.patient_id} ({self.get_priority_display()})"
    
    def validate(self) -> list:
        """Validate referral data and return list of errors"""
        errors = []
        
        # Required fields
        if not self.patient_id or len(self.patient_id.strip()) < 1:
            errors.append("Patient ID is required")
        
        if not self.referring_doctor_id:
            errors.append("Referring doctor ID is required")
        
        # Enum validations
        if self.priority not in self.PRIORITIES:
            errors.append(f"Invalid priority. Must be one of: {list(self.PRIORITIES.keys())}")
        
        if self.status not in self.STATUSES:
            errors.append(f"Invalid status. Must be one of: {list(self.STATUSES.keys())}")
        
        if self.study_type and self.study_type not in self.STUDY_TYPES:
            errors.append(f"Invalid study type. Must be one of: {list(self.STUDY_TYPES.keys())}")
        
        # Date validations
        if self.access_expires and self.access_expires <= datetime.utcnow():
            errors.append("Access expiration date must be in the future")
        
        return errors
    
    def get_priority_display(self) -> str:
        """Get human-readable priority"""
        return self.PRIORITIES.get(self.priority, self.priority)
    
    def get_status_display(self) -> str:
        """Get human-readable status"""
        return self.STATUSES.get(self.status, self.status)
    
    def get_study_type_display(self) -> str:
        """Get human-readable study type"""
        return self.STUDY_TYPES.get(self.study_type, self.study_type)
    
    def is_urgent(self) -> bool:
        """Check if referral is urgent or emergency"""
        return self.priority in ['urgent', 'emergency']
    
    def is_expired(self) -> bool:
        """Check if access has expired"""
        if not self.access_expires:
            return False
        return self.access_expires <= datetime.utcnow()
    
    def days_since_referral(self) -> int:
        """Get number of days since referral"""
        if not self.referral_date:
            return 0
        return (datetime.utcnow() - self.referral_date).days
    
    def grant_access(self, expires_in_days: int = 30) -> bool:
        """Grant access to referring doctor"""
        try:
            self.access_granted = True
            self.access_expires = datetime.utcnow() + timedelta(days=expires_in_days)
            self.status = 'completed'
            self.processed_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
            return True
        except Exception:
            return False
    
    def revoke_access(self) -> bool:
        """Revoke access from referring doctor"""
        try:
            self.access_granted = False
            self.access_expires = datetime.utcnow()  # Set to past date
            self.updated_at = datetime.utcnow()
            return True
        except Exception:
            return False
    
    def extend_access(self, additional_days: int) -> bool:
        """Extend access period"""
        try:
            if not self.access_expires:
                self.access_expires = datetime.utcnow() + timedelta(days=additional_days)
            else:
                self.access_expires += timedelta(days=additional_days)
            self.updated_at = datetime.utcnow()
            return True
        except Exception:
            return False
    
    def get_workflow_data(self) -> dict:
        """Get workflow data as dictionary"""
        if not self.workflow_data:
            return {}
        try:
            return json.loads(self.workflow_data)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_workflow_data(self, data: dict):
        """Set workflow data from dictionary"""
        try:
            self.workflow_data = json.dumps(data)
        except (TypeError, ValueError):
            self.workflow_data = "{}"
    
    def update_workflow_step(self, step: str, status: str, details: dict = None):
        """Update specific workflow step"""
        workflow = self.get_workflow_data()
        workflow[step] = {
            'status': status,
            'timestamp': datetime.utcnow().isoformat(),
            'details': details or {}
        }
        self.set_workflow_data(workflow)
    
    def mark_notification_sent(self, notification_type: str = 'email'):
        """Mark notification as sent"""
        self.notification_sent = True
        self.update_workflow_step('notification', 'sent', {
            'type': notification_type,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def mark_patient_contacted(self, contact_method: str = 'email'):
        """Mark patient as contacted"""
        self.patient_contacted = True
        self.update_workflow_step('patient_contact', 'completed', {
            'method': contact_method,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def calculate_priority_score(self) -> int:
        """Calculate priority score for workflow ordering"""
        base_scores = {
            'emergency': 100,
            'urgent': 50,
            'routine': 10
        }
        
        score = base_scores.get(self.priority, 10)
        
        # Increase score based on days waiting
        days_waiting = self.days_since_referral()
        score += days_waiting * 2
        
        # Increase score if notification not sent
        if not self.notification_sent:
            score += 20
        
        return score
    
    def to_dict(self, include_workflow: bool = False) -> dict:
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'patient_id': self.patient_id,
            'patient_name': self.patient_name,
            'patient_dob': self.patient_dob,
            'patient_gender': self.patient_gender,
            'referring_doctor_id': self.referring_doctor_id,
            'study_instance_uid': self.study_instance_uid,
            'referral_date': self.referral_date.isoformat() if self.referral_date else None,
            'study_type': self.study_type,
            'study_type_display': self.get_study_type_display(),
            'clinical_indication': self.clinical_indication,
            'priority': self.priority,
            'priority_display': self.get_priority_display(),
            'status': self.status,
            'status_display': self.get_status_display(),
            'access_granted': self.access_granted,
            'access_expires': self.access_expires.isoformat() if self.access_expires else None,
            'notification_sent': self.notification_sent,
            'patient_contacted': self.patient_contacted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'days_since_referral': self.days_since_referral(),
            'is_urgent': self.is_urgent(),
            'is_expired': self.is_expired(),
            'priority_score': self.calculate_priority_score()
        }
        
        if include_workflow:
            data['workflow_data'] = self.get_workflow_data()
        
        # Include doctor information if available
        if self.referring_doctor:
            data['referring_doctor'] = {
                'id': self.referring_doctor.id,
                'name': self.referring_doctor.name,
                'hpcsa_number': self.referring_doctor.hpcsa_number,
                'practice_name': self.referring_doctor.practice_name
            }
        
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PatientReferral':
        """Create instance from dictionary"""
        referral = cls()
        
        # Map fields
        fields = [
            'patient_id', 'referring_doctor_id', 'study_instance_uid',
            'study_type', 'clinical_indication', 'priority', 'patient_name',
            'patient_dob', 'patient_gender', 'access_granted', 'notification_sent',
            'patient_contacted', 'status'
        ]
        
        for field in fields:
            if field in data:
                setattr(referral, field, data[field])
        
        # Handle date fields
        if 'referral_date' in data and data['referral_date']:
            if isinstance(data['referral_date'], str):
                referral.referral_date = datetime.fromisoformat(data['referral_date'])
            else:
                referral.referral_date = data['referral_date']
        
        if 'access_expires' in data and data['access_expires']:
            if isinstance(data['access_expires'], str):
                referral.access_expires = datetime.fromisoformat(data['access_expires'])
            else:
                referral.access_expires = data['access_expires']
        
        # Handle workflow data
        if 'workflow_data' in data:
            if isinstance(data['workflow_data'], dict):
                referral.set_workflow_data(data['workflow_data'])
            else:
                referral.workflow_data = data['workflow_data']
        
        return referral
