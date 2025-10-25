"""
Face Recognition Authentication System for South African Medical Imaging
Advanced biometric authentication with privacy-focused design
"""

import os
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import sqlite3
import logging
from dataclasses import dataclass, asdict
import base64
import io
import hashlib
import secrets

try:
    import cv2
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("Warning: face_recognition not available. Install with: pip install face_recognition")

try:
    from PIL import Image
    import numpy as np
    IMAGING_AVAILABLE = True
except ImportError:
    IMAGING_AVAILABLE = False
    print("Warning: PIL not available. Install with: pip install Pillow")

from .south_african_localization import sa_localization

@dataclass
class FaceProfile:
    """Face profile data for user"""
    user_id: str
    face_encoding: str  # Base64 encoded face embedding
    face_image_hash: str  # Hash of reference image (for verification)
    enrollment_date: str
    last_used: Optional[str] = None
    usage_count: int = 0
    is_active: bool = True
    confidence_threshold: float = 0.6
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Don't include sensitive face encoding in API responses
        data.pop('face_encoding', None)
        return data

@dataclass
class FaceAuthAttempt:
    """Face authentication attempt record"""
    attempt_id: str
    user_id: str
    success: bool
    confidence_score: float
    ip_address: Optional[str]
    user_agent: Optional[str]
    failure_reason: Optional[str]
    attempted_at: str

class FaceRecognitionAuth:
    """Advanced face recognition authentication system"""
    
    def __init__(self, db_path: str = "face_auth.db"):
        self.db_path = db_path
        self.logger = self._setup_logging()
        self.face_encodings_cache = {}
        self.default_confidence_threshold = 0.6
        self.max_face_distance = 0.4  # Lower = more strict
        self._init_database()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for face recognition auth"""
        logger = logging.getLogger('face_auth')
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
        """Initialize face recognition database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Face profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_profiles (
                user_id TEXT PRIMARY KEY,
                face_encoding TEXT NOT NULL,
                face_image_hash TEXT NOT NULL,
                enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                confidence_threshold REAL DEFAULT 0.6
            )
        ''')
        
        # Face authentication attempts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_auth_attempts (
                attempt_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                confidence_score REAL,
                ip_address TEXT,
                user_agent TEXT,
                failure_reason TEXT,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Face recognition settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_auth_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Initialize default settings
        default_settings = {
            'enabled': 'false',
            'confidence_threshold': '0.6',
            'max_attempts_per_hour': '10',
            'require_liveness_detection': 'true',
            'allow_multiple_faces': 'false',
            'image_quality_threshold': '0.7'
        }
        
        for key, value in default_settings.items():
            cursor.execute('''
                INSERT OR IGNORE INTO face_auth_settings (setting_key, setting_value)
                VALUES (?, ?)
            ''', (key, value))
        
        conn.commit()
        conn.close()
    
    def enroll_face(self, user_id: str, face_image_data: bytes) -> Tuple[bool, str]:
        """Enroll a user's face for authentication"""
        if not FACE_RECOGNITION_AVAILABLE:
            return False, "Face recognition library not available"
        
        try:
            # Convert image data to numpy array
            image_array = self._bytes_to_image_array(face_image_data)
            if image_array is None:
                return False, "Invalid image format"
            
            # Detect faces in the image
            face_locations = face_recognition.face_locations(image_array)
            
            if len(face_locations) == 0:
                return False, "No face detected in image"
            
            if len(face_locations) > 1:
                return False, "Multiple faces detected. Please use image with single face"
            
            # Check image quality
            quality_score = self._assess_image_quality(image_array, face_locations[0])
            if quality_score < 0.7:
                return False, f"Image quality too low (score: {quality_score:.2f}). Please use better lighting and higher resolution"
            
            # Generate face encoding
            face_encodings = face_recognition.face_encodings(image_array, face_locations)
            
            if len(face_encodings) == 0:
                return False, "Could not generate face encoding"
            
            face_encoding = face_encodings[0]
            
            # Convert encoding to base64 for storage
            encoding_bytes = face_encoding.tobytes()
            encoding_b64 = base64.b64encode(encoding_bytes).decode('utf-8')
            
            # Generate hash of image for verification
            image_hash = hashlib.sha256(face_image_data).hexdigest()
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO face_profiles (
                    user_id, face_encoding, face_image_hash, enrollment_date, is_active
                ) VALUES (?, ?, ?, ?, ?)
            ''', (user_id, encoding_b64, image_hash, datetime.now().isoformat(), True))
            
            conn.commit()
            conn.close()
            
            # Update cache
            self.face_encodings_cache[user_id] = face_encoding
            
            self.logger.info(f"Face enrolled successfully for user {user_id}")
            return True, "Face enrolled successfully"
            
        except Exception as e:
            self.logger.error(f"Face enrollment failed for user {user_id}: {e}")
            return False, f"Enrollment failed: {str(e)}"
    
    def authenticate_face(self, user_id: str, face_image_data: bytes, 
                         ip_address: str = None, user_agent: str = None) -> Tuple[bool, str, float]:
        """Authenticate user using face recognition"""
        if not FACE_RECOGNITION_AVAILABLE:
            return False, "Face recognition not available", 0.0
        
        attempt_id = f"face_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}"
        
        try:
            # Check if face auth is enabled
            if not self._is_face_auth_enabled():
                return False, "Face authentication is disabled", 0.0
            
            # Check rate limiting
            if not self._check_rate_limit(user_id):
                self._log_auth_attempt(attempt_id, user_id, False, 0.0, ip_address, user_agent, "Rate limit exceeded")
                return False, "Too many attempts. Please try again later", 0.0
            
            # Get stored face encoding
            stored_encoding = self._get_stored_face_encoding(user_id)
            if stored_encoding is None:
                self._log_auth_attempt(attempt_id, user_id, False, 0.0, ip_address, user_agent, "No face profile found")
                return False, "No face profile found for user", 0.0
            
            # Convert input image to array
            image_array = self._bytes_to_image_array(face_image_data)
            if image_array is None:
                self._log_auth_attempt(attempt_id, user_id, False, 0.0, ip_address, user_agent, "Invalid image format")
                return False, "Invalid image format", 0.0
            
            # Detect faces
            face_locations = face_recognition.face_locations(image_array)
            
            if len(face_locations) == 0:
                self._log_auth_attempt(attempt_id, user_id, False, 0.0, ip_address, user_agent, "No face detected")
                return False, "No face detected in image", 0.0
            
            if len(face_locations) > 1:
                self._log_auth_attempt(attempt_id, user_id, False, 0.0, ip_address, user_agent, "Multiple faces detected")
                return False, "Multiple faces detected", 0.0
            
            # Generate encoding for input image
            face_encodings = face_recognition.face_encodings(image_array, face_locations)
            
            if len(face_encodings) == 0:
                self._log_auth_attempt(attempt_id, user_id, False, 0.0, ip_address, user_agent, "Could not generate face encoding")
                return False, "Could not process face", 0.0
            
            input_encoding = face_encodings[0]
            
            # Compare faces
            face_distance = face_recognition.face_distance([stored_encoding], input_encoding)[0]
            confidence_score = 1.0 - face_distance  # Convert distance to confidence
            
            # Get user's confidence threshold
            threshold = self._get_user_confidence_threshold(user_id)
            
            # Determine if authentication successful
            success = face_distance <= self.max_face_distance and confidence_score >= threshold
            
            if success:
                # Update usage statistics
                self._update_face_usage(user_id)
                self._log_auth_attempt(attempt_id, user_id, True, confidence_score, ip_address, user_agent, None)
                
                self.logger.info(f"Face authentication successful for user {user_id} (confidence: {confidence_score:.3f})")
                return True, "Face authentication successful", confidence_score
            else:
                failure_reason = f"Confidence too low: {confidence_score:.3f} < {threshold}"
                self._log_auth_attempt(attempt_id, user_id, False, confidence_score, ip_address, user_agent, failure_reason)
                
                self.logger.warning(f"Face authentication failed for user {user_id}: {failure_reason}")
                return False, "Face does not match", confidence_score
                
        except Exception as e:
            self.logger.error(f"Face authentication error for user {user_id}: {e}")
            self._log_auth_attempt(attempt_id, user_id, False, 0.0, ip_address, user_agent, f"System error: {str(e)}")
            return False, "Authentication system error", 0.0
    
    def _bytes_to_image_array(self, image_data: bytes) -> Optional[np.ndarray]:
        """Convert image bytes to numpy array"""
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to numpy array
            image_array = np.array(image)
            
            return image_array
            
        except Exception as e:
            self.logger.error(f"Image conversion failed: {e}")
            return None
    
    def _assess_image_quality(self, image_array: np.ndarray, face_location: Tuple[int, int, int, int]) -> float:
        """Assess the quality of face image for enrollment"""
        try:
            top, right, bottom, left = face_location
            
            # Extract face region
            face_image = image_array[top:bottom, left:right]
            
            # Check face size (should be at least 100x100 pixels)
            face_height, face_width = face_image.shape[:2]
            size_score = min(1.0, min(face_height, face_width) / 100.0)
            
            # Check brightness (avoid too dark or too bright)
            gray_face = cv2.cvtColor(face_image, cv2.COLOR_RGB2GRAY)
            brightness = np.mean(gray_face) / 255.0
            brightness_score = 1.0 - abs(brightness - 0.5) * 2  # Optimal around 0.5
            
            # Check contrast using standard deviation
            contrast_score = min(1.0, np.std(gray_face) / 64.0)  # Normalize by typical std
            
            # Check sharpness using Laplacian variance
            laplacian_var = cv2.Laplacian(gray_face, cv2.CV_64F).var()
            sharpness_score = min(1.0, laplacian_var / 500.0)  # Normalize
            
            # Weighted average of quality metrics
            quality_score = (
                size_score * 0.3 +
                brightness_score * 0.25 +
                contrast_score * 0.25 +
                sharpness_score * 0.2
            )
            
            return quality_score
            
        except Exception as e:
            self.logger.error(f"Image quality assessment failed: {e}")
            return 0.5  # Default moderate quality
    
    def _get_stored_face_encoding(self, user_id: str) -> Optional[np.ndarray]:
        """Get stored face encoding for user"""
        try:
            # Check cache first
            if user_id in self.face_encodings_cache:
                return self.face_encodings_cache[user_id]
            
            # Get from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT face_encoding FROM face_profiles 
                WHERE user_id = ? AND is_active = TRUE
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                # Decode base64 encoding
                encoding_bytes = base64.b64decode(result[0])
                face_encoding = np.frombuffer(encoding_bytes, dtype=np.float64)
                
                # Cache for future use
                self.face_encodings_cache[user_id] = face_encoding
                
                return face_encoding
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get stored face encoding for {user_id}: {e}")
            return None
    
    def _get_user_confidence_threshold(self, user_id: str) -> float:
        """Get confidence threshold for user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT confidence_threshold FROM face_profiles WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else self.default_confidence_threshold
            
        except Exception as e:
            self.logger.error(f"Failed to get confidence threshold for {user_id}: {e}")
            return self.default_confidence_threshold
    
    def _is_face_auth_enabled(self) -> bool:
        """Check if face authentication is enabled system-wide"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT setting_value FROM face_auth_settings WHERE setting_key = 'enabled'
            ''', )
            
            result = cursor.fetchone()
            conn.close()
            
            return result and result[0].lower() == 'true'
            
        except Exception as e:
            self.logger.error(f"Failed to check face auth status: {e}")
            return False
    
    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get max attempts per hour setting
            cursor.execute('''
                SELECT setting_value FROM face_auth_settings 
                WHERE setting_key = 'max_attempts_per_hour'
            ''')
            
            result = cursor.fetchone()
            max_attempts = int(result[0]) if result else 10
            
            # Count attempts in last hour
            one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
            
            cursor.execute('''
                SELECT COUNT(*) FROM face_auth_attempts 
                WHERE user_id = ? AND attempted_at > ?
            ''', (user_id, one_hour_ago))
            
            attempt_count = cursor.fetchone()[0]
            conn.close()
            
            return attempt_count < max_attempts
            
        except Exception as e:
            self.logger.error(f"Rate limit check failed for {user_id}: {e}")
            return True  # Allow on error
    
    def _update_face_usage(self, user_id: str):
        """Update face authentication usage statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE face_profiles 
                SET last_used = ?, usage_count = usage_count + 1
                WHERE user_id = ?
            ''', (datetime.now().isoformat(), user_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to update face usage for {user_id}: {e}")
    
    def _log_auth_attempt(self, attempt_id: str, user_id: str, success: bool, 
                         confidence_score: float, ip_address: str = None, 
                         user_agent: str = None, failure_reason: str = None):
        """Log face authentication attempt"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO face_auth_attempts (
                    attempt_id, user_id, success, confidence_score, ip_address, 
                    user_agent, failure_reason, attempted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                attempt_id, user_id, success, confidence_score, ip_address,
                user_agent, failure_reason, datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to log auth attempt: {e}")
    
    def get_user_face_profile(self, user_id: str) -> Optional[FaceProfile]:
        """Get user's face profile"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, face_encoding, face_image_hash, enrollment_date,
                       last_used, usage_count, is_active, confidence_threshold
                FROM face_profiles WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return FaceProfile(
                    user_id=result[0],
                    face_encoding=result[1],
                    face_image_hash=result[2],
                    enrollment_date=result[3],
                    last_used=result[4],
                    usage_count=result[5],
                    is_active=bool(result[6]),
                    confidence_threshold=result[7]
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get face profile for {user_id}: {e}")
            return None
    
    def disable_face_auth_for_user(self, user_id: str) -> bool:
        """Disable face authentication for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE face_profiles SET is_active = FALSE WHERE user_id = ?
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
            # Remove from cache
            self.face_encodings_cache.pop(user_id, None)
            
            self.logger.info(f"Face authentication disabled for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to disable face auth for {user_id}: {e}")
            return False
    
    def get_face_auth_stats(self) -> Dict[str, Any]:
        """Get face authentication statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total enrolled users
            cursor.execute('SELECT COUNT(*) FROM face_profiles WHERE is_active = TRUE')
            enrolled_users = cursor.fetchone()[0]
            
            # Recent attempts (last 24 hours)
            cursor.execute('''
                SELECT COUNT(*) FROM face_auth_attempts 
                WHERE attempted_at > datetime('now', '-24 hours')
            ''')
            recent_attempts = cursor.fetchone()[0]
            
            # Success rate (last 24 hours)
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    COUNT(*) as total
                FROM face_auth_attempts 
                WHERE attempted_at > datetime('now', '-24 hours')
            ''')
            
            result = cursor.fetchone()
            successful, total = result[0] or 0, result[1] or 0
            success_rate = (successful / total * 100) if total > 0 else 0
            
            # Average confidence score
            cursor.execute('''
                SELECT AVG(confidence_score) FROM face_auth_attempts 
                WHERE success = 1 AND attempted_at > datetime('now', '-24 hours')
            ''')
            
            avg_confidence = cursor.fetchone()[0] or 0.0
            
            conn.close()
            
            return {
                'enrolled_users': enrolled_users,
                'recent_attempts_24h': recent_attempts,
                'success_rate_24h': round(success_rate, 1),
                'average_confidence': round(avg_confidence, 3),
                'system_enabled': self._is_face_auth_enabled()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get face auth stats: {e}")
            return {}
    
    def update_system_settings(self, settings: Dict[str, str]) -> bool:
        """Update face authentication system settings"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for key, value in settings.items():
                cursor.execute('''
                    INSERT OR REPLACE INTO face_auth_settings (setting_key, setting_value, updated_at)
                    VALUES (?, ?, ?)
                ''', (key, value, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            self.logger.info("Face auth system settings updated")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update system settings: {e}")
            return False

# Global face recognition auth instance
face_recognition_auth = FaceRecognitionAuth()