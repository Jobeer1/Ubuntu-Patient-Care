"""
Layout data model for Medical Reporting Module
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
import uuid

# Import unified base
from .database import Base

class ScreenLayout(Base):
    """Screen layout model for customizable UI layouts"""
    __tablename__ = 'screen_layouts'
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Layout identification
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(String(36), nullable=False, index=True)
    
    # Layout categorization
    examination_type = Column(String(100), nullable=True)  # CT Chest, MRI Brain, etc.
    specialty = Column(String(50), nullable=True)  # radiology, cardiology, etc.
    layout_type = Column(String(50), nullable=False, default='custom')  # preset, custom, shared
    
    # Layout configuration
    viewport_config = Column(JSON, nullable=False, default=dict)  # Viewport arrangement
    panel_arrangement = Column(JSON, nullable=False, default=dict)  # Panel positions
    monitor_setup = Column(JSON, nullable=False, default=dict)  # Multi-monitor config
    window_settings = Column(JSON, nullable=False, default=dict)  # Window/level settings
    
    # Layout properties
    grid_rows = Column(Integer, nullable=False, default=2)
    grid_columns = Column(Integer, nullable=False, default=2)
    is_default = Column(Boolean, nullable=False, default=False)
    is_shared = Column(Boolean, nullable=False, default=False)
    is_system_preset = Column(Boolean, nullable=False, default=False)
    
    # Usage tracking
    usage_count = Column(Integer, nullable=False, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Audit
    created_by = Column(String(36), nullable=False)
    updated_by = Column(String(36), nullable=False)
    
    def __repr__(self):
        return f"<ScreenLayout(id='{self.id}', name='{self.name}', user_id='{self.user_id}')>"
    
    def to_dict(self):
        """Convert layout to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'examination_type': self.examination_type,
            'specialty': self.specialty,
            'layout_type': self.layout_type,
            'viewport_config': self.viewport_config,
            'panel_arrangement': self.panel_arrangement,
            'monitor_setup': self.monitor_setup,
            'window_settings': self.window_settings,
            'grid_rows': self.grid_rows,
            'grid_columns': self.grid_columns,
            'is_default': self.is_default,
            'is_shared': self.is_shared,
            'is_system_preset': self.is_system_preset,
            'usage_count': self.usage_count,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
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
    
    def set_as_default(self, user_id):
        """Set this layout as default for the user"""
        self.is_default = True
        self.updated_by = user_id
        self.updated_at = datetime.utcnow()
    
    def update_viewport_config(self, config, updated_by):
        """Update viewport configuration"""
        self.viewport_config = config
        self.updated_by = updated_by
        self.updated_at = datetime.utcnow()
    
    def update_panel_arrangement(self, arrangement, updated_by):
        """Update panel arrangement"""
        self.panel_arrangement = arrangement
        self.updated_by = updated_by
        self.updated_at = datetime.utcnow()
    
    def clone_for_user(self, new_user_id, new_name=None):
        """Create a copy of this layout for another user"""
        clone_data = self.to_dict()
        clone_data.pop('id')
        clone_data.pop('created_at')
        clone_data.pop('updated_at')
        clone_data.pop('last_used_at')
        
        clone_data['user_id'] = new_user_id
        clone_data['created_by'] = new_user_id
        clone_data['updated_by'] = new_user_id
        clone_data['usage_count'] = 0
        clone_data['is_default'] = False
        
        if new_name:
            clone_data['name'] = new_name
        else:
            clone_data['name'] = f"Copy of {self.name}"
        
        return clone_data

class ViewportConfiguration(Base):
    """Viewport configuration for detailed viewport settings"""
    __tablename__ = 'viewport_configurations'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    layout_id = Column(String(36), nullable=False)  # Foreign key reference
    
    # Viewport identification
    viewport_index = Column(Integer, nullable=False)  # 0, 1, 2, 3 for 2x2 grid
    viewport_name = Column(String(50), nullable=True)
    
    # Position and size
    position_x = Column(Integer, nullable=False, default=0)
    position_y = Column(Integer, nullable=False, default=0)
    width = Column(Integer, nullable=False, default=512)
    height = Column(Integer, nullable=False, default=512)
    
    # Display settings
    window_center = Column(Integer, nullable=True)
    window_width = Column(Integer, nullable=True)
    zoom_level = Column(Integer, nullable=False, default=100)  # Percentage
    pan_x = Column(Integer, nullable=False, default=0)
    pan_y = Column(Integer, nullable=False, default=0)
    
    # Image settings
    invert_colors = Column(Boolean, nullable=False, default=False)
    rotation_angle = Column(Integer, nullable=False, default=0)  # 0, 90, 180, 270
    flip_horizontal = Column(Boolean, nullable=False, default=False)
    flip_vertical = Column(Boolean, nullable=False, default=False)
    
    # Annotations and overlays
    show_annotations = Column(Boolean, nullable=False, default=True)
    show_measurements = Column(Boolean, nullable=False, default=True)
    show_patient_info = Column(Boolean, nullable=False, default=True)
    show_study_info = Column(Boolean, nullable=False, default=True)
    
    def __repr__(self):
        return f"<ViewportConfiguration(id='{self.id}', layout_id='{self.layout_id}', index={self.viewport_index})>"
    
    def to_dict(self):
        """Convert viewport configuration to dictionary"""
        return {
            'id': self.id,
            'layout_id': self.layout_id,
            'viewport_index': self.viewport_index,
            'viewport_name': self.viewport_name,
            'position_x': self.position_x,
            'position_y': self.position_y,
            'width': self.width,
            'height': self.height,
            'window_center': self.window_center,
            'window_width': self.window_width,
            'zoom_level': self.zoom_level,
            'pan_x': self.pan_x,
            'pan_y': self.pan_y,
            'invert_colors': self.invert_colors,
            'rotation_angle': self.rotation_angle,
            'flip_horizontal': self.flip_horizontal,
            'flip_vertical': self.flip_vertical,
            'show_annotations': self.show_annotations,
            'show_measurements': self.show_measurements,
            'show_patient_info': self.show_patient_info,
            'show_study_info': self.show_study_info
        }