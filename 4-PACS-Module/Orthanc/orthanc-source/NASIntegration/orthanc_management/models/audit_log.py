"""
Orthanc Management Models - Audit Log
Comprehensive audit logging for HPCSA and POPIA compliance
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Index, CheckConstraint
from datetime import datetime
import json
import socket

from ..database.manager import Base
from ..database.schema import DatabaseCompatibleMixin, generate_id, get_timestamp_default


class AuditLog(Base, DatabaseCompatibleMixin):
    """
    Audit Log Model
    Comprehensive audit trail for compliance with HPCSA and POPIA requirements
    """
    __tablename__ = 'audit_logs'
    
    # Primary key
    id = Column(String(50), primary_key=True, default=generate_id)
    
    # User information
    user_id = Column(String(50), nullable=True, index=True)
    user_type = Column(String(20), nullable=False)  # admin, doctor, patient, system
    user_name = Column(String(100), nullable=True)
    hpcsa_number = Column(String(20), nullable=True)  # For doctor users
    
    # Action information
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(50), nullable=True, index=True)
    details = Column(Text, nullable=True)  # JSON details
    
    # Request information
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    session_id = Column(String(100), nullable=True)
    request_method = Column(String(10), nullable=True)  # GET, POST, etc.
    request_url = Column(String(500), nullable=True)
    
    # Result information
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    response_code = Column(String(10), nullable=True)
    
    # Compliance and security
    data_accessed = Column(Text, nullable=True)  # JSON array of accessed data types
    patient_ids = Column(Text, nullable=True)  # JSON array of patient IDs accessed
    study_uids = Column(Text, nullable=True)  # JSON array of study UIDs accessed
    compliance_category = Column(String(50), nullable=True)  # HPCSA, POPIA, etc.
    
    # System information
    server_name = Column(String(100), nullable=True)
    application_version = Column(String(20), nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime, nullable=False, default=get_timestamp_default, index=True)
    
    # Table constraints
    __table_args__ = (
        Index('idx_audit_logs_user_action', 'user_id', 'action'),
        Index('idx_audit_logs_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_logs_timestamp_action', 'timestamp', 'action'),
        Index('idx_audit_logs_user_type_timestamp', 'user_type', 'timestamp'),
        Index('idx_audit_logs_hpcsa_timestamp', 'hpcsa_number', 'timestamp'),
        Index('idx_audit_logs_compliance', 'compliance_category', 'timestamp'),
        Index('idx_audit_logs_patient_access', 'user_id', 'resource_type'),
        CheckConstraint('user_type IN ("admin", "doctor", "patient", "system", "anonymous")',
                       name='ck_audit_logs_user_type'),
    )
    
    # Class constants
    USER_TYPES = {
        'admin': 'Administrator',
        'doctor': 'Referring Doctor',
        'patient': 'Patient',
        'system': 'System Process',
        'anonymous': 'Anonymous User'
    }
    
    ACTIONS = {
        # Authentication actions
        'login': 'User Login',
        'logout': 'User Logout',
        'login_failed': 'Failed Login Attempt',
        'password_change': 'Password Changed',
        'account_locked': 'Account Locked',
        
        # Data access actions
        'view_patient': 'Viewed Patient Data',
        'view_study': 'Viewed Medical Study',
        'download_image': 'Downloaded Medical Image',
        'download_report': 'Downloaded Medical Report',
        'search_patients': 'Searched Patient Database',
        
        # Data modification actions
        'create_patient': 'Created Patient Record',
        'update_patient': 'Updated Patient Record',
        'delete_patient': 'Deleted Patient Record',
        'upload_study': 'Uploaded Medical Study',
        'delete_study': 'Deleted Medical Study',
        'add_annotation': 'Added Image Annotation',
        
        # Administrative actions
        'grant_access': 'Granted Patient Access',
        'revoke_access': 'Revoked Patient Access',
        'create_share': 'Created Patient Share Link',
        'access_share': 'Accessed Patient Share Link',
        'config_change': 'Changed System Configuration',
        'user_management': 'User Management Action',
        
        # System actions
        'system_start': 'System Started',
        'system_stop': 'System Stopped',
        'backup_created': 'Database Backup Created',
        'data_migration': 'Data Migration Performed',
        'security_scan': 'Security Scan Performed'
    }
    
    RESOURCE_TYPES = {
        'patient': 'Patient Record',
        'study': 'Medical Study',
        'series': 'Image Series',
        'instance': 'DICOM Instance',
        'doctor': 'Referring Doctor',
        'authorization': 'Patient Authorization',
        'share': 'Patient Share',
        'config': 'System Configuration',
        'user': 'User Account',
        'session': 'User Session',
        'system': 'System Resource'
    }
    
    COMPLIANCE_CATEGORIES = {
        'hpcsa': 'HPCSA Compliance',
        'popia': 'POPIA Compliance',
        'hipaa': 'HIPAA Compliance',
        'security': 'Security Audit',
        'access_control': 'Access Control',
        'data_protection': 'Data Protection'
    }
    
    def __repr__(self):
        return f"<AuditLog(id='{self.id}', action='{self.action}', user='{self.user_id}')>"
    
    def __str__(self):
        timestamp = self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else 'Unknown'
        return f"[{timestamp}] {self.action} by {self.user_name or self.user_id or 'Unknown'}"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.server_name:
            try:
                self.server_name = socket.gethostname()
            except:
                self.server_name = 'unknown'
    
    def validate(self) -> list:
        """Validate audit log data and return list of errors"""
        errors = []
        
        # Required fields
        if not self.action:
            errors.append("Action is required")
        
        if not self.resource_type:
            errors.append("Resource type is required")
        
        # Enum validations
        if self.user_type not in self.USER_TYPES:
            errors.append(f"Invalid user type. Must be one of: {list(self.USER_TYPES.keys())}")
        
        if self.action not in self.ACTIONS:
            # Allow custom actions but warn
            pass
        
        if self.resource_type not in self.RESOURCE_TYPES:
            # Allow custom resource types but warn
            pass
        
        if self.compliance_category and self.compliance_category not in self.COMPLIANCE_CATEGORIES:
            errors.append(f"Invalid compliance category. Must be one of: {list(self.COMPLIANCE_CATEGORIES.keys())}")
        
        # Validate JSON fields
        json_fields = ['details', 'data_accessed', 'patient_ids', 'study_uids']
        for field in json_fields:
            value = getattr(self, field)
            if value:
                try:
                    json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    errors.append(f"{field} must be valid JSON")
        
        # Business logic validations
        if self.user_type == 'doctor' and not self.hpcsa_number:
            errors.append("HPCSA number is required for doctor users")
        
        if not self.success and not self.error_message:
            errors.append("Error message is required for failed actions")
        
        return errors
    
    def get_details(self) -> dict:
        """Get details as dictionary"""
        if not self.details:
            return {}
        try:
            return json.loads(self.details)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_details(self, details: dict):
        """Set details from dictionary"""
        try:
            self.details = json.dumps(details)
        except (TypeError, ValueError):
            self.details = "{}"
    
    def get_data_accessed(self) -> list:
        """Get accessed data types as list"""
        if not self.data_accessed:
            return []
        try:
            return json.loads(self.data_accessed)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_data_accessed(self, data_types: list):
        """Set accessed data types from list"""
        try:
            self.data_accessed = json.dumps(data_types)
        except (TypeError, ValueError):
            self.data_accessed = "[]"
    
    def get_patient_ids(self) -> list:
        """Get patient IDs as list"""
        if not self.patient_ids:
            return []
        try:
            return json.loads(self.patient_ids)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_patient_ids(self, patient_ids: list):
        """Set patient IDs from list"""
        try:
            self.patient_ids = json.dumps(patient_ids)
        except (TypeError, ValueError):
            self.patient_ids = "[]"
    
    def get_study_uids(self) -> list:
        """Get study UIDs as list"""
        if not self.study_uids:
            return []
        try:
            return json.loads(self.study_uids)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_study_uids(self, study_uids: list):
        """Set study UIDs from list"""
        try:
            self.study_uids = json.dumps(study_uids)
        except (TypeError, ValueError):
            self.study_uids = "[]"
    
    def get_action_display(self) -> str:
        """Get human-readable action"""
        return self.ACTIONS.get(self.action, self.action)
    
    def get_user_type_display(self) -> str:
        """Get human-readable user type"""
        return self.USER_TYPES.get(self.user_type, self.user_type)
    
    def get_resource_type_display(self) -> str:
        """Get human-readable resource type"""
        return self.RESOURCE_TYPES.get(self.resource_type, self.resource_type)
    
    def get_compliance_category_display(self) -> str:
        """Get human-readable compliance category"""
        return self.COMPLIANCE_CATEGORIES.get(self.compliance_category, self.compliance_category)
    
    def is_patient_data_access(self) -> bool:
        """Check if this is patient data access"""
        patient_actions = [
            'view_patient', 'view_study', 'download_image', 'download_report',
            'update_patient', 'delete_patient', 'upload_study', 'delete_study'
        ]
        return self.action in patient_actions
    
    def is_security_relevant(self) -> bool:
        """Check if this is security-relevant action"""
        security_actions = [
            'login', 'logout', 'login_failed', 'password_change', 'account_locked',
            'grant_access', 'revoke_access', 'config_change', 'user_management'
        ]
        return self.action in security_actions or not self.success
    
    def is_compliance_required(self) -> bool:
        """Check if this action requires compliance logging"""
        return (self.is_patient_data_access() or 
                self.is_security_relevant() or 
                self.user_type == 'doctor')
    
    def add_patient_access(self, patient_id: str, study_uid: str = None):
        """Add patient access information"""
        # Add patient ID
        patient_ids = self.get_patient_ids()
        if patient_id not in patient_ids:
            patient_ids.append(patient_id)
            self.set_patient_ids(patient_ids)
        
        # Add study UID if provided
        if study_uid:
            study_uids = self.get_study_uids()
            if study_uid not in study_uids:
                study_uids.append(study_uid)
                self.set_study_uids(study_uids)
    
    def add_detail(self, key: str, value):
        """Add detail to the details JSON"""
        details = self.get_details()
        details[key] = value
        self.set_details(details)
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'user_type': self.user_type,
            'user_type_display': self.get_user_type_display(),
            'user_name': self.user_name,
            'action': self.action,
            'action_display': self.get_action_display(),
            'resource_type': self.resource_type,
            'resource_type_display': self.get_resource_type_display(),
            'resource_id': self.resource_id,
            'success': self.success,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'compliance_category': self.compliance_category,
            'compliance_category_display': self.get_compliance_category_display(),
            'is_patient_data_access': self.is_patient_data_access(),
            'is_security_relevant': self.is_security_relevant(),
            'server_name': self.server_name,
            'application_version': self.application_version
        }
        
        if include_sensitive:
            data.update({
                'hpcsa_number': self.hpcsa_number,
                'details': self.get_details(),
                'ip_address': self.ip_address,
                'user_agent': self.user_agent,
                'session_id': self.session_id,
                'request_method': self.request_method,
                'request_url': self.request_url,
                'error_message': self.error_message,
                'response_code': self.response_code,
                'data_accessed': self.get_data_accessed(),
                'patient_ids': self.get_patient_ids(),
                'study_uids': self.get_study_uids()
            })
        
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AuditLog':
        """Create instance from dictionary"""
        log = cls()
        
        # Map fields
        fields = [
            'user_id', 'user_type', 'user_name', 'hpcsa_number', 'action',
            'resource_type', 'resource_id', 'ip_address', 'user_agent',
            'session_id', 'request_method', 'request_url', 'success',
            'error_message', 'response_code', 'compliance_category',
            'server_name', 'application_version'
        ]
        
        for field in fields:
            if field in data:
                setattr(log, field, data[field])
        
        # Handle JSON fields
        if 'details' in data:
            if isinstance(data['details'], dict):
                log.set_details(data['details'])
            else:
                log.details = data['details']
        
        if 'data_accessed' in data:
            if isinstance(data['data_accessed'], list):
                log.set_data_accessed(data['data_accessed'])
            else:
                log.data_accessed = data['data_accessed']
        
        if 'patient_ids' in data:
            if isinstance(data['patient_ids'], list):
                log.set_patient_ids(data['patient_ids'])
            else:
                log.patient_ids = data['patient_ids']
        
        if 'study_uids' in data:
            if isinstance(data['study_uids'], list):
                log.set_study_uids(data['study_uids'])
            else:
                log.study_uids = data['study_uids']
        
        return log
    
    @classmethod
    def create_login_log(cls, user_id: str, user_type: str, user_name: str,
                        success: bool, ip_address: str = None, hpcsa_number: str = None,
                        error_message: str = None) -> 'AuditLog':
        """Factory method for login audit logs"""
        return cls(
            user_id=user_id,
            user_type=user_type,
            user_name=user_name,
            hpcsa_number=hpcsa_number,
            action='login' if success else 'login_failed',
            resource_type='session',
            resource_id=user_id,
            success=success,
            error_message=error_message,
            ip_address=ip_address,
            compliance_category='hpcsa' if user_type == 'doctor' else 'security'
        )
    
    @classmethod
    def create_patient_access_log(cls, user_id: str, user_type: str, user_name: str,
                                 action: str, patient_id: str, study_uid: str = None,
                                 hpcsa_number: str = None, details: dict = None) -> 'AuditLog':
        """Factory method for patient data access logs"""
        log = cls(
            user_id=user_id,
            user_type=user_type,
            user_name=user_name,
            hpcsa_number=hpcsa_number,
            action=action,
            resource_type='patient',
            resource_id=patient_id,
            compliance_category='hpcsa' if user_type == 'doctor' else 'popia'
        )
        
        log.add_patient_access(patient_id, study_uid)
        
        if details:
            log.set_details(details)
        
        return log
