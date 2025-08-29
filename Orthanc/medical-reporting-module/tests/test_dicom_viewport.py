"""
Tests for DICOM image handling and viewport management
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import threading
import time
from datetime import datetime

from services.dicom_image_service import DicomImageService, dicom_image_service
from services.viewport_manager import (
    ViewportManager, ViewportLayout, ImageManipulation, 
    ViewportState, LayoutConfiguration, viewport_manager
)

class TestDicomImageService(unittest.TestCase):
    """Test DICOM image service functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.service = DicomImageService()
        
        # Mock dependencies
        self.mock_cache = Mock()
        self.mock_offline_manager = Mock()
        self.mock_orthanc_client = Mock()
        
        self.service.cache_service = self.mock_cache
        self.service.offline_manager = self.mock_offline_manager
    
    def test_load_study_images_cached(self):
        """Test loading study images from cache"""
        study_id = "test_study_123"
        cached_metadata = {
            'study_id': study_id,
            'series': [{'series_id': 'series_1', 'instances': []}],
            'LastUpdate': '2024-01-01T00:00:00Z'
        }
        
        self.mock_cache.get_cached_dicom_metadata.return_value = cached_metadata
        self.mock_offline_manager.is_online.return_value = True
        self.mock_offline_manager.is_service_available.return_value = True
        
        with patch('services.dicom_image_service.orthanc_client', self.mock_orthanc_client):
            self.mock_orthanc_client.get_study_details.return_value = None
            
            result = self.service.load_study_images(study_id)
            
            self.assertIn('study_id', result)
            self.assertEqual(result['study_id'], study_id)
            self.assertTrue(result['cached'])
    
    def test_load_study_images_server(self):
        """Test loading study images from server"""
        study_id = "test_study_456"
        server_data = {
            'study_id': study_id,
            'series': [{'series_id': 'series_1', 'instances': []}],
            'LastUpdate': '2024-01-02T00:00:00Z'
        }
        
        self.mock_cache.get_cached_dicom_metadata.return_value = None
        self.mock_offline_manager.is_service_available.return_value = True
        
        with patch('services.dicom_image_service.orthanc_client', self.mock_orthanc_client):
            self.mock_orthanc_client.get_study_details.return_value = server_data
            self.mock_orthanc_client.get_study_series.return_value = []
            
            result = self.service.load_study_images(study_id)
            
            self.assertIn('study_id', result)
            self.assertEqual(result['study_id'], study_id)
            self.assertFalse(result.get('cached', True))
    
    def test_load_image_cached(self):
        """Test loading individual image from cache"""
        study_id = "study_1"
        series_id = "series_1"
        instance_id = "instance_1"
        
        mock_image_data = b"mock_dicom_image_data"
        mock_metadata = {"WindowCenter": 128, "WindowWidth": 256}
        
        self.mock_cache.get_cached_dicom_image.return_value = (mock_image_data, mock_metadata)
        
        result = self.service.load_image(study_id, series_id, instance_id)
        
        self.assertEqual(result, mock_image_data)
        self.assertEqual(self.service.metrics['cache_hits'], 1)
    
    def test_load_image_with_callback(self):
        """Test loading image with callback"""
        study_id = "study_1"
        series_id = "series_1"
        instance_id = "instance_1"
        
        mock_image_data = b"mock_dicom_image_data"
        mock_metadata = {"WindowCenter": 128, "WindowWidth": 256}
        
        callback_called = threading.Event()
        callback_result = {}
        
        def test_callback(image_data, metadata):
            callback_result['image_data'] = image_data
            callback_result['metadata'] = metadata
            callback_called.set()
        
        self.mock_cache.get_cached_dicom_image.return_value = (mock_image_data, mock_metadata)
        
        result = self.service.load_image(study_id, series_id, instance_id, callback=test_callback)
        
        # Should return image data immediately for cached images
        self.assertEqual(result, mock_image_data)
        
        # Callback should still be called
        callback_called.wait(timeout=1.0)
        self.assertTrue(callback_called.is_set())
        self.assertEqual(callback_result['image_data'], mock_image_data)
    
    def test_prefetch_images(self):
        """Test image prefetching"""
        study_id = "study_1"
        series_id = "series_1"
        current_index = 5
        total_instances = 10
        
        mock_instances = [
            {'ID': f'instance_{i}'} for i in range(total_instances)
        ]
        
        self.mock_offline_manager.is_service_available.return_value = True
        self.mock_cache.get_cached_dicom_image.return_value = None
        
        with patch('services.dicom_image_service.orthanc_client', self.mock_orthanc_client):
            self.mock_orthanc_client.get_series_instances.return_value = mock_instances
            
            self.service.prefetch_images(study_id, series_id, current_index, total_instances)
            
            # Should have items in prefetch queue
            self.assertGreater(len(self.service._prefetch_queue), 0)
    
    def test_get_performance_metrics(self):
        """Test performance metrics collection"""
        # Add some test data
        self.service.metrics['cache_hits'] = 10
        self.service.metrics['cache_misses'] = 5
        self.service.metrics['load_times'] = [0.1, 0.2, 0.15, 0.3]
        
        metrics = self.service.get_performance_metrics()
        
        self.assertEqual(metrics['cache_hits'], 10)
        self.assertEqual(metrics['cache_misses'], 5)
        self.assertAlmostEqual(metrics['cache_hit_rate'], 10/15)
        self.assertAlmostEqual(metrics['average_load_time'], 0.1875)
        self.assertEqual(metrics['total_loads'], 4)

class TestViewportManager(unittest.TestCase):
    """Test viewport manager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = ViewportManager()
    
    def test_single_viewport_layout(self):
        """Test single viewport layout"""
        success = self.manager.set_layout(ViewportLayout.SINGLE)
        
        self.assertTrue(success)
        self.assertEqual(len(self.manager.viewports), 1)
        self.assertEqual(self.manager.current_layout, ViewportLayout.SINGLE)
        self.assertIsNotNone(self.manager.active_viewport_id)
    
    def test_quad_viewport_layout(self):
        """Test quad viewport layout"""
        success = self.manager.set_layout(ViewportLayout.QUAD)
        
        self.assertTrue(success)
        self.assertEqual(len(self.manager.viewports), 4)
        self.assertEqual(self.manager.current_layout, ViewportLayout.QUAD)
    
    def test_set_active_viewport(self):
        """Test setting active viewport"""
        self.manager.set_layout(ViewportLayout.DUAL_HORIZONTAL)
        
        viewport_ids = list(self.manager.viewports.keys())
        second_viewport = viewport_ids[1]
        
        success = self.manager.set_active_viewport(second_viewport)
        
        self.assertTrue(success)
        self.assertEqual(self.manager.active_viewport_id, second_viewport)
        self.assertTrue(self.manager.viewports[second_viewport].is_active)
    
    def test_load_image_to_viewport(self):
        """Test loading image to viewport"""
        self.manager.set_layout(ViewportLayout.SINGLE)
        viewport_id = list(self.manager.viewports.keys())[0]
        
        study_id = "study_1"
        series_id = "series_1"
        instance_id = "instance_1"
        
        with patch('services.viewport_manager.dicom_image_service') as mock_service:
            success = self.manager.load_image_to_viewport(
                viewport_id, study_id, series_id, instance_id
            )
            
            self.assertTrue(success)
            
            viewport = self.manager.viewports[viewport_id]
            self.assertEqual(viewport.study_id, study_id)
            self.assertEqual(viewport.series_id, series_id)
            self.assertEqual(viewport.instance_id, instance_id)
            self.assertTrue(viewport.is_loading)
            
            # Verify DICOM service was called
            mock_service.load_image.assert_called_once()
    
    def test_image_manipulation_zoom(self):
        """Test image zoom manipulation"""
        self.manager.set_layout(ViewportLayout.SINGLE)
        viewport_id = list(self.manager.viewports.keys())[0]
        
        # Test zoom in
        success = self.manager.apply_image_manipulation(
            viewport_id, ImageManipulation.ZOOM_IN
        )
        
        self.assertTrue(success)
        viewport = self.manager.viewports[viewport_id]
        self.assertGreater(viewport.zoom_level, 1.0)
        
        # Test zoom out
        original_zoom = viewport.zoom_level
        success = self.manager.apply_image_manipulation(
            viewport_id, ImageManipulation.ZOOM_OUT
        )
        
        self.assertTrue(success)
        self.assertLess(viewport.zoom_level, original_zoom)
    
    def test_image_manipulation_pan(self):
        """Test image pan manipulation"""
        self.manager.set_layout(ViewportLayout.SINGLE)
        viewport_id = list(self.manager.viewports.keys())[0]
        
        pan_value = {'x': 10, 'y': -5}
        success = self.manager.apply_image_manipulation(
            viewport_id, ImageManipulation.PAN, pan_value
        )
        
        self.assertTrue(success)
        viewport = self.manager.viewports[viewport_id]
        self.assertEqual(viewport.pan_x, 10)
        self.assertEqual(viewport.pan_y, -5)
    
    def test_image_manipulation_window_level(self):
        """Test window/level manipulation"""
        self.manager.set_layout(ViewportLayout.SINGLE)
        viewport_id = list(self.manager.viewports.keys())[0]
        
        wl_value = {'center': 128, 'width': 256}
        success = self.manager.apply_image_manipulation(
            viewport_id, ImageManipulation.WINDOW_LEVEL, wl_value
        )
        
        self.assertTrue(success)
        viewport = self.manager.viewports[viewport_id]
        self.assertEqual(viewport.window_center, 128)
        self.assertEqual(viewport.window_width, 256)
    
    def test_image_manipulation_reset(self):
        """Test image manipulation reset"""
        self.manager.set_layout(ViewportLayout.SINGLE)
        viewport_id = list(self.manager.viewports.keys())[0]
        
        # Apply some manipulations first
        viewport = self.manager.viewports[viewport_id]
        viewport.zoom_level = 2.0
        viewport.pan_x = 50
        viewport.pan_y = -30
        viewport.rotation = 90
        viewport.flip_horizontal = True
        
        # Reset
        success = self.manager.apply_image_manipulation(
            viewport_id, ImageManipulation.RESET
        )
        
        self.assertTrue(success)
        self.assertEqual(viewport.zoom_level, 1.0)
        self.assertEqual(viewport.pan_x, 0.0)
        self.assertEqual(viewport.pan_y, 0.0)
        self.assertEqual(viewport.rotation, 0.0)
        self.assertFalse(viewport.flip_horizontal)
        self.assertFalse(viewport.flip_vertical)
    
    def test_clear_viewport(self):
        """Test clearing viewport"""
        self.manager.set_layout(ViewportLayout.SINGLE)
        viewport_id = list(self.manager.viewports.keys())[0]
        
        # Set some data first
        viewport = self.manager.viewports[viewport_id]
        viewport.study_id = "study_1"
        viewport.series_id = "series_1"
        viewport.instance_id = "instance_1"
        viewport.zoom_level = 2.0
        
        success = self.manager.clear_viewport(viewport_id)
        
        self.assertTrue(success)
        self.assertIsNone(viewport.study_id)
        self.assertIsNone(viewport.series_id)
        self.assertIsNone(viewport.instance_id)
        self.assertEqual(viewport.zoom_level, 1.0)
    
    def test_custom_layout(self):
        """Test custom layout creation"""
        custom_positions = [
            {"x": 0, "y": 0, "width": 60, "height": 100},
            {"x": 60, "y": 0, "width": 40, "height": 50},
            {"x": 60, "y": 50, "width": 40, "height": 50}
        ]
        
        custom_config = LayoutConfiguration(
            layout_type=ViewportLayout.CUSTOM,
            viewport_count=3,
            viewport_positions=custom_positions,
            name="Custom 3-Panel",
            is_custom=True
        )
        
        success = self.manager.set_layout(ViewportLayout.CUSTOM, custom_config)
        
        self.assertTrue(success)
        self.assertEqual(len(self.manager.viewports), 3)
        self.assertEqual(self.manager.current_layout, ViewportLayout.CUSTOM)
    
    def test_viewport_callbacks(self):
        """Test viewport change callbacks"""
        callback_called = threading.Event()
        callback_data = {}
        
        def test_callback(viewport_id, change_type, viewport_state):
            callback_data['viewport_id'] = viewport_id
            callback_data['change_type'] = change_type
            callback_data['viewport_state'] = viewport_state
            callback_called.set()
        
        self.manager.add_viewport_change_callback(test_callback)
        self.manager.set_layout(ViewportLayout.SINGLE)
        
        viewport_id = list(self.manager.viewports.keys())[0]
        self.manager.apply_image_manipulation(viewport_id, ImageManipulation.ZOOM_IN)
        
        callback_called.wait(timeout=1.0)
        self.assertTrue(callback_called.is_set())
        self.assertEqual(callback_data['viewport_id'], viewport_id)
        self.assertEqual(callback_data['change_type'], 'manipulation_applied')
    
    def test_get_layout_info(self):
        """Test getting layout information"""
        self.manager.set_layout(ViewportLayout.DUAL_HORIZONTAL)
        
        layout_info = self.manager.get_layout_info()
        
        self.assertEqual(layout_info['current_layout'], ViewportLayout.DUAL_HORIZONTAL.value)
        self.assertEqual(layout_info['viewport_count'], 2)
        self.assertIn('viewports', layout_info)
        self.assertIn('layout_config', layout_info)
    
    def test_get_available_layouts(self):
        """Test getting available layouts"""
        layouts = self.manager.get_available_layouts()
        
        self.assertIsInstance(layouts, list)
        self.assertGreater(len(layouts), 0)
        
        # Check that all default layouts are included
        layout_types = [layout['type'] for layout in layouts]
        self.assertIn(ViewportLayout.SINGLE.value, layout_types)
        self.assertIn(ViewportLayout.DUAL_HORIZONTAL.value, layout_types)
        self.assertIn(ViewportLayout.QUAD.value, layout_types)

class TestIntegration(unittest.TestCase):
    """Integration tests for DICOM and viewport components"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.dicom_service = DicomImageService()
        self.viewport_manager = ViewportManager()
        
        # Mock external dependencies
        self.mock_cache = Mock()
        self.mock_offline_manager = Mock()
        self.mock_orthanc_client = Mock()
        
        self.dicom_service.cache_service = self.mock_cache
        self.dicom_service.offline_manager = self.mock_offline_manager
    
    def test_full_image_loading_workflow(self):
        """Test complete image loading workflow"""
        # Set up viewport
        self.viewport_manager.set_layout(ViewportLayout.SINGLE)
        viewport_id = list(self.viewport_manager.viewports.keys())[0]
        
        # Mock image data
        mock_image_data = b"mock_dicom_image_data"
        mock_metadata = {"WindowCenter": 128, "WindowWidth": 256}
        
        self.mock_cache.get_cached_dicom_image.return_value = (mock_image_data, mock_metadata)
        
        # Load image to viewport
        with patch('services.viewport_manager.dicom_image_service', self.dicom_service):
            success = self.viewport_manager.load_image_to_viewport(
                viewport_id, "study_1", "series_1", "instance_1"
            )
            
            self.assertTrue(success)
            
            # Verify viewport state
            viewport = self.viewport_manager.viewports[viewport_id]
            self.assertEqual(viewport.study_id, "study_1")
            self.assertEqual(viewport.series_id, "series_1")
            self.assertEqual(viewport.instance_id, "instance_1")
    
    def test_multi_viewport_image_loading(self):
        """Test loading different images to multiple viewports"""
        # Set up quad layout
        self.viewport_manager.set_layout(ViewportLayout.QUAD)
        viewport_ids = list(self.viewport_manager.viewports.keys())
        
        # Mock different images for each viewport
        def mock_get_cached_image(study_id, series_id, instance_id):
            return (f"image_data_{instance_id}".encode(), {"WindowCenter": 128})
        
        self.mock_cache.get_cached_dicom_image.side_effect = mock_get_cached_image
        
        # Load different images to each viewport
        with patch('services.viewport_manager.dicom_image_service', self.dicom_service):
            for i, viewport_id in enumerate(viewport_ids):
                success = self.viewport_manager.load_image_to_viewport(
                    viewport_id, f"study_{i}", f"series_{i}", f"instance_{i}"
                )
                self.assertTrue(success)
        
        # Verify each viewport has different image
        for i, viewport_id in enumerate(viewport_ids):
            viewport = self.viewport_manager.viewports[viewport_id]
            self.assertEqual(viewport.study_id, f"study_{i}")
            self.assertEqual(viewport.series_id, f"series_{i}")
            self.assertEqual(viewport.instance_id, f"instance_{i}")

if __name__ == '__main__':
    unittest.main()