"""
Orthanc Management Models - Orthanc Config
Dynamic Orthanc server configuration management
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Index
from datetime import datetime
import json

from ..database.manager import Base
from ..database.schema import DatabaseCompatibleMixin, generate_id, get_timestamp_default


class OrthancConfig(Base, DatabaseCompatibleMixin):
    """
    Orthanc Configuration Model
    Manages dynamic Orthanc server configurations with versioning and rollback
    """
    __tablename__ = 'orthanc_configs'
    
    # Primary key
    id = Column(String(50), primary_key=True, default=generate_id)
    
    # Configuration identification
    config_name = Column(String(100), nullable=False, unique=True)
    config_data = Column(Text, nullable=False)  # JSON configuration
    description = Column(Text, nullable=True)
    version = Column(String(20), nullable=False, default='1.0.0')
    
    # Status and control
    is_active = Column(Boolean, nullable=False, default=False, index=True)
    is_default = Column(Boolean, nullable=False, default=False)
    is_template = Column(Boolean, nullable=False, default=False)
    
    # Audit fields
    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=get_timestamp_default)
    updated_at = Column(DateTime, nullable=True, onupdate=get_timestamp_default)
    applied_at = Column(DateTime, nullable=True)
    applied_by = Column(String(50), nullable=True)
    
    # Validation and backup
    validation_status = Column(String(20), nullable=False, default='pending')
    validation_errors = Column(Text, nullable=True)  # JSON array of errors
    backup_config_id = Column(String(50), nullable=True)  # Reference to previous config
    
    # Environment and deployment
    environment = Column(String(20), nullable=False, default='development')
    deployment_notes = Column(Text, nullable=True)
    rollback_notes = Column(Text, nullable=True)
    
    # Table constraints
    __table_args__ = (
        Index('idx_orthanc_configs_name_active', 'config_name', 'is_active'),
        Index('idx_orthanc_configs_created_by', 'created_by'),
        Index('idx_orthanc_configs_environment', 'environment'),
        Index('idx_orthanc_configs_template', 'is_template'),
        Index('idx_orthanc_configs_version', 'config_name', 'version'),
    )
    
    # Class constants
    VALIDATION_STATUSES = {
        'pending': 'Pending Validation',
        'valid': 'Valid Configuration',
        'invalid': 'Invalid Configuration',
        'warning': 'Valid with Warnings'
    }
    
    ENVIRONMENTS = {
        'development': 'Development',
        'testing': 'Testing',
        'staging': 'Staging',
        'production': 'Production'
    }
    
    # Default Orthanc configuration template
    DEFAULT_CONFIG = {
        "Name": "Orthanc Management System",
        "HttpPort": 8042,
        "DicomPort": 4242,
        "HttpDescribeErrors": True,
        "HttpCompressionEnabled": True,
        "DicomServerEnabled": True,
        "DicomAet": "ORTHANC",
        "DicomCheckCalledAet": False,
        "DicomCheckModalityHost": False,
        "RemoteAccessAllowed": True,
        "AuthenticationEnabled": True,
        "SslEnabled": False,
        "SslCertificate": "",
        "StorageDirectory": "./orthanc-db",
        "IndexDirectory": "./orthanc-db",
        "StorageCompression": False,
        "MaximumStorageSize": 0,
        "MaximumPatientCount": 0,
        "LimitFindInstances": 0,
        "LimitFindResults": 0,
        "LogLevel": "default",
        "LogFile": "",
        "HttpRequestTimeout": 60,
        "DicomConnectionTimeout": 30,
        "DicomAssociationTimeout": 30,
        "JobsHistorySize": 10,
        "SaveJobs": True,
        "Plugins": [],
        "Dictionary": {},
        "DicomModalities": {},
        "OrthancPeers": {},
        "LuaScripts": [],
        "HttpHeaders": {},
        "OverwriteInstances": False,
        "DefaultEncoding": "Latin1"
    }
    
    def __repr__(self):
        return f"<OrthancConfig(id='{self.id}', name='{self.config_name}', version='{self.version}')>"
    
    def __str__(self):
        return f"Config: {self.config_name} v{self.version} ({'Active' if self.is_active else 'Inactive'})"
    
    def validate(self) -> list:
        """Validate configuration data and return list of errors"""
        errors = []
        
        # Required fields
        if not self.config_name or len(self.config_name.strip()) < 1:
            errors.append("Configuration name is required")
        
        if not self.config_data:
            errors.append("Configuration data is required")
        else:
            # Validate JSON format
            try:
                config = json.loads(self.config_data)
                if not isinstance(config, dict):
                    errors.append("Configuration data must be a JSON object")
            except (json.JSONDecodeError, TypeError):
                errors.append("Configuration data must be valid JSON")
        
        if not self.created_by or len(self.created_by.strip()) < 1:
            errors.append("Created by user ID is required")
        
        if not self.version:
            errors.append("Version is required")
        
        # Enum validations
        if self.validation_status not in self.VALIDATION_STATUSES:
            errors.append(f"Invalid validation status. Must be one of: {list(self.VALIDATION_STATUSES.keys())}")
        
        if self.environment not in self.ENVIRONMENTS:
            errors.append(f"Invalid environment. Must be one of: {list(self.ENVIRONMENTS.keys())}")
        
        # Business logic validations
        if self.applied_at and not self.applied_by:
            errors.append("Applied by user is required when applied date is set")
        
        return errors
    
    def get_config_data(self) -> dict:
        """Get configuration data as dictionary"""
        if not self.config_data:
            return {}
        try:
            return json.loads(self.config_data)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_config_data(self, config: dict):
        """Set configuration data from dictionary"""
        try:
            self.config_data = json.dumps(config, indent=2)
        except (TypeError, ValueError):
            self.config_data = "{}"
    
    def get_validation_errors(self) -> list:
        """Get validation errors as list"""
        if not self.validation_errors:
            return []
        try:
            return json.loads(self.validation_errors)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_validation_errors(self, errors: list):
        """Set validation errors from list"""
        try:
            self.validation_errors = json.dumps(errors)
        except (TypeError, ValueError):
            self.validation_errors = "[]"
    
    def validate_orthanc_config(self) -> tuple:
        """Validate Orthanc-specific configuration and return (is_valid, errors, warnings)"""
        config = self.get_config_data()
        errors = []
        warnings = []
        
        # Required Orthanc settings
        required_fields = ['Name', 'HttpPort', 'DicomPort']
        for field in required_fields:
            if field not in config:
                errors.append(f"Required field '{field}' is missing")
        
        # Port validations
        if 'HttpPort' in config:
            try:
                port = int(config['HttpPort'])
                if port < 1 or port > 65535:
                    errors.append("HttpPort must be between 1 and 65535")
                elif port < 1024:
                    warnings.append("HttpPort below 1024 may require administrator privileges")
            except (ValueError, TypeError):
                errors.append("HttpPort must be a valid integer")
        
        if 'DicomPort' in config:
            try:
                port = int(config['DicomPort'])
                if port < 1 or port > 65535:
                    errors.append("DicomPort must be between 1 and 65535")
                elif port < 1024:
                    warnings.append("DicomPort below 1024 may require administrator privileges")
            except (ValueError, TypeError):
                errors.append("DicomPort must be a valid integer")
        
        # Directory validations
        directory_fields = ['StorageDirectory', 'IndexDirectory']
        for field in directory_fields:
            if field in config and config[field]:
                import os
                path = config[field]
                if not os.path.isabs(path):
                    warnings.append(f"{field} uses relative path - consider absolute path for production")
        
        # Security validations
        if config.get('RemoteAccessAllowed', False) and not config.get('AuthenticationEnabled', False):
            warnings.append("Remote access enabled without authentication - security risk")
        
        if config.get('SslEnabled', False) and not config.get('SslCertificate'):
            errors.append("SSL enabled but no certificate specified")
        
        # Storage validations
        max_storage = config.get('MaximumStorageSize', 0)
        if max_storage and max_storage < 1024*1024*1024:  # Less than 1GB
            warnings.append("MaximumStorageSize is very small - may fill up quickly")
        
        # Set validation status
        if errors:
            self.validation_status = 'invalid'
        elif warnings:
            self.validation_status = 'warning'
        else:
            self.validation_status = 'valid'
        
        # Store errors and warnings
        all_issues = [{'type': 'error', 'message': msg} for msg in errors] + \
                    [{'type': 'warning', 'message': msg} for msg in warnings]
        self.set_validation_errors(all_issues)
        
        return len(errors) == 0, errors, warnings
    
    def merge_with_default(self) -> dict:
        """Merge configuration with default settings"""
        merged = self.DEFAULT_CONFIG.copy()
        user_config = self.get_config_data()
        merged.update(user_config)
        return merged
    
    def get_diff_from_default(self) -> dict:
        """Get differences from default configuration"""
        default = self.DEFAULT_CONFIG
        current = self.get_config_data()
        
        diff = {
            'added': {},
            'modified': {},
            'removed': []
        }
        
        # Find added and modified
        for key, value in current.items():
            if key not in default:
                diff['added'][key] = value
            elif default[key] != value:
                diff['modified'][key] = {
                    'old': default[key],
                    'new': value
                }
        
        # Find removed
        for key in default:
            if key not in current:
                diff['removed'].append(key)
        
        return diff
    
    def apply_configuration(self, applied_by: str) -> bool:
        """Mark configuration as applied"""
        try:
            self.is_active = True
            self.applied_at = datetime.utcnow()
            self.applied_by = applied_by
            self.updated_at = datetime.utcnow()
            return True
        except Exception:
            return False
    
    def deactivate(self) -> bool:
        """Deactivate configuration"""
        try:
            self.is_active = False
            self.updated_at = datetime.utcnow()
            return True
        except Exception:
            return False
    
    def create_backup_reference(self, backup_config_id: str):
        """Set reference to backup configuration"""
        self.backup_config_id = backup_config_id
    
    def increment_version(self) -> str:
        """Increment version number"""
        try:
            parts = self.version.split('.')
            if len(parts) == 3:
                major, minor, patch = map(int, parts)
                patch += 1
                self.version = f"{major}.{minor}.{patch}"
            else:
                self.version = "1.0.1"
        except (ValueError, IndexError):
            self.version = "1.0.1"
        
        return self.version
    
    def to_dict(self, include_config_data: bool = True) -> dict:
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'config_name': self.config_name,
            'description': self.description,
            'version': self.version,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'is_template': self.is_template,
            'validation_status': self.validation_status,
            'validation_status_display': self.VALIDATION_STATUSES.get(self.validation_status),
            'validation_errors': self.get_validation_errors(),
            'environment': self.environment,
            'environment_display': self.ENVIRONMENTS.get(self.environment),
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'applied_by': self.applied_by,
            'backup_config_id': self.backup_config_id,
            'deployment_notes': self.deployment_notes,
            'rollback_notes': self.rollback_notes
        }
        
        if include_config_data:
            data['config_data'] = self.get_config_data()
            data['diff_from_default'] = self.get_diff_from_default()
        
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'OrthancConfig':
        """Create instance from dictionary"""
        config = cls()
        
        # Map fields
        fields = [
            'config_name', 'description', 'version', 'is_active', 'is_default',
            'is_template', 'validation_status', 'environment', 'created_by',
            'applied_by', 'backup_config_id', 'deployment_notes', 'rollback_notes'
        ]
        
        for field in fields:
            if field in data:
                setattr(config, field, data[field])
        
        # Handle config data
        if 'config_data' in data:
            if isinstance(data['config_data'], dict):
                config.set_config_data(data['config_data'])
            else:
                config.config_data = data['config_data']
        
        # Handle dates
        date_fields = ['applied_at']
        for field in date_fields:
            if field in data and data[field]:
                if isinstance(data[field], str):
                    setattr(config, field, datetime.fromisoformat(data[field]))
                else:
                    setattr(config, field, data[field])
        
        return config
    
    @classmethod
    def create_default_config(cls, created_by: str, environment: str = 'development') -> 'OrthancConfig':
        """Create a default Orthanc configuration"""
        config = cls(
            config_name=f"Default {environment.title()} Configuration",
            description="Default Orthanc configuration with recommended settings",
            version="1.0.0",
            is_default=True,
            environment=environment,
            created_by=created_by
        )
        
        config.set_config_data(cls.DEFAULT_CONFIG.copy())
        config.validate_orthanc_config()
        
        return config
    
    @classmethod
    def create_from_template(cls, template_config: 'OrthancConfig', new_name: str, 
                           created_by: str, environment: str = None) -> 'OrthancConfig':
        """Create new configuration from template"""
        config = cls(
            config_name=new_name,
            description=f"Based on template: {template_config.config_name}",
            version="1.0.0",
            environment=environment or template_config.environment,
            created_by=created_by,
            backup_config_id=template_config.id
        )
        
        config.set_config_data(template_config.get_config_data())
        config.validate_orthanc_config()
        
        return config
