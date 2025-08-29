"""
Drag and Drop Handler for Medical Reporting Module
Handles drag and drop operations for layout customization
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from services.layout_manager import LayoutManager, DragDropAction, LayoutElement, LayoutElementType

logger = logging.getLogger(__name__)

class DropZoneType(Enum):
    """Types of drop zones"""
    MONITOR = "monitor"
    ELEMENT_SWAP = "element_swap"
    ELEMENT_SPLIT = "element_split"
    ELEMENT_MERGE = "element_merge"
    VIEWPORT_SLOT = "viewport_slot"
    PANEL_DOCK = "panel_dock"

class SnapMode(Enum):
    """Snap modes for drag operations"""
    NONE = "none"
    GRID = "grid"
    ELEMENT_EDGES = "element_edges"
    MONITOR_EDGES = "monitor_edges"
    ALL = "all"

@dataclass
class DropZone:
    """Drop zone configuration"""
    zone_id: str
    zone_type: DropZoneType
    monitor_id: str
    x: float
    y: float
    width: float
    height: float
    is_active: bool = False
    accepts_types: List[LayoutElementType] = None
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.accepts_types is None:
            self.accepts_types = list(LayoutElementType)
        if self.properties is None:
            self.properties = {}

@dataclass
class DragOperation:
    """Current drag operation state"""
    element_id: str
    monitor_id: str
    action: DragDropAction
    start_x: float
    start_y: float
    current_x: float
    current_y: float
    start_element_x: float
    start_element_y: float
    start_element_width: float
    start_element_height: float
    snap_mode: SnapMode = SnapMode.GRID
    grid_size: float = 5.0  # Grid snap size in percentage
    started_at: datetime = None
    
    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.utcnow()

class DragDropHandler:
    """Handles drag and drop operations for layout customization"""
    
    def __init__(self, layout_manager: LayoutManager):
        self.layout_manager = layout_manager
        self.current_drag: Optional[DragOperation] = None
        self.drop_zones: List[DropZone] = []
        self.active_drop_zone: Optional[DropZone] = None
        
        # Configuration
        self.snap_threshold = 10.0  # Pixels for snap detection
        self.grid_size = 5.0  # Default grid size in percentage
        self.auto_scroll_margin = 50  # Pixels from edge to trigger auto-scroll
        
        # Event callbacks
        self.drag_start_callbacks: List[Callable] = []
        self.drag_update_callbacks: List[Callable] = []
        self.drag_end_callbacks: List[Callable] = []
        self.drop_zone_callbacks: List[Callable] = []
        
        # Visual feedback
        self.show_drop_zones = True
        self.show_snap_guides = True
        self.show_element_outlines = True
    
    def start_drag(self, element_id: str, monitor_id: str, action: DragDropAction,
                  start_x: float, start_y: float, snap_mode: SnapMode = SnapMode.GRID) -> bool:
        """Start a drag operation"""
        try:
            if self.current_drag:
                logger.warning("Drag operation already in progress")
                return False
            
            # Find the element
            element = self.layout_manager._find_element(monitor_id, element_id)
            if not element:
                logger.error(f"Element not found: {element_id}")
                return False
            
            # Check if element supports the action
            if action == DragDropAction.MOVE and not element.is_movable:
                logger.warning(f"Element {element_id} is not movable")
                return False
            if action == DragDropAction.RESIZE and not element.is_resizable:
                logger.warning(f"Element {element_id} is not resizable")
                return False
            
            # Create drag operation
            self.current_drag = DragOperation(
                element_id=element_id,
                monitor_id=monitor_id,
                action=action,
                start_x=start_x,
                start_y=start_y,
                current_x=start_x,
                current_y=start_y,
                start_element_x=element.x,
                start_element_y=element.y,
                start_element_width=element.width,
                start_element_height=element.height,
                snap_mode=snap_mode,
                grid_size=self.grid_size
            )
            
            # Generate drop zones
            self._generate_drop_zones(action, element)
            
            # Start drag in layout manager
            self.layout_manager.start_drag_operation(monitor_id, element_id, action, start_x, start_y)
            
            # Notify callbacks
            self._notify_drag_start(self.current_drag)
            
            logger.debug(f"Started drag operation: {action.value} on {element_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start drag operation: {e}")
            return False
    
    def update_drag(self, current_x: float, current_y: float) -> bool:
        """Update the current drag operation"""
        try:
            if not self.current_drag:
                return False
            
            # Update current position
            self.current_drag.current_x = current_x
            self.current_drag.current_y = current_y
            
            # Apply snapping
            snapped_x, snapped_y = self._apply_snapping(current_x, current_y)
            
            # Calculate new element position/size
            if self.current_drag.action == DragDropAction.MOVE:
                delta_x = snapped_x - self.current_drag.start_x
                delta_y = snapped_y - self.current_drag.start_y
                
                new_x = self.current_drag.start_element_x + delta_x
                new_y = self.current_drag.start_element_y + delta_y
                
                # Apply constraints
                new_x = max(0, min(100, new_x))
                new_y = max(0, min(100, new_y))
                
                # Update element position
                self.layout_manager.move_element(
                    self.current_drag.monitor_id,
                    self.current_drag.element_id,
                    new_x, new_y
                )
                
            elif self.current_drag.action == DragDropAction.RESIZE:
                delta_x = snapped_x - self.current_drag.start_x
                delta_y = snapped_y - self.current_drag.start_y
                
                new_width = self.current_drag.start_element_width + delta_x
                new_height = self.current_drag.start_element_height + delta_y
                
                # Update element size
                self.layout_manager.resize_element(
                    self.current_drag.monitor_id,
                    self.current_drag.element_id,
                    new_width, new_height
                )
            
            # Update active drop zone
            self._update_active_drop_zone(snapped_x, snapped_y)
            
            # Notify callbacks
            self._notify_drag_update(self.current_drag, snapped_x, snapped_y)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update drag operation: {e}")
            return False
    
    def end_drag(self, final_x: float, final_y: float) -> bool:
        """End the current drag operation"""
        try:
            if not self.current_drag:
                return False
            
            # Final update
            self.update_drag(final_x, final_y)
            
            # Handle drop zone actions
            success = self._handle_drop_action()
            
            # End drag in layout manager
            self.layout_manager.end_drag_operation(final_x, final_y)
            
            # Notify callbacks
            self._notify_drag_end(self.current_drag, success)
            
            # Clean up
            drag_info = self.current_drag
            self.current_drag = None
            self.drop_zones.clear()
            self.active_drop_zone = None
            
            logger.debug(f"Ended drag operation: {drag_info.action.value}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to end drag operation: {e}")
            return False
    
    def cancel_drag(self) -> bool:
        """Cancel the current drag operation"""
        try:
            if not self.current_drag:
                return False
            
            # Cancel drag in layout manager
            self.layout_manager.cancel_drag_operation()
            
            # Notify callbacks
            self._notify_drag_end(self.current_drag, False)
            
            # Clean up
            self.current_drag = None
            self.drop_zones.clear()
            self.active_drop_zone = None
            
            logger.debug("Cancelled drag operation")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel drag operation: {e}")
            return False
    
    def _apply_snapping(self, x: float, y: float) -> Tuple[float, float]:
        """Apply snapping to coordinates"""
        try:
            if not self.current_drag or self.current_drag.snap_mode == SnapMode.NONE:
                return x, y
            
            snapped_x, snapped_y = x, y
            
            # Grid snapping
            if self.current_drag.snap_mode in [SnapMode.GRID, SnapMode.ALL]:
                grid_size = self.current_drag.grid_size
                snapped_x = round(x / grid_size) * grid_size
                snapped_y = round(y / grid_size) * grid_size
            
            # Element edge snapping
            if self.current_drag.snap_mode in [SnapMode.ELEMENT_EDGES, SnapMode.ALL]:
                snapped_x, snapped_y = self._snap_to_element_edges(snapped_x, snapped_y)
            
            # Monitor edge snapping
            if self.current_drag.snap_mode in [SnapMode.MONITOR_EDGES, SnapMode.ALL]:
                snapped_x, snapped_y = self._snap_to_monitor_edges(snapped_x, snapped_y)
            
            return snapped_x, snapped_y
            
        except Exception as e:
            logger.error(f"Failed to apply snapping: {e}")
            return x, y
    
    def _snap_to_element_edges(self, x: float, y: float) -> Tuple[float, float]:
        """Snap to edges of other elements"""
        try:
            if not self.layout_manager.current_layout:
                return x, y
            
            snapped_x, snapped_y = x, y
            min_snap_distance = float('inf')
            
            # Get current element
            current_element = self.layout_manager._find_element(
                self.current_drag.monitor_id, 
                self.current_drag.element_id
            )
            if not current_element:
                return x, y
            
            # Check all other elements
            for monitor in self.layout_manager.current_layout.monitors:
                for element in monitor.elements:
                    if element.element_id == self.current_drag.element_id:
                        continue
                    
                    # Check horizontal edges
                    for edge_x in [element.x, element.x + element.width]:
                        distance = abs(current_element.x - edge_x)
                        if distance < self.snap_threshold and distance < min_snap_distance:
                            snapped_x = x + (edge_x - current_element.x)
                            min_snap_distance = distance
                    
                    # Check vertical edges
                    for edge_y in [element.y, element.y + element.height]:
                        distance = abs(current_element.y - edge_y)
                        if distance < self.snap_threshold and distance < min_snap_distance:
                            snapped_y = y + (edge_y - current_element.y)
                            min_snap_distance = distance
            
            return snapped_x, snapped_y
            
        except Exception as e:
            logger.error(f"Failed to snap to element edges: {e}")
            return x, y
    
    def _snap_to_monitor_edges(self, x: float, y: float) -> Tuple[float, float]:
        """Snap to monitor edges"""
        try:
            # Get current element
            current_element = self.layout_manager._find_element(
                self.current_drag.monitor_id, 
                self.current_drag.element_id
            )
            if not current_element:
                return x, y
            
            snapped_x, snapped_y = x, y
            
            # Snap to monitor edges (0, 100)
            if abs(current_element.x) < self.snap_threshold:
                snapped_x = x - current_element.x
            elif abs(current_element.x + current_element.width - 100) < self.snap_threshold:
                snapped_x = x + (100 - current_element.x - current_element.width)
            
            if abs(current_element.y) < self.snap_threshold:
                snapped_y = y - current_element.y
            elif abs(current_element.y + current_element.height - 100) < self.snap_threshold:
                snapped_y = y + (100 - current_element.y - current_element.height)
            
            return snapped_x, snapped_y
            
        except Exception as e:
            logger.error(f"Failed to snap to monitor edges: {e}")
            return x, y
    
    def _generate_drop_zones(self, action: DragDropAction, element: LayoutElement):
        """Generate drop zones for the current drag operation"""
        try:
            self.drop_zones.clear()
            
            if not self.layout_manager.current_layout:
                return
            
            # Generate zones based on action
            if action == DragDropAction.MOVE:
                self._generate_move_drop_zones(element)
            elif action == DragDropAction.RESIZE:
                self._generate_resize_drop_zones(element)
            elif action in [DragDropAction.SPLIT, DragDropAction.MERGE]:
                self._generate_split_merge_drop_zones(element)
            
        except Exception as e:
            logger.error(f"Failed to generate drop zones: {e}")
    
    def _generate_move_drop_zones(self, element: LayoutElement):
        """Generate drop zones for move operations"""
        try:
            # Add monitor drop zones
            for monitor in self.layout_manager.current_layout.monitors:
                zone = DropZone(
                    zone_id=f"monitor_{monitor.monitor_id}",
                    zone_type=DropZoneType.MONITOR,
                    monitor_id=monitor.monitor_id,
                    x=0, y=0, width=100, height=100,
                    accepts_types=[element.element_type]
                )
                self.drop_zones.append(zone)
                
                # Add element swap zones
                for other_element in monitor.elements:
                    if other_element.element_id != element.element_id:
                        zone = DropZone(
                            zone_id=f"swap_{other_element.element_id}",
                            zone_type=DropZoneType.ELEMENT_SWAP,
                            monitor_id=monitor.monitor_id,
                            x=other_element.x,
                            y=other_element.y,
                            width=other_element.width,
                            height=other_element.height,
                            accepts_types=[element.element_type],
                            properties={'target_element_id': other_element.element_id}
                        )
                        self.drop_zones.append(zone)
            
        except Exception as e:
            logger.error(f"Failed to generate move drop zones: {e}")
    
    def _generate_resize_drop_zones(self, element: LayoutElement):
        """Generate drop zones for resize operations"""
        try:
            # For resize operations, we don't need specific drop zones
            # The resize is handled by the drag update logic
            pass
            
        except Exception as e:
            logger.error(f"Failed to generate resize drop zones: {e}")
    
    def _generate_split_merge_drop_zones(self, element: LayoutElement):
        """Generate drop zones for split and merge operations"""
        try:
            # Add split zones for viewport elements
            if element.element_type == LayoutElementType.VIEWPORT:
                monitor = self.layout_manager._find_monitor(self.current_drag.monitor_id)
                if monitor:
                    # Add zones for splitting the viewport
                    for other_element in monitor.elements:
                        if (other_element.element_type == LayoutElementType.VIEWPORT and 
                            other_element.element_id != element.element_id):
                            
                            zone = DropZone(
                                zone_id=f"split_{other_element.element_id}",
                                zone_type=DropZoneType.ELEMENT_SPLIT,
                                monitor_id=monitor.monitor_id,
                                x=other_element.x,
                                y=other_element.y,
                                width=other_element.width,
                                height=other_element.height,
                                accepts_types=[LayoutElementType.VIEWPORT],
                                properties={'target_element_id': other_element.element_id}
                            )
                            self.drop_zones.append(zone)
            
        except Exception as e:
            logger.error(f"Failed to generate split/merge drop zones: {e}")
    
    def _update_active_drop_zone(self, x: float, y: float):
        """Update the active drop zone based on current position"""
        try:
            self.active_drop_zone = None
            
            # Find the drop zone under the current position
            for zone in self.drop_zones:
                if (zone.x <= x <= zone.x + zone.width and 
                    zone.y <= y <= zone.y + zone.height):
                    
                    # Check if the element type is accepted
                    element = self.layout_manager._find_element(
                        self.current_drag.monitor_id,
                        self.current_drag.element_id
                    )
                    
                    if element and element.element_type in zone.accepts_types:
                        self.active_drop_zone = zone
                        zone.is_active = True
                        break
            
            # Deactivate other zones
            for zone in self.drop_zones:
                if zone != self.active_drop_zone:
                    zone.is_active = False
            
        except Exception as e:
            logger.error(f"Failed to update active drop zone: {e}")
    
    def _handle_drop_action(self) -> bool:
        """Handle the drop action based on the active drop zone"""
        try:
            if not self.active_drop_zone:
                return True  # No special action needed
            
            if self.active_drop_zone.zone_type == DropZoneType.ELEMENT_SWAP:
                return self._handle_element_swap()
            elif self.active_drop_zone.zone_type == DropZoneType.ELEMENT_SPLIT:
                return self._handle_element_split()
            elif self.active_drop_zone.zone_type == DropZoneType.ELEMENT_MERGE:
                return self._handle_element_merge()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle drop action: {e}")
            return False
    
    def _handle_element_swap(self) -> bool:
        """Handle element swap operation"""
        try:
            if not self.active_drop_zone or not self.current_drag:
                return False
            
            target_element_id = self.active_drop_zone.properties.get('target_element_id')
            if not target_element_id:
                return False
            
            # Get both elements
            source_element = self.layout_manager._find_element(
                self.current_drag.monitor_id,
                self.current_drag.element_id
            )
            target_element = self.layout_manager._find_element(
                self.active_drop_zone.monitor_id,
                target_element_id
            )
            
            if not source_element or not target_element:
                return False
            
            # Swap positions
            temp_x, temp_y = source_element.x, source_element.y
            temp_width, temp_height = source_element.width, source_element.height
            
            source_element.x = target_element.x
            source_element.y = target_element.y
            source_element.width = target_element.width
            source_element.height = target_element.height
            
            target_element.x = temp_x
            target_element.y = temp_y
            target_element.width = temp_width
            target_element.height = temp_height
            
            logger.info(f"Swapped elements: {source_element.element_id} <-> {target_element_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle element swap: {e}")
            return False
    
    def _handle_element_split(self) -> bool:
        """Handle element split operation"""
        try:
            # This would implement viewport splitting logic
            # For now, just log the action
            logger.info("Element split operation requested")
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle element split: {e}")
            return False
    
    def _handle_element_merge(self) -> bool:
        """Handle element merge operation"""
        try:
            # This would implement viewport merging logic
            # For now, just log the action
            logger.info("Element merge operation requested")
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle element merge: {e}")
            return False
    
    def get_drop_zones(self) -> List[Dict[str, Any]]:
        """Get current drop zones for UI rendering"""
        try:
            return [
                {
                    'zone_id': zone.zone_id,
                    'zone_type': zone.zone_type.value,
                    'monitor_id': zone.monitor_id,
                    'x': zone.x,
                    'y': zone.y,
                    'width': zone.width,
                    'height': zone.height,
                    'is_active': zone.is_active,
                    'accepts_types': [t.value for t in zone.accepts_types],
                    'properties': zone.properties
                }
                for zone in self.drop_zones
            ]
            
        except Exception as e:
            logger.error(f"Failed to get drop zones: {e}")
            return []
    
    def get_drag_state(self) -> Optional[Dict[str, Any]]:
        """Get current drag state for UI rendering"""
        try:
            if not self.current_drag:
                return None
            
            return {
                'element_id': self.current_drag.element_id,
                'monitor_id': self.current_drag.monitor_id,
                'action': self.current_drag.action.value,
                'start_x': self.current_drag.start_x,
                'start_y': self.current_drag.start_y,
                'current_x': self.current_drag.current_x,
                'current_y': self.current_drag.current_y,
                'snap_mode': self.current_drag.snap_mode.value,
                'grid_size': self.current_drag.grid_size,
                'started_at': self.current_drag.started_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get drag state: {e}")
            return None
    
    def set_snap_mode(self, snap_mode: SnapMode):
        """Set the snap mode for drag operations"""
        if self.current_drag:
            self.current_drag.snap_mode = snap_mode
        logger.debug(f"Set snap mode to: {snap_mode.value}")
    
    def set_grid_size(self, grid_size: float):
        """Set the grid size for snapping"""
        self.grid_size = max(1.0, min(25.0, grid_size))
        if self.current_drag:
            self.current_drag.grid_size = self.grid_size
        logger.debug(f"Set grid size to: {self.grid_size}")
    
    def add_drag_start_callback(self, callback: Callable):
        """Add callback for drag start events"""
        self.drag_start_callbacks.append(callback)
    
    def add_drag_update_callback(self, callback: Callable):
        """Add callback for drag update events"""
        self.drag_update_callbacks.append(callback)
    
    def add_drag_end_callback(self, callback: Callable):
        """Add callback for drag end events"""
        self.drag_end_callbacks.append(callback)
    
    def add_drop_zone_callback(self, callback: Callable):
        """Add callback for drop zone events"""
        self.drop_zone_callbacks.append(callback)
    
    def _notify_drag_start(self, drag_operation: DragOperation):
        """Notify drag start callbacks"""
        try:
            for callback in self.drag_start_callbacks:
                try:
                    callback(drag_operation)
                except Exception as e:
                    logger.error(f"Error in drag start callback: {e}")
        except Exception as e:
            logger.error(f"Failed to notify drag start: {e}")
    
    def _notify_drag_update(self, drag_operation: DragOperation, x: float, y: float):
        """Notify drag update callbacks"""
        try:
            for callback in self.drag_update_callbacks:
                try:
                    callback(drag_operation, x, y)
                except Exception as e:
                    logger.error(f"Error in drag update callback: {e}")
        except Exception as e:
            logger.error(f"Failed to notify drag update: {e}")
    
    def _notify_drag_end(self, drag_operation: DragOperation, success: bool):
        """Notify drag end callbacks"""
        try:
            for callback in self.drag_end_callbacks:
                try:
                    callback(drag_operation, success)
                except Exception as e:
                    logger.error(f"Error in drag end callback: {e}")
        except Exception as e:
            logger.error(f"Failed to notify drag end: {e}")

# Global drag drop handler instance (will be initialized with layout manager)
drag_drop_handler: Optional[DragDropHandler] = None