"""
Report data model for Medical Reporting Module
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
import uuid

# Import unified base
from .database import Base

class ReportStatus(Enum):
    """Report status enumeration"""
    DRAFT = "draft"
    TYPING = "typing"
    REVIEW = "review"
    FINALIZED = "finalized"
    SUBMITTED = "submitted"
    FINAL = "final"
    ARCHIVED = "archived"

class ReportType(Enum):
    """Report type enumeration"""
    DIAGNOSTIC = "diagnostic"
    SCREENING = "screening"
    FOLLOW_UP = "follow_up"
    EMERGENCY = "emergency"
    CONSULTATION = "consultation"

class Report(Base):
    """Report model for storing medical reports"""
    __tablename__ = 'reports'
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign keys and relationships
    study_id = Column(String(64), nullable=False, index=True)
    patient_id = Column(String(64), nullable=False, index=True)
    doctor_id = Column(String(36), nullable=False, index=True)
    template_id = Column(String(36), ForeignKey('report_templates.id'), nullable=True)
    
    # Report content
    content = Column(JSON, nullable=False, default=dict)
    findings = Column(Text, nullable=True)
    impression = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    
    # Voice and dictation
    voice_recording_path = Column(String(255), nullable=True)
    voice_duration_seconds = Column(Integer, nullable=True)
    transcription_confidence = Column(Integer, nullable=True)  # 0-100
    
    # Report type and classification
    report_type = Column(String(20), nullable=False, default=ReportType.DIAGNOSTIC.value)
    
    # Status and workflow
    status = Column(String(20), nullable=False, default=ReportStatus.DRAFT.value)
    priority = Column(String(10), nullable=False, default='normal')  # urgent, high, normal, low
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    dictated_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    finalized_at = Column(DateTime, nullable=True)
    
    # Offline and sync
    is_offline_created = Column(Boolean, nullable=False, default=False)
    last_sync_at = Column(DateTime, nullable=True)
    sync_version = Column(Integer, nullable=False, default=1)
    
    # Audit trail
    created_by = Column(String(36), nullable=False)
    updated_by = Column(String(36), nullable=False)
    
    # Relationships (commented out to avoid circular import issues in testing)
    # template = relationship("ReportTemplate", back_populates="reports")
    # voice_sessions = relationship("VoiceSession", back_populates="report")
    # offline_changes = relationship("OfflineChange", back_populates="report")
    
    def __repr__(self):
        return f"<Report(id='{self.id}', patient_id='{self.patient_id}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert report to dictionary"""
        return {
            'id': self.id,
            'study_id': self.study_id,
            'patient_id': self.patient_id,
            'doctor_id': self.doctor_id,
            'template_id': self.template_id,
            'report_type': self.report_type,
            'content': self.content,
            'findings': self.findings,
            'impression': self.impression,
            'recommendations': self.recommendations,
            'voice_recording_path': self.voice_recording_path,
            'voice_duration_seconds': self.voice_duration_seconds,
            'transcription_confidence': self.transcription_confidence,
            'status': self.status,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'dictated_at': self.dictated_at.isoformat() if self.dictated_at else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'finalized_at': self.finalized_at.isoformat() if self.finalized_at else None,
            'is_offline_created': self.is_offline_created,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'sync_version': self.sync_version,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }
    
    def update_status(self, new_status, updated_by):
        """Update report status with timestamp"""
        self.status = new_status
        self.updated_by = updated_by
        self.updated_at = datetime.utcnow()
        
        if new_status == ReportStatus.TYPING.value:
            self.submitted_at = datetime.utcnow()
        elif new_status == ReportStatus.FINAL.value:
            self.finalized_at = datetime.utcnow()
    
    def is_editable(self):
        """Check if report can be edited"""
        return self.status in [ReportStatus.DRAFT.value, ReportStatus.REVIEW.value]
    
    def get_age_in_hours(self):
        """Get report age in hours"""
        if self.created_at:
            return (datetime.utcnow() - self.created_at).total_seconds() / 3600
        return 0

class OfflineChange(Base):
    """Track changes made while offline"""
    __tablename__ = 'offline_changes'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String(36), ForeignKey('reports.id'), nullable=False)
    
    # Change details
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    change_type = Column(String(20), nullable=False)  # create, update, delete
    
    # Timestamps
    changed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    synced_at = Column(DateTime, nullable=True)
    
    # Conflict resolution
    is_conflict = Column(Boolean, nullable=False, default=False)
    conflict_resolved = Column(Boolean, nullable=False, default=False)
    resolution_strategy = Column(String(50), nullable=True)
    
    # User info
    changed_by = Column(String(36), nullable=False)
    
    # Relationships
    # report = relationship("Report", back_populates="offline_changes")
    
    def __repr__(self):
        return f"<OfflineChange(id='{self.id}', report_id='{self.report_id}', field='{self.field_name}')>"