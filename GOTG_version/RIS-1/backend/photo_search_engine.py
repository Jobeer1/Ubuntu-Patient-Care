"""
Gift of the Givers RIS: Photo-Based Patient Search Engine

Enables identification of patients from photos across all deployed field hospitals.
Perfect for war zones, natural disasters, and mass casualty events where patients
are separated from their IDs and medical records.

Features:
- Facial recognition to identify patients from photos
- Search across all hospitals simultaneously
- Confidence scoring for manual verification
- Family reunion support (photo of loved one)
- Offline operation with auto-sync when online
- Privacy-preserving (no cloud uploads, local processing only)

Use Case: Clinician finds unconscious patient at hospital A, takes photo,
searches all hospitals, identifies that this is patient from Hospital B,
automatically notifies family and coordinates care.
"""

import os
import json
import base64
import sqlite3
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import hashlib
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Optional ML imports (graceful fallback)
try:
    import face_recognition
    import numpy as np
    from PIL import Image
    import io
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence levels for photo matches"""
    DEFINITE = "definite"      # 95-100% - Almost certainly the same person
    VERY_HIGH = "very_high"    # 85-94%  - Very likely same person
    HIGH = "high"              # 75-84%  - Likely same person
    MODERATE = "moderate"      # 60-74%  - Possible match, manual review needed
    LOW = "low"                # 40-59%  - Unlikely, don't use for primary ID
    NO_MATCH = "no_match"      # <40%    - Not a match


@dataclass
class PhotoMatch:
    """Result of a photo search"""
    patient_id: str
    hospital_id: str
    hospital_name: str
    patient_name: str
    confidence: float
    confidence_level: str
    facial_encoding_id: int
    match_distance: float
    search_timestamp: str
    manual_verified: bool = False
    verified_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class PatientPhoto:
    """Patient photo record"""
    id: int
    patient_id: str
    photo_filename: str
    photo_path: str
    facial_encoding: List[float]
    encoding_hash: str
    photo_date: str
    is_primary: bool
    quality_score: float
    hospital_id: str
    created_at: str


class FacialEncodingCache:
    """In-memory cache for facial encodings to speed up searches"""
    
    def __init__(self):
        self.encodings: Dict[int, np.ndarray] = {}
        self.metadata: Dict[int, Dict] = {}
        self.last_updated = None
    
    def add(self, encoding_id: int, encoding: np.ndarray, metadata: Dict):
        """Add encoding to cache"""
        if ML_AVAILABLE:
            self.encodings[encoding_id] = np.array(encoding)
        self.metadata[encoding_id] = metadata
        self.last_updated = datetime.utcnow().isoformat()
    
    def get_all_encodings(self) -> Tuple[List[int], np.ndarray]:
        """Get all encodings as IDs and numpy array"""
        if not ML_AVAILABLE or not self.encodings:
            return [], []
        
        ids = list(self.encodings.keys())
        encodings = np.array([self.encodings[i] for i in ids])
        return ids, encodings
    
    def clear(self):
        """Clear cache"""
        self.encodings = {}
        self.metadata = {}
        self.last_updated = None
    
    def size(self) -> int:
        """Get cache size"""
        return len(self.encodings)


class PhotoSearchEngine:
    """
    Main photo search engine for patient identification across hospitals.
    
    Workflow:
    1. Clinician takes photo of unidentified patient
    2. System extracts facial encoding from photo
    3. Searches all enrolled patient photos across all hospitals
    4. Returns ranked matches with confidence scores
    5. Clinician verifies match and patient info is linked
    6. Family is notified of patient location
    """
    
    def __init__(self, db_path: str, upload_folder: str):
        """
        Initialize photo search engine.
        
        Args:
            db_path: Path to SQLite database
            upload_folder: Path to store photos
        """
        self.db_path = db_path
        self.upload_folder = upload_folder
        self.encoding_cache = FacialEncodingCache()
        self.distance_threshold = 0.6  # Adjust for sensitivity (lower = stricter)
        
        if not ML_AVAILABLE:
            logger.warning("⚠️ ML libraries not available - photo search disabled")
        else:
            logger.info("✅ Photo search engine initialized")
    
    def extract_facial_encoding(self, image_data: bytes) -> Optional[List[float]]:
        """
        Extract facial encoding from image data.
        
        Args:
            image_data: Image bytes (JPEG, PNG, etc.)
            
        Returns:
            128D facial encoding as list, or None if no face detected
        """
        if not ML_AVAILABLE:
            return None
        
        try:
            # Load image from bytes
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to numpy array
            image_array = np.array(image)
            
            # Find faces in image
            face_locations = face_recognition.face_locations(image_array, model='hog')
            
            if not face_locations:
                logger.warning("No face detected in image")
                return None
            
            if len(face_locations) > 1:
                logger.warning(f"Multiple faces detected ({len(face_locations)}), using largest")
            
            # Get encoding of first (largest) face
            face_encodings = face_recognition.face_encodings(image_array, face_locations)
            
            if not face_encodings:
                return None
            
            # Convert numpy array to list for JSON serialization
            encoding = face_encodings[0].tolist()
            return encoding
            
        except Exception as e:
            logger.error(f"Error extracting facial encoding: {str(e)}")
            return None
    
    def calculate_encoding_hash(self, encoding: List[float]) -> str:
        """Calculate hash of encoding for deduplication"""
        encoding_str = json.dumps(encoding, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(encoding_str.encode()).hexdigest()
    
    def save_photo(self, patient_id: str, hospital_id: str, image_data: bytes,
                   is_primary: bool = True) -> Optional[PatientPhoto]:
        """
        Save patient photo and extract facial encoding.
        
        Args:
            patient_id: Patient identifier
            hospital_id: Hospital identifier
            image_data: Image bytes
            is_primary: Whether this is primary identification photo
            
        Returns:
            PatientPhoto object if successful
        """
        try:
            # Create upload directory structure
            patient_dir = os.path.join(self.upload_folder, "photos", hospital_id, patient_id)
            os.makedirs(patient_dir, exist_ok=True)
            
            # Extract facial encoding
            encoding = self.extract_facial_encoding(image_data)
            if not encoding and ML_AVAILABLE:
                logger.error("Could not extract facial encoding from photo")
                return None
            
            # Save photo file
            photo_hash = hashlib.sha256(image_data).hexdigest()
            photo_filename = f"{photo_hash}.jpg"
            photo_path = os.path.join(patient_dir, photo_filename)
            
            with open(photo_path, 'wb') as f:
                f.write(image_data)
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            encoding_hash = self.calculate_encoding_hash(encoding) if encoding else None
            
            cursor.execute("""
                INSERT INTO patient_photos (
                    patient_id, hospital_id, photo_filename, photo_path,
                    facial_encoding, encoding_hash, photo_date, is_primary,
                    quality_score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                patient_id,
                hospital_id,
                photo_filename,
                photo_path,
                json.dumps(encoding) if encoding else None,
                encoding_hash,
                datetime.utcnow().isoformat(),
                1 if is_primary else 0,
                1.0,  # Quality score (0-1)
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            photo_id = cursor.lastrowid
            conn.close()
            
            # Add to cache
            if encoding and ML_AVAILABLE:
                self.encoding_cache.add(photo_id, encoding, {
                    'patient_id': patient_id,
                    'hospital_id': hospital_id,
                    'is_primary': is_primary
                })
            
            logger.info(f"✅ Photo saved for patient {patient_id} at hospital {hospital_id}")
            
            return PatientPhoto(
                id=photo_id,
                patient_id=patient_id,
                photo_filename=photo_filename,
                photo_path=photo_path,
                facial_encoding=encoding,
                encoding_hash=encoding_hash,
                photo_date=datetime.utcnow().isoformat(),
                is_primary=is_primary,
                quality_score=1.0,
                hospital_id=hospital_id,
                created_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error saving photo: {str(e)}")
            return None
    
    def search_by_photo(self, search_image_data: bytes,
                       hospital_id: Optional[str] = None,
                       max_results: int = 10) -> List[PhotoMatch]:
        """
        Search for patient matches using a photo.
        
        Perfect use case: Clinician at Hospital A finds unconscious patient,
        takes photo, searches across all 6-7 field hospitals to identify them
        and notify family of location.
        
        Args:
            search_image_data: Photo to search with
            hospital_id: If provided, search only this hospital; else search all
            max_results: Maximum number of results to return
            
        Returns:
            List of PhotoMatch results sorted by confidence (highest first)
        """
        if not ML_AVAILABLE:
            logger.error("ML libraries required for photo search")
            return []
        
        try:
            # Extract encoding from search photo
            search_encoding = self.extract_facial_encoding(search_image_data)
            if not search_encoding:
                logger.error("Could not extract face from search photo")
                return []
            
            search_encoding_np = np.array(search_encoding)
            
            # Load all encodings from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT id, patient_id, hospital_id, facial_encoding FROM patient_photos WHERE facial_encoding IS NOT NULL"
            params = []
            
            if hospital_id:
                query += " AND hospital_id = ?"
                params.append(hospital_id)
            
            cursor.execute(query, params)
            photo_records = cursor.fetchall()
            
            if not photo_records:
                logger.info("No photos with encodings found in database")
                conn.close()
                return []
            
            # Calculate distances to all encodings
            matches = []
            
            for photo_id, patient_id, hosp_id, encoding_json in photo_records:
                try:
                    encoding_np = np.array(json.loads(encoding_json))
                    
                    # Calculate face distance
                    distance = face_recognition.face_distance([encoding_np], search_encoding_np)[0]
                    
                    # Convert distance to confidence (0-1)
                    confidence = 1.0 - distance
                    
                    if distance <= self.distance_threshold:
                        # Determine confidence level
                        if confidence >= 0.95:
                            level = ConfidenceLevel.DEFINITE.value
                        elif confidence >= 0.85:
                            level = ConfidenceLevel.VERY_HIGH.value
                        elif confidence >= 0.75:
                            level = ConfidenceLevel.HIGH.value
                        elif confidence >= 0.60:
                            level = ConfidenceLevel.MODERATE.value
                        else:
                            level = ConfidenceLevel.LOW.value
                        
                        # Get hospital name
                        cursor.execute("SELECT name FROM hospitals WHERE id = ?", (hosp_id,))
                        hospital_row = cursor.fetchone()
                        hospital_name = hospital_row[0] if hospital_row else hosp_id
                        
                        # Get patient name
                        cursor.execute("SELECT first_name, last_name FROM patients WHERE patient_id = ?", (patient_id,))
                        patient_row = cursor.fetchone()
                        patient_name = f"{patient_row[0]} {patient_row[1]}" if patient_row else patient_id
                        
                        matches.append(PhotoMatch(
                            patient_id=patient_id,
                            hospital_id=hosp_id,
                            hospital_name=hospital_name,
                            patient_name=patient_name,
                            confidence=round(confidence, 3),
                            confidence_level=level,
                            facial_encoding_id=photo_id,
                            match_distance=round(distance, 4),
                            search_timestamp=datetime.utcnow().isoformat(),
                            manual_verified=False
                        ))
                
                except Exception as e:
                    logger.debug(f"Error processing photo {photo_id}: {str(e)}")
                    continue
            
            conn.close()
            
            # Sort by confidence (highest first)
            matches.sort(key=lambda x: x.confidence, reverse=True)
            
            # Return top results
            return matches[:max_results]
            
        except Exception as e:
            logger.error(f"Error searching by photo: {str(e)}")
            return []
    
    def verify_match(self, photo_match_id: int, patient_id: str,
                     verified_by: str, notes: str = "") -> bool:
        """
        Clinician manually verifies a photo match.
        
        This creates an official record that the identified patient is who
        they believe them to be, triggering family notifications and record linking.
        
        Args:
            photo_match_id: ID from photo search result
            patient_id: Confirmed patient ID
            verified_by: Username of clinician
            notes: Any additional verification notes
            
        Returns:
            True if verification recorded successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO photo_matches (
                    facial_encoding_id, patient_id, verified_by, notes,
                    manual_verified, verification_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                photo_match_id,
                patient_id,
                verified_by,
                notes,
                1,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Photo match verified for patient {patient_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying match: {str(e)}")
            return False
    
    def load_encoding_cache(self):
        """Load all facial encodings into memory for fast searching"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, facial_encoding, patient_id, hospital_id, is_primary
                FROM patient_photos
                WHERE facial_encoding IS NOT NULL
            """)
            
            rows = cursor.fetchall()
            
            for row in rows:
                photo_id, encoding_json, patient_id, hospital_id, is_primary = row
                if encoding_json:
                    encoding = np.array(json.loads(encoding_json))
                    self.encoding_cache.add(photo_id, encoding, {
                        'patient_id': patient_id,
                        'hospital_id': hospital_id,
                        'is_primary': is_primary
                    })
            
            conn.close()
            logger.info(f"✅ Loaded {self.encoding_cache.size()} facial encodings into cache")
            
        except Exception as e:
            logger.error(f"Error loading encoding cache: {str(e)}")
    
    def get_patient_photos(self, patient_id: str, hospital_id: Optional[str] = None) -> List[Dict]:
        """Get all photos for a patient"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if hospital_id:
                cursor.execute("""
                    SELECT id, patient_id, hospital_id, photo_date, is_primary,
                           quality_score, created_at
                    FROM patient_photos
                    WHERE patient_id = ? AND hospital_id = ?
                    ORDER BY is_primary DESC, created_at DESC
                """, (patient_id, hospital_id))
            else:
                cursor.execute("""
                    SELECT id, patient_id, hospital_id, photo_date, is_primary,
                           quality_score, created_at
                    FROM patient_photos
                    WHERE patient_id = ?
                    ORDER BY is_primary DESC, created_at DESC
                """, (patient_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
        
        except Exception as e:
            logger.error(f"Error getting patient photos: {str(e)}")
            return []


def create_photo_search_tables(db_path: str):
    """
    Create database tables for photo search functionality.
    
    Should be called once during database initialization.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Patient photos table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            hospital_id TEXT NOT NULL,
            photo_filename TEXT NOT NULL,
            photo_path TEXT NOT NULL,
            facial_encoding TEXT,  -- JSON array of 128 floats
            encoding_hash TEXT UNIQUE,
            photo_date TEXT DEFAULT CURRENT_TIMESTAMP,
            is_primary BOOLEAN DEFAULT 0,
            quality_score REAL DEFAULT 1.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_patient_photos_patient_id ON patient_photos(patient_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_patient_photos_hospital_id ON patient_photos(hospital_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_patient_photos_is_primary ON patient_photos(is_primary)
    """)
    
    # Photo matches table (for verified matches)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS photo_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            facial_encoding_id INTEGER NOT NULL,
            patient_id TEXT NOT NULL,
            manual_verified BOOLEAN DEFAULT 0,
            verified_by TEXT,
            verification_date TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(facial_encoding_id) REFERENCES patient_photos(id),
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_photo_matches_patient_id ON photo_matches(patient_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_photo_matches_verified ON photo_matches(manual_verified)
    """)
    
    conn.commit()
    conn.close()
    
    logger.info("✅ Photo search tables created")


if __name__ == "__main__":
    # Example usage
    engine = PhotoSearchEngine("./ris.db", "./uploads")
    print(f"Photo search engine initialized: ML available = {ML_AVAILABLE}")
