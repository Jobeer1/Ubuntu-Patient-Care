"""
Viewport Manager for Medical Reporting Module
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class ViewportLayout(Enum):
    SINGLE = "1x1"
    DUAL_HORIZONTAL = "1x2"
    QUAD = "2x2"

class ImageManipulation(Enum):
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    PAN = "pan"
    RESET = "reset"

@dataclass
class ViewportState:
    viewport_id: str
    study_id: Optional[str] = None
    zoom_level: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0
    is_active: bool = False
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()

class ViewportManager:
    def __init__(self):
        self.viewports: Dict[str, ViewportState] = {}
        self.current_layout = ViewportLayout.SINGLE
        self.active_viewport_id: Optional[str] = None
        self.set_layout(ViewportLayout.SINGLE)
    
    def set_layout(self, layout_type: ViewportLayout) -> bool:
        try:
            self.viewports.clear()
            
            if layout_type == ViewportLayout.SINGLE:
                viewport_count = 1
            elif layout_type == ViewportLayout.DUAL_HORIZONTAL:
                viewport_count = 2
            elif layout_type == ViewportLayout.QUAD:
                viewport_count = 4
            else:
                viewport_count = 1
            
            for i in range(viewport_count):
                viewport_id = f"viewport_{i}"
                viewport_state = ViewportState(viewport_id=viewport_id)
                self.viewports[viewport_id] = viewport_state
            
            if self.viewports:
                first_viewport = list(self.viewports.keys())[0]
                self.set_active_viewport(first_viewport)
            
            self.current_layout = layout_type
            return True
            
        except Exception as e:
            logger.error(f"Failed to set layout: {e}")
            return False
    
    def set_active_viewport(self, viewport_id: str) -> bool:
        try:
            if viewport_id not in self.viewports:
                return False
            
            if self.active_viewport_id:
                current_active = self.viewports.get(self.active_viewport_id)
                if current_active:
                    current_active.is_active = False
            
            self.active_viewport_id = viewport_id
            self.viewports[viewport_id].is_active = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to set active viewport: {e}")
            return False
    
    def apply_image_manipulation(self, viewport_id: str, 
                               manipulation: ImageManipulation, 
                               value: Any = None) -> bool:
        try:
            viewport = self.viewports.get(viewport_id)
            if not viewport:
                return False
            
            if manipulation == ImageManipulation.ZOOM_IN:
                viewport.zoom_level *= 1.2
            elif manipulation == ImageManipulation.ZOOM_OUT:
                viewport.zoom_level /= 1.2
            elif manipulation == ImageManipulation.PAN:
                if isinstance(value, dict):
                    viewport.pan_x += value.get('x', 0)
                    viewport.pan_y += value.get('y', 0)
            elif manipulation == ImageManipulation.RESET:
                viewport.zoom_level = 1.0
                viewport.pan_x = 0.0
                viewport.pan_y = 0.0
            
            viewport.last_updated = datetime.utcnow()
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply image manipulation: {e}")
            return False
    
    def get_layout_info(self) -> Dict[str, Any]:
        return {
            'current_layout': self.current_layout.value,
            'viewport_count': len(self.viewports),
            'active_viewport': self.active_viewport_id,
            'viewports': {vid: asdict(vp) for vid, vp in self.viewports.items()}
        }
    
    def get_available_layouts(self) -> List[Dict[str, Any]]:
        return [
            {'type': ViewportLayout.SINGLE.value, 'name': 'Single View', 'viewport_count': 1},
            {'type': ViewportLayout.DUAL_HORIZONTAL.value, 'name': 'Dual Horizontal', 'viewport_count': 2},
            {'type': ViewportLayout.QUAD.value, 'name': 'Quad View', 'viewport_count': 4}
        ]
    
    def clear_viewport(self, viewport_id: str) -> bool:
        try:
            viewport = self.viewports.get(viewport_id)
            if not viewport:
                return False
            
            viewport.study_id = None
            viewport.zoom_level = 1.0
            viewport.pan_x = 0.0
            viewport.pan_y = 0.0
            viewport.last_updated = datetime.utcnow()
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear viewport: {e}")
            return False
    
    def get_viewport_performance_info(self) -> Dict[str, Any]:
        return {
            'viewport_count': len(self.viewports),
            'active_viewport': self.active_viewport_id,
        }

viewport_manager = ViewportManager()