"""Lightweight Face Recognition for Patient Identification"""
from typing import Optional, Dict, Any, List
import os

try:
    import face_recognition
    import numpy as np
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("WARNING: face_recognition not installed. Install with: pip install face-recognition")


class FaceRecognitionService:
    """Service for facial recognition and patient identification (offline-capable)"""
    
    # Store known faces for patients
    _known_face_encodings = {}
    _known_face_names = {}
    
    @staticmethod
    def is_available() -> bool:
        """Check if face_recognition is available"""
        return FACE_RECOGNITION_AVAILABLE
    
    @staticmethod
    def register_patient_face(
        image_path: str,
        patient_id: str,
        patient_name: str
    ) -> Dict[str, Any]:
        """
        Register a patient's face for identification
        
        Args:
            image_path: Path to patient photo
            patient_id: Unique patient identifier
            patient_name: Patient name
        
        Returns:
            {
                "success": True,
                "patient_id": "patient123",
                "message": "Face registered successfully",
                "faces_detected": 1
            }
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return {
                "success": False,
                "error": "face_recognition not installed"
            }
        
        if not os.path.exists(image_path):
            return {
                "success": False,
                "error": f"Image not found: {image_path}"
            }
        
        try:
            # Load image
            image = face_recognition.load_image_file(image_path)
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(image)
            
            if len(face_encodings) == 0:
                return {
                    "success": False,
                    "error": "No face detected in image",
                    "message": "Please provide a clear photo of the patient's face"
                }
            
            if len(face_encodings) > 1:
                return {
                    "success": False,
                    "error": "Multiple faces detected",
                    "message": "Please provide image with only one face",
                    "faces_detected": len(face_encodings)
                }
            
            # Store encoding
            encoding = face_encodings[0]
            FaceRecognitionService._known_face_encodings[patient_id] = encoding
            FaceRecognitionService._known_face_names[patient_id] = patient_name
            
            return {
                "success": True,
                "patient_id": patient_id,
                "patient_name": patient_name,
                "message": "Face registered successfully",
                "faces_detected": 1
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def identify_patient(
        image_path: str,
        tolerance: float = 0.6
    ) -> Dict[str, Any]:
        """
        Identify patient from photo
        
        Args:
            image_path: Path to photo to identify
            tolerance: Face distance tolerance (0.0-1.0, lower=stricter)
        
        Returns:
            {
                "success": True,
                "patient_id": "patient123",
                "patient_name": "John Doe",
                "confidence": 0.95,
                "message": "Patient identified"
            }
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return {
                "success": False,
                "error": "face_recognition not installed"
            }
        
        if not os.path.exists(image_path):
            return {
                "success": False,
                "error": f"Image not found: {image_path}"
            }
        
        if not FaceRecognitionService._known_face_encodings:
            return {
                "success": False,
                "message": "No patients registered yet",
                "error": "Please register patient faces first"
            }
        
        try:
            # Load image
            image = face_recognition.load_image_file(image_path)
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(image)
            
            if len(face_encodings) == 0:
                return {
                    "success": False,
                    "error": "No face detected in image"
                }
            
            # Get first face
            face_encoding = face_encodings[0]
            
            # Compare with known faces
            known_ids = list(FaceRecognitionService._known_face_encodings.keys())
            known_encodings = list(FaceRecognitionService._known_face_encodings.values())
            
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
            
            best_match_index = np.argmin(face_distances)
            best_distance = face_distances[best_match_index]
            
            if best_distance < tolerance:
                patient_id = known_ids[best_match_index]
                patient_name = FaceRecognitionService._known_face_names[patient_id]
                confidence = 1 - best_distance
                
                return {
                    "success": True,
                    "patient_id": patient_id,
                    "patient_name": patient_name,
                    "confidence": float(confidence),
                    "distance": float(best_distance),
                    "message": f"Patient identified: {patient_name}"
                }
            else:
                return {
                    "success": False,
                    "message": "Patient not recognized",
                    "error": "No matching patient found",
                    "best_match_distance": float(best_distance),
                    "suggestion": "Please register this patient first"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def extract_patient_photo_from_document(
        document_image_path: str
    ) -> Dict[str, Any]:
        """
        Extract patient photo from ID document
        
        Useful for automatic patient registration from ID cards
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return {
                "success": False,
                "error": "face_recognition not installed"
            }
        
        if not os.path.exists(document_image_path):
            return {
                "success": False,
                "error": f"Image not found: {document_image_path}"
            }
        
        try:
            image = face_recognition.load_image_file(document_image_path)
            face_encodings = face_recognition.face_encodings(image)
            
            if len(face_encodings) == 0:
                return {
                    "success": False,
                    "error": "No face found in document"
                }
            
            if len(face_encodings) > 1:
                # Multiple faces - return first (probably patient photo)
                pass
            
            return {
                "success": True,
                "faces_detected": len(face_encodings),
                "message": f"Found {len(face_encodings)} face(s) in document",
                "can_use_for_registration": len(face_encodings) >= 1
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def list_registered_patients() -> Dict[str, Any]:
        """List all registered patients"""
        patients = []
        for patient_id, name in FaceRecognitionService._known_face_names.items():
            patients.append({
                "patient_id": patient_id,
                "patient_name": name,
                "registered": True
            })
        
        return {
            "success": True,
            "total_registered": len(patients),
            "patients": patients
        }
    
    @staticmethod
    def clear_patient_face(patient_id: str) -> Dict[str, Any]:
        """Remove a patient's face encoding"""
        if patient_id in FaceRecognitionService._known_face_encodings:
            del FaceRecognitionService._known_face_encodings[patient_id]
            del FaceRecognitionService._known_face_names[patient_id]
            return {
                "success": True,
                "message": f"Face for patient {patient_id} removed"
            }
        else:
            return {
                "success": False,
                "error": f"Patient {patient_id} not found"
            }
