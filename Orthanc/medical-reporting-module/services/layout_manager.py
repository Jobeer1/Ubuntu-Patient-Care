"""
Layout Manager for Medical Reporting Module
Manages customizable screen layouts and multi-monitor configurations
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid

from services.viewport_manager import ViewportManager, ViewportLayout, ViewportState
from models.layout import ScreenLayout

logger = logging.getLogger(__name__)

class LayoutElementType(Enum):
    """Types of layout elements"""
    VIEWPORT = "viewport"
    REPORT_EDITOR = "report_editor"
    TEMPLATE_PANEL = "template_panel"
    VOICE_CONTROLS = "voice_controls"
    STUDY_BROWSER = "study_browser"
    PATIENT_INFO = "patient_info"
    TOOLBAR = "toolbar"
    STATUS_BAR = "status_bar"
    CUSTOM_PANEL = "custom_panel"

class LayoutPresetType(Enum):
    """Types of layout presets"""
    GENERAL_RADIOLOGY = "general_radiology"
    CHEST_XRAY = "chest_xray"
    CT_SCAN = "ct_scan"
    MRI_SCAN = "mri_scan"
    ULTRASOUND = "ultrasound"
    MAMMOGRAPHY = "mammography"
    NUCLEAR_MEDICINE = "nuclear_medicine"
    CUSTOM = "custom"

class DragDropAction(Enum):
    """Drag and drop actions"""
    MOVE = "move"
    RESIZE = "resize"
    SWAP = "swap"
    SPLIT = "split"
    MERGE = "merge"

@dataclass
class LayoutElement:
    """Individual layout element configuration"""
    element_id: str
    element_type: LayoutElementType
    x: float  # Percentage of screen width
    y: float  # Percentage of screen height
    width: float  # Percentage of screen width
    height: float  # Percentage of screen height
    z_index: int = 0
    is_resizable: bool = True
    is_movable: bool = True
    is_visible: bool = True
    min_width: float = 5.0  # Minimum width percentage
    min_height: float = 5.0  # Minimum height percentage
    max_width: float = 100.0  # Maximum width percentage
    max_height: float = 100.0  # Maximum height percentage
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        # Validate dimensions
        self.x = max(0, min(100, self.x))
        self.y = max(0, min(100, self.y))
        self.width = max(self.min_width, min(self.max_width, self.width))
        self.height = max(self.min_height, min(self.max_height, self.height))

@dataclass
class MonitorConfiguration:
    """Configuration for a single monitor"""
    monitor_id: str
    is_primary: bool = False
    width_pixels: int = 1920
    height_pixels: int = 1080
    x_offset: int = 0  # X offset from primary monitor
    y_offset: int = 0  # Y offset from primary monitor
    scale_factor: float = 1.0
    elements: List[LayoutElement] = field(default_factory=list)

@dataclass
class LayoutConfiguration:
    """Complete layout configuration"""
    layout_id: str
    name: str
    preset_type: LayoutPresetType
    user_id: Optional[str] = None
    examination_type: Optional[str] = None
    monitors: List[MonitorConfiguration] = field(default_factory=list)
    is_default: bool = False
    is_shared: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1
    
    def __post_init__(self):
        if not self.layout_id:
            self.layout_id = str(uuid.uuid4())

class LayoutManager:
    """Manages customizable screen layouts and configurations"""
    
    def __init__(self, viewport_manager: ViewportManager):
        self.viewport_manager = viewport_manager
        self.current_layout: Optional[LayoutConfiguration] = None
        self.saved_layouts: Dict[str, LayoutConfiguration] = {}
        self.layout_presets: Dict[LayoutPresetType, LayoutConfiguration] = {}
        
        # Event callbacks
        self.layout_change_callbacks: List[Callable] = []
        self.element_change_callbacks: List[Callable] = []
        self.drag_drop_callbacks: List[Callable] = []
        
        # Drag and drop state
        self.drag_state: Optional[Dict[str, Any]] = None
        self.drop_zones: List[Dict[str, Any]] = []
        
        # Multi-monitor support
        self.detected_monitors: List[MonitorConfiguration] = []
        self.active_monitors: List[str] = []
        
        # Initialize default presets
        self._create_default_presets()
        self._detect_monitors()
    
    def _create_default_presets(self):
        """Create default layout presets for different examination types"""
        
        # General Radiology Layout
        general_elements = [
            LayoutElement(
                element_id="main_viewport",
                element_type=LayoutElementType.VIEWPORT,
                x=0, y=0, width=60, height=70,
                properties={"viewport_layout": "quad"}
            ),
            LayoutElement(
                element_id="report_editor",
                element_type=LayoutElementType.REPORT_EDITOR,
                x=60, y=0, width=40, height=50
            ),
            LayoutElement(
                element_id="template_panel",
                element_type=LayoutElementType.TEMPLATE_PANEL,
                x=60, y=50, width=40, height=20
            ),
            LayoutElement(
                element_id="voice_controls",
                element_type=LayoutElementType.VOICE_CONTROLS,
                x=60, y=70, width=40, height=10
            ),
            LayoutElement(
                element_id="study_browser",
                element_type=LayoutElementType.STUDY_BROWSER,
                x=0, y=70, width=30, height=25
            ),
            LayoutElement(
                element_id="patient_info",
                element_type=LayoutElementType.PATIENT_INFO,
                x=30, y=70, width=30, height=25
            ),
            LayoutElement(
                element_id="toolbar",
                element_type=LayoutElementType.TOOLBAR,
                x=0, y=95, width=100, height=3,
                is_resizable=False
            ),
            LayoutElement(
                element_id="status_bar",
                element_type=LayoutElementType.STATUS_BAR,
                x=0, y=97, width=100, height=3,
                is_resizable=False, is_movable=False
            )
        ]
        
        primary_monitor = MonitorConfiguration(
            monitor_id="primary",
            is_primary=True,
            elements=general_elements
        )
        
        self.layout_presets[LayoutPresetType.GENERAL_RADIOLOGY] = LayoutConfiguration(
            layout_id="preset_general_radiology",
            name="General Radiology",
            preset_type=LayoutPresetType.GENERAL_RADIOLOGY,
            monitors=[primary_monitor],
            is_default=True
        )
        
        # Chest X-Ray Layout (Single large viewport)
        chest_elements = [
            LayoutElement(
                element_id="main_viewport",
                element_type=LayoutElementType.VIEWPORT,
                x=0, y=0, width=70, height=85,
                properties={"viewport_layout": "single"}
            ),
            LayoutElement(
                element_id="report_editor",
                element_type=LayoutElementType.REPORT_EDITOR,
                x=70, y=0, width=30, height=60
            ),
            LayoutElement(
                element_id="template_panel",
                element_type=LayoutElementType.TEMPLATE_PANEL,
                x=70, y=60, width=30, height=25
            ),
            LayoutElement(
                element_id="patient_info",
                element_type=LayoutElementType.PATIENT_INFO,
                x=0, y=85, width=70, height=10
            ),
            LayoutElement(
                element_id="voice_controls",
                element_type=LayoutElementType.VOICE_CONTROLS,
                x=70, y=85, width=30, height=10
            ),
            LayoutElement(
                element_id="status_bar",
                element_type=LayoutElementType.STATUS_BAR,
                x=0, y=95, width=100, height=5,
                is_resizable=False, is_movable=False
            )
        ]
        
        chest_monitor = MonitorConfiguration(
            monitor_id="primary",
            is_primary=True,
            elements=chest_elements
        )
        
        self.layout_presets[LayoutPresetType.CHEST_XRAY] = LayoutConfiguration(
            layout_id="preset_chest_xray",
            name="Chest X-Ray",
            preset_type=LayoutPresetType.CHEST_XRAY,
            monitors=[chest_monitor],
            is_default=True
        )
        
        # CT Scan Layout (Multi-viewport with comparison)
        ct_elements = [
            LayoutElement(
                element_id="current_viewport",
                element_type=LayoutElementType.VIEWPORT,
                x=0, y=0, width=40, height=70,
                properties={"viewport_layout": "single", "series_type": "current"}
            ),
            LayoutElement(
                element_id="comparison_viewport",
                element_type=LayoutElementType.VIEWPORT,
                x=40, y=0, width=40, height=70,
                properties={"viewport_layout": "single", "series_type": "comparison"}
            ),
            LayoutElement(
                element_id="report_editor",
                element_type=LayoutElementType.REPORT_EDITOR,
                x=80, y=0, width=20, height=50
            ),
            LayoutElement(
                element_id="template_panel",
                element_type=LayoutElementType.TEMPLATE_PANEL,
                x=80, y=50, width=20, height=20
            ),
            LayoutElement(
                element_id="study_browser",
                element_type=LayoutElementType.STUDY_BROWSER,
                x=0, y=70, width=40, height=25
            ),
            LayoutElement(
                element_id="patient_info",
                element_type=LayoutElementType.PATIENT_INFO,
                x=40, y=70, width=40, height=15
            ),
            LayoutElement(
                element_id="voice_controls",
                element_type=LayoutElementType.VOICE_CONTROLS,
                x=40, y=85, width=40, height=10
            ),
            LayoutElement(
                element_id="toolbar",
                element_type=LayoutElementType.TOOLBAR,
                x=80, y=70, width=20, height=25
            ),
            LayoutElement(
                element_id="status_bar",
                element_type=LayoutElementType.STATUS_BAR,
                x=0, y=95, width=100, height=5,
                is_resizable=False, is_movable=False
            )
        ]
        
        ct_monitor = MonitorConfiguration(
            monitor_id="primary",
            is_primary=True,
            elements=ct_elements
        )
        
        self.layout_presets[LayoutPresetType.CT_SCAN] = LayoutConfiguration(
            layout_id="preset_ct_scan",
            name="CT Scan",
            preset_type=LayoutPresetType.CT_SCAN,
            monitors=[ct_monitor],
            is_default=True
        )
    
    def _detect_monitors(self):
        """Detect available monitors (mock implementation)"""
        # In a real implementation, this would detect actual monitors
        primary_monitor = MonitorConfiguration(
            monitor_id="monitor_0",
            is_primary=True,
            width_pixels=1920,
            height_pixels=1080,
            x_offset=0,
            y_offset=0
        )
        
        self.detected_monitors = [primary_monitor]
        self.active_monitors = ["monitor_0"]
        
        logger.info(f"Detected {len(self.detected_monitors)} monitors")
    
    def create_layout(self, name: str, preset_type: LayoutPresetType = LayoutPresetType.CUSTOM,
                     user_id: Optional[str] = None, examination_type: Optional[str] = None) -> LayoutConfiguration:
        """Create a new layout configuration"""
        try:
            layout_config = LayoutConfiguration(
                layout_id=str(uuid.uuid4()),
                name=name,
                preset_type=preset_type,
                user_id=user_id,
                examination_type=examination_type
            )
            
            # Add primary monitor with default elements
            primary_monitor = MonitorConfiguration(
                monitor_id="primary",
                is_primary=True,
                elements=[]
            )
            layout_config.monitors.append(primary_monitor)
            
            logger.info(f"Created new layout: {name}")
            return layout_config
            
        except Exception as e:
            logger.error(f"Failed to create layout: {e}")
            raise
    
    def load_layout(self, layout_id: str) -> bool:
        """Load a layout configuration"""
        try:
            # Try to load from saved layouts first
            if layout_id in self.saved_layouts:
                layout_config = self.saved_layouts[layout_id]
            else:
                # Try to load from presets
                preset_layout = None
                for preset_type, preset_config in self.layout_presets.items():
                    if preset_config.layout_id == layout_id:
                        preset_layout = preset_config
                        break
                
                if not preset_layout:
                    logger.error(f"Layout not found: {layout_id}")
                    return False
                
                layout_config = preset_layout
            
            # Apply the layout
            self.current_layout = layout_config
            self._apply_layout_configuration(layout_config)
            
            # Notify callbacks
            self._notify_layout_change('loaded', layout_config)
            
            logger.info(f"Loaded layout: {layout_config.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load layout: {e}")
            return False
    
    def save_layout(self, layout_config: LayoutConfiguration, overwrite: bool = False) -> bool:
        """Save a layout configuration"""
        try:
            if layout_config.layout_id in self.saved_layouts and not overwrite:
                logger.warning(f"Layout already exists: {layout_config.layout_id}")
                return False
            
            # Update modification time and version
            layout_config.modified_at = datetime.utcnow()
            if layout_config.layout_id in self.saved_layouts:
                layout_config.version += 1
            
            # Save to memory (in real implementation, would save to database)
            self.saved_layouts[layout_config.layout_id] = layout_config
            
            # If this is the current layout, update it
            if self.current_layout and self.current_layout.layout_id == layout_config.layout_id:
                self.current_layout = layout_config
            
            logger.info(f"Saved layout: {layout_config.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save layout: {e}")
            return False
    
    def _apply_layout_configuration(self, layout_config: LayoutConfiguration):
        """Apply a layout configuration to the interface"""
        try:
            # Apply to each monitor
            for monitor_config in layout_config.monitors:
                self._apply_monitor_configuration(monitor_config)
            
            # Update viewport manager if viewport elements exist
            viewport_elements = []
            for monitor in layout_config.monitors:
                viewport_elements.extend([
                    elem for elem in monitor.elements 
                    if elem.element_type == LayoutElementType.VIEWPORT
                ])
            
            if viewport_elements:
                self._configure_viewports(viewport_elements)
            
        except Exception as e:
            logger.error(f"Failed to apply layout configuration: {e}")
            raise
    
    def _apply_monitor_configuration(self, monitor_config: MonitorConfiguration):
        """Apply configuration to a specific monitor"""
        try:
            logger.debug(f"Applying configuration to monitor: {monitor_config.monitor_id}")
            
            # In a real implementation, this would:
            # 1. Position windows on the correct monitor
            # 2. Set element sizes and positions
            # 3. Configure monitor-specific settings
            
            for element in monitor_config.elements:
                self._position_element(element, monitor_config)
            
        except Exception as e:
            logger.error(f"Failed to apply monitor configuration: {e}")
            raise
    
    def _position_element(self, element: LayoutElement, monitor: MonitorConfiguration):
        """Position an element on a monitor"""
        try:
            # Calculate absolute pixel positions
            abs_x = int((element.x / 100.0) * monitor.width_pixels)
            abs_y = int((element.y / 100.0) * monitor.height_pixels)
            abs_width = int((element.width / 100.0) * monitor.width_pixels)
            abs_height = int((element.height / 100.0) * monitor.height_pixels)
            
            # Apply monitor offset
            abs_x += monitor.x_offset
            abs_y += monitor.y_offset
            
            logger.debug(f"Positioned element {element.element_id} at ({abs_x}, {abs_y}) "
                        f"size ({abs_width}, {abs_height})")
            
            # In a real implementation, this would actually position the UI element
            
        except Exception as e:
            logger.error(f"Failed to position element: {e}")
    
    def _configure_viewports(self, viewport_elements: List[LayoutElement]):
        """Configure viewport manager based on viewport elements"""
        try:
            # Find the main viewport element
            main_viewport = None
            for element in viewport_elements:
                if element.element_id == "main_viewport" or element.properties.get("is_main", False):
                    main_viewport = element
                    break
            
            if not main_viewport and viewport_elements:
                main_viewport = viewport_elements[0]
            
            if main_viewport:
                # Configure viewport layout based on element properties
                viewport_layout_str = main_viewport.properties.get("viewport_layout", "single")
                
                if viewport_layout_str == "single":
                    self.viewport_manager.set_layout(ViewportLayout.SINGLE)
                elif viewport_layout_str == "dual_horizontal":
                    self.viewport_manager.set_layout(ViewportLayout.DUAL_HORIZONTAL)
                elif viewport_layout_str == "quad":
                    self.viewport_manager.set_layout(ViewportLayout.QUAD)
                
                logger.debug(f"Configured viewport layout: {viewport_layout_str}")
            
        except Exception as e:
            logger.error(f"Failed to configure viewports: {e}")
    
    def add_element(self, monitor_id: str, element: LayoutElement) -> bool:
        """Add an element to a monitor"""
        try:
            if not self.current_layout:
                logger.error("No current layout to add element to")
                return False
            
            # Find the monitor
            monitor = None
            for mon in self.current_layout.monitors:
                if mon.monitor_id == monitor_id:
                    monitor = mon
                    break
            
            if not monitor:
                logger.error(f"Monitor not found: {monitor_id}")
                return False
            
            # Check for element ID conflicts
            existing_ids = [elem.element_id for elem in monitor.elements]
            if element.element_id in existing_ids:
                logger.error(f"Element ID already exists: {element.element_id}")
                return False
            
            # Add the element
            monitor.elements.append(element)
            
            # Apply the element positioning
            self._position_element(element, monitor)
            
            # Notify callbacks
            self._notify_element_change('added', element, monitor_id)
            
            logger.info(f"Added element {element.element_id} to monitor {monitor_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add element: {e}")
            return False
    
    def remove_element(self, monitor_id: str, element_id: str) -> bool:
        """Remove an element from a monitor"""
        try:
            if not self.current_layout:
                logger.error("No current layout to remove element from")
                return False
            
            # Find the monitor and element
            monitor = None
            element = None
            
            for mon in self.current_layout.monitors:
                if mon.monitor_id == monitor_id:
                    monitor = mon
                    for elem in mon.elements:
                        if elem.element_id == element_id:
                            element = elem
                            break
                    break
            
            if not monitor or not element:
                logger.error(f"Element not found: {element_id} on monitor {monitor_id}")
                return False
            
            # Remove the element
            monitor.elements.remove(element)
            
            # Notify callbacks
            self._notify_element_change('removed', element, monitor_id)
            
            logger.info(f"Removed element {element_id} from monitor {monitor_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove element: {e}")
            return False
    
    def move_element(self, monitor_id: str, element_id: str, new_x: float, new_y: float) -> bool:
        """Move an element to a new position"""
        try:
            element = self._find_element(monitor_id, element_id)
            if not element:
                return False
            
            if not element.is_movable:
                logger.warning(f"Element {element_id} is not movable")
                return False
            
            # Update position
            old_x, old_y = element.x, element.y
            element.x = max(0, min(100, new_x))
            element.y = max(0, min(100, new_y))
            
            # Reposition the element
            monitor = self._find_monitor(monitor_id)
            if monitor:
                self._position_element(element, monitor)
            
            # Notify callbacks
            self._notify_element_change('moved', element, monitor_id, {
                'old_position': (old_x, old_y),
                'new_position': (element.x, element.y)
            })
            
            logger.debug(f"Moved element {element_id} to ({element.x}, {element.y})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move element: {e}")
            return False
    
    def resize_element(self, monitor_id: str, element_id: str, 
                      new_width: float, new_height: float) -> bool:
        """Resize an element"""
        try:
            element = self._find_element(monitor_id, element_id)
            if not element:
                return False
            
            if not element.is_resizable:
                logger.warning(f"Element {element_id} is not resizable")
                return False
            
            # Update size with constraints
            old_width, old_height = element.width, element.height
            element.width = max(element.min_width, min(element.max_width, new_width))
            element.height = max(element.min_height, min(element.max_height, new_height))
            
            # Reposition the element
            monitor = self._find_monitor(monitor_id)
            if monitor:
                self._position_element(element, monitor)
            
            # Notify callbacks
            self._notify_element_change('resized', element, monitor_id, {
                'old_size': (old_width, old_height),
                'new_size': (element.width, element.height)
            })
            
            logger.debug(f"Resized element {element_id} to ({element.width}, {element.height})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resize element: {e}")
            return False
    
    def start_drag_operation(self, monitor_id: str, element_id: str, 
                           action: DragDropAction, start_x: float, start_y: float) -> bool:
        """Start a drag and drop operation"""
        try:
            element = self._find_element(monitor_id, element_id)
            if not element:
                return False
            
            # Check if element supports the action
            if action == DragDropAction.MOVE and not element.is_movable:
                return False
            if action == DragDropAction.RESIZE and not element.is_resizable:
                return False
            
            # Set drag state
            self.drag_state = {
                'monitor_id': monitor_id,
                'element_id': element_id,
                'action': action,
                'start_x': start_x,
                'start_y': start_y,
                'start_element_x': element.x,
                'start_element_y': element.y,
                'start_element_width': element.width,
                'start_element_height': element.height,
                'started_at': datetime.utcnow()
            }
            
            # Update drop zones
            self._update_drop_zones(action)
            
            logger.debug(f"Started drag operation: {action.value} on {element_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start drag operation: {e}")
            return False
    
    def update_drag_operation(self, current_x: float, current_y: float) -> bool:
        """Update an ongoing drag operation"""
        try:
            if not self.drag_state:
                return False
            
            element = self._find_element(
                self.drag_state['monitor_id'], 
                self.drag_state['element_id']
            )
            if not element:
                return False
            
            # Calculate deltas
            delta_x = current_x - self.drag_state['start_x']
            delta_y = current_y - self.drag_state['start_y']
            
            # Apply based on action
            if self.drag_state['action'] == DragDropAction.MOVE:
                new_x = self.drag_state['start_element_x'] + delta_x
                new_y = self.drag_state['start_element_y'] + delta_y
                self.move_element(self.drag_state['monitor_id'], element.element_id, new_x, new_y)
                
            elif self.drag_state['action'] == DragDropAction.RESIZE:
                new_width = self.drag_state['start_element_width'] + delta_x
                new_height = self.drag_state['start_element_height'] + delta_y
                self.resize_element(self.drag_state['monitor_id'], element.element_id, new_width, new_height)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update drag operation: {e}")
            return False
    
    def end_drag_operation(self, final_x: float, final_y: float) -> bool:
        """End a drag and drop operation"""
        try:
            if not self.drag_state:
                return False
            
            # Final update
            self.update_drag_operation(final_x, final_y)
            
            # Notify callbacks
            self._notify_drag_drop('completed', self.drag_state)
            
            # Clear drag state
            drag_info = self.drag_state
            self.drag_state = None
            self.drop_zones.clear()
            
            logger.debug(f"Completed drag operation: {drag_info['action'].value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to end drag operation: {e}")
            return False
    
    def cancel_drag_operation(self) -> bool:
        """Cancel an ongoing drag operation"""
        try:
            if not self.drag_state:
                return False
            
            # Restore original position/size
            element = self._find_element(
                self.drag_state['monitor_id'], 
                self.drag_state['element_id']
            )
            
            if element:
                element.x = self.drag_state['start_element_x']
                element.y = self.drag_state['start_element_y']
                element.width = self.drag_state['start_element_width']
                element.height = self.drag_state['start_element_height']
                
                # Reposition
                monitor = self._find_monitor(self.drag_state['monitor_id'])
                if monitor:
                    self._position_element(element, monitor)
            
            # Notify callbacks
            self._notify_drag_drop('cancelled', self.drag_state)
            
            # Clear drag state
            self.drag_state = None
            self.drop_zones.clear()
            
            logger.debug("Cancelled drag operation")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel drag operation: {e}")
            return False
    
    def _update_drop_zones(self, action: DragDropAction):
        """Update available drop zones for current drag operation"""
        try:
            self.drop_zones.clear()
            
            if not self.current_layout:
                return
            
            # Add drop zones based on action
            for monitor in self.current_layout.monitors:
                if action == DragDropAction.MOVE:
                    # Add monitor as drop zone
                    self.drop_zones.append({
                        'type': 'monitor',
                        'monitor_id': monitor.monitor_id,
                        'x': 0, 'y': 0, 'width': 100, 'height': 100
                    })
                    
                    # Add element drop zones for swapping
                    for element in monitor.elements:
                        if element.element_id != self.drag_state['element_id']:
                            self.drop_zones.append({
                                'type': 'element_swap',
                                'monitor_id': monitor.monitor_id,
                                'element_id': element.element_id,
                                'x': element.x, 'y': element.y,
                                'width': element.width, 'height': element.height
                            })
            
        except Exception as e:
            logger.error(f"Failed to update drop zones: {e}")
    
    def get_layout_presets(self) -> List[Dict[str, Any]]:
        """Get available layout presets"""
        try:
            presets = []
            for preset_type, layout_config in self.layout_presets.items():
                presets.append({
                    'layout_id': layout_config.layout_id,
                    'name': layout_config.name,
                    'preset_type': preset_type.value,
                    'examination_type': layout_config.examination_type,
                    'is_default': layout_config.is_default,
                    'monitor_count': len(layout_config.monitors),
                    'element_count': sum(len(m.elements) for m in layout_config.monitors)
                })
            
            return presets
            
        except Exception as e:
            logger.error(f"Failed to get layout presets: {e}")
            return []
    
    def get_saved_layouts(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get saved layouts for a user"""
        try:
            layouts = []
            for layout_config in self.saved_layouts.values():
                # Filter by user if specified
                if user_id and layout_config.user_id != user_id:
                    continue
                
                layouts.append({
                    'layout_id': layout_config.layout_id,
                    'name': layout_config.name,
                    'preset_type': layout_config.preset_type.value,
                    'user_id': layout_config.user_id,
                    'examination_type': layout_config.examination_type,
                    'is_shared': layout_config.is_shared,
                    'created_at': layout_config.created_at.isoformat(),
                    'modified_at': layout_config.modified_at.isoformat(),
                    'version': layout_config.version,
                    'monitor_count': len(layout_config.monitors),
                    'element_count': sum(len(m.elements) for m in layout_config.monitors)
                })
            
            return layouts
            
        except Exception as e:
            logger.error(f"Failed to get saved layouts: {e}")
            return []
    
    def get_current_layout_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current layout"""
        try:
            if not self.current_layout:
                return None
            
            return {
                'layout_id': self.current_layout.layout_id,
                'name': self.current_layout.name,
                'preset_type': self.current_layout.preset_type.value,
                'user_id': self.current_layout.user_id,
                'examination_type': self.current_layout.examination_type,
                'monitors': [
                    {
                        'monitor_id': monitor.monitor_id,
                        'is_primary': monitor.is_primary,
                        'width_pixels': monitor.width_pixels,
                        'height_pixels': monitor.height_pixels,
                        'element_count': len(monitor.elements),
                        'elements': [
                            {
                                'element_id': elem.element_id,
                                'element_type': elem.element_type.value,
                                'x': elem.x, 'y': elem.y,
                                'width': elem.width, 'height': elem.height,
                                'is_visible': elem.is_visible,
                                'properties': elem.properties
                            }
                            for elem in monitor.elements
                        ]
                    }
                    for monitor in self.current_layout.monitors
                ],
                'created_at': self.current_layout.created_at.isoformat(),
                'modified_at': self.current_layout.modified_at.isoformat(),
                'version': self.current_layout.version
            }
            
        except Exception as e:
            logger.error(f"Failed to get current layout info: {e}")
            return None
    
    def _find_element(self, monitor_id: str, element_id: str) -> Optional[LayoutElement]:
        """Find an element by monitor and element ID"""
        if not self.current_layout:
            return None
        
        for monitor in self.current_layout.monitors:
            if monitor.monitor_id == monitor_id:
                for element in monitor.elements:
                    if element.element_id == element_id:
                        return element
        return None
    
    def _find_monitor(self, monitor_id: str) -> Optional[MonitorConfiguration]:
        """Find a monitor by ID"""
        if not self.current_layout:
            return None
        
        for monitor in self.current_layout.monitors:
            if monitor.monitor_id == monitor_id:
                return monitor
        return None
    
    def add_layout_change_callback(self, callback: Callable):
        """Add callback for layout changes"""
        self.layout_change_callbacks.append(callback)
    
    def add_element_change_callback(self, callback: Callable):
        """Add callback for element changes"""
        self.element_change_callbacks.append(callback)
    
    def add_drag_drop_callback(self, callback: Callable):
        """Add callback for drag and drop operations"""
        self.drag_drop_callbacks.append(callback)
    
    def _notify_layout_change(self, change_type: str, layout_config: LayoutConfiguration):
        """Notify layout change callbacks"""
        try:
            for callback in self.layout_change_callbacks:
                try:
                    callback(change_type, layout_config)
                except Exception as e:
                    logger.error(f"Error in layout change callback: {e}")
        except Exception as e:
            logger.error(f"Failed to notify layout change: {e}")
    
    def _notify_element_change(self, change_type: str, element: LayoutElement, 
                             monitor_id: str, extra_data: Optional[Dict[str, Any]] = None):
        """Notify element change callbacks"""
        try:
            for callback in self.element_change_callbacks:
                try:
                    callback(change_type, element, monitor_id, extra_data)
                except Exception as e:
                    logger.error(f"Error in element change callback: {e}")
        except Exception as e:
            logger.error(f"Failed to notify element change: {e}")
    
    def _notify_drag_drop(self, change_type: str, drag_state: Dict[str, Any]):
        """Notify drag and drop callbacks"""
        try:
            for callback in self.drag_drop_callbacks:
                try:
                    callback(change_type, drag_state)
                except Exception as e:
                    logger.error(f"Error in drag drop callback: {e}")
        except Exception as e:
            logger.error(f"Failed to notify drag drop: {e}")

# Global layout manager instance (will be initialized with viewport manager)
layout_manager: Optional[LayoutManager] = None