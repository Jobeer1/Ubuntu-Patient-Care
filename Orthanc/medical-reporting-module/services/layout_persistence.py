"""
Layout Persistence Service for Medical Reporting Module
Handles saving and loading of layout configurations
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models.database import get_db_session
from models.layout import ScreenLayout
from services.layout_manager import LayoutConfiguration, LayoutPresetType, MonitorConfiguration, LayoutElement

logger = logging.getLogger(__name__)

class LayoutPersistenceService:
    """Service for persisting layout configurations"""
    
    def __init__(self):
        self.cache: Dict[str, LayoutConfiguration] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_timeout_minutes = 30
    
    def save_layout(self, layout_config: LayoutConfiguration) -> bool:
        """Save a layout configuration to the database"""
        try:
            with get_db_session() as session:
                # Check if layout already exists
                existing_layout = session.query(ScreenLayout).filter(
                    ScreenLayout.layout_id == layout_config.layout_id
                ).first()
                
                if existing_layout:
                    # Update existing layout
                    existing_layout.name = layout_config.name
                    existing_layout.preset_type = layout_config.preset_type.value
                    existing_layout.user_id = layout_config.user_id
                    existing_layout.examination_type = layout_config.examination_type
                    existing_layout.configuration = self._serialize_layout_config(layout_config)
                    existing_layout.is_default = layout_config.is_default
                    existing_layout.is_shared = layout_config.is_shared
                    existing_layout.modified_at = datetime.utcnow()
                    existing_layout.version = layout_config.version
                    
                    logger.info(f"Updated existing layout: {layout_config.name}")
                else:
                    # Create new layout
                    new_layout = ScreenLayout(
                        layout_id=layout_config.layout_id,
                        name=layout_config.name,
                        preset_type=layout_config.preset_type.value,
                        user_id=layout_config.user_id,
                        examination_type=layout_config.examination_type,
                        configuration=self._serialize_layout_config(layout_config),
                        is_default=layout_config.is_default,
                        is_shared=layout_config.is_shared,
                        created_at=layout_config.created_at,
                        modified_at=layout_config.modified_at,
                        version=layout_config.version
                    )
                    
                    session.add(new_layout)
                    logger.info(f"Created new layout: {layout_config.name}")
                
                session.commit()
                
                # Update cache
                self.cache[layout_config.layout_id] = layout_config
                self.cache_expiry[layout_config.layout_id] = datetime.utcnow()
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to save layout: {e}")
            return False
    
    def load_layout(self, layout_id: str) -> Optional[LayoutConfiguration]:
        """Load a layout configuration from the database"""
        try:
            # Check cache first
            if self._is_cached(layout_id):
                return self.cache[layout_id]
            
            with get_db_session() as session:
                layout_record = session.query(ScreenLayout).filter(
                    ScreenLayout.layout_id == layout_id
                ).first()
                
                if not layout_record:
                    logger.warning(f"Layout not found: {layout_id}")
                    return None
                
                # Deserialize configuration
                layout_config = self._deserialize_layout_config(layout_record)
                
                # Update cache
                self.cache[layout_id] = layout_config
                self.cache_expiry[layout_id] = datetime.utcnow()
                
                logger.info(f"Loaded layout: {layout_config.name}")
                return layout_config
                
        except Exception as e:
            logger.error(f"Failed to load layout: {e}")
            return None
    
    def delete_layout(self, layout_id: str) -> bool:
        """Delete a layout configuration"""
        try:
            with get_db_session() as session:
                layout_record = session.query(ScreenLayout).filter(
                    ScreenLayout.layout_id == layout_id
                ).first()
                
                if not layout_record:
                    logger.warning(f"Layout not found for deletion: {layout_id}")
                    return False
                
                session.delete(layout_record)
                session.commit()
                
                # Remove from cache
                if layout_id in self.cache:
                    del self.cache[layout_id]
                if layout_id in self.cache_expiry:
                    del self.cache_expiry[layout_id]
                
                logger.info(f"Deleted layout: {layout_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete layout: {e}")
            return False
    
    def get_user_layouts(self, user_id: str) -> List[LayoutConfiguration]:
        """Get all layouts for a specific user"""
        try:
            with get_db_session() as session:
                layout_records = session.query(ScreenLayout).filter(
                    or_(
                        ScreenLayout.user_id == user_id,
                        ScreenLayout.is_shared == True
                    )
                ).order_by(ScreenLayout.modified_at.desc()).all()
                
                layouts = []
                for record in layout_records:
                    try:
                        layout_config = self._deserialize_layout_config(record)
                        layouts.append(layout_config)
                        
                        # Update cache
                        self.cache[layout_config.layout_id] = layout_config
                        self.cache_expiry[layout_config.layout_id] = datetime.utcnow()
                        
                    except Exception as e:
                        logger.error(f"Failed to deserialize layout {record.layout_id}: {e}")
                        continue
                
                logger.info(f"Retrieved {len(layouts)} layouts for user {user_id}")
                return layouts
                
        except Exception as e:
            logger.error(f"Failed to get user layouts: {e}")
            return []
    
    def get_layouts_by_examination_type(self, examination_type: str, 
                                       user_id: Optional[str] = None) -> List[LayoutConfiguration]:
        """Get layouts filtered by examination type"""
        try:
            with get_db_session() as session:
                query = session.query(ScreenLayout).filter(
                    ScreenLayout.examination_type == examination_type
                )
                
                if user_id:
                    query = query.filter(
                        or_(
                            ScreenLayout.user_id == user_id,
                            ScreenLayout.is_shared == True
                        )
                    )
                
                layout_records = query.order_by(ScreenLayout.modified_at.desc()).all()
                
                layouts = []
                for record in layout_records:
                    try:
                        layout_config = self._deserialize_layout_config(record)
                        layouts.append(layout_config)
                    except Exception as e:
                        logger.error(f"Failed to deserialize layout {record.layout_id}: {e}")
                        continue
                
                logger.info(f"Retrieved {len(layouts)} layouts for examination type {examination_type}")
                return layouts
                
        except Exception as e:
            logger.error(f"Failed to get layouts by examination type: {e}")
            return []
    
    def get_default_layouts(self) -> List[LayoutConfiguration]:
        """Get all default layouts"""
        try:
            with get_db_session() as session:
                layout_records = session.query(ScreenLayout).filter(
                    ScreenLayout.is_default == True
                ).order_by(ScreenLayout.name).all()
                
                layouts = []
                for record in layout_records:
                    try:
                        layout_config = self._deserialize_layout_config(record)
                        layouts.append(layout_config)
                    except Exception as e:
                        logger.error(f"Failed to deserialize layout {record.layout_id}: {e}")
                        continue
                
                logger.info(f"Retrieved {len(layouts)} default layouts")
                return layouts
                
        except Exception as e:
            logger.error(f"Failed to get default layouts: {e}")
            return []
    
    def clone_layout(self, source_layout_id: str, new_name: str, 
                    user_id: Optional[str] = None) -> Optional[LayoutConfiguration]:
        """Clone an existing layout with a new name"""
        try:
            # Load the source layout
            source_layout = self.load_layout(source_layout_id)
            if not source_layout:
                logger.error(f"Source layout not found: {source_layout_id}")
                return None
            
            # Create a new layout configuration
            import uuid
            new_layout = LayoutConfiguration(
                layout_id=str(uuid.uuid4()),
                name=new_name,
                preset_type=LayoutPresetType.CUSTOM,
                user_id=user_id,
                examination_type=source_layout.examination_type,
                monitors=source_layout.monitors.copy(),  # Deep copy monitors
                is_default=False,
                is_shared=False,
                created_at=datetime.utcnow(),
                modified_at=datetime.utcnow(),
                version=1
            )
            
            # Save the cloned layout
            if self.save_layout(new_layout):
                logger.info(f"Cloned layout {source_layout_id} to {new_layout.layout_id}")
                return new_layout
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to clone layout: {e}")
            return None
    
    def export_layout(self, layout_id: str) -> Optional[Dict[str, Any]]:
        """Export a layout configuration to a dictionary"""
        try:
            layout_config = self.load_layout(layout_id)
            if not layout_config:
                return None
            
            return self._serialize_layout_config(layout_config)
            
        except Exception as e:
            logger.error(f"Failed to export layout: {e}")
            return None
    
    def import_layout(self, layout_data: Dict[str, Any], 
                     user_id: Optional[str] = None) -> Optional[LayoutConfiguration]:
        """Import a layout configuration from a dictionary"""
        try:
            # Create a temporary ScreenLayout record for deserialization
            temp_record = ScreenLayout(
                layout_id=layout_data.get('layout_id', str(uuid.uuid4())),
                name=layout_data.get('name', 'Imported Layout'),
                preset_type=layout_data.get('preset_type', 'custom'),
                user_id=user_id,
                examination_type=layout_data.get('examination_type'),
                configuration=layout_data,
                is_default=False,
                is_shared=False,
                created_at=datetime.utcnow(),
                modified_at=datetime.utcnow(),
                version=1
            )
            
            # Deserialize the configuration
            layout_config = self._deserialize_layout_config(temp_record)
            
            # Save the imported layout
            if self.save_layout(layout_config):
                logger.info(f"Imported layout: {layout_config.name}")
                return layout_config
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to import layout: {e}")
            return None
    
    def _serialize_layout_config(self, layout_config: LayoutConfiguration) -> Dict[str, Any]:
        """Serialize a layout configuration to a dictionary"""
        try:
            return {
                'layout_id': layout_config.layout_id,
                'name': layout_config.name,
                'preset_type': layout_config.preset_type.value,
                'user_id': layout_config.user_id,
                'examination_type': layout_config.examination_type,
                'monitors': [
                    {
                        'monitor_id': monitor.monitor_id,
                        'is_primary': monitor.is_primary,
                        'width_pixels': monitor.width_pixels,
                        'height_pixels': monitor.height_pixels,
                        'x_offset': monitor.x_offset,
                        'y_offset': monitor.y_offset,
                        'scale_factor': monitor.scale_factor,
                        'elements': [
                            {
                                'element_id': elem.element_id,
                                'element_type': elem.element_type.value,
                                'x': elem.x,
                                'y': elem.y,
                                'width': elem.width,
                                'height': elem.height,
                                'z_index': elem.z_index,
                                'is_resizable': elem.is_resizable,
                                'is_movable': elem.is_movable,
                                'is_visible': elem.is_visible,
                                'min_width': elem.min_width,
                                'min_height': elem.min_height,
                                'max_width': elem.max_width,
                                'max_height': elem.max_height,
                                'properties': elem.properties,
                                'created_at': elem.created_at.isoformat()
                            }
                            for elem in monitor.elements
                        ]
                    }
                    for monitor in layout_config.monitors
                ],
                'is_default': layout_config.is_default,
                'is_shared': layout_config.is_shared,
                'created_at': layout_config.created_at.isoformat(),
                'modified_at': layout_config.modified_at.isoformat(),
                'version': layout_config.version
            }
            
        except Exception as e:
            logger.error(f"Failed to serialize layout config: {e}")
            raise
    
    def _deserialize_layout_config(self, layout_record: ScreenLayout) -> LayoutConfiguration:
        """Deserialize a layout configuration from a database record"""
        try:
            config_data = layout_record.configuration
            
            # Parse monitors
            monitors = []
            for monitor_data in config_data.get('monitors', []):
                # Parse elements
                elements = []
                for elem_data in monitor_data.get('elements', []):
                    from services.layout_manager import LayoutElement, LayoutElementType
                    
                    element = LayoutElement(
                        element_id=elem_data['element_id'],
                        element_type=LayoutElementType(elem_data['element_type']),
                        x=elem_data['x'],
                        y=elem_data['y'],
                        width=elem_data['width'],
                        height=elem_data['height'],
                        z_index=elem_data.get('z_index', 0),
                        is_resizable=elem_data.get('is_resizable', True),
                        is_movable=elem_data.get('is_movable', True),
                        is_visible=elem_data.get('is_visible', True),
                        min_width=elem_data.get('min_width', 5.0),
                        min_height=elem_data.get('min_height', 5.0),
                        max_width=elem_data.get('max_width', 100.0),
                        max_height=elem_data.get('max_height', 100.0),
                        properties=elem_data.get('properties', {}),
                        created_at=datetime.fromisoformat(elem_data['created_at'])
                    )
                    elements.append(element)
                
                monitor = MonitorConfiguration(
                    monitor_id=monitor_data['monitor_id'],
                    is_primary=monitor_data.get('is_primary', False),
                    width_pixels=monitor_data.get('width_pixels', 1920),
                    height_pixels=monitor_data.get('height_pixels', 1080),
                    x_offset=monitor_data.get('x_offset', 0),
                    y_offset=monitor_data.get('y_offset', 0),
                    scale_factor=monitor_data.get('scale_factor', 1.0),
                    elements=elements
                )
                monitors.append(monitor)
            
            # Create layout configuration
            layout_config = LayoutConfiguration(
                layout_id=layout_record.layout_id,
                name=layout_record.name,
                preset_type=LayoutPresetType(layout_record.preset_type),
                user_id=layout_record.user_id,
                examination_type=layout_record.examination_type,
                monitors=monitors,
                is_default=layout_record.is_default,
                is_shared=layout_record.is_shared,
                created_at=layout_record.created_at,
                modified_at=layout_record.modified_at,
                version=layout_record.version
            )
            
            return layout_config
            
        except Exception as e:
            logger.error(f"Failed to deserialize layout config: {e}")
            raise
    
    def _is_cached(self, layout_id: str) -> bool:
        """Check if a layout is cached and not expired"""
        if layout_id not in self.cache:
            return False
        
        if layout_id not in self.cache_expiry:
            return False
        
        # Check if cache has expired
        cache_time = self.cache_expiry[layout_id]
        now = datetime.utcnow()
        elapsed_minutes = (now - cache_time).total_seconds() / 60
        
        if elapsed_minutes > self.cache_timeout_minutes:
            # Remove expired cache entry
            del self.cache[layout_id]
            del self.cache_expiry[layout_id]
            return False
        
        return True
    
    def clear_cache(self):
        """Clear the layout cache"""
        self.cache.clear()
        self.cache_expiry.clear()
        logger.info("Cleared layout cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cached_layouts': len(self.cache),
            'cache_timeout_minutes': self.cache_timeout_minutes,
            'cache_entries': list(self.cache.keys())
        }

# Global layout persistence service instance
layout_persistence_service = LayoutPersistenceService()