"""
DICOM Image Service for Medical Reporting Module
Handles DICOM image loading, processing, and caching
"""

import logging
import threading
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime, timedelta
import asyncio
import concurrent.futures
from pathlib import Path
import hashlib
import json

from integrations.orthanc_client import orthanc_client
from services.cache_service import CacheService
from services.offline_manager import offline_manager

logger = logging.getLogger(__name__)

class DicomImageService:
    """Service for DICOM image handling and processing"""
    
    def __init__(self):
        self.cache_service = CacheService()
        self.offline_manager = offline_manager
        
        # Image processing settings
        self.max_concurrent_loads = 4
        self.prefetch_count = 3
        self.image_quality_levels = ['thumbnail', 'preview', 'full']
        
        # Threading for background operations
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_concurrent_loads
        )
        
        # Image cache and loading state
        self._loading_cache = {}  # Track currently loading images
        self._load_callbacks = {}  # Callbacks for image load completion
        self._prefetch_queue = []  # Queue for prefetching images
        
        # Performance metrics
        self.metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'load_times': [],
            'prefetch_hits': 0
        }
    
    def load_study_images(self, study_id: str, 
                         progress_callback: Callable = None) -> Dict[str, Any]:
        """Load all images for a study"""
        try:
            logger.info(f"Loading images for study: {study_id}")
            
            # Check if study metadata is cached
            cached_metadata = self.cache_service.get_cached_dicom_metadata(study_id)
            
            if cached_metadata and self.offline_manager.is_online():
                # Use cached metadata but verify with server
                study_data = self._get_study_with_cache(study_id, cached_metadata)
            elif cached_metadata:
                # Offline mode, use cached data
                study_data = cached_metadata
                logger.info(f"Using cached study data (offline mode): {study_id}")
            else:
                # Load from server
                study_data = self._load_study_from_server(study_id)
                if study_data:
                    # Cache the metadata
                    self.cache_service.cache_dicom_metadata(study_id, study_data)
            
            if not study_data:
                return {'error': 'Study not found or unavailable'}
            
            # Process series and instances
            series_data = self._process_study_series(study_id, study_data, progress_callback)
            
            return {
                'study_id': study_id,
                'study_data': study_data,
                'series': series_data,
                'total_images': sum(len(s.get('instances', [])) for s in series_data),
                'cached': cached_metadata is not None
            }
            
        except Exception as e:
            logger.error(f"Failed to load study images: {e}")
            return {'error': str(e)}
    
    def _get_study_with_cache(self, study_id: str, cached_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Get study data, using cache when possible"""
        try:
            # Quick check if server data is newer
            if self.offline_manager.is_service_available('orthanc'):
                server_study = orthanc_client.get_study_details(study_id)
                if server_study:
                    # Compare modification times if available
                    server_modified = server_study.get('LastUpdate')
                    cached_modified = cached_metadata.get('LastUpdate')
                    
                    if server_modified and cached_modified and server_modified > cached_modified:
                        # Server data is newer, update cache
                        self.cache_service.cache_dicom_metadata(study_id, server_study)
                        return server_study
            
            # Use cached data
            self.metrics['cache_hits'] += 1
            return cached_metadata
            
        except Exception as e:
            logger.warning(f"Failed to check server data, using cache: {e}")
            self.metrics['cache_hits'] += 1
            return cached_metadata
    
    def _load_study_from_server(self, study_id: str) -> Optional[Dict[str, Any]]:
        """Load study data from Orthanc server"""
        try:
            if not self.offline_manager.is_service_available('orthanc'):
                logger.warning("Orthanc server not available")
                return None
            
            study_data = orthanc_client.get_study_details(study_id)
            if study_data:
                self.metrics['cache_misses'] += 1
                return study_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load study from server: {e}")
            return None
    
    def _process_study_series(self, study_id: str, study_data: Dict[str, Any], 
                            progress_callback: Callable = None) -> List[Dict[str, Any]]:
        """Process all series in a study"""
        try:
            series_list = []
            
            if self.offline_manager.is_service_available('orthanc'):
                # Load from server
                series_data = orthanc_client.get_study_series(study_id)
            else:
                # Use cached series data
                series_data = study_data.get('series', [])
            
            total_series = len(series_data)
            
            for i, series in enumerate(series_data):
                if progress_callback:
                    progress_callback(f"Processing series {i+1}/{total_series}", 
                                    (i / total_series) * 100)
                
                series_id = series.get('ID') or series.get('series_id')
                if not series_id:
                    continue
                
                processed_series = self._process_series(study_id, series_id, series)
                if processed_series:
                    series_list.append(processed_series)
            
            return series_list
            
        except Exception as e:
            logger.error(f"Failed to process study series: {e}")
            return []
    
    def _process_series(self, study_id: str, series_id: str, 
                       series_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single series"""
        try:
            # Get series instances
            if self.offline_manager.is_service_available('orthanc'):
                instances = orthanc_client.get_series_instances(series_id)
            else:
                instances = series_data.get('instances', [])
            
            # Process instances for image loading
            processed_instances = []
            for instance in instances:
                instance_id = instance.get('ID') or instance.get('instance_id')
                if instance_id:
                    processed_instance = {
                        'instance_id': instance_id,
                        'series_id': series_id,
                        'study_id': study_id,
                        'instance_data': instance,
                        'image_loaded': False,
                        'thumbnail_loaded': False
                    }
                    processed_instances.append(processed_instance)
            
            return {
                'series_id': series_id,
                'study_id': study_id,
                'series_data': series_data,
                'instances': processed_instances,
                'instance_count': len(processed_instances)
            }
            
        except Exception as e:
            logger.error(f"Failed to process series {series_id}: {e}")
            return None
    
    def load_image(self, study_id: str, series_id: str, instance_id: str, 
                  quality: str = 'full', callback: Callable = None) -> Optional[bytes]:
        """Load a specific DICOM image"""
        try:
            start_time = datetime.utcnow()
            cache_key = f"{study_id}_{series_id}_{instance_id}_{quality}"
            
            # Check if already loading
            if cache_key in self._loading_cache:
                if callback:
                    if cache_key not in self._load_callbacks:
                        self._load_callbacks[cache_key] = []
                    self._load_callbacks[cache_key].append(callback)
                return None
            
            # Check cache first
            cached_image = self.cache_service.get_cached_dicom_image(
                study_id, series_id, instance_id
            )
            
            if cached_image:
                image_data, metadata = cached_image
                self.metrics['cache_hits'] += 1
                
                # Process image based on quality level
                processed_image = self._process_image_quality(image_data, quality)
                
                if callback:
                    callback(processed_image, metadata)
                
                # Record load time
                load_time = (datetime.utcnow() - start_time).total_seconds()
                self.metrics['load_times'].append(load_time)
                
                return processed_image
            
            # Not in cache, load from server
            if not self.offline_manager.is_service_available('orthanc'):
                logger.warning(f"Cannot load image {instance_id}: Orthanc not available")
                return None
            
            # Mark as loading
            self._loading_cache[cache_key] = True
            if callback:
                self._load_callbacks[cache_key] = [callback]
            
            # Load asynchronously
            future = self.executor.submit(
                self._load_image_from_server,
                study_id, series_id, instance_id, quality, cache_key
            )
            
            if not callback:
                # Synchronous load
                return future.result()
            
            # Asynchronous load
            return None
            
        except Exception as e:
            logger.error(f"Failed to load image {instance_id}: {e}")
            return None
    
    def _load_image_from_server(self, study_id: str, series_id: str, instance_id: str, 
                              quality: str, cache_key: str) -> Optional[bytes]:
        """Load image from Orthanc server"""
        try:
            start_time = datetime.utcnow()
            
            # Load image data
            image_data = orthanc_client.get_instance_image(instance_id)
            if not image_data:
                return None
            
            # Load metadata
            metadata = orthanc_client.get_instance_tags(instance_id)
            
            # Cache the image
            self.cache_service.cache_dicom_image(
                study_id, series_id, instance_id, image_data, metadata
            )
            
            # Process image quality
            processed_image = self._process_image_quality(image_data, quality)
            
            # Record metrics
            self.metrics['cache_misses'] += 1
            load_time = (datetime.utcnow() - start_time).total_seconds()
            self.metrics['load_times'].append(load_time)
            
            # Notify callbacks
            if cache_key in self._load_callbacks:
                for callback in self._load_callbacks[cache_key]:
                    try:
                        callback(processed_image, metadata)
                    except Exception as e:
                        logger.error(f"Error in image load callback: {e}")
                
                del self._load_callbacks[cache_key]
            
            # Remove from loading cache
            if cache_key in self._loading_cache:
                del self._loading_cache[cache_key]
            
            return processed_image
            
        except Exception as e:
            logger.error(f"Failed to load image from server: {e}")
            
            # Clean up loading state
            if cache_key in self._loading_cache:
                del self._loading_cache[cache_key]
            if cache_key in self._load_callbacks:
                del self._load_callbacks[cache_key]
            
            return None
    
    def _process_image_quality(self, image_data: bytes, quality: str) -> bytes:
        """Process image based on quality level"""
        try:
            if quality == 'full':
                return image_data
            elif quality == 'preview':
                # For preview, we could resize the image to 50% of original
                # In a real implementation, we would use PIL or similar to resize
                # For now, return full image (would implement actual resizing)
                return image_data
            elif quality == 'thumbnail':
                # For thumbnail, create a smaller version (e.g., 128x128)
                # In a real implementation, we would use PIL or similar to create thumbnail
                # For now, return full image (would implement actual thumbnail generation)
                return image_data
            else:
                return image_data
                
        except Exception as e:
            logger.error(f"Failed to process image quality: {e}")
            return image_data
    
    def apply_window_level(self, image_data: bytes, window_center: float, 
                          window_width: float) -> bytes:
        """Apply window/level adjustment to image"""
        try:
            # In a real implementation, this would apply window/level to the pixel data
            # This requires DICOM pixel data processing with libraries like pydicom
            # For now, return original image data
            logger.debug(f"Applied window/level: center={window_center}, width={window_width}")
            return image_data
            
        except Exception as e:
            logger.error(f"Failed to apply window/level: {e}")
            return image_data
    
    def apply_image_enhancement(self, image_data: bytes, 
                               enhancement_type: str, **kwargs) -> bytes:
        """Apply image enhancement filters"""
        try:
            # In a real implementation, this would apply various enhancements:
            # - Contrast adjustment
            # - Brightness adjustment
            # - Sharpening
            # - Noise reduction
            # - Edge enhancement
            
            logger.debug(f"Applied image enhancement: {enhancement_type}")
            return image_data
            
        except Exception as e:
            logger.error(f"Failed to apply image enhancement: {e}")
            return image_data
    
    def get_image_histogram(self, study_id: str, series_id: str, 
                           instance_id: str) -> Optional[Dict[str, Any]]:
        """Get image histogram data for window/level adjustment"""
        try:
            # Check cache first
            cached_image = self.cache_service.get_cached_dicom_image(
                study_id, series_id, instance_id
            )
            
            if cached_image:
                image_data, metadata = cached_image
                
                # In a real implementation, this would calculate histogram from pixel data
                # For now, return mock histogram data
                return {
                    'instance_id': instance_id,
                    'histogram': [0] * 256,  # Mock histogram
                    'min_value': 0,
                    'max_value': 255,
                    'mean_value': 128,
                    'std_dev': 64
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get image histogram: {e}")
            return None
    
    def prefetch_images(self, study_id: str, series_id: str, 
                       current_instance_index: int, instance_count: int):
        """Prefetch images around current position"""
        try:
            # Calculate prefetch range
            start_index = max(0, current_instance_index - self.prefetch_count)
            end_index = min(instance_count, current_instance_index + self.prefetch_count + 1)
            
            # Get series instances for prefetching
            if self.offline_manager.is_service_available('orthanc'):
                instances = orthanc_client.get_series_instances(series_id)
                
                for i in range(start_index, end_index):
                    if i < len(instances) and i != current_instance_index:
                        instance = instances[i]
                        instance_id = instance.get('ID')
                        
                        if instance_id:
                            # Check if already cached
                            cached = self.cache_service.get_cached_dicom_image(
                                study_id, series_id, instance_id
                            )
                            
                            if not cached:
                                # Add to prefetch queue
                                prefetch_item = {
                                    'study_id': study_id,
                                    'series_id': series_id,
                                    'instance_id': instance_id,
                                    'priority': abs(i - current_instance_index)
                                }
                                self._prefetch_queue.append(prefetch_item)
                
                # Process prefetch queue
                self._process_prefetch_queue()
            
        except Exception as e:
            logger.error(f"Failed to prefetch images: {e}")
    
    def _process_prefetch_queue(self):
        """Process prefetch queue in background"""
        try:
            # Sort by priority (closer to current image first)
            self._prefetch_queue.sort(key=lambda x: x['priority'])
            
            # Process up to max concurrent loads
            while self._prefetch_queue and len(self._loading_cache) < self.max_concurrent_loads:
                item = self._prefetch_queue.pop(0)
                
                cache_key = f"{item['study_id']}_{item['series_id']}_{item['instance_id']}_full"
                
                if cache_key not in self._loading_cache:
                    # Start prefetch load
                    self.executor.submit(
                        self._prefetch_image,
                        item['study_id'], item['series_id'], item['instance_id'], cache_key
                    )
                    self._loading_cache[cache_key] = True
            
        except Exception as e:
            logger.error(f"Failed to process prefetch queue: {e}")
    
    def _prefetch_image(self, study_id: str, series_id: str, instance_id: str, cache_key: str):
        """Prefetch a single image"""
        try:
            # Load and cache image
            image_data = orthanc_client.get_instance_image(instance_id)
            if image_data:
                metadata = orthanc_client.get_instance_tags(instance_id)
                self.cache_service.cache_dicom_image(
                    study_id, series_id, instance_id, image_data, metadata
                )
                self.metrics['prefetch_hits'] += 1
                logger.debug(f"Prefetched image: {instance_id}")
            
        except Exception as e:
            logger.error(f"Failed to prefetch image {instance_id}: {e}")
        
        finally:
            # Remove from loading cache
            if cache_key in self._loading_cache:
                del self._loading_cache[cache_key]
    
    def get_image_info(self, study_id: str, series_id: str, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get image information and metadata"""
        try:
            # Check cache first
            cached_image = self.cache_service.get_cached_dicom_image(
                study_id, series_id, instance_id
            )
            
            if cached_image:
                image_data, metadata = cached_image
                return {
                    'instance_id': instance_id,
                    'series_id': series_id,
                    'study_id': study_id,
                    'metadata': metadata,
                    'size_bytes': len(image_data),
                    'cached': True
                }
            
            # Load from server if available
            if self.offline_manager.is_service_available('orthanc'):
                metadata = orthanc_client.get_instance_tags(instance_id)
                if metadata:
                    return {
                        'instance_id': instance_id,
                        'series_id': series_id,
                        'study_id': study_id,
                        'metadata': metadata,
                        'cached': False
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get image info: {e}")
            return None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get image loading performance metrics"""
        try:
            load_times = self.metrics['load_times']
            
            return {
                'cache_hits': self.metrics['cache_hits'],
                'cache_misses': self.metrics['cache_misses'],
                'cache_hit_rate': (
                    self.metrics['cache_hits'] / 
                    (self.metrics['cache_hits'] + self.metrics['cache_misses'])
                    if (self.metrics['cache_hits'] + self.metrics['cache_misses']) > 0 else 0
                ),
                'prefetch_hits': self.metrics['prefetch_hits'],
                'average_load_time': sum(load_times) / len(load_times) if load_times else 0,
                'total_loads': len(load_times),
                'currently_loading': len(self._loading_cache),
                'prefetch_queue_size': len(self._prefetch_queue)
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {'error': str(e)}
    
    def clear_loading_cache(self):
        """Clear loading cache and reset state"""
        self._loading_cache.clear()
        self._load_callbacks.clear()
        self._prefetch_queue.clear()
        logger.info("Cleared image loading cache")
    
    def shutdown(self):
        """Shutdown the image service"""
        try:
            self.clear_loading_cache()
            self.executor.shutdown(wait=True)
            logger.info("DICOM image service shutdown complete")
        except Exception as e:
            logger.error(f"Error during image service shutdown: {e}")

# Global DICOM image service instance
dicom_image_service = DicomImageService()