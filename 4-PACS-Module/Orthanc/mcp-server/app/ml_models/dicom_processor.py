"""
DICOM Processing Engine
Handles loading and converting DICOM series to 3D volumes
Phase 1 - Backend Processing
"""

import numpy as np
import logging
from pathlib import Path
from typing import Tuple, Dict, Optional, Any

try:
    import SimpleITK as sitk
    SITK_AVAILABLE = True
except ImportError:
    SITK_AVAILABLE = False
    logging.warning("SimpleITK not installed - use 'pip install SimpleITK'")
    sitk = None  # Define sitk as None when not available

logger = logging.getLogger(__name__)


class DICOMProcessor:
    """
    Processes DICOM series and converts to 3D volumes for visualization
    """
    
    def __init__(self):
        """Initialize DICOM processor"""
        if not SITK_AVAILABLE:
            raise RuntimeError("SimpleITK is required. Install with: pip install SimpleITK")
        self.logger = logging.getLogger(__name__)
    
    def load_dicom_series(self, dicom_dir: str) -> Optional[Any]:
        """
        Load DICOM series from directory
        
        Args:
            dicom_dir: Path to directory containing DICOM files
            
        Returns:
            SimpleITK Image object or None if failed
        """
        try:
            reader = sitk.ImageSeriesReader()
            
            # Get all DICOM files in directory
            dicom_names = reader.GetGDCMSeriesFileNames(dicom_dir)
            
            if not dicom_names:
                self.logger.error(f"No DICOM files found in {dicom_dir}")
                return None
            
            reader.SetFileNames(dicom_names)
            image = reader.Execute()
            
            self.logger.info(f"Loaded DICOM series: {image.GetSize()}")
            return image
            
        except Exception as e:
            self.logger.error(f"Error loading DICOM series: {e}")
            return None
    
    def load_single_dicom(self, dicom_file: str) -> Optional[Any]:
        """
        Load single DICOM file
        
        Args:
            dicom_file: Path to DICOM file
            
        Returns:
            SimpleITK Image object or None if failed
        """
        try:
            image = sitk.ReadImage(dicom_file)
            self.logger.info(f"Loaded DICOM file: {image.GetSize()}")
            return image
        except Exception as e:
            self.logger.error(f"Error loading DICOM file: {e}")
            return None
    
    def convert_to_numpy(self, sitk_image: Any) -> np.ndarray:
        """
        Convert SimpleITK image to numpy array
        
        Args:
            sitk_image: SimpleITK Image object
            
        Returns:
            NumPy array in (Z, Y, X) format
        """
        try:
            array = sitk.GetArrayFromImage(sitk_image)
            self.logger.info(f"Converted to numpy array: {array.shape}, dtype: {array.dtype}")
            return array
        except Exception as e:
            self.logger.error(f"Error converting to numpy: {e}")
            return None
    
    def normalize_hounsfield(self, array: np.ndarray, 
                            window_center: int = 40,
                            window_width: int = 400) -> np.ndarray:
        """
        Normalize CT values using Hounsfield window/level
        
        Args:
            array: Input numpy array (CT values in HU)
            window_center: Center of window (default: 40 for soft tissue)
            window_width: Width of window (default: 400)
            
        Returns:
            Normalized array (0.0-1.0)
        """
        try:
            # Calculate window limits
            window_min = window_center - (window_width / 2)
            window_max = window_center + (window_width / 2)
            
            # Clip and normalize
            normalized = np.clip(array, window_min, window_max)
            normalized = (normalized - window_min) / window_width
            
            self.logger.info(f"Normalized array to range [0, 1]")
            return normalized.astype(np.float32)
            
        except Exception as e:
            self.logger.error(f"Error normalizing Hounsfield: {e}")
            return None
    
    def generate_thumbnail(self, array: np.ndarray, 
                          slice_idx: Optional[int] = None,
                          size: Tuple[int, int] = (256, 256)) -> np.ndarray:
        """
        Generate thumbnail from middle slice
        
        Args:
            array: Input 3D numpy array
            slice_idx: Which slice to use (default: middle)
            size: Output thumbnail size
            
        Returns:
            2D thumbnail array
        """
        try:
            if slice_idx is None:
                slice_idx = array.shape[0] // 2
            
            # Get middle slice
            thumb = array[slice_idx, :, :]
            
            # Resize
            from scipy import ndimage
            zoom_factor = size[0] / thumb.shape[0]
            thumb = ndimage.zoom(thumb, zoom_factor, order=1)
            
            self.logger.info(f"Generated thumbnail: {thumb.shape}")
            return thumb.astype(np.float32)
            
        except Exception as e:
            self.logger.error(f"Error generating thumbnail: {e}")
            return None
    
    def get_metadata(self, sitk_image: Any) -> Dict:
        """
        Extract metadata from DICOM image
        
        Args:
            sitk_image: SimpleITK Image object
            
        Returns:
            Dictionary with metadata
        """
        try:
            metadata = {
                'size': sitk_image.GetSize(),
                'spacing': sitk_image.GetSpacing(),
                'origin': sitk_image.GetOrigin(),
                'direction': sitk_image.GetDirection(),
                'pixel_type': sitk_image.GetPixelIDTypeAsString(),
                'number_of_components': sitk_image.GetNumberOfComponentsPerPixel(),
                'dimension': sitk_image.GetDimension(),
            }
            
            self.logger.info(f"Extracted metadata: {metadata}")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error extracting metadata: {e}")
            return {}
    
    def process_dicom_series(self, dicom_path: str, 
                            window_center: int = 40,
                            window_width: int = 400) -> Dict:
        """
        Complete pipeline: load -> convert -> normalize
        
        Args:
            dicom_path: Path to DICOM directory or file
            window_center: Hounsfield window center
            window_width: Hounsfield window width
            
        Returns:
            Dictionary with processed data and metadata
        """
        try:
            # Load DICOM
            if Path(dicom_path).is_dir():
                sitk_image = self.load_dicom_series(dicom_path)
            else:
                sitk_image = self.load_single_dicom(dicom_path)
            
            if sitk_image is None:
                return None
            
            # Get metadata
            metadata = self.get_metadata(sitk_image)
            
            # Convert to numpy
            array = self.convert_to_numpy(sitk_image)
            if array is None:
                return None
            
            # Normalize Hounsfield values
            normalized = self.normalize_hounsfield(
                array, 
                window_center=window_center,
                window_width=window_width
            )
            if normalized is None:
                return None
            
            # Generate thumbnail
            thumbnail = self.generate_thumbnail(normalized)
            
            result = {
                'volume': normalized,
                'metadata': metadata,
                'thumbnail': thumbnail,
                'shape': normalized.shape,
                'dtype': str(normalized.dtype),
                'min': float(normalized.min()),
                'max': float(normalized.max()),
            }
            
            self.logger.info("DICOM processing complete")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in process_dicom_series: {e}")
            return None


# Singleton instance
_processor = None


def get_processor() -> DICOMProcessor:
    """Get or create DICOM processor instance"""
    global _processor
    if _processor is None:
        _processor = DICOMProcessor()
    return _processor


if __name__ == "__main__":
    # Test script
    logging.basicConfig(level=logging.INFO)
    
    processor = DICOMProcessor()
    print("DICOM Processor initialized successfully")
