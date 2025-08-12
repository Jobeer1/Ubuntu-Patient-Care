"""
Advanced DICOM Viewer for South African Medical Professionals
World-class offline viewer with measurement tools, AI assistance, and SA-specific features
"""

import os
import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
import sqlite3
import logging
from dataclasses import dataclass, asdict
import base64
import io

try:
    import pydicom
    from pydicom.pixel_data_handlers.util import apply_windowing
    PYDICOM_AVAILABLE = True
except ImportError:
    PYDICOM_AVAILABLE = False
    print("Warning: pydicom not available. Install with: pip install pydicom")

try:
    import numpy as np
    from PIL import Image, ImageEnhance, ImageFilter
    import cv2
    IMAGING_AVAILABLE = True
except ImportError:
    IMAGING_AVAILABLE = False
    print("Warning: Imaging libraries not available. Install with: pip install numpy pillow opencv-python")

try:
    from scipy import ndimage
    from skimage import measure, morphology, filters
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: SciPy/scikit-image not available. Install with: pip install scipy scikit-image")

from .south_african_localization import sa_localization

@dataclass
class DicomViewerSession:
    """DICOM viewer session data"""
    session_id: str
    user_id: str
    study_id: str
    series_id: str
    instance_id: str
    window_center: float
    window_width: float
    zoom_level: float
    pan_x: float
    pan_y: float
    rotation: float
    flip_horizontal: bool
    flip_vertical: bool
    invert: bool
    layout_config: str  # JSON
    measurements: str   # JSON
    annotations: str    # JSON
    created_at: str
    updated_at: str

@dataclass
class Measurement:
    """DICOM measurement data"""
    measurement_id: str
    type: str  # 'length', 'angle', 'area', 'volume', 'pixel_value', 'hounsfield'
    points: List[Tuple[float, float]]
    value: float
    unit: str
    description: str
    created_by: str
    created_at: str

@dataclass
class Annotation:
    """DICOM annotation data"""
    annotation_id: str
    type: str  # 'text', 'arrow', 'rectangle', 'circle', 'freehand'
    points: List[Tuple[float, float]]
    text: str
    style: Dict[str, Any]
    created_by: str
    created_at: str

class AdvancedDicomViewer:
    """World-class DICOM viewer with SA-specific features"""
    
    def __init__(self, db_path: str = "dicom_viewer.db"):
        self.db_path = db_path
        self.logger = self._setup_logging()
        self.cache_dir = "dicom_cache"
        self.presets = self._load_window_presets()
        self.measurement_tools = self._init_measurement_tools()
        self.ai_tools = self._init_ai_tools()
        self._init_database()
        
        # Create cache directory
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for DICOM viewer"""
        logger = logging.getLogger('dicom_viewer')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _init_database(self):
        """Initialize DICOM viewer database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Viewer sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS viewer_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                study_id TEXT,
                series_id TEXT,
                instance_id TEXT,
                window_center REAL DEFAULT 0,
                window_width REAL DEFAULT 400,
                zoom_level REAL DEFAULT 1.0,
                pan_x REAL DEFAULT 0,
                pan_y REAL DEFAULT 0,
                rotation REAL DEFAULT 0,
                flip_horizontal BOOLEAN DEFAULT FALSE,
                flip_vertical BOOLEAN DEFAULT FALSE,
                invert BOOLEAN DEFAULT FALSE,
                layout_config TEXT DEFAULT '{}',
                measurements TEXT DEFAULT '[]',
                annotations TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Measurements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS measurements (
                measurement_id TEXT PRIMARY KEY,
                session_id TEXT,
                type TEXT NOT NULL,
                points TEXT NOT NULL,  -- JSON array of points
                value REAL,
                unit TEXT,
                description TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES viewer_sessions (session_id)
            )
        ''')
        
        # Annotations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS annotations (
                annotation_id TEXT PRIMARY KEY,
                session_id TEXT,
                type TEXT NOT NULL,
                points TEXT NOT NULL,  -- JSON array of points
                text TEXT,
                style TEXT DEFAULT '{}',  -- JSON style object
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES viewer_sessions (session_id)
            )
        ''')
        
        # User presets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_presets (
                preset_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                modality TEXT,
                window_center REAL,
                window_width REAL,
                description TEXT,
                is_default BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # AI analysis results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_analysis (
                analysis_id TEXT PRIMARY KEY,
                session_id TEXT,
                analysis_type TEXT NOT NULL,
                results TEXT NOT NULL,  -- JSON results
                confidence REAL,
                processing_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES viewer_sessions (session_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_window_presets(self) -> Dict[str, Dict[str, Any]]:
        """Load window/level presets for different modalities"""
        return {
            'CT': {
                'abdomen': {'center': 50, 'width': 400, 'description': 'Abdomen Soft Tissue'},
                'bone': {'center': 400, 'width': 1500, 'description': 'Bone Window'},
                'brain': {'center': 40, 'width': 80, 'description': 'Brain Tissue'},
                'chest': {'center': -600, 'width': 1600, 'description': 'Chest/Lung'},
                'liver': {'center': 60, 'width': 160, 'description': 'Liver'},
                'mediastinum': {'center': 50, 'width': 350, 'description': 'Mediastinum'},
                'spine': {'center': 50, 'width': 250, 'description': 'Spine Soft Tissue'},
                'angio': {'center': 300, 'width': 600, 'description': 'CT Angiography'}
            },
            'MR': {
                't1': {'center': 500, 'width': 1000, 'description': 'T1 Weighted'},
                't2': {'center': 500, 'width': 1000, 'description': 'T2 Weighted'},
                'flair': {'center': 500, 'width': 1000, 'description': 'FLAIR'},
                'dwi': {'center': 500, 'width': 1000, 'description': 'Diffusion Weighted'},
                'gre': {'center': 500, 'width': 1000, 'description': 'Gradient Echo'},
                'stir': {'center': 500, 'width': 1000, 'description': 'STIR'}
            },
            'XR': {
                'chest': {'center': 32768, 'width': 65536, 'description': 'Chest X-Ray'},
                'abdomen': {'center': 32768, 'width': 65536, 'description': 'Abdomen X-Ray'},
                'bone': {'center': 32768, 'width': 65536, 'description': 'Bone X-Ray'},
                'soft_tissue': {'center': 32768, 'width': 65536, 'description': 'Soft Tissue'}
            },
            'US': {
                'general': {'center': 128, 'width': 256, 'description': 'General Ultrasound'},
                'doppler': {'center': 128, 'width': 256, 'description': 'Doppler Ultrasound'},
                'cardiac': {'center': 128, 'width': 256, 'description': 'Cardiac Ultrasound'}
            },
            'MG': {
                'standard': {'center': 32768, 'width': 65536, 'description': 'Standard Mammography'},
                'contrast': {'center': 32768, 'width': 65536, 'description': 'Contrast Enhanced'}
            }
        }
    
    def _init_measurement_tools(self) -> Dict[str, Any]:
        """Initialize measurement tools"""
        return {
            'length': {
                'name': 'Linear Measurement',
                'description': 'Measure distance between two points',
                'points_required': 2,
                'unit': 'mm'
            },
            'angle': {
                'name': 'Angle Measurement',
                'description': 'Measure angle between three points',
                'points_required': 3,
                'unit': 'degrees'
            },
            'area': {
                'name': 'Area Measurement',
                'description': 'Measure area of polygon',
                'points_required': 3,  # minimum
                'unit': 'mm²'
            },
            'circle': {
                'name': 'Circle Measurement',
                'description': 'Measure circular area',
                'points_required': 2,  # center and edge
                'unit': 'mm²'
            },
            'ellipse': {
                'name': 'Ellipse Measurement',
                'description': 'Measure elliptical area',
                'points_required': 3,  # center and two radii
                'unit': 'mm²'
            },
            'pixel_value': {
                'name': 'Pixel Value',
                'description': 'Get pixel intensity value',
                'points_required': 1,
                'unit': 'HU'  # Hounsfield Units for CT
            },
            'roi_stats': {
                'name': 'ROI Statistics',
                'description': 'Statistical analysis of region',
                'points_required': 3,  # minimum for ROI
                'unit': 'various'
            }
        }
    
    def _init_ai_tools(self) -> Dict[str, Any]:
        """Initialize AI-powered tools"""
        return {
            'lung_nodule_detection': {
                'name': 'Lung Nodule Detection',
                'description': 'Detect pulmonary nodules in chest CT',
                'modality': 'CT',
                'body_part': 'CHEST'
            },
            'bone_age_assessment': {
                'name': 'Bone Age Assessment',
                'description': 'Assess skeletal maturity from hand X-ray',
                'modality': 'XR',
                'body_part': 'HAND'
            },
            'fracture_detection': {
                'name': 'Fracture Detection',
                'description': 'Detect bone fractures in X-rays',
                'modality': 'XR',
                'body_part': 'BONE'
            },
            'brain_hemorrhage': {
                'name': 'Brain Hemorrhage Detection',
                'description': 'Detect intracranial hemorrhage in head CT',
                'modality': 'CT',
                'body_part': 'HEAD'
            },
            'cardiac_function': {
                'name': 'Cardiac Function Analysis',
                'description': 'Analyze cardiac function from echo/MR',
                'modality': 'US,MR',
                'body_part': 'HEART'
            }
        }
    
    def load_dicom_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load DICOM file and extract metadata"""
        if not PYDICOM_AVAILABLE:
            self.logger.error("pydicom not available")
            return None
        
        try:
            # Read DICOM file
            ds = pydicom.dcmread(file_path)
            
            # Extract pixel data
            pixel_array = None
            if hasattr(ds, 'pixel_array'):
                pixel_array = ds.pixel_array
                
                # Handle different bit depths
                if ds.BitsStored == 16:
                    if ds.PixelRepresentation == 1:  # Signed
                        pixel_array = pixel_array.astype(np.int16)
                    else:  # Unsigned
                        pixel_array = pixel_array.astype(np.uint16)
                elif ds.BitsStored == 8:
                    pixel_array = pixel_array.astype(np.uint8)
            
            # Extract metadata
            metadata = {
                'patient_name': str(ds.get('PatientName', '')),
                'patient_id': str(ds.get('PatientID', '')),
                'study_date': str(ds.get('StudyDate', '')),
                'study_time': str(ds.get('StudyTime', '')),
                'modality': str(ds.get('Modality', '')),
                'study_description': str(ds.get('StudyDescription', '')),
                'series_description': str(ds.get('SeriesDescription', '')),
                'institution_name': str(ds.get('InstitutionName', '')),
                'manufacturer': str(ds.get('Manufacturer', '')),
                'model_name': str(ds.get('ManufacturerModelName', '')),
                'study_instance_uid': str(ds.get('StudyInstanceUID', '')),
                'series_instance_uid': str(ds.get('SeriesInstanceUID', '')),
                'sop_instance_uid': str(ds.get('SOPInstanceUID', '')),
                'rows': int(ds.get('Rows', 0)),
                'columns': int(ds.get('Columns', 0)),
                'pixel_spacing': ds.get('PixelSpacing', [1.0, 1.0]),
                'slice_thickness': float(ds.get('SliceThickness', 1.0)),
                'window_center': ds.get('WindowCenter', 0),
                'window_width': ds.get('WindowWidth', 400),
                'rescale_intercept': float(ds.get('RescaleIntercept', 0)),
                'rescale_slope': float(ds.get('RescaleSlope', 1)),
                'bits_stored': int(ds.get('BitsStored', 16)),
                'pixel_representation': int(ds.get('PixelRepresentation', 0))
            }
            
            # Handle multiple window values
            if isinstance(metadata['window_center'], (list, tuple)):
                metadata['window_center'] = float(metadata['window_center'][0])
            else:
                metadata['window_center'] = float(metadata['window_center'])
                
            if isinstance(metadata['window_width'], (list, tuple)):
                metadata['window_width'] = float(metadata['window_width'][0])
            else:
                metadata['window_width'] = float(metadata['window_width'])
            
            return {
                'metadata': metadata,
                'pixel_array': pixel_array,
                'dicom_dataset': ds
            }
            
        except Exception as e:
            self.logger.error(f"Failed to load DICOM file {file_path}: {e}")
            return None
    
    def apply_window_level(self, pixel_array: np.ndarray, center: float, width: float,
                          rescale_intercept: float = 0, rescale_slope: float = 1) -> np.ndarray:
        """Apply window/level to pixel data"""
        if not IMAGING_AVAILABLE:
            return pixel_array
        
        try:
            # Apply rescale slope and intercept (for Hounsfield units in CT)
            if rescale_slope != 1 or rescale_intercept != 0:
                pixel_array = pixel_array * rescale_slope + rescale_intercept
            
            # Apply windowing
            min_val = center - width / 2
            max_val = center + width / 2
            
            # Clip values to window range
            windowed = np.clip(pixel_array, min_val, max_val)
            
            # Normalize to 0-255 for display
            windowed = ((windowed - min_val) / (max_val - min_val) * 255).astype(np.uint8)
            
            return windowed
            
        except Exception as e:
            self.logger.error(f"Failed to apply window/level: {e}")
            return pixel_array
    
    def apply_image_enhancements(self, image: np.ndarray, enhancements: Dict[str, Any]) -> np.ndarray:
        """Apply image enhancements (zoom, pan, rotate, flip, etc.)"""
        if not IMAGING_AVAILABLE:
            return image
        
        try:
            enhanced = image.copy()
            
            # Convert to PIL Image for easier manipulation
            if len(enhanced.shape) == 2:  # Grayscale
                pil_image = Image.fromarray(enhanced, mode='L')
            else:  # RGB
                pil_image = Image.fromarray(enhanced)
            
            # Apply rotation
            if enhancements.get('rotation', 0) != 0:
                pil_image = pil_image.rotate(enhancements['rotation'], expand=True)
            
            # Apply flips
            if enhancements.get('flip_horizontal', False):
                pil_image = pil_image.transpose(Image.FLIP_LEFT_RIGHT)
            
            if enhancements.get('flip_vertical', False):
                pil_image = pil_image.transpose(Image.FLIP_TOP_BOTTOM)
            
            # Apply inversion
            if enhancements.get('invert', False):
                pil_image = Image.eval(pil_image, lambda x: 255 - x)
            
            # Apply zoom (will be handled by frontend for performance)
            
            # Apply filters
            if enhancements.get('sharpen', False):
                pil_image = pil_image.filter(ImageFilter.SHARPEN)
            
            if enhancements.get('smooth', False):
                pil_image = pil_image.filter(ImageFilter.SMOOTH)
            
            if enhancements.get('edge_enhance', False):
                pil_image = pil_image.filter(ImageFilter.EDGE_ENHANCE)
            
            # Convert back to numpy array
            enhanced = np.array(pil_image)
            
            return enhanced
            
        except Exception as e:
            self.logger.error(f"Failed to apply image enhancements: {e}")
            return image
    
    def calculate_measurement(self, measurement_type: str, points: List[Tuple[float, float]],
                            pixel_spacing: List[float] = [1.0, 1.0]) -> Dict[str, Any]:
        """Calculate measurement based on type and points"""
        try:
            if measurement_type == 'length':
                if len(points) < 2:
                    return {'error': 'Length measurement requires 2 points'}
                
                p1, p2 = points[0], points[1]
                pixel_distance = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                real_distance = pixel_distance * pixel_spacing[0]  # Assume isotropic for simplicity
                
                return {
                    'value': round(real_distance, 2),
                    'unit': 'mm',
                    'description': f'Distance: {real_distance:.2f} mm'
                }
            
            elif measurement_type == 'angle':
                if len(points) < 3:
                    return {'error': 'Angle measurement requires 3 points'}
                
                p1, p2, p3 = points[0], points[1], points[2]
                
                # Calculate vectors
                v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
                v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
                
                # Calculate angle
                cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                angle = np.arccos(np.clip(cos_angle, -1.0, 1.0)) * 180 / np.pi
                
                return {
                    'value': round(angle, 1),
                    'unit': 'degrees',
                    'description': f'Angle: {angle:.1f}°'
                }
            
            elif measurement_type == 'area':
                if len(points) < 3:
                    return {'error': 'Area measurement requires at least 3 points'}
                
                # Calculate polygon area using shoelace formula
                x_coords = [p[0] for p in points]
                y_coords = [p[1] for p in points]
                
                pixel_area = 0.5 * abs(sum(x_coords[i] * y_coords[i+1] - x_coords[i+1] * y_coords[i] 
                                         for i in range(-1, len(x_coords)-1)))
                
                # Convert to real area (mm²)
                real_area = pixel_area * pixel_spacing[0] * pixel_spacing[1]
                
                return {
                    'value': round(real_area, 2),
                    'unit': 'mm²',
                    'description': f'Area: {real_area:.2f} mm²'
                }
            
            elif measurement_type == 'circle':
                if len(points) < 2:
                    return {'error': 'Circle measurement requires 2 points (center and edge)'}
                
                center, edge = points[0], points[1]
                pixel_radius = np.sqrt((edge[0] - center[0])**2 + (edge[1] - center[1])**2)
                real_radius = pixel_radius * pixel_spacing[0]
                real_area = np.pi * real_radius**2
                
                return {
                    'value': round(real_area, 2),
                    'unit': 'mm²',
                    'description': f'Circle Area: {real_area:.2f} mm² (r={real_radius:.2f} mm)'
                }
            
            else:
                return {'error': f'Unknown measurement type: {measurement_type}'}
                
        except Exception as e:
            self.logger.error(f"Failed to calculate measurement: {e}")
            return {'error': str(e)}
    
    def create_viewer_session(self, user_id: str, study_id: str = None, 
                            series_id: str = None, instance_id: str = None) -> str:
        """Create new viewer session"""
        try:
            session_id = f"viewer_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id[:8]}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO viewer_sessions (
                    session_id, user_id, study_id, series_id, instance_id
                ) VALUES (?, ?, ?, ?, ?)
            ''', (session_id, user_id, study_id, series_id, instance_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Created viewer session: {session_id}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to create viewer session: {e}")
            return ""
    
    def save_measurement(self, session_id: str, measurement: Measurement) -> bool:
        """Save measurement to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO measurements (
                    measurement_id, session_id, type, points, value, unit, description, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                measurement.measurement_id, session_id, measurement.type,
                json.dumps(measurement.points), measurement.value, measurement.unit,
                measurement.description, measurement.created_by
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save measurement: {e}")
            return False
    
    def save_annotation(self, session_id: str, annotation: Annotation) -> bool:
        """Save annotation to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO annotations (
                    annotation_id, session_id, type, points, text, style, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                annotation.annotation_id, session_id, annotation.type,
                json.dumps(annotation.points), annotation.text,
                json.dumps(annotation.style), annotation.created_by
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save annotation: {e}")
            return False
    
    def get_window_presets(self, modality: str) -> Dict[str, Dict[str, Any]]:
        """Get window/level presets for modality"""
        return self.presets.get(modality.upper(), {})
    
    def convert_to_base64_image(self, pixel_array: np.ndarray) -> str:
        """Convert pixel array to base64 encoded image for web display"""
        if not IMAGING_AVAILABLE:
            return ""
        
        try:
            # Ensure 8-bit data
            if pixel_array.dtype != np.uint8:
                pixel_array = ((pixel_array - pixel_array.min()) / 
                              (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)
            
            # Convert to PIL Image
            if len(pixel_array.shape) == 2:  # Grayscale
                pil_image = Image.fromarray(pixel_array, mode='L')
            else:  # RGB
                pil_image = Image.fromarray(pixel_array)
            
            # Convert to base64
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            self.logger.error(f"Failed to convert image to base64: {e}")
            return ""
    
    def get_viewer_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get viewer usage statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            where_clause = "WHERE user_id = ?" if user_id else ""
            params = [user_id] if user_id else []
            
            # Total sessions
            cursor.execute(f'SELECT COUNT(*) FROM viewer_sessions {where_clause}', params)
            total_sessions = cursor.fetchone()[0]
            
            # Total measurements
            cursor.execute(f'''
                SELECT COUNT(*) FROM measurements m
                JOIN viewer_sessions v ON m.session_id = v.session_id
                {where_clause}
            ''', params)
            total_measurements = cursor.fetchone()[0]
            
            # Total annotations
            cursor.execute(f'''
                SELECT COUNT(*) FROM annotations a
                JOIN viewer_sessions v ON a.session_id = v.session_id
                {where_clause}
            ''', params)
            total_annotations = cursor.fetchone()[0]
            
            # Recent activity (last 7 days)
            cursor.execute(f'''
                SELECT COUNT(*) FROM viewer_sessions 
                {where_clause} {"AND" if where_clause else "WHERE"} 
                created_at > datetime('now', '-7 days')
            ''', params)
            recent_activity = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_sessions': total_sessions,
                'total_measurements': total_measurements,
                'total_annotations': total_annotations,
                'recent_activity_7d': recent_activity
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get viewer stats: {e}")
            return {}

# Global DICOM viewer instance
advanced_dicom_viewer = AdvancedDicomViewer()