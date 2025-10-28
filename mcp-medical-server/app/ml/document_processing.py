"""Document Processing Pipeline - Combines all ML models for automated form filling"""
from typing import Dict, Any, Optional, List
import json
from pathlib import Path

from app.ml.speech_recognition import SpeechRecognitionService
from app.ml.face_recognition_service import FaceRecognitionService
from app.ml.ocr_service import OCRService


class DocumentProcessingPipeline:
    """End-to-end document processing combining speech, face, and OCR"""
    
    def __init__(self):
        self.speech_service = SpeechRecognitionService()
        self.face_service = FaceRecognitionService()
        self.ocr_service = OCRService()
    
    def process_preauth_workflow(
        self,
        patient_photo_path: Optional[str] = None,
        audio_dictation_path: Optional[str] = None,
        id_card_image_path: Optional[str] = None,
        form_image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete pre-authorization workflow:
        1. Identify patient from photo
        2. Transcribe clinical dictation
        3. Extract ID information
        4. Extract form data
        5. Combine all data
        
        Args:
            patient_photo_path: Path to patient photo (for identification)
            audio_dictation_path: Path to audio file (clinical dictation)
            id_card_image_path: Path to ID card image
            form_image_path: Path to form image to extract from
        
        Returns:
            Complete pre-auth form data ready for submission
        """
        
        combined_data = {
            "success": True,
            "workflow": "preauth_automation",
            "timestamp": None,
            "patient_identification": None,
            "clinical_data": None,
            "identity_data": None,
            "form_data": None,
            "final_form": None,
            "confidence_score": 0.0,
            "errors": []
        }
        
        from datetime import datetime
        combined_data["timestamp"] = datetime.now().isoformat()
        
        # Step 1: Identify patient from photo
        if patient_photo_path:
            combined_data["patient_identification"] = self._identify_patient_step(
                patient_photo_path
            )
            if not combined_data["patient_identification"].get("success"):
                combined_data["errors"].append(
                    "Patient identification failed"
                )
        
        # Step 2: Transcribe clinical dictation
        if audio_dictation_path:
            combined_data["clinical_data"] = self._transcribe_clinical_step(
                audio_dictation_path
            )
            if not combined_data["clinical_data"].get("success"):
                combined_data["errors"].append(
                    "Clinical transcription failed"
                )
        
        # Step 3: Extract ID information
        if id_card_image_path:
            combined_data["identity_data"] = self._extract_identity_step(
                id_card_image_path
            )
            if not combined_data["identity_data"].get("success"):
                combined_data["errors"].append(
                    "Identity extraction failed"
                )
        
        # Step 4: Extract form data
        if form_image_path:
            combined_data["form_data"] = self._extract_form_step(
                form_image_path
            )
            if not combined_data["form_data"].get("success"):
                combined_data["errors"].append(
                    "Form extraction failed"
                )
        
        # Step 5: Combine all data into final form
        combined_data["final_form"] = self._combine_all_data(combined_data)
        
        # Calculate overall confidence
        combined_data["confidence_score"] = self._calculate_confidence(combined_data)
        
        # Set success based on critical fields
        if combined_data["final_form"]:
            combined_data["success"] = True
        else:
            combined_data["success"] = False
        
        return combined_data
    
    def process_patient_onboarding(
        self,
        patient_photo_path: str,
        id_card_image_path: str,
        audio_introduction_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Patient onboarding workflow:
        1. Register patient face
        2. Extract ID information
        3. Extract audio introduction
        
        Returns:
            Patient profile data
        """
        
        profile = {
            "success": True,
            "face_registered": False,
            "identity_extracted": False,
            "audio_captured": False,
            "patient_data": {},
            "errors": []
        }
        
        # Step 1: Register face
        face_result = self.face_service.register_patient_face(
            patient_photo_path,
            patient_id="",
            patient_name=""
        )
        
        if face_result.get("success"):
            profile["face_registered"] = True
        else:
            profile["errors"].append(f"Face registration failed: {face_result.get('error')}")
        
        # Step 2: Extract ID
        id_result = self.ocr_service.extract_medical_id(
            id_card_image_path,
            id_type="sa_id"
        )
        
        if id_result.get("success"):
            profile["identity_extracted"] = True
            profile["patient_data"].update(id_result.get("extracted_data", {}))
        else:
            profile["errors"].append(f"ID extraction failed: {id_result.get('error')}")
        
        # Step 3: Audio introduction (optional)
        if audio_introduction_path:
            audio_result = self.speech_service.transcribe_audio(
                audio_introduction_path,
                language="eng"
            )
            
            if audio_result.get("success"):
                profile["audio_captured"] = True
                profile["patient_data"]["introduction"] = audio_result.get("text")
            else:
                profile["errors"].append(
                    f"Audio capture failed: {audio_result.get('error')}"
                )
        
        # Register with proper ID if we extracted it
        if profile["patient_data"].get("id_number"):
            self.face_service.register_patient_face(
                patient_photo_path,
                patient_id=profile["patient_data"]["id_number"],
                patient_name=profile["patient_data"].get("name", "Unknown")
            )
        
        profile["success"] = (
            profile["face_registered"] and 
            profile["identity_extracted"]
        )
        
        return profile
    
    def extract_all_preauth_fields(
        self,
        audio_path: str,
        id_card_path: str,
        form_image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract all pre-auth required fields from all sources
        
        Returns:
            All extracted fields consolidated
        """
        
        all_fields = {}
        
        # From audio
        if audio_path:
            audio_result = self.speech_service.transcribe_preauth_form(audio_path)
            if audio_result.get("success"):
                all_fields.update(audio_result.get("extracted_fields", {}))
        
        # From ID card
        if id_card_path:
            id_result = self.ocr_service.extract_medical_id(id_card_path)
            if id_result.get("success"):
                id_data = id_result.get("extracted_data", {})
                # Map OCR fields to standard field names
                all_fields["patient_id"] = id_data.get("id_number")
                all_fields["patient_name"] = id_data.get("name")
                if "date_of_birth" in id_data:
                    all_fields["date_of_birth"] = id_data["date_of_birth"]
        
        # From form image
        if form_image_path:
            form_result = self.ocr_service.extract_form_fields(form_image_path, "preauth")
            if form_result.get("success"):
                all_fields.update(form_result.get("extracted_fields", {}))
        
        return {
            "success": True,
            "extracted_fields": all_fields,
            "field_count": len(all_fields),
            "ready_for_submission": self._validate_preauth_form(all_fields)
        }
    
    def batch_process_documents(
        self,
        documents: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Process multiple documents in batch
        
        Each document dict should have:
        {
            "type": "preauth|patient_info|insurance",
            "patient_photo": "path/to/photo",
            "audio": "path/to/audio",
            "id_card": "path/to/id",
            "form": "path/to/form"
        }
        
        Returns:
            List of processed documents
        """
        
        results = []
        
        for doc in documents:
            if doc.get("type") == "preauth":
                result = self.process_preauth_workflow(
                    patient_photo_path=doc.get("patient_photo"),
                    audio_dictation_path=doc.get("audio"),
                    id_card_image_path=doc.get("id_card"),
                    form_image_path=doc.get("form")
                )
            elif doc.get("type") == "patient_onboarding":
                result = self.process_patient_onboarding(
                    patient_photo_path=doc.get("patient_photo"),
                    id_card_image_path=doc.get("id_card"),
                    audio_introduction_path=doc.get("audio")
                )
            else:
                result = {"success": False, "error": f"Unknown document type: {doc.get('type')}"}
            
            results.append(result)
        
        return {
            "batch_process": True,
            "document_count": len(documents),
            "processed_count": len([r for r in results if r.get("success")]),
            "results": results
        }
    
    # Private helper methods
    
    def _identify_patient_step(self, patient_photo_path: str) -> Dict[str, Any]:
        """Step 1: Identify patient from photo"""
        result = self.face_service.identify_patient(patient_photo_path)
        
        return {
            "success": result.get("success", False),
            "patient_id": result.get("patient_id"),
            "patient_name": result.get("patient_name"),
            "confidence": result.get("confidence", 0),
            "error": result.get("error")
        }
    
    def _transcribe_clinical_step(self, audio_path: str) -> Dict[str, Any]:
        """Step 2: Transcribe clinical dictation"""
        result = self.speech_service.transcribe_preauth_form(audio_path)
        
        return {
            "success": result.get("success", False),
            "raw_text": result.get("text"),
            "extracted_fields": result.get("extracted_fields", {}),
            "error": result.get("error")
        }
    
    def _extract_identity_step(self, id_card_path: str) -> Dict[str, Any]:
        """Step 3: Extract ID information"""
        result = self.ocr_service.extract_medical_id(
            id_card_path,
            id_type="sa_id"
        )
        
        return {
            "success": result.get("success", False),
            "extracted_data": result.get("extracted_data", {}),
            "confidence": result.get("confidence", 0),
            "error": result.get("error")
        }
    
    def _extract_form_step(self, form_image_path: str) -> Dict[str, Any]:
        """Step 4: Extract form data"""
        result = self.ocr_service.extract_form_fields(
            form_image_path,
            form_type="preauth"
        )
        
        return {
            "success": result.get("success", False),
            "extracted_fields": result.get("extracted_fields", {}),
            "confidence": result.get("confidence", 0),
            "error": result.get("error")
        }
    
    def _combine_all_data(self, combined_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step 5: Combine all extracted data"""
        final_form = {}
        
        # From patient identification
        if combined_data["patient_identification"]:
            final_form["patient_id"] = combined_data["patient_identification"].get("patient_id")
            final_form["patient_name"] = combined_data["patient_identification"].get("patient_name")
        
        # From clinical data
        if combined_data["clinical_data"] and combined_data["clinical_data"].get("success"):
            final_form.update(
                combined_data["clinical_data"].get("extracted_fields", {})
            )
        
        # From identity data
        if combined_data["identity_data"] and combined_data["identity_data"].get("success"):
            final_form.update(
                combined_data["identity_data"].get("extracted_data", {})
            )
        
        # From form data
        if combined_data["form_data"] and combined_data["form_data"].get("success"):
            final_form.update(
                combined_data["form_data"].get("extracted_fields", {})
            )
        
        return final_form if final_form else None
    
    def _calculate_confidence(self, combined_data: Dict[str, Any]) -> float:
        """Calculate overall confidence score"""
        scores = []
        
        if combined_data["patient_identification"]:
            conf = combined_data["patient_identification"].get("confidence", 0)
            if conf > 0:
                scores.append(conf)
        
        if combined_data["clinical_data"] and combined_data["clinical_data"].get("success"):
            scores.append(0.85)  # Audio transcription generally reliable
        
        if combined_data["identity_data"]:
            conf = combined_data["identity_data"].get("confidence", 0)
            if conf > 0:
                scores.append(conf)
        
        if combined_data["form_data"]:
            conf = combined_data["form_data"].get("confidence", 0)
            if conf > 0:
                scores.append(conf)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _validate_preauth_form(self, fields: Dict[str, Any]) -> bool:
        """Check if form has all required pre-auth fields"""
        required_fields = [
            "patient_id",
            "patient_name",
            "procedure",
            "urgency"
        ]
        
        return all(fields.get(field) for field in required_fields)
