"""
Performance tests for DICOM image handling and viewport management
"""

import unittest
import time
import threading
from unittest.mock import Mock, patch
import concurrent.futures

from services.dicom_image_service import DicomImageService
from services.viewport_manager import ViewportManager, ViewportLayout

class TestDicomImagePerformance(unittest.TestCase):
    """Performance tests for DICOM image service"""
    
    def setUp(self):
        """Set up performance test fixtures"""
        self.service = DicomImageService()
        
        # Mock dependencies for consistent performance testing
        self.mock_cache = Mock()
        self.mock_offline_manager = Mock()
        self.mock_orthanc_client = Mock()
        
        self.service.cache_service = self.mock_cache
        self.service.offline_manager = self.mock_offline_manager
        
        # Mock image data of various sizes
        self.small_image = b"x" * (1024 * 100)  # 100KB
        self.medium_image = b"x" * (1024 * 1024)  # 1MB
        self.large_image = b"x" * (1024 * 1024 * 5)  # 5MB
    
    def test_cached_image_load_performance(self):
        """Test performance of cached image loading"""
        study_id = "perf_study"
        series_id = "perf_series"
        
        # Test with different image sizes
        test_cases = [
            ("small", self.small_image),
            ("medium", self.medium_image),
            ("large", self.large_image)
        ]
        
        for size_name, image_data in test_cases:
            with self.subTest(size=size_name):
                instance_id = f"instance_{size_name}"
                metadata = {"WindowCenter": 128, "WindowWidth": 256}
                
                self.mock_cache.get_cached_dicom_image.return_value = (image_data, metadata)
                
                # Measure load time
                start_time = time.time()
                result = self.service.load_image(study_id, series_id, instance_id)
                end_time = time.time()
                
                load_time = end_time - start_time
                
                self.assertEqual(result, image_data)
                self.assertLess(load_time, 0.1, f"Cached {size_name} image load took too long: {load_time:.3f}s")
    
    def test_concurrent_image_loading(self):
        """Test concurrent image loading performance"""
        study_id = "concurrent_study"
        series_id = "concurrent_series"
        
        # Mock cached images
        def mock_get_cached_image(study_id, series_id, instance_id):
            # Simulate some processing time
            time.sleep(0.01)
            return (self.medium_image, {"WindowCenter": 128})
        
        self.mock_cache.get_cached_dicom_image.side_effect = mock_get_cached_image
        
        # Load multiple images concurrently
        num_images = 10
        instance_ids = [f"instance_{i}" for i in range(num_images)]
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for instance_id in instance_ids:
                future = executor.submit(
                    self.service.load_image, study_id, series_id, instance_id
                )
                futures.append(future)
            
            # Wait for all to complete
            results = [future.result() for future in futures]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All images should be loaded
        self.assertEqual(len(results), num_images)
        for result in results:
            self.assertEqual(result, self.medium_image)
        
        # Should be faster than sequential loading
        expected_sequential_time = num_images * 0.01
        self.assertLess(total_time, expected_sequential_time * 0.8, 
                       f"Concurrent loading not efficient: {total_time:.3f}s vs expected < {expected_sequential_time * 0.8:.3f}s")
    
    def test_prefetch_performance(self):
        """Test prefetch performance"""
        study_id = "prefetch_study"
        series_id = "prefetch_series"
        
        # Mock series with multiple instances
        mock_instances = [{'ID': f'instance_{i}'} for i in range(20)]
        
        self.mock_offline_manager.is_service_available.return_value = True
        self.mock_cache.get_cached_dicom_image.return_value = None
        
        with patch('services.dicom_image_service.orthanc_client', self.mock_orthanc_client):
            self.mock_orthanc_client.get_series_instances.return_value = mock_instances
            
            start_time = time.time()
            self.service.prefetch_images(study_id, series_id, 10, 20)
            end_time = time.time()
            
            prefetch_setup_time = end_time - start_time
            
            # Prefetch setup should be fast
            self.assertLess(prefetch_setup_time, 0.1, 
                           f"Prefetch setup took too long: {prefetch_setup_time:.3f}s")
            
            # Should have items in prefetch queue
            self.assertGreater(len(self.service._prefetch_queue), 0)
    
    def test_memory_usage_with_large_images(self):
        """Test memory usage with large images"""
        study_id = "memory_study"
        series_id = "memory_series"
        
        # Load multiple large images
        num_images = 5
        for i in range(num_images):
            instance_id = f"large_instance_{i}"
            metadata = {"WindowCenter": 128, "WindowWidth": 256}
            
            self.mock_cache.get_cached_dicom_image.return_value = (self.large_image, metadata)
            
            result = self.service.load_image(study_id, series_id, instance_id)
            self.assertEqual(result, self.large_image)
        
        # Test that metrics are being tracked
        metrics = self.service.get_performance_metrics()
        self.assertEqual(metrics['cache_hits'], num_images)
        self.assertEqual(metrics['total_loads'], num_images)

class TestViewportManagerPerformance(unittest.TestCase):
    """Performance tests for viewport manager"""
    
    def setUp(self):
        """Set up viewport performance test fixtures"""
        self.manager = ViewportManager()
    
    def test_layout_switching_performance(self):
        """Test performance of layout switching"""
        layouts = [
            ViewportLayout.SINGLE,
            ViewportLayout.DUAL_HORIZONTAL,
            ViewportLayout.DUAL_VERTICAL,
            ViewportLayout.QUAD
        ]
        
        for layout in layouts:
            with self.subTest(layout=layout):
                start_time = time.time()
                success = self.manager.set_layout(layout)
                end_time = time.time()
                
                switch_time = end_time - start_time
                
                self.assertTrue(success)
                self.assertLess(switch_time, 0.05, 
                               f"Layout switch to {layout.value} took too long: {switch_time:.3f}s")
    
    def test_viewport_manipulation_performance(self):
        """Test performance of viewport manipulations"""
        self.manager.set_layout(ViewportLayout.QUAD)
        viewport_ids = list(self.manager.viewports.keys())
        
        from services.viewport_manager import ImageManipulation
        
        manipulations = [
            ImageManipulation.ZOOM_IN,
            ImageManipulation.ZOOM_OUT,
            ImageManipulation.PAN,
            ImageManipulation.WINDOW_LEVEL,
            ImageManipulation.ROTATE,
            ImageManipulation.RESET
        ]
        
        # Test manipulation performance on all viewports
        start_time = time.time()
        
        for viewport_id in viewport_ids:
            for manipulation in manipulations:
                if manipulation == ImageManipulation.PAN:
                    value = {'x': 10, 'y': -5}
                elif manipulation == ImageManipulation.WINDOW_LEVEL:
                    value = {'center': 128, 'width': 256}
                else:
                    value = None
                
                success = self.manager.apply_image_manipulation(viewport_id, manipulation, value)
                self.assertTrue(success)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        total_operations = len(viewport_ids) * len(manipulations)
        avg_time_per_operation = total_time / total_operations
        
        self.assertLess(avg_time_per_operation, 0.001, 
                       f"Average manipulation time too slow: {avg_time_per_operation:.4f}s per operation")
    
    def test_concurrent_viewport_updates(self):
        """Test concurrent viewport updates"""
        self.manager.set_layout(ViewportLayout.QUAD)
        viewport_ids = list(self.manager.viewports.keys())
        
        def update_viewport(viewport_id):
            """Update a viewport with multiple manipulations"""
            from services.viewport_manager import ImageManipulation
            
            manipulations = [
                (ImageManipulation.ZOOM_IN, None),
                (ImageManipulation.PAN, {'x': 5, 'y': -3}),
                (ImageManipulation.WINDOW_LEVEL, {'center': 100, 'width': 200}),
                (ImageManipulation.ROTATE, 45)
            ]
            
            for manipulation, value in manipulations:
                success = self.manager.apply_image_manipulation(viewport_id, manipulation, value)
                if not success:
                    return False
            return True
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for viewport_id in viewport_ids:
                future = executor.submit(update_viewport, viewport_id)
                futures.append(future)
            
            results = [future.result() for future in futures]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All updates should succeed
        self.assertTrue(all(results))
        
        # Should complete quickly
        self.assertLess(total_time, 0.1, 
                       f"Concurrent viewport updates took too long: {total_time:.3f}s")
    
    def test_large_number_of_viewports(self):
        """Test performance with large number of viewports"""
        # Create custom layout with many viewports
        from services.viewport_manager import LayoutConfiguration, ViewportLayout
        
        num_viewports = 16
        viewport_positions = []
        
        # Create 4x4 grid
        for row in range(4):
            for col in range(4):
                viewport_positions.append({
                    "x": col * 25,
                    "y": row * 25,
                    "width": 25,
                    "height": 25
                })
        
        custom_config = LayoutConfiguration(
            layout_type=ViewportLayout.CUSTOM,
            viewport_count=num_viewports,
            viewport_positions=viewport_positions,
            name="16-Panel Grid",
            is_custom=True
        )
        
        start_time = time.time()
        success = self.manager.set_layout(ViewportLayout.CUSTOM, custom_config)
        end_time = time.time()
        
        setup_time = end_time - start_time
        
        self.assertTrue(success)
        self.assertEqual(len(self.manager.viewports), num_viewports)
        self.assertLess(setup_time, 0.1, 
                       f"Large viewport setup took too long: {setup_time:.3f}s")
        
        # Test getting layout info performance
        start_time = time.time()
        layout_info = self.manager.get_layout_info()
        end_time = time.time()
        
        info_time = end_time - start_time
        
        self.assertEqual(layout_info['viewport_count'], num_viewports)
        self.assertLess(info_time, 0.05, 
                       f"Getting layout info took too long: {info_time:.3f}s")

class TestIntegratedPerformance(unittest.TestCase):
    """Integrated performance tests"""
    
    def setUp(self):
        """Set up integrated performance test fixtures"""
        self.dicom_service = DicomImageService()
        self.viewport_manager = ViewportManager()
        
        # Mock dependencies
        self.mock_cache = Mock()
        self.mock_offline_manager = Mock()
        
        self.dicom_service.cache_service = self.mock_cache
        self.dicom_service.offline_manager = self.mock_offline_manager
        
        # Mock image data
        self.test_image = b"x" * (1024 * 1024)  # 1MB test image
    
    def test_full_workflow_performance(self):
        """Test performance of complete image loading and display workflow"""
        # Set up quad layout
        self.viewport_manager.set_layout(ViewportLayout.QUAD)
        viewport_ids = list(self.viewport_manager.viewports.keys())
        
        # Mock cached images
        def mock_get_cached_image(study_id, series_id, instance_id):
            return (self.test_image, {"WindowCenter": 128, "WindowWidth": 256})
        
        self.mock_cache.get_cached_dicom_image.side_effect = mock_get_cached_image
        
        start_time = time.time()
        
        # Load images to all viewports
        with patch('services.viewport_manager.dicom_image_service', self.dicom_service):
            for i, viewport_id in enumerate(viewport_ids):
                success = self.viewport_manager.load_image_to_viewport(
                    viewport_id, f"study_{i}", f"series_{i}", f"instance_{i}"
                )
                self.assertTrue(success)
        
        # Apply manipulations to all viewports
        from services.viewport_manager import ImageManipulation
        
        for viewport_id in viewport_ids:
            self.viewport_manager.apply_image_manipulation(viewport_id, ImageManipulation.ZOOM_IN)
            self.viewport_manager.apply_image_manipulation(
                viewport_id, ImageManipulation.PAN, {'x': 10, 'y': -5}
            )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Complete workflow should be fast
        self.assertLess(total_time, 0.5, 
                       f"Complete workflow took too long: {total_time:.3f}s")
        
        # Verify all viewports have images loaded
        for i, viewport_id in enumerate(viewport_ids):
            viewport = self.viewport_manager.viewports[viewport_id]
            self.assertEqual(viewport.study_id, f"study_{i}")
            self.assertGreater(viewport.zoom_level, 1.0)
            self.assertEqual(viewport.pan_x, 10)
            self.assertEqual(viewport.pan_y, -5)

if __name__ == '__main__':
    # Run performance tests with timing
    start_time = time.time()
    unittest.main(verbosity=2)
    end_time = time.time()
    print(f"\nTotal test execution time: {end_time - start_time:.2f} seconds")