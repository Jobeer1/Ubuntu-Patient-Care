"""
Template data model for Medical Reporting Module
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
import uuid

# Import unified base
from .database import Base

class ReportTemplate(Base):
    """Template model for report templates"""
    __tablename__ = 'report_templates'
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Template identification
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)  # radiology, pathology, etc.
    specialty = Column(String(50), nullable=False)  # cardiology, orthopedics, etc.
    procedure_type = Column(String(100), nullable=True)  # CT Chest, MRI Brain, etc.
    
    # Voice commands
    voice_commands = Column(JSON, nullable=False, default=list)  # List of voice commands
    primary_command = Column(String(100), nullable=True)  # Main voice command
    
    # Template structure
    sections = Column(JSON, nullable=False, default=list)  # Template sections
    default_values = Column(JSON, nullable=False, default=dict)  # Default field values
    required_fields = Column(JSON, nullable=False, default=list)  # Required fields
    
    # Customization
    is_custom = Column(Boolean, nullable=False, default=False)
    is_system_template = Column(Boolean, nullable=False, default=False)
    parent_template_id = Column(String(36), nullable=True)  # For custom templates
    
    # Usage and popularity
    usage_count = Column(Integer, nullable=False, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    is_approved = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Audit
    created_by = Column(String(36), nullable=False)
    updated_by = Column(String(36), nullable=False)
    
    # Relationships
    reports = relationship("Report", back_populates="template")
    
    def __repr__(self):
        return f"<ReportTemplate(id='{self.id}', name='{self.name}', category='{self.category}')>"
    
    def to_dict(self):
        """Convert template to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'specialty': self.specialty,
            'procedure_type': self.procedure_type,
            'voice_commands': self.voice_commands,
            'primary_command': self.primary_command,
            'sections': self.sections,
            'default_values': self.default_values,
            'required_fields': self.required_fields,
            'is_custom': self.is_custom,
            'is_system_template': self.is_system_template,
            'parent_template_id': self.parent_template_id,
            'usage_count': self.usage_count,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'is_active': self.is_active,
            'is_approved': self.is_approved,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }
    
    def increment_usage(self):
        """Increment usage count and update last used timestamp"""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def add_voice_command(self, command):
        """Add a voice command to the template"""
        if command not in self.voice_commands:
            self.voice_commands.append(command)
            if not self.primary_command:
                self.primary_command = command
            self.updated_at = datetime.utcnow()
    
    def remove_voice_command(self, command):
        """Remove a voice command from the template"""
        if command in self.voice_commands:
            self.voice_commands.remove(command)
            if self.primary_command == command and self.voice_commands:
                self.primary_command = self.voice_commands[0]
            elif self.primary_command == command:
                self.primary_command = None
            self.updated_at = datetime.utcnow()
    
    def get_section_by_name(self, section_name):
        """Get a specific section by name"""
        for section in self.sections:
            if section.get('name') == section_name:
                return section
        return None
    
    def validate_required_fields(self, report_data):
        """Validate that all required fields are present in report data"""
        missing_fields = []
        for field in self.required_fields:
            if field not in report_data or not report_data[field]:
                missing_fields.append(field)
        return missing_fields

class TemplateSection(Base):
    """Template section model for structured templates"""
    __tablename__ = 'template_sections'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id = Column(String(36), nullable=False)  # Foreign key reference
    
    # Section details
    name = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    
    # Section type and behavior
    section_type = Column(String(50), nullable=False)  # text, checkbox, dropdown, etc.
    is_required = Column(Boolean, nullable=False, default=False)
    is_repeatable = Column(Boolean, nullable=False, default=False)
    
    # Content and options
    default_content = Column(Text, nullable=True)
    options = Column(JSON, nullable=True)  # For dropdown/checkbox sections
    validation_rules = Column(JSON, nullable=True)
    
    # Voice integration
    voice_trigger = Column(String(100), nullable=True)  # Voice command to jump to section
    
    def __repr__(self):
        return f"<TemplateSection(id='{self.id}', name='{self.name}', template_id='{self.template_id}')>"
    
    def to_dict(self):
        """Convert section to dictionary"""
        return {
            'id': self.id,
            'template_id': self.template_id,
            'name': self.name,
            'title': self.title,
            'description': self.description,
            'order_index': self.order_index,
            'section_type': self.section_type,
            'is_required': self.is_required,
            'is_repeatable': self.is_repeatable,
            'default_content': self.default_content,
            'options': self.options,
            'validation_rules': self.validation_rules,
            'voice_trigger': self.voice_trigger
        }