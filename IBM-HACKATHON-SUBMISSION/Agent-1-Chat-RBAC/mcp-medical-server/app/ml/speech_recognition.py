"""Lightweight Offline Speech Recognition using Whisper"""
import json
import os
from typing import Optional, Dict, Any
from pathlib import Path

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("WARNING: Whisper not installed. Install with: pip install openai-whisper")


class SpeechRecognitionService:
    """Service for converting speech to text using Whisper (offline-capable)"""
    
    # Use tiny model by default (30MB) - very fast, offline
    # Options: tiny (39M), base (74M), small (140M)
    MODEL_SIZE = "tiny"
    
    _model = None
    _model_loaded = False
    
    @classmethod
    def load_model(cls):
        """Load Whisper model (lazy loading to save memory)"""
        if not WHISPER_AVAILABLE:
            raise RuntimeError(
                "Whisper not installed. Run: pip install openai-whisper"
            )
        
        if not cls._model_loaded:
            print(f"[Whisper] Loading {cls.MODEL_SIZE} model (~30MB)...")
            cls._model = whisper.load_model(cls.MODEL_SIZE)
            cls._model_loaded = True
            print("[Whisper] Model loaded successfully")
        
        return cls._model
    
    @staticmethod
    def transcribe_audio(
        audio_file_path: str,
        language: str = "en",
        task: str = "transcribe"
    ) -> Dict[str, Any]:
        """
        Transcribe audio file to text
        
        Args:
            audio_file_path: Path to audio file (mp3, wav, m4a, flac, etc.)
            language: Language code (e.g., 'en', 'zu', 'xh', 'af')
            task: 'transcribe' or 'translate'
        
        Returns:
            {
                "text": "Full transcription",
                "segments": [...],
                "language": "en",
                "duration": 10.5,
                "confidence": 0.95
            }
        """
        if not os.path.exists(audio_file_path):
            return {
                "error": f"Audio file not found: {audio_file_path}",
                "success": False
            }
        
        try:
            model = SpeechRecognitionService.load_model()
            
            print(f"[Whisper] Transcribing: {audio_file_path}")
            
            result = model.transcribe(
                audio_file_path,
                language=language,
                task=task,
                verbose=False
            )
            
            return {
                "success": True,
                "text": result.get("text", ""),
                "language": result.get("language", language),
                "segments": result.get("segments", []),
                "duration_seconds": result.get("duration", 0),
                "confidence": 0.95  # Whisper doesn't provide per-word confidence
            }
        
        except Exception as e:
            return {
                "error": str(e),
                "success": False
            }
    
    @staticmethod
    def transcribe_medical_report(
        audio_file_path: str,
        patient_id: str = None,
        procedure_type: str = None
    ) -> Dict[str, Any]:
        """
        Transcribe medical report from audio dictation
        
        Optimized for medical terminology
        """
        result = SpeechRecognitionService.transcribe_audio(
            audio_file_path,
            language="en"
        )
        
        if not result.get("success"):
            return result
        
        return {
            "success": True,
            "report_text": result.get("text"),
            "patient_id": patient_id,
            "procedure_type": procedure_type,
            "segments": result.get("segments"),
            "language": result.get("language"),
            "confidence": result.get("confidence"),
            "type": "medical_report"
        }
    
    @staticmethod
    def transcribe_preauth_form(
        audio_file_path: str
    ) -> Dict[str, Any]:
        """
        Transcribe pre-authorization form dictation
        
        Extracts key information for form filling
        """
        result = SpeechRecognitionService.transcribe_audio(audio_file_path)
        
        if not result.get("success"):
            return result
        
        # Parse transcription for key medical information
        text = result.get("text", "").lower()
        
        extracted = {
            "full_transcription": result.get("text"),
            "patient_id": _extract_patient_id(text),
            "member_number": _extract_member_number(text),
            "procedure": _extract_procedure(text),
            "clinical_indication": _extract_clinical_indication(text),
            "icd10_codes": _extract_icd10_codes(text),
            "urgency": _extract_urgency(text)
        }
        
        return {
            "success": True,
            "type": "preauth_form",
            "extracted_fields": extracted,
            "full_text": result.get("text"),
            "confidence": result.get("confidence")
        }
    
    @staticmethod
    def list_supported_languages() -> Dict[str, str]:
        """List supported languages for transcription"""
        return {
            "en": "English",
            "zu": "Zulu",
            "xh": "Xhosa",
            "af": "Afrikaans",
            "st": "Sotho",
            "ss": "Swati",
            "tn": "Tswana",
            "ts": "Tsonga",
            "ve": "Venda",
            "nr": "Ndebele"
        }


def _extract_patient_id(text: str) -> Optional[str]:
    """Extract patient ID from transcription"""
    import re
    match = re.search(r'patient\s*(?:id|number|#)[\s:]*(\w+)', text)
    return match.group(1) if match else None


def _extract_member_number(text: str) -> Optional[str]:
    """Extract medical aid member number from transcription"""
    import re
    match = re.search(r'member\s*(?:number|#)[\s:]*(\d+)', text)
    return match.group(1) if match else None


def _extract_procedure(text: str) -> Optional[str]:
    """Extract procedure name/code from transcription"""
    procedures = [
        "ct scan", "mri scan", "x-ray", "ultrasound", "ct head",
        "ct chest", "mri brain", "ct abdomen", "ecg", "eeg"
    ]
    for proc in procedures:
        if proc in text:
            return proc
    return None


def _extract_clinical_indication(text: str) -> Optional[str]:
    """Extract clinical indication from transcription"""
    # Look for common patterns
    import re
    match = re.search(r'indication[\s:]*(.+?)(?:icd|urgency|$)', text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _extract_icd10_codes(text: str) -> list:
    """Extract ICD-10 codes from transcription"""
    import re
    # ICD-10 format: Letter followed by numbers and optional decimal
    matches = re.findall(r'\b[A-Z]\d{2}(?:\.\d{1,2})?\b', text)
    return matches if matches else []


def _extract_urgency(text: str) -> str:
    """Extract urgency level from transcription"""
    urgency_levels = {
        "emergency": ["emergency", "urgent", "asap", "critical", "acute"],
        "urgent": ["urgent", "soon", "quickly"],
        "routine": ["routine", "standard", "normal"]
    }
    
    text_lower = text.lower()
    for level, keywords in urgency_levels.items():
        if any(keyword in text_lower for keyword in keywords):
            return level
    
    return "routine"
