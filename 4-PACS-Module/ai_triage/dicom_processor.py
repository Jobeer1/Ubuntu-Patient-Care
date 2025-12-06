import pydicom
import numpy as np
from typing import List, Dict, Any, Union, Tuple, Optional
import logging
from pathlib import Path
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DicomProcessorError(Exception):
    """Base exception for DicomProcessor errors."""
    pass

class DicomSliceExtractor:
    """
    Handles extraction of pixel data and metadata from DICOM files.
    Supports single-frame and multi-frame DICOMs.
    Normalizes pixel values for AI model consumption.
    """
    
    def __init__(self):
        pass

    def load_dicom(self, source: Union[str, Path, bytes, io.BytesIO]) -> pydicom.dataset.FileDataset:
        """
        Loads a DICOM dataset from various sources (path, bytes, file-like).
        """
        try:
            if isinstance(source, (str, Path)):
                return pydicom.dcmread(str(source))
            elif isinstance(source, (bytes, io.BytesIO)):
                if isinstance(source, bytes):
                    source = io.BytesIO(source)
                return pydicom.dcmread(source)
            else:
                raise ValueError(f"Unsupported source type: {type(source)}")
        except Exception as e:
            raise DicomProcessorError(f"Failed to load DICOM: {str(e)}")

    def get_metadata(self, ds: pydicom.dataset.FileDataset) -> Dict[str, Any]:
        """
        Extracts standard metadata useful for triage and identification.
        """
        return {
            "PatientID": str(getattr(ds, "PatientID", "UNKNOWN")),
            "StudyInstanceUID": str(getattr(ds, "StudyInstanceUID", "UNKNOWN")),
            "SeriesInstanceUID": str(getattr(ds, "SeriesInstanceUID", "UNKNOWN")),
            "SOPInstanceUID": str(getattr(ds, "SOPInstanceUID", "UNKNOWN")),
            "Modality": str(getattr(ds, "Modality", "UNKNOWN")),
            "BodyPartExamined": str(getattr(ds, "BodyPartExamined", "UNKNOWN")),
            "StudyDescription": str(getattr(ds, "StudyDescription", "")),
            "SeriesDescription": str(getattr(ds, "SeriesDescription", "")),
            "AcquisitionDate": str(getattr(ds, "AcquisitionDate", "")),
            "InstanceNumber": int(getattr(ds, "InstanceNumber", 0)),
            "Manufacturer": str(getattr(ds, "Manufacturer", "UNKNOWN")),
            "PhotometricInterpretation": str(getattr(ds, "PhotometricInterpretation", "UNKNOWN"))
        }

    def apply_windowing(self, image: np.ndarray, ds: pydicom.dataset.FileDataset) -> np.ndarray:
        """
        Applies Window Center and Window Width if present (VOI LUT).
        Converts to Hounsfield Units (HU) if RescaleSlope/Intercept are present (Modality LUT).
        Normalizes result to 0-1 range.
        """
        # Apply Rescale Slope/Intercept (Modality LUT) -> HU
        slope = getattr(ds, 'RescaleSlope', 1)
        intercept = getattr(ds, 'RescaleIntercept', 0)
        image = image * slope + intercept

        # Apply Windowing (VOI LUT)
        if hasattr(ds, 'WindowCenter') and hasattr(ds, 'WindowWidth'):
            wc = ds.WindowCenter
            ww = ds.WindowWidth
            
            # Handle multi-value windowing (take first)
            if isinstance(wc, pydicom.multival.MultiValue):
                wc = wc[0]
            if isinstance(ww, pydicom.multival.MultiValue):
                ww = ww[0]
                
            min_val = wc - (ww / 2)
            max_val = wc + (ww / 2)
            
            image = np.clip(image, min_val, max_val)
            # Normalize to 0-1 range based on window
            if ww != 0:
                image = (image - min_val) / ww
            image = np.clip(image, 0, 1)
        else:
            # Min-max normalization if no windowing
            min_val = np.min(image)
            max_val = np.max(image)
            if max_val > min_val:
                image = (image - min_val) / (max_val - min_val)
            else:
                # Avoid division by zero for constant images
                image = np.zeros_like(image)
                
        return image

    def process_slice(self, ds: pydicom.dataset.FileDataset, target_size: Optional[Tuple[int, int]] = None) -> np.ndarray:
        """
        Extracts and normalizes pixel data for a single slice.
        Returns a 2D numpy array (float32, 0-1 range).
        """
        try:
            pixel_array = ds.pixel_array.astype(np.float32)
            
            # Handle Photometric Interpretation (e.g., MONOCHROME1 vs MONOCHROME2)
            # MONOCHROME1: 0 is white, 1 is black. We usually want 0=black (air), 1=white (bone).
            # If MONOCHROME1, we might need to invert, but usually RescaleSlope/Intercept handles the values correctly for HU.
            # However, for display/CNN, we usually expect standard appearance.
            # Let's stick to standard windowing which usually handles this if we respect HU.
            
            # Apply windowing/normalization
            processed = self.apply_windowing(pixel_array, ds)
            
            # Resize if needed
            if target_size:
                import cv2
                processed = cv2.resize(processed, target_size, interpolation=cv2.INTER_AREA)
                
            return processed
        except Exception as e:
            raise DicomProcessorError(f"Error processing slice: {str(e)}")

    def extract_frames(self, source: Union[str, Path, bytes], target_size: Optional[Tuple[int, int]] = None) -> List[Dict[str, Any]]:
        """
        Main entry point. Handles single-frame and multi-frame DICOMs.
        Returns a list of dicts, each containing 'pixel_data' (numpy array) and 'metadata' (dict).
        """
        ds = self.load_dicom(source)
        metadata = self.get_metadata(ds)
        
        results = []
        
        try:
            if not hasattr(ds, 'pixel_array'):
                 raise DicomProcessorError("DICOM file has no pixel data")
            
            pixel_array = ds.pixel_array
        except Exception as e:
             raise DicomProcessorError(f"Could not extract pixel array: {str(e)}")

        # Check if multi-frame
        # pixel_array.ndim can be 2 (rows, cols) or 3 (frames, rows, cols) or 4 (frames, rows, cols, channels) for RGB
        
        if pixel_array.ndim == 3 and getattr(ds, "NumberOfFrames", 1) > 1:
            # Multi-frame grayscale
            num_frames = pixel_array.shape[0]
            logger.info(f"Processing multi-frame DICOM with {num_frames} frames")
            
            for i in range(num_frames):
                slice_data = pixel_array[i].astype(np.float32)
                processed = self.apply_windowing(slice_data, ds)
                
                if target_size:
                    import cv2
                    processed = cv2.resize(processed, target_size, interpolation=cv2.INTER_AREA)
                
                frame_meta = metadata.copy()
                frame_meta['InstanceNumber'] = i + 1 
                frame_meta['FrameIndex'] = i
                
                results.append({
                    "pixel_data": processed,
                    "metadata": frame_meta,
                    "original_shape": slice_data.shape
                })
                
        elif pixel_array.ndim == 2:
            # Single frame grayscale
            processed = self.process_slice(ds, target_size)
            results.append({
                "pixel_data": processed,
                "metadata": metadata,
                "original_shape": pixel_array.shape
            })
            
        elif pixel_array.ndim == 3 and getattr(ds, "NumberOfFrames", 1) == 1:
             # Single frame RGB (Rows, Cols, 3)
             # Convert to grayscale for now as most medical models expect grayscale
             # Or keep as is if model expects RGB. 
             # For now, let's convert to grayscale using standard weights if it's RGB
             if pixel_array.shape[2] == 3:
                 # Simple average or luminosity
                 gray = np.dot(pixel_array[...,:3], [0.2989, 0.5870, 0.1140])
                 processed = self.apply_windowing(gray.astype(np.float32), ds)
                 if target_size:
                    import cv2
                    processed = cv2.resize(processed, target_size, interpolation=cv2.INTER_AREA)
                 results.append({
                    "pixel_data": processed,
                    "metadata": metadata,
                    "original_shape": gray.shape
                 })
             else:
                 raise DicomProcessorError(f"Unsupported 3D shape for single frame: {pixel_array.shape}")

        else:
             raise DicomProcessorError(f"Unsupported pixel array shape: {pixel_array.shape}")
             
        return results
