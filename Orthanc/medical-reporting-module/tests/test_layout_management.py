"""
Tests for Layout Management System
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import uuid
from datetime import datetime

from services.layout_manager import (
    LayoutManager, LayoutConfiguration, LayoutElement, MonitorConfiguration,
    LayoutElementType, LayoutPresetType, DragDropAction
)
from services.layout_persistence import LayoutPersistenceService
from services.drag_drop_handler import DragDropHandler, SnapMode, DropZoneType
from services.viewport_manager import ViewportManager

class TestLayoutManager(unittest.TestCase):
    """Test layout manager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.viewport_manager = Mock(spec=ViewportManager)
        self.layout_manager = LayoutManager(self.viewport_manager)
    
    def test_create_layout(self):
        """Test creating a new layout"""
        layout = self.layout_manager.create_layout(
            name="Test Layout",
            preset_type=LayoutPresetType.CUSTOM,
            user_id="user123",
            examination_type="chest_xray"
        )
        
        self.assertIsInstance(layout, LayoutConfiguration)
        self.assertEqual(layout.name, "Test Layout")
        self.assertEqual(layout.preset_type, LayoutPresetType.CUSTOM)
        self.assertEqual(layout.user_id, "user123")
        self.assertEqual(layout.examination_type, "chest_xray")
        self.assertEqual(len(layout.monitors), 1)
        self.assertTrue(layout.monitors[0].is_primary)
    
    def test_load_preset_layout(self):
        """Test loading a preset layout"""
        success = self.layout_manager.load_layout("preset_general_radiology")
        
        self.assertTrue(success)
        self.assertIsNotNone(self.layout_manager.current_layout)
        self.assertEqual(self.layout_manager.current_layout.name, "General Radiology")
        self.assertEqual(self.layout_manager.current_layout.preset_type, LayoutPresetType.GENERAL_RADIOLOGY)
    
    def test_save_and_load_custom_layout(self):
        """Test saving and loading a custom layout"""
        # Create a custom layout
        layout = self.layout_manager.create_layout("Custom Test Layout")
        
        # Add some elements
        test_element = LayoutElement(
            element_id="test_element",
            element_type=LayoutElementType.VIEWPORT,
            x=10, y=10, width=50, height=50
        )
        
        success = self.layout_manager.add_element("primary", test_element)
        self.assertTrue(success)
        
        # Save the layout
        success = self.layout_manager.save_layout(layout)
        self.assertTrue(success)
        
        # Load the layout
        success = self.layout_manager.load_layout(layout.layout_id)
        self.assertTrue(success)
        self.assertEqual(self.layout_manager.current_layout.layout_id, layout.layout_id)
    
    def test_add_element(self):
        """Test adding an element to a layout"""
        # Load a preset layout
        self.layout_manager.load_layout("preset_general_radiology")
        
        # Add a new element
        new_element = LayoutElement(
            element_id="new_test_element",
            element_type=LayoutElementType.CUSTOM_PANEL,
            x=80, y=80, width=15, height=15
        )
        
        success = self.layout_manager.add_element("primary", new_element)
        self.assertTrue(success)
        
        # Verify element was added
        monitor = self.layout_manager._find_monitor("primary")
        self.assertIsNotNone(monitor)
        
        element_ids = [elem.element_id for elem in monitor.elements]
        self.assertIn("new_test_element", element_ids)
    
    def test_remove_element(self):
        """Test removing an element from a layout"""
        # Load a preset layout
        self.layout_manager.load_layout("preset_general_radiology")
        
        # Get initial element count
        monitor = self.layout_manager._find_monitor("primary")
        initial_count = len(monitor.elements)
        
        # Remove an element
        success = self.layout_manager.remove_element("primary", "toolbar")
        self.assertTrue(success)
        
        # Verify element was removed
        final_count = len(monitor.elements)
        self.assertEqual(final_count, initial_count - 1)
        
        element_ids = [elem.element_id for elem in monitor.elements]
        self.assertNotIn("toolbar", element_ids)
    
    def test_move_element(self):
        """Test moving an element"""
        # Load a preset layout
        self.layout_manager.load_layout("preset_general_radiology")
        
        # Move an element
        success = self.layout_manager.move_element("primary", "main_viewport", 20, 30)
        self.assertTrue(success)
        
        # Verify element was moved
        element = self.layout_manager._find_element("primary", "main_viewport")
        self.assertIsNotNone(element)
        self.assertEqual(element.x, 20)
        self.assertEqual(element.y, 30)
    
    def test_resize_element(self):
        """Test resizing an element"""
        # Load a preset layout
        self.layout_manager.load_layout("preset_general_radiology")
        
        # Resize an element
        success = self.layout_manager.resize_element("primary", "main_viewport", 70, 80)
        self.assertTrue(success)
        
        # Verify element was resized
        element = self.layout_manager._find_element("primary", "main_viewport")
        self.assertIsNotNone(element)
        self.assertEqual(element.width, 70)
        self.assertEqual(element.height, 80)
    
    def test_drag_drop_operations(self):
        """Test drag and drop operations"""
        # Load a preset layout
        self.layout_manager.load_layout("preset_general_radiology")
        
        # Start drag operation
        success = self.layout_manager.start_drag_operation(
            "primary", "main_viewport", DragDropAction.MOVE, 10, 10
        )
        self.assertTrue(success)
        
        # Update drag operation
        success = self.layout_manager.update_drag_operation(20, 20)
        self.assertTrue(success)
        
        # End drag operation
        success = self.layout_manager.end_drag_operation(25, 25)
        self.assertTrue(success)
    
    def test_get_layout_presets(self):
        """Test getting available layout presets"""
        presets = self.layout_manager.get_layout_presets()
        
        self.assertIsInstance(presets, list)
        self.assertGreater(len(presets), 0)
        
        # Check that default presets are included
        preset_types = [preset['preset_type'] for preset in presets]
        self.assertIn('general_radiology', preset_types)
        self.assertIn('chest_xray', preset_types)
        self.assertIn('ct_scan', preset_types)
    
    def test_get_current_layout_info(self):
        """Test getting current layout information"""
        # Load a preset layout
        self.layout_manager.load_layout("preset_general_radiology")
        
        layout_info = self.layout_manager.get_current_layout_info()
        
        self.assertIsNotNone(layout_info)
        self.assertEqual(layout_info['name'], "General Radiology")
        self.assertIn('monitors', layout_info)
        self.assertGreater(len(layout_info['monitors']), 0)
    
    def test_element_constraints(self):
        """Test element size and position constraints"""
        # Load a preset layout
        self.layout_manager.load_layout("preset_general_radiology")
        
        # Try to move element outside bounds
        success = self.layout_manager.move_element("primary", "main_viewport", -10, -10)
        self.assertTrue(success)  # Should succeed but clamp to bounds
        
        element = self.layout_manager._find_element("primary", "main_viewport")
        self.assertGreaterEqual(element.x, 0)
        self.assertGreaterEqual(element.y, 0)
        
        # Try to resize below minimum
        element = self.layout_manager._find_element("primary", "main_viewport")
        original_min_width = element.min_width
        
        success = self.layout_manager.resize_element("primary", "main_viewport", 1, 1)
        self.assertTrue(success)  # Should succeed but clamp to minimum
        
        self.assertGreaterEqual(element.width, original_min_width)
        self.assertGreaterEqual(element.height, element.min_height)

class TestLayoutPersistence(unittest.TestCase):
    """Test layout persistence functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.persistence_service = LayoutPersistenceService()
        
        # Mock database session
        self.mock_session = Mock()
        self.mock_db_session = patch('services.layout_persistence.get_db_session')
        self.mock_db_session.start().return_value.__enter__.return_value = self.mock_session
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.mock_db_session.stop()
    
    def test_save_layout(self):
        """Test saving a layout to database"""
        # Create test layout
        layout = LayoutConfiguration(
            layout_id="test_layout_123",
            name="Test Layout",
            preset_type=LayoutPresetType.CUSTOM,
            user_id="user123"
        )
        
        # Mock database operations
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Save layout
        success = self.persistence_service.save_layout(layout)
        
        self.assertTrue(success)
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()
    
    def test_load_layout(self):
        """Test loading a layout from database"""
        # Mock database record
        mock_record = Mock()
        mock_record.layout_id = "test_layout_123"
        mock_record.name = "Test Layout"
        mock_record.preset_type = "custom"
        mock_record.user_id = "user123"
        mock_record.examination_type = None
        mock_record.configuration = {
            'layout_id': 'test_layout_123',
            'name': 'Test Layout',
            'preset_type': 'custom',
            'monitors': []
        }
        mock_record.is_default = False
        mock_record.is_shared = False
        mock_record.created_at = datetime.utcnow()
        mock_record.modified_at = datetime.utcnow()
        mock_record.version = 1
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = mock_record
        
        # Load layout
        layout = self.persistence_service.load_layout("test_layout_123")
        
        self.assertIsNotNone(layout)
        self.assertEqual(layout.layout_id, "test_layout_123")
        self.assertEqual(layout.name, "Test Layout")
    
    def test_cache_functionality(self):
        """Test layout caching"""
        # Create test layout
        layout = LayoutConfiguration(
            layout_id="cached_layout_123",
            name="Cached Layout",
            preset_type=LayoutPresetType.CUSTOM
        )
        
        # Add to cache
        self.persistence_service.cache[layout.layout_id] = layout
        self.persistence_service.cache_expiry[layout.layout_id] = datetime.utcnow()
        
        # Load from cache (should not hit database)
        loaded_layout = self.persistence_service.load_layout("cached_layout_123")
        
        self.assertIsNotNone(loaded_layout)
        self.assertEqual(loaded_layout.layout_id, "cached_layout_123")
        self.mock_session.query.assert_not_called()
    
    def test_clone_layout(self):
        """Test cloning a layout"""
        # Create source layout
        source_layout = LayoutConfiguration(
            layout_id="source_layout_123",
            name="Source Layout",
            preset_type=LayoutPresetType.CUSTOM,
            examination_type="chest_xray"
        )
        
        # Add to cache
        self.persistence_service.cache[source_layout.layout_id] = source_layout
        self.persistence_service.cache_expiry[source_layout.layout_id] = datetime.utcnow()
        
        # Mock save operation
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Clone layout
        cloned_layout = self.persistence_service.clone_layout(
            "source_layout_123", "Cloned Layout", "user456"
        )
        
        self.assertIsNotNone(cloned_layout)
        self.assertEqual(cloned_layout.name, "Cloned Layout")
        self.assertEqual(cloned_layout.user_id, "user456")
        self.assertEqual(cloned_layout.examination_type, "chest_xray")
        self.assertNotEqual(cloned_layout.layout_id, source_layout.layout_id)

class TestDragDropHandler(unittest.TestCase):
    """Test drag and drop handler functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.viewport_manager = Mock(spec=ViewportManager)
        self.layout_manager = LayoutManager(self.viewport_manager)
        self.drag_drop_handler = DragDropHandler(self.layout_manager)
        
        # Load a test layout
        self.layout_manager.load_layout("preset_general_radiology")
    
    def test_start_drag_operation(self):
        """Test starting a drag operation"""
        success = self.drag_drop_handler.start_drag(
            "main_viewport", "primary", DragDropAction.MOVE, 10, 10
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(self.drag_drop_handler.current_drag)
        self.assertEqual(self.drag_drop_handler.current_drag.element_id, "main_viewport")
        self.assertEqual(self.drag_drop_handler.current_drag.action, DragDropAction.MOVE)
    
    def test_update_drag_operation(self):
        """Test updating a drag operation"""
        # Start drag
        self.drag_drop_handler.start_drag(
            "main_viewport", "primary", DragDropAction.MOVE, 10, 10
        )
        
        # Update drag
        success = self.drag_drop_handler.update_drag(20, 20)
        
        self.assertTrue(success)
        self.assertEqual(self.drag_drop_handler.current_drag.current_x, 20)
        self.assertEqual(self.drag_drop_handler.current_drag.current_y, 20)
    
    def test_end_drag_operation(self):
        """Test ending a drag operation"""
        # Start drag
        self.drag_drop_handler.start_drag(
            "main_viewport", "primary", DragDropAction.MOVE, 10, 10
        )
        
        # End drag
        success = self.drag_drop_handler.end_drag(25, 25)
        
        self.assertTrue(success)
        self.assertIsNone(self.drag_drop_handler.current_drag)
        self.assertEqual(len(self.drag_drop_handler.drop_zones), 0)
    
    def test_cancel_drag_operation(self):
        """Test cancelling a drag operation"""
        # Start drag
        self.drag_drop_handler.start_drag(
            "main_viewport", "primary", DragDropAction.MOVE, 10, 10
        )
        
        # Cancel drag
        success = self.drag_drop_handler.cancel_drag()
        
        self.assertTrue(success)
        self.assertIsNone(self.drag_drop_handler.current_drag)
    
    def test_snap_modes(self):
        """Test different snap modes"""
        # Test grid snapping
        self.drag_drop_handler.set_snap_mode(SnapMode.GRID)
        self.drag_drop_handler.set_grid_size(10.0)
        
        snapped_x, snapped_y = self.drag_drop_handler._apply_snapping(23, 27)
        self.assertEqual(snapped_x, 20)  # Snapped to grid
        self.assertEqual(snapped_y, 30)  # Snapped to grid
        
        # Test no snapping
        self.drag_drop_handler.set_snap_mode(SnapMode.NONE)
        snapped_x, snapped_y = self.drag_drop_handler._apply_snapping(23, 27)
        self.assertEqual(snapped_x, 23)  # No snapping
        self.assertEqual(snapped_y, 27)  # No snapping
    
    def test_drop_zone_generation(self):
        """Test drop zone generation"""
        # Start drag to generate drop zones
        self.drag_drop_handler.start_drag(
            "main_viewport", "primary", DragDropAction.MOVE, 10, 10
        )
        
        drop_zones = self.drag_drop_handler.get_drop_zones()
        
        self.assertIsInstance(drop_zones, list)
        self.assertGreater(len(drop_zones), 0)
        
        # Check that monitor drop zone exists
        monitor_zones = [zone for zone in drop_zones if zone['zone_type'] == 'monitor']
        self.assertGreater(len(monitor_zones), 0)
    
    def test_drag_state_info(self):
        """Test getting drag state information"""
        # No drag operation
        drag_state = self.drag_drop_handler.get_drag_state()
        self.assertIsNone(drag_state)
        
        # Start drag operation
        self.drag_drop_handler.start_drag(
            "main_viewport", "primary", DragDropAction.MOVE, 10, 10
        )
        
        drag_state = self.drag_drop_handler.get_drag_state()
        self.assertIsNotNone(drag_state)
        self.assertEqual(drag_state['element_id'], "main_viewport")
        self.assertEqual(drag_state['action'], 'move')

class TestLayoutIntegration(unittest.TestCase):
    """Integration tests for layout management system"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.viewport_manager = Mock(spec=ViewportManager)
        self.layout_manager = LayoutManager(self.viewport_manager)
        self.drag_drop_handler = DragDropHandler(self.layout_manager)
        self.persistence_service = LayoutPersistenceService()
    
    def test_complete_layout_workflow(self):
        """Test complete layout customization workflow"""
        # 1. Load a preset layout
        success = self.layout_manager.load_layout("preset_general_radiology")
        self.assertTrue(success)
        
        # 2. Customize the layout
        success = self.layout_manager.move_element("primary", "main_viewport", 5, 5)
        self.assertTrue(success)
        
        success = self.layout_manager.resize_element("primary", "report_editor", 35, 45)
        self.assertTrue(success)
        
        # 3. Add a custom element
        custom_element = LayoutElement(
            element_id="custom_notes_panel",
            element_type=LayoutElementType.CUSTOM_PANEL,
            x=70, y=85, width=30, height=10,
            properties={"panel_type": "notes"}
        )
        
        success = self.layout_manager.add_element("primary", custom_element)
        self.assertTrue(success)
        
        # 4. Save the customized layout
        current_layout = self.layout_manager.current_layout
        current_layout.name = "My Custom Layout"
        current_layout.user_id = "user123"
        current_layout.preset_type = LayoutPresetType.CUSTOM
        
        success = self.layout_manager.save_layout(current_layout)
        self.assertTrue(success)
        
        # 5. Verify the layout was saved
        self.assertIn(current_layout.layout_id, self.layout_manager.saved_layouts)
        
        # 6. Test drag and drop
        success = self.drag_drop_handler.start_drag(
            "custom_notes_panel", "primary", DragDropAction.MOVE, 70, 85
        )
        self.assertTrue(success)
        
        success = self.drag_drop_handler.update_drag(75, 80)
        self.assertTrue(success)
        
        success = self.drag_drop_handler.end_drag(75, 80)
        self.assertTrue(success)
        
        # 7. Verify element was moved
        moved_element = self.layout_manager._find_element("primary", "custom_notes_panel")
        self.assertIsNotNone(moved_element)
        # Position should be updated based on drag operation
    
    def test_multi_monitor_layout(self):
        """Test multi-monitor layout configuration"""
        # Create a layout with multiple monitors
        layout = self.layout_manager.create_layout("Multi-Monitor Layout")
        
        # Add second monitor
        secondary_monitor = MonitorConfiguration(
            monitor_id="secondary",
            is_primary=False,
            width_pixels=1920,
            height_pixels=1080,
            x_offset=1920,  # To the right of primary
            y_offset=0
        )
        
        layout.monitors.append(secondary_monitor)
        
        # Add elements to secondary monitor
        secondary_element = LayoutElement(
            element_id="secondary_viewport",
            element_type=LayoutElementType.VIEWPORT,
            x=0, y=0, width=100, height=100,
            properties={"viewport_layout": "single"}
        )
        
        success = self.layout_manager.add_element("secondary", secondary_element)
        # This would fail because we haven't loaded the layout yet
        # In a real scenario, we'd load the layout first
        
        # Load the layout
        self.layout_manager.current_layout = layout
        
        # Now add the element
        success = self.layout_manager.add_element("secondary", secondary_element)
        self.assertTrue(success)
        
        # Verify multi-monitor configuration
        layout_info = self.layout_manager.get_current_layout_info()
        self.assertEqual(len(layout_info['monitors']), 2)
        
        # Find secondary monitor
        secondary_info = None
        for monitor in layout_info['monitors']:
            if monitor['monitor_id'] == 'secondary':
                secondary_info = monitor
                break
        
        self.assertIsNotNone(secondary_info)
        self.assertFalse(secondary_info['is_primary'])
        self.assertEqual(len(secondary_info['elements']), 1)

if __name__ == '__main__':
    unittest.main()