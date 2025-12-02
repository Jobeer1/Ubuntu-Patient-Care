"""
Lightweight ML Models Integration Layer
Facial recognition, fingerprint matching, and identity validation
Optimized for low-resource devices (Raspberry Pi, low-end laptops)
"""

import os
import json
import logging
import hashlib
import sqlite3
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import numpy as np
from dataclasses import dataclass, asdict
from enum import Enum
import threading

# Try importing optional ML libraries (graceful fallback if not installed)
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import face_recognition  # dlib-based, ~50MB lightweight
    HAS_FACE_RECOGNITION = True
except ImportError:
    HAS_FACE_RECOGNITION = False

logger = logging.getLogger(__name__)

# =============================================
# Data Classes & Enums
# =============================================

class ModelType(Enum):
    """Supported ML model types"""
    FACIAL_RECOGNITION = "facial_recognition"
    FINGERPRINT_MATCHING = "fingerprint_matching"
    IDENTITY_VALIDATION = "identity_validation"
    NAME_FUZZY_MATCH = "name_fuzzy_match"

class ConfidenceLevel(Enum):
    """Confidence thresholds for matches"""
    HIGH = 0.95      # >95% confidence (certain match)
    MEDIUM = 0.85    # 85-95% confidence (probable match)
    LOW = 0.70       # 70-85% confidence (possible match)
    INSUFFICIENT = 0.0  # <70% confidence (not a match)

@dataclass
class BiometricMatch:
    """Result of a biometric matching operation"""
    matched: bool
    confidence: float
    match_type: str  # 'facial', 'fingerprint', 'combined'
    patient_id: Optional[int]
    distance_metric: Optional[float]
    algorithm_version: str
    timestamp: str
    explanation: str

@dataclass
class FamilyLink:
    """Connection between patients (family members)"""
    patient_id: int
    family_member_id: int
    relationship: str  # 'parent', 'child', 'sibling', 'spouse', 'other'
    confidence: float
    match_sources: List[str]  # ['facial', 'phone', 'name', 'address']
    verified: bool
    created_at: str

# =============================================
# Facial Recognition Engine (Lightweight)
# =============================================

class FacialRecognitionEngine:
    """
    Lightweight facial recognition using face_recognition library
    - <50MB model size (dlib models)
    - Can recognize 1000+ faces per minute on CPU
    - Suitable for Raspberry Pi 4+
    """
    
    def __init__(self, db_path: str = './ris.db', model: str = 'hog'):
        """
        Initialize facial recognition engine
        
        Args:
            db_path: Path to SQLite database
            model: 'hog' (faster) or 'cnn' (more accurate, slower)
        """
        self.db_path = db_path
        self.model = model
        self.available = HAS_FACE_RECOGNITION
        self.face_encodings_cache = {}  # In-memory cache for speed
        self.lock = threading.RLock()
        
        if not self.available:
            logger.warning("face_recognition library not installed. Facial recognition disabled.")
    
    def enroll_patient_face(self, patient_id: int, image_path: str, 
                           image_bytes: Optional[bytes] = None) -> Tuple[bool, Dict]:
        """
        Enroll a patient's facial biometric
        
        Args:
            patient_id: Patient ID
            image_path: Path to face image
            image_bytes: Optional image bytes (overrides image_path)
        
        Returns:
            (success, result_dict)
        """
        if not self.available:
            return False, {'error': 'Face recognition library not available'}
        
        try:
            # Load image
            if image_bytes:
                import io
                from PIL import Image
                img = Image.open(io.BytesIO(image_bytes))
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                image_array = np.array(img)
            else:
                image_array = face_recognition.load_image_file(image_path)
            
            # Detect faces in image
            face_locations = face_recognition.face_locations(image_array, model=self.model)
            
            if not face_locations:
                return False, {
                    'error': 'No face detected in image',
                    'face_count': 0
                }
            
            if len(face_locations) > 1:
                logger.warning(f"Multiple faces detected for patient {patient_id}")
            
            # Generate facial encodings (128-dimensional vector)
            face_encodings = face_recognition.face_encodings(
                image_array, 
                face_locations
            )
            
            # Take first face (primary face)
            face_encoding = face_encodings[0]
            
            # Store encoding in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if patient already has facial encoding
            cursor.execute("""
                SELECT id FROM facial_encodings 
                WHERE patient_id = ? AND is_primary = 1
            """, (patient_id,))
            
            existing = cursor.fetchone()
            
            # Encode as compressed JSON
            encoding_json = json.dumps(face_encoding.tolist())
            encoding_hash = hashlib.sha256(encoding_json.encode()).hexdigest()
            
            if existing:
                # Update existing
                cursor.execute("""
                    UPDATE facial_encodings 
                    SET encoding = ?, encoding_hash = ?, updated_at = ?
                    WHERE patient_id = ? AND is_primary = 1
                """, (encoding_json, encoding_hash, datetime.utcnow().isoformat(), patient_id))
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO facial_encodings 
                    (patient_id, encoding, encoding_hash, is_primary, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (patient_id, encoding_json, encoding_hash, 1, datetime.utcnow().isoformat()))
            
            conn.commit()
            conn.close()
            
            # Cache for fast lookups
            with self.lock:
                self.face_encodings_cache[patient_id] = face_encoding
            
            return True, {
                'patient_id': patient_id,
                'faces_detected': len(face_locations),
                'encoding_hash': encoding_hash,
                'model_used': self.model,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error enrolling face for patient {patient_id}: {str(e)}")
            return False, {'error': str(e)}
    
    def identify_patient_by_face(self, image_path: str = None, 
                                image_bytes: bytes = None,
                                distance_threshold: float = 0.6) -> List[BiometricMatch]:
        """
        Identify patient from facial image
        
        Args:
            image_path: Path to query face image
            image_bytes: Optional image bytes
            distance_threshold: Maximum distance for match (0.6 = strict)
        
        Returns:
            List of potential matches sorted by confidence
        """
        if not self.available:
            return []
        
        try:
            # Load query image
            if image_bytes:
                import io
                from PIL import Image
                img = Image.open(io.BytesIO(image_bytes))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                query_image = np.array(img)
            else:
                query_image = face_recognition.load_image_file(image_path)
            
            # Detect and encode faces in query image
            query_locations = face_recognition.face_locations(query_image, model=self.model)
            if not query_locations:
                return []
            
            query_encodings = face_recognition.face_encodings(query_image, query_locations)
            if not query_encodings:
                return []
            
            query_encoding = query_encodings[0]  # Use first/primary face
            
            # Load all enrolled facial encodings from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fe.patient_id, fe.encoding, p.first_name, p.last_name
                FROM facial_encodings fe
                JOIN patients p ON fe.patient_id = p.id
                WHERE fe.is_primary = 1
                ORDER BY fe.updated_at DESC
            """)
            
            enrolled_faces = cursor.fetchall()
            conn.close()
            
            matches = []
            
            # Compare query encoding against all enrolled faces
            for patient_id, encoding_json, first_name, last_name in enrolled_faces:
                try:
                    enrolled_encoding = np.array(json.loads(encoding_json))
                    
                    # Calculate face distance (lower = more similar)
                    distance = face_recognition.face_distance(
                        [enrolled_encoding], 
                        query_encoding
                    )[0]
                    
                    # Skip if distance exceeds threshold
                    if distance > distance_threshold:
                        continue
                    
                    # Convert distance to confidence (0-1, higher = better)
                    # Distance 0.0 = perfect match (confidence 1.0)
                    # Distance 0.6 = threshold (confidence 0.0)
                    confidence = max(0, 1.0 - (distance / distance_threshold))
                    
                    if confidence >= ConfidenceLevel.LOW.value:
                        matches.append(BiometricMatch(
                            matched=confidence >= ConfidenceLevel.MEDIUM.value,
                            confidence=round(confidence, 3),
                            match_type='facial',
                            patient_id=patient_id,
                            distance_metric=round(distance, 3),
                            algorithm_version='face_recognition_1.4',
                            timestamp=datetime.utcnow().isoformat(),
                            explanation=f"Facial match with {first_name} {last_name} (distance: {distance:.3f})"
                        ))
                
                except Exception as e:
                    logger.error(f"Error comparing faces for patient {patient_id}: {str(e)}")
                    continue
            
            # Sort by confidence (highest first)
            matches.sort(key=lambda x: x.confidence, reverse=True)
            
            return matches
        
        except Exception as e:
            logger.error(f"Error identifying patient by face: {str(e)}")
            return []

# =============================================
# Fingerprint Recognition Engine (Lightweight)
# =============================================

class FingerprintEngine:
    """
    Lightweight fingerprint matching
    - Uses minutiae-based matching (openCV)
    - Alternative: NBIS (free, open-source)
    - Template size: ~1KB per fingerprint
    """
    
    def __init__(self, db_path: str = './ris.db'):
        self.db_path = db_path
        self.available = HAS_CV2
        
        if not self.available:
            logger.warning("OpenCV not available. Fingerprint matching disabled.")
    
    def enroll_fingerprint(self, patient_id: int, finger_position: str,
                          image_path: str = None, 
                          image_bytes: bytes = None) -> Tuple[bool, Dict]:
        """
        Enroll patient fingerprint
        
        Args:
            patient_id: Patient ID
            finger_position: 'thumb_left', 'index_left', 'middle_left', etc.
            image_path: Path to fingerprint image
            image_bytes: Optional image bytes
        
        Returns:
            (success, result_dict)
        """
        if not self.available:
            return False, {'error': 'OpenCV not available'}
        
        try:
            # Load fingerprint image
            if image_bytes:
                import io
                nparr = np.frombuffer(image_bytes, np.uint8)
                fingerprint = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            else:
                fingerprint = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            
            if fingerprint is None:
                return False, {'error': 'Could not load fingerprint image'}
            
            # Extract minutiae points (simplified approach)
            # In production, use NBIS or commercial library
            minutiae = self._extract_minutiae(fingerprint)
            
            # Store fingerprint template in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            minutiae_json = json.dumps(minutiae, default=str)
            
            cursor.execute("""
                INSERT INTO fingerprints 
                (patient_id, finger_position, minutiae, created_at)
                VALUES (?, ?, ?, ?)
            """, (patient_id, finger_position, minutiae_json, datetime.utcnow().isoformat()))
            
            conn.commit()
            conn.close()
            
            return True, {
                'patient_id': patient_id,
                'finger_position': finger_position,
                'minutiae_count': len(minutiae),
                'timestamp': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error enrolling fingerprint for patient {patient_id}: {str(e)}")
            return False, {'error': str(e)}
    
    def identify_by_fingerprint(self, image_path: str = None,
                               image_bytes: bytes = None,
                               min_matching_points: int = 8) -> List[BiometricMatch]:
        """
        Identify patient from fingerprint image
        
        Args:
            image_path: Path to query fingerprint image
            image_bytes: Optional image bytes
            min_matching_points: Minimum points for match (8-12 typical)
        
        Returns:
            List of potential matches
        """
        if not self.available:
            return []
        
        try:
            # Load query fingerprint
            if image_bytes:
                import io
                nparr = np.frombuffer(image_bytes, np.uint8)
                query_print = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            else:
                query_print = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            
            if query_print is None:
                return []
            
            query_minutiae = self._extract_minutiae(query_print)
            
            # Load all enrolled fingerprints
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.patient_id, f.minutiae, p.first_name, p.last_name
                FROM fingerprints f
                JOIN patients p ON f.patient_id = p.id
                ORDER BY f.created_at DESC
            """)
            
            enrolled_prints = cursor.fetchall()
            conn.close()
            
            matches = []
            
            # Compare minutiae against all enrolled fingerprints
            for patient_id, minutiae_json, first_name, last_name in enrolled_prints:
                try:
                    enrolled_minutiae = json.loads(minutiae_json)
                    
                    # Count matching minutiae points
                    matching_points = self._match_minutiae(query_minutiae, enrolled_minutiae)
                    
                    if matching_points >= min_matching_points:
                        # Confidence based on matching points
                        # Max ~30 points typical per fingerprint
                        confidence = min(1.0, matching_points / 15.0)
                        
                        matches.append(BiometricMatch(
                            matched=matching_points >= min_matching_points,
                            confidence=round(confidence, 3),
                            match_type='fingerprint',
                            patient_id=patient_id,
                            distance_metric=matching_points,
                            algorithm_version='minutiae_extraction_1.0',
                            timestamp=datetime.utcnow().isoformat(),
                            explanation=f"Fingerprint match with {first_name} {last_name} ({matching_points} points)"
                        ))
                
                except Exception as e:
                    logger.error(f"Error comparing fingerprints for patient {patient_id}: {str(e)}")
                    continue
            
            matches.sort(key=lambda x: x.confidence, reverse=True)
            return matches
        
        except Exception as e:
            logger.error(f"Error identifying by fingerprint: {str(e)}")
            return []
    
    @staticmethod
    def _extract_minutiae(fingerprint_image: np.ndarray) -> List[Dict]:
        """
        Extract minutiae points from fingerprint image (simplified)
        In production, use proper NBIS/SourceAFIS implementation
        
        Returns:
            List of minutiae points with coordinates and angle
        """
        # Simplified minutiae extraction
        # Proper implementation would use NBIS library
        
        # Apply threshold
        _, binary = cv2.threshold(fingerprint_image, 127, 255, cv2.THRESH_BINARY)
        
        # Skeletonize (extract ridge lines)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        skeleton = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        # Find contours (ridge endpoints and bifurcations)
        contours, _ = cv2.findContours(skeleton, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        minutiae = []
        for i, contour in enumerate(contours[:20]):  # Limit to top 20 points
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                minutiae.append({
                    'x': cx,
                    'y': cy,
                    'type': 'ridge_endpoint',  # or 'bifurcation'
                    'angle': int(np.arctan2(cy, cx) * 180 / np.pi)
                })
        
        return minutiae
    
    @staticmethod
    def _match_minutiae(query_minutiae: List[Dict], 
                       enrolled_minutiae: List[Dict]) -> int:
        """
        Match two sets of minutiae points
        
        Returns:
            Number of matching minutiae points
        """
        matching_count = 0
        
        # Simple distance-based matching
        # Production: use proper alignment algorithm
        for q_point in query_minutiae:
            for e_point in enrolled_minutiae:
                # Calculate distance between points
                dist = np.sqrt(
                    (q_point['x'] - e_point['x']) ** 2 +
                    (q_point['y'] - e_point['y']) ** 2
                )
                
                # If points are close and angle similar, count as match
                if dist < 20:  # 20-pixel tolerance
                    angle_diff = abs(q_point['angle'] - e_point['angle'])
                    if angle_diff < 30 or angle_diff > 330:  # 30-degree tolerance
                        matching_count += 1
                        break
        
        return matching_count

# =============================================
# Identity Matching Engine
# =============================================

class IdentityMatcher:
    """
    Multi-modal identity matching combining:
    - Fuzzy name matching
    - Date of birth validation
    - Phone number normalization
    - Address similarity
    - ID number validation
    """
    
    def __init__(self, db_path: str = './ris.db'):
        self.db_path = db_path
    
    def fuzzy_name_match(self, name1: str, name2: str) -> float:
        """
        Calculate name similarity (0-1)
        Uses Levenshtein-like similarity
        """
        try:
            from difflib import SequenceMatcher
            # Normalize names
            n1 = ' '.join(name1.lower().split())
            n2 = ' '.join(name2.lower().split())
            
            # Calculate similarity ratio
            ratio = SequenceMatcher(None, n1, n2).ratio()
            return round(ratio, 3)
        except:
            return 0.0
    
    def validate_id_number(self, id_type: str, id_number: str) -> Tuple[bool, str]:
        """
        Validate ID number based on format
        Supports: South African ID, Passport, etc.
        """
        if id_type == 'SA_ID':
            # South African ID validation
            if len(id_number) != 13 or not id_number.isdigit():
                return False, "Invalid format"
            
            # Luhn algorithm check
            digits = [int(d) for d in id_number]
            checksum = sum(digits[::2]) + sum([sum(divmod(int(d) * 2, 10)) for d in [id_number[i] for i in range(1, 13, 2)]])
            
            if checksum % 10 == 0:
                return True, "Valid"
            return False, "Checksum failed"
        
        return True, "Format not validated"
    
    def normalize_phone(self, phone: str) -> str:
        """Normalize phone number to standard format"""
        # Remove non-digits
        normalized = ''.join(filter(str.isdigit, phone))
        
        # If South African, ensure +27 prefix
        if len(normalized) == 10 and normalized[0] == '0':
            normalized = '27' + normalized[1:]
        elif len(normalized) == 9:
            normalized = '27' + normalized
        
        return normalized
    
    def match_patients(self, patient_data: Dict) -> List[Tuple[int, float]]:
        """
        Find potential duplicate patients in database
        
        Returns:
            List of (patient_id, match_confidence) tuples
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all patients for comparison
        cursor.execute("""
            SELECT id, first_name, last_name, date_of_birth, phone, id_number
            FROM patients
            WHERE status = 'active'
        """)
        
        existing_patients = cursor.fetchall()
        conn.close()
        
        matches = []
        
        for existing_id, first_name, last_name, dob, phone, id_num in existing_patients:
            confidence = 0.0
            
            # Name matching (40% weight)
            name_sim = self.fuzzy_name_match(
                f"{patient_data.get('first_name', '')} {patient_data.get('last_name', '')}",
                f"{first_name} {last_name}"
            )
            confidence += name_sim * 0.4
            
            # Date of birth matching (20% weight)
            if patient_data.get('date_of_birth') == dob:
                confidence += 0.2
            
            # Phone matching (20% weight)
            if phone and patient_data.get('phone'):
                if self.normalize_phone(phone) == self.normalize_phone(patient_data['phone']):
                    confidence += 0.2
            
            # ID number matching (20% weight)
            if id_num and patient_data.get('id_number'):
                if id_num == patient_data['id_number']:
                    confidence += 0.2
            
            if confidence > 0.5:  # Only return potential matches
                matches.append((existing_id, round(confidence, 3)))
        
        return sorted(matches, key=lambda x: x[1], reverse=True)
