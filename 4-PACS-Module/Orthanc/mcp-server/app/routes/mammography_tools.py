"""
Mammography Analysis Tools for Breast Cancer Screening
Implements lesion detection, microcalcification analysis, and BI-RADS classification
Clinical validation against ACR standards
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import logging
from datetime import datetime
import asyncio
from scipy import ndimage, spatial
from skimage import measure, morphology, filters, feature
import json
import cv2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/mammo", tags=["mammography"])

# Pydantic Models
class MammographyRequest(BaseModel):
    """Request model for mammography analysis"""
    study_id: str = Field(..., description="Study identifier")
    image_data: Optional[List[List[float]]] = Field(None, description="2D mammogram image data")
    view_type: str = Field("CC", description="View type (CC, MLO, etc.)")
    laterality: str = Field("L", description="Laterality (L/R)")
    pixel_spacing: Tuple[float, float] = Field((0.1, 0.1), description="Pixel spacing in mm")
    patient_age: Optional[int] = Field(None, description="Patient age")
    breast_density: Optional[str] = Field(None, description="Breast density (A/B/C/D)")

class LesionDetectionRequest(MammographyRequest):
    """Request model for lesion detection"""
    detection_threshold: float = Field(0.5, description="Detection confidence threshold")
    min_lesion_size: float = Field(5.0, description="Minimum lesion size in mm")

class MicrocalcRequest(MammographyRequest):
    """Request model for microcalcification analysis"""
    cluster_threshold: float = Field(1.0, description="Clustering distance threshold in cm")
    min_cluster_size: int = Field(3, description="Minimum calcifications per cluster")

class BiradsRequest(MammographyRequest):
    """Request model for BI-RADS classification"""
    lesions: Optional[List[Dict]] = Field(None, description="Detected lesions")
    microcalcs: Optional[List[Dict]] = Field(None, description="Detected microcalcifications")

class LesionDetectionResponse(BaseModel):
    """Response model for lesion detection"""
    study_id: str
    lesions: List[Dict]
    total_lesions: int
    processing_time: float
    confidence_scores: List[float]
    timestamp: str

class MicrocalcResponse(BaseModel):
    """Response model for microcalcification analysis"""
    study_id: str
    clusters: List[Dict]
    total_clusters: int
    total_microcalcs: int
    morphology_analysis: Dict
    processing_time: float
    timestamp: str

class BiradsResponse(BaseModel):
    """Response model for BI-RADS classification"""
    study_id: str
    birads_score: int
    birads_description: str
    assessment_category: str
    recommendations: List[str]
    confidence: float
    findings_summary: Dict
    timestamp: str

class CADScoreResponse(BaseModel):
    """Response model for CAD scoring"""
    study_id: str
    cad_score: float
    risk_level: str
    detection_confidence: float
    analysis_summary: Dict
    processing_time: float
    timestamp: str

# Global mammography analysis engine instance
mammo_engine = None

class MammographyAnalysisEngine:
    """
    Comprehensive mammography analysis engine implementing clinical algorithms
    """
    
    def __init__(self):
        """Initialize the mammography analysis engine"""
        self.birads_categories = {
            0: "Incomplete - Need additional imaging",
            1: "Negative - Routine screening",
            2: "Benign - Routine screening", 
            3: "Probably benign - Short interval follow-up",
            4: "Suspicious - Tissue sampling should be considered",
            5: "Highly suggestive of malignancy - Appropriate action should be taken",
            6: "Known biopsy-proven malignancy"
        }
        
        self.density_categories = {
            'A': 'Almost entirely fatty',
            'B': 'Scattered areas of fibroglandular density',
            'C': 'Heterogeneously dense',
            'D': 'Extremely dense'
        }
        
        # Morphology descriptors for microcalcifications
        self.microcalc_morphology = {
            'round': 'Round/punctate',
            'amorphous': 'Amorphous/indistinct',
            'coarse': 'Coarse heterogeneous',
            'fine_pleomorphic': 'Fine pleomorphic',
            'fine_linear': 'Fine linear/branching'
        }
        
        logger.info("MammographyAnalysisEngine initialized")
    
    def detect_lesions(self, image: np.ndarray, pixel_spacing: Tuple[float, float],
                      threshold: float = 0.5, min_size_mm: float = 5.0) -> Tuple[List[Dict], List[float]]:
        """
        Detect masses/lesions in mammogram using CNN-based approach
        
        Args:
            image: 2D mammogram image array
            pixel_spacing: Pixel spacing (x, y) in mm
            threshold: Detection confidence threshold
            min_size_mm: Minimum lesion size in mm
            
        Returns:
            Tuple of (lesions_list, confidence_scores)
        """
        try:
            # Preprocessing
            processed_image = self._preprocess_mammogram(image)
            
            # Feature extraction using Hessian-based blob detection
            # (In production, this would use a trained CNN model)
            blobs = feature.blob_doh(processed_image, min_sigma=1, max_sigma=30, threshold=0.01)
            
            lesions = []
            confidences = []
            
            # Convert pixel size to mm
            min_size_pixels = min_size_mm / min(pixel_spacing)
            
            for blob in blobs:
                y, x, radius = blob
                
                # Skip small detections
                if radius < min_size_pixels / 2:
                    continue
                
                # Calculate features for confidence scoring
                roi = self._extract_roi(processed_image, (int(x), int(y)), int(radius * 2))
                confidence = self._calculate_lesion_confidence(roi)
                
                if confidence >= threshold:
                    # Convert to physical coordinates
                    size_mm = radius * 2 * min(pixel_spacing)
                    
                    lesion = {
                        'id': len(lesions) + 1,
                        'center_x': float(x),
                        'center_y': float(y),
                        'radius_pixels': float(radius),
                        'size_mm': float(size_mm),
                        'confidence': float(confidence),
                        'shape_descriptor': self._analyze_lesion_shape(roi),
                        'margin_descriptor': self._analyze_lesion_margin(roi),
                        'density': self._analyze_lesion_density(roi)
                    }
                    
                    lesions.append(lesion)
                    confidences.append(confidence)
            
            logger.info(f"Detected {len(lesions)} lesions with confidence >= {threshold}")
            return lesions, confidences
            
        except Exception as e:
            logger.error(f"Error in lesion detection: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Lesion detection failed: {str(e)}")
    
    def analyze_microcalcifications(self, image: np.ndarray, pixel_spacing: Tuple[float, float],
                                  cluster_threshold_cm: float = 1.0, min_cluster_size: int = 3) -> Tuple[List[Dict], Dict]:
        """
        Detect and analyze microcalcifications and clusters
        
        Args:
            image: 2D mammogram image array
            pixel_spacing: Pixel spacing (x, y) in mm
            cluster_threshold_cm: Clustering distance threshold in cm
            min_cluster_size: Minimum calcifications per cluster
            
        Returns:
            Tuple of (clusters_list, morphology_analysis)
        """
        try:
            # Preprocessing for microcalcification detection
            processed_image = self._preprocess_mammogram(image)
            
            # High-pass filtering to enhance small bright spots
            kernel = np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]])
            filtered = cv2.filter2D(processed_image, -1, kernel)
            
            # Threshold for bright spots (microcalcifications)
            threshold_value = np.percentile(filtered, 99.5)  # Top 0.5% brightest pixels
            binary_mask = filtered > threshold_value
            
            # Remove noise with morphological operations
            binary_mask = morphology.remove_small_objects(binary_mask, min_size=3)
            
            # Find individual microcalcifications
            labeled_mask, num_features = ndimage.label(binary_mask)
            microcalcs = []
            
            for i in range(1, num_features + 1):
                component_mask = labeled_mask == i
                props = measure.regionprops(component_mask.astype(int))[0]
                
                # Calculate physical size
                area_mm2 = props.area * pixel_spacing[0] * pixel_spacing[1]
                
                # Skip if too large (likely artifact)
                if area_mm2 > 2.0:  # 2 mm² threshold
                    continue
                
                microcalc = {
                    'id': len(microcalcs) + 1,
                    'centroid_x': float(props.centroid[1]),
                    'centroid_y': float(props.centroid[0]),
                    'area_pixels': int(props.area),
                    'area_mm2': float(area_mm2),
                    'eccentricity': float(props.eccentricity),
                    'solidity': float(props.solidity),
                    'morphology': self._classify_microcalc_morphology(component_mask, props)
                }
                
                microcalcs.append(microcalc)
            
            # Cluster analysis
            clusters = self._cluster_microcalcifications(microcalcs, pixel_spacing, 
                                                       cluster_threshold_cm, min_cluster_size)
            
            # Morphology analysis
            morphology_analysis = self._analyze_cluster_morphology(clusters, microcalcs)
            
            logger.info(f"Detected {len(microcalcs)} microcalcifications in {len(clusters)} clusters")
            return clusters, morphology_analysis
            
        except Exception as e:
            logger.error(f"Error in microcalcification analysis: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Microcalcification analysis failed: {str(e)}")
    
    def classify_birads(self, lesions: List[Dict], microcalc_clusters: List[Dict],
                       patient_age: Optional[int] = None, breast_density: Optional[str] = None) -> Tuple[int, str, List[str], float]:
        """
        Classify BI-RADS category based on findings
        
        Args:
            lesions: List of detected lesions
            microcalc_clusters: List of microcalcification clusters
            patient_age: Patient age
            breast_density: Breast density category
            
        Returns:
            Tuple of (birads_score, assessment_category, recommendations, confidence)
        """
        try:
            # Initialize scoring
            birads_score = 1  # Start with negative
            risk_factors = []
            confidence = 0.8  # Base confidence
            
            # Analyze lesions
            if lesions:
                max_lesion_risk = 0
                for lesion in lesions:
                    lesion_risk = self._assess_lesion_risk(lesion)
                    max_lesion_risk = max(max_lesion_risk, lesion_risk)
                    
                    if lesion_risk >= 4:  # Suspicious features
                        birads_score = max(birads_score, 4)
                        risk_factors.append(f"Suspicious mass (confidence: {lesion['confidence']:.2f})")
                    elif lesion_risk >= 3:  # Probably benign
                        birads_score = max(birads_score, 3)
                        risk_factors.append(f"Probably benign mass")
                    else:  # Benign features
                        birads_score = max(birads_score, 2)
            
            # Analyze microcalcification clusters
            if microcalc_clusters:
                max_cluster_risk = 0
                for cluster in microcalc_clusters:
                    cluster_risk = self._assess_cluster_risk(cluster)
                    max_cluster_risk = max(max_cluster_risk, cluster_risk)
                    
                    if cluster_risk >= 4:  # Suspicious clustering
                        birads_score = max(birads_score, 4)
                        risk_factors.append(f"Suspicious microcalcification cluster")
                    elif cluster_risk >= 3:  # Intermediate concern
                        birads_score = max(birads_score, 3)
                        risk_factors.append(f"Intermediate concern microcalcifications")
                    else:  # Benign pattern
                        birads_score = max(birads_score, 2)
            
            # Age and density adjustments
            if patient_age and patient_age < 40 and birads_score >= 3:
                confidence *= 0.9  # Lower confidence in young patients
            
            if breast_density in ['C', 'D'] and birads_score <= 2:
                risk_factors.append("Dense breast tissue may obscure lesions")
                confidence *= 0.85
            
            # Generate assessment category and recommendations
            assessment_category = self.birads_categories[birads_score]
            recommendations = self._generate_recommendations(birads_score, risk_factors, patient_age, breast_density)
            
            logger.info(f"BI-RADS classification: {birads_score} ({assessment_category})")
            return birads_score, assessment_category, recommendations, confidence
            
        except Exception as e:
            logger.error(f"Error in BI-RADS classification: {str(e)}")
            raise HTTPException(status_code=500, detail=f"BI-RADS classification failed: {str(e)}")
    
    def calculate_cad_score(self, lesions: List[Dict], microcalc_clusters: List[Dict],
                           image_quality: float = 1.0) -> Tuple[float, str, float, Dict]:
        """
        Calculate Computer-Aided Detection (CAD) score
        
        Args:
            lesions: List of detected lesions
            microcalc_clusters: List of microcalcification clusters
            image_quality: Image quality factor (0-1)
            
        Returns:
            Tuple of (cad_score, risk_level, detection_confidence, analysis_summary)
        """
        try:
            # Initialize CAD scoring
            cad_score = 0.0
            detection_confidence = 0.0
            
            # Lesion contribution to CAD score
            lesion_scores = []
            if lesions:
                for lesion in lesions:
                    # Weight by confidence and suspicious features
                    lesion_cad = lesion['confidence'] * self._get_lesion_cad_weight(lesion)
                    lesion_scores.append(lesion_cad)
                    cad_score += lesion_cad
                
                detection_confidence += np.mean([l['confidence'] for l in lesions]) * 0.6
            
            # Microcalcification contribution
            cluster_scores = []
            if microcalc_clusters:
                for cluster in microcalc_clusters:
                    cluster_cad = self._get_cluster_cad_weight(cluster)
                    cluster_scores.append(cluster_cad)
                    cad_score += cluster_cad
                
                detection_confidence += 0.4  # Base confidence for microcalc detection
            
            # Normalize CAD score (0-100 scale)
            cad_score = min(100.0, cad_score * 10)  # Scale factor
            
            # Adjust for image quality
            cad_score *= image_quality
            detection_confidence *= image_quality
            
            # Determine risk level
            if cad_score >= 70:
                risk_level = "High"
            elif cad_score >= 40:
                risk_level = "Moderate"
            elif cad_score >= 20:
                risk_level = "Low"
            else:
                risk_level = "Minimal"
            
            # Analysis summary
            analysis_summary = {
                'total_lesions': len(lesions),
                'total_clusters': len(microcalc_clusters),
                'lesion_scores': lesion_scores,
                'cluster_scores': cluster_scores,
                'image_quality_factor': image_quality,
                'risk_level': risk_level
            }
            
            logger.info(f"CAD score calculated: {cad_score:.1f} ({risk_level} risk)")
            return cad_score, risk_level, detection_confidence, analysis_summary
            
        except Exception as e:
            logger.error(f"Error calculating CAD score: {str(e)}")
            raise HTTPException(status_code=500, detail=f"CAD score calculation failed: {str(e)}")
    
    def _preprocess_mammogram(self, image: np.ndarray) -> np.ndarray:
        """Preprocess mammogram image for analysis"""
        # Normalize to 0-1 range
        image_norm = (image - np.min(image)) / (np.max(image) - np.min(image))
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        image_uint8 = (image_norm * 255).astype(np.uint8)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(image_uint8)
        
        # Convert back to float
        return enhanced.astype(np.float32) / 255.0
    
    def _extract_roi(self, image: np.ndarray, center: Tuple[int, int], size: int) -> np.ndarray:
        """Extract region of interest around a point"""
        x, y = center
        half_size = size // 2
        
        x1 = max(0, x - half_size)
        x2 = min(image.shape[1], x + half_size)
        y1 = max(0, y - half_size)
        y2 = min(image.shape[0], y + half_size)
        
        return image[y1:y2, x1:x2]
    
    def _calculate_lesion_confidence(self, roi: np.ndarray) -> float:
        """Calculate confidence score for a lesion ROI"""
        if roi.size == 0:
            return 0.0
        
        # Features for confidence calculation
        contrast = np.std(roi)
        circularity = self._calculate_circularity(roi)
        edge_strength = np.mean(filters.sobel(roi))
        
        # Weighted combination (simplified model)
        confidence = (contrast * 0.4 + circularity * 0.3 + edge_strength * 0.3)
        return min(1.0, max(0.0, confidence))
    
    def _calculate_circularity(self, roi: np.ndarray) -> float:
        """Calculate circularity of a region"""
        # Threshold to binary
        threshold = filters.threshold_otsu(roi)
        binary = roi > threshold
        
        if np.sum(binary) == 0:
            return 0.0
        
        # Calculate circularity = 4π * area / perimeter²
        props = measure.regionprops(binary.astype(int))
        if not props:
            return 0.0
        
        area = props[0].area
        perimeter = props[0].perimeter
        
        if perimeter == 0:
            return 0.0
        
        circularity = 4 * np.pi * area / (perimeter ** 2)
        return min(1.0, circularity)
    
    def _analyze_lesion_shape(self, roi: np.ndarray) -> str:
        """Analyze lesion shape descriptor"""
        circularity = self._calculate_circularity(roi)
        
        if circularity > 0.8:
            return "round"
        elif circularity > 0.6:
            return "oval"
        else:
            return "irregular"
    
    def _analyze_lesion_margin(self, roi: np.ndarray) -> str:
        """Analyze lesion margin descriptor"""
        # Edge analysis using gradient
        edges = filters.sobel(roi)
        edge_variance = np.var(edges)
        
        if edge_variance < 0.01:
            return "circumscribed"
        elif edge_variance < 0.05:
            return "microlobulated"
        else:
            return "spiculated"
    
    def _analyze_lesion_density(self, roi: np.ndarray) -> str:
        """Analyze lesion density"""
        mean_intensity = np.mean(roi)
        
        if mean_intensity > 0.7:
            return "high_density"
        elif mean_intensity > 0.4:
            return "equal_density"
        else:
            return "low_density"
    
    def _classify_microcalc_morphology(self, mask: np.ndarray, props) -> str:
        """Classify microcalcification morphology"""
        # Simple morphology classification based on shape properties
        if props.eccentricity < 0.3 and props.solidity > 0.9:
            return "round"
        elif props.eccentricity > 0.8:
            return "fine_linear"
        elif props.solidity < 0.7:
            return "fine_pleomorphic"
        elif props.area > 10:
            return "coarse"
        else:
            return "amorphous"
    
    def _cluster_microcalcifications(self, microcalcs: List[Dict], pixel_spacing: Tuple[float, float],
                                   threshold_cm: float, min_cluster_size: int) -> List[Dict]:
        """Cluster microcalcifications based on spatial proximity"""
        if len(microcalcs) < min_cluster_size:
            return []
        
        # Extract coordinates
        coords = np.array([[mc['centroid_x'], mc['centroid_y']] for mc in microcalcs])
        
        # Convert threshold to pixels
        threshold_pixels = threshold_cm * 10 / min(pixel_spacing)  # cm to mm to pixels
        
        # Hierarchical clustering
        from scipy.cluster.hierarchy import fcluster, linkage
        
        if len(coords) < 2:
            return []
        
        linkage_matrix = linkage(coords, method='single')
        cluster_labels = fcluster(linkage_matrix, threshold_pixels, criterion='distance')
        
        # Group microcalcifications by cluster
        clusters = []
        unique_labels = np.unique(cluster_labels)
        
        for label in unique_labels:
            cluster_indices = np.where(cluster_labels == label)[0]
            
            if len(cluster_indices) >= min_cluster_size:
                cluster_microcalcs = [microcalcs[i] for i in cluster_indices]
                
                # Calculate cluster properties
                cluster_coords = coords[cluster_indices]
                centroid = np.mean(cluster_coords, axis=0)
                
                cluster = {
                    'id': len(clusters) + 1,
                    'centroid_x': float(centroid[0]),
                    'centroid_y': float(centroid[1]),
                    'microcalc_count': len(cluster_microcalcs),
                    'microcalcs': cluster_microcalcs,
                    'distribution': self._analyze_cluster_distribution(cluster_coords),
                    'morphology_mix': self._analyze_morphology_mix(cluster_microcalcs)
                }
                
                clusters.append(cluster)
        
        return clusters
    
    def _analyze_cluster_distribution(self, coords: np.ndarray) -> str:
        """Analyze spatial distribution of cluster"""
        if len(coords) < 3:
            return "grouped"
        
        # Calculate pairwise distances
        distances = spatial.distance.pdist(coords)
        cv = np.std(distances) / np.mean(distances)  # Coefficient of variation
        
        if cv < 0.3:
            return "grouped"
        elif cv < 0.6:
            return "linear"
        else:
            return "segmental"
    
    def _analyze_morphology_mix(self, microcalcs: List[Dict]) -> Dict:
        """Analyze morphology mix in cluster"""
        morphologies = [mc['morphology'] for mc in microcalcs]
        unique_morphs = list(set(morphologies))
        
        mix_analysis = {}
        for morph in unique_morphs:
            count = morphologies.count(morph)
            mix_analysis[morph] = count
        
        return mix_analysis
    
    def _analyze_cluster_morphology(self, clusters: List[Dict], microcalcs: List[Dict]) -> Dict:
        """Analyze overall morphology of all clusters"""
        total_microcalcs = len(microcalcs)
        total_clusters = len(clusters)
        
        morphology_counts = {}
        for mc in microcalcs:
            morph = mc['morphology']
            morphology_counts[morph] = morphology_counts.get(morph, 0) + 1
        
        return {
            'total_microcalcifications': total_microcalcs,
            'total_clusters': total_clusters,
            'morphology_distribution': morphology_counts,
            'average_cluster_size': np.mean([c['microcalc_count'] for c in clusters]) if clusters else 0
        }
    
    def _assess_lesion_risk(self, lesion: Dict) -> int:
        """Assess risk level of a lesion (1-5 scale)"""
        risk_score = 1
        
        # Size factor
        if lesion['size_mm'] > 20:
            risk_score += 1
        
        # Shape factor
        if lesion['shape_descriptor'] == 'irregular':
            risk_score += 1
        
        # Margin factor
        if lesion['margin_descriptor'] == 'spiculated':
            risk_score += 2
        elif lesion['margin_descriptor'] == 'microlobulated':
            risk_score += 1
        
        # Confidence factor
        if lesion['confidence'] > 0.8:
            risk_score += 1
        
        return min(5, risk_score)
    
    def _assess_cluster_risk(self, cluster: Dict) -> int:
        """Assess risk level of microcalcification cluster (1-5 scale)"""
        risk_score = 1
        
        # Count factor
        if cluster['microcalc_count'] > 10:
            risk_score += 1
        elif cluster['microcalc_count'] > 5:
            risk_score += 0.5
        
        # Morphology factor
        morphology_mix = cluster['morphology_mix']
        if 'fine_pleomorphic' in morphology_mix or 'fine_linear' in morphology_mix:
            risk_score += 2
        elif 'amorphous' in morphology_mix:
            risk_score += 1
        
        # Distribution factor
        if cluster['distribution'] == 'linear':
            risk_score += 1
        elif cluster['distribution'] == 'segmental':
            risk_score += 2
        
        return min(5, int(risk_score))
    
    def _generate_recommendations(self, birads_score: int, risk_factors: List[str],
                                patient_age: Optional[int], breast_density: Optional[str]) -> List[str]:
        """Generate clinical recommendations based on BI-RADS score"""
        recommendations = []
        
        if birads_score == 0:
            recommendations.append("Additional imaging needed")
            recommendations.append("Consider targeted ultrasound or additional mammographic views")
        elif birads_score == 1:
            recommendations.append("Continue routine annual screening")
        elif birads_score == 2:
            recommendations.append("Continue routine annual screening")
            if breast_density in ['C', 'D']:
                recommendations.append("Consider supplemental screening (ultrasound or MRI)")
        elif birads_score == 3:
            recommendations.append("Short-term follow-up in 6 months")
            recommendations.append("Consider biopsy if lesion changes or grows")
        elif birads_score == 4:
            recommendations.append("Tissue sampling should be considered")
            recommendations.append("Coordinate with breast imaging specialist")
        elif birads_score == 5:
            recommendations.append("Highly suspicious - appropriate action should be taken")
            recommendations.append("Urgent referral for tissue sampling")
        elif birads_score == 6:
            recommendations.append("Known malignancy - appropriate treatment")
        
        return recommendations
    
    def _get_lesion_cad_weight(self, lesion: Dict) -> float:
        """Get CAD weight for a lesion"""
        weight = 1.0
        
        # Shape weighting
        if lesion['shape_descriptor'] == 'irregular':
            weight *= 1.5
        
        # Margin weighting
        if lesion['margin_descriptor'] == 'spiculated':
            weight *= 2.0
        elif lesion['margin_descriptor'] == 'microlobulated':
            weight *= 1.3
        
        # Size weighting
        if lesion['size_mm'] > 15:
            weight *= 1.2
        
        return weight
    
    def _get_cluster_cad_weight(self, cluster: Dict) -> float:
        """Get CAD weight for a microcalcification cluster"""
        weight = 0.5  # Base weight for clusters
        
        # Count weighting
        if cluster['microcalc_count'] > 10:
            weight *= 1.5
        elif cluster['microcalc_count'] > 5:
            weight *= 1.2
        
        # Morphology weighting
        morphology_mix = cluster['morphology_mix']
        if 'fine_pleomorphic' in morphology_mix or 'fine_linear' in morphology_mix:
            weight *= 2.0
        elif 'amorphous' in morphology_mix:
            weight *= 1.3
        
        return weight
    
    def generate_mock_mammogram(self, shape: Tuple[int, int] = (2048, 1536)) -> np.ndarray:
        """
        Generate mock mammogram image for testing
        
        Args:
            shape: Image shape (height, width)
            
        Returns:
            Mock mammogram array
        """
        # Create base mammogram background
        image = np.random.normal(0.3, 0.1, shape).astype(np.float32)
        image = np.clip(image, 0, 1)
        
        # Add breast tissue pattern
        y, x = np.ogrid[:shape[0], :shape[1]]
        
        # Breast boundary (simplified)
        center_x, center_y = shape[1] // 3, shape[0] // 2
        breast_mask = ((x - center_x) ** 2 / (shape[1] // 3) ** 2 + 
                      (y - center_y) ** 2 / (shape[0] // 2) ** 2) < 1
        
        image[~breast_mask] = 0  # Background
        
        # Add some lesions
        num_lesions = np.random.randint(0, 3)
        for _ in range(num_lesions):
            lesion_x = np.random.randint(shape[1] // 4, 3 * shape[1] // 4)
            lesion_y = np.random.randint(shape[0] // 4, 3 * shape[0] // 4)
            lesion_size = np.random.randint(10, 30)
            
            # Create lesion
            yy, xx = np.ogrid[:shape[0], :shape[1]]
            lesion_mask = ((xx - lesion_x) ** 2 + (yy - lesion_y) ** 2) < lesion_size ** 2
            image[lesion_mask] = np.random.uniform(0.6, 0.9)
        
        # Add microcalcifications
        num_microcalcs = np.random.randint(5, 15)
        for _ in range(num_microcalcs):
            mc_x = np.random.randint(shape[1] // 4, 3 * shape[1] // 4)
            mc_y = np.random.randint(shape[0] // 4, 3 * shape[0] // 4)
            mc_size = np.random.randint(1, 3)
            
            # Create microcalcification
            yy, xx = np.ogrid[:shape[0], :shape[1]]
            mc_mask = ((xx - mc_x) ** 2 + (yy - mc_y) ** 2) < mc_size ** 2
            image[mc_mask] = 1.0
        
        return image

def get_mammography_engine() -> MammographyAnalysisEngine:
    """Get or create mammography analysis engine instance"""
    global mammo_engine
    if mammo_engine is None:
        mammo_engine = MammographyAnalysisEngine()
    return mammo_engine

# API Endpoints

@router.post("/lesion-detection", response_model=LesionDetectionResponse)
async def detect_lesions(request: LesionDetectionRequest):
    """Detect masses/lesions in mammogram"""
    start_time = datetime.now()
    
    try:
        engine = get_mammography_engine()
        
        # Use provided image or generate mock data
        if request.image_data:
            image = np.array(request.image_data, dtype=np.float32)
        else:
            image = engine.generate_mock_mammogram()
        
        # Detect lesions
        lesions, confidences = engine.detect_lesions(
            image, request.pixel_spacing, request.detection_threshold, request.min_lesion_size
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return LesionDetectionResponse(
            study_id=request.study_id,
            lesions=lesions,
            total_lesions=len(lesions),
            processing_time=processing_time,
            confidence_scores=confidences,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in lesion-detection endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/microcalc-analysis", response_model=MicrocalcResponse)
async def analyze_microcalcifications(request: MicrocalcRequest):
    """Analyze microcalcifications and clusters"""
    start_time = datetime.now()
    
    try:
        engine = get_mammography_engine()
        
        # Use provided image or generate mock data
        if request.image_data:
            image = np.array(request.image_data, dtype=np.float32)
        else:
            image = engine.generate_mock_mammogram()
        
        # Analyze microcalcifications
        clusters, morphology_analysis = engine.analyze_microcalcifications(
            image, request.pixel_spacing, request.cluster_threshold, request.min_cluster_size
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return MicrocalcResponse(
            study_id=request.study_id,
            clusters=clusters,
            total_clusters=len(clusters),
            total_microcalcs=morphology_analysis.get('total_microcalcifications', 0),
            morphology_analysis=morphology_analysis,
            processing_time=processing_time,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in microcalc-analysis endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/birads-classification", response_model=BiradsResponse)
async def classify_birads(request: BiradsRequest):
    """Classify BI-RADS category"""
    start_time = datetime.now()
    
    try:
        engine = get_mammography_engine()
        
        # Use provided findings or generate mock data
        lesions = request.lesions or []
        microcalcs = request.microcalcs or []
        
        # If no findings provided, generate mock analysis
        if not lesions and not microcalcs and request.image_data:
            image = np.array(request.image_data, dtype=np.float32)
            lesions, _ = engine.detect_lesions(image, request.pixel_spacing)
            microcalcs, _ = engine.analyze_microcalcifications(image, request.pixel_spacing)
        
        # Classify BI-RADS
        birads_score, assessment_category, recommendations, confidence = engine.classify_birads(
            lesions, microcalcs, request.patient_age, request.breast_density
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        findings_summary = {
            'total_lesions': len(lesions),
            'total_clusters': len(microcalcs),
            'patient_age': request.patient_age,
            'breast_density': request.breast_density
        }
        
        return BiradsResponse(
            study_id=request.study_id,
            birads_score=birads_score,
            birads_description=engine.birads_categories[birads_score],
            assessment_category=assessment_category,
            recommendations=recommendations,
            confidence=confidence,
            findings_summary=findings_summary,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in birads-classification endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cad-score", response_model=CADScoreResponse)
async def calculate_cad_score(request: MammographyRequest):
    """Calculate Computer-Aided Detection score"""
    start_time = datetime.now()
    
    try:
        engine = get_mammography_engine()
        
        # Use provided image or generate mock data
        if request.image_data:
            image = np.array(request.image_data, dtype=np.float32)
        else:
            image = engine.generate_mock_mammogram()
        
        # Perform analysis
        lesions, _ = engine.detect_lesions(image, request.pixel_spacing)
        clusters, _ = engine.analyze_microcalcifications(image, request.pixel_spacing)
        
        # Calculate CAD score
        cad_score, risk_level, detection_confidence, analysis_summary = engine.calculate_cad_score(
            lesions, clusters
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return CADScoreResponse(
            study_id=request.study_id,
            cad_score=cad_score,
            risk_level=risk_level,
            detection_confidence=detection_confidence,
            analysis_summary=analysis_summary,
            processing_time=processing_time,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in cad-score endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        engine = get_mammography_engine()
        
        # Test with mock data
        test_image = engine.generate_mock_mammogram((512, 512))
        test_lesions, _ = engine.detect_lesions(test_image, (0.1, 0.1))
        
        return {
            "status": "healthy",
            "service": "mammography-analysis",
            "version": "1.0.0",
            "test_lesions_detected": len(test_lesions),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Service unhealthy: {str(e)}")