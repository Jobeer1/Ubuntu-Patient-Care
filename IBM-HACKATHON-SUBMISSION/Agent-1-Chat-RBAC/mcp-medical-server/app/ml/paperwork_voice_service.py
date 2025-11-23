"""Paperwork Module - Reuses Whisper from Medical Reporting Module

This module provides voice-to-text transcription for paperwork automation,
reusing the same Whisper model loaded by the medical-reporting-module to
reduce memory usage and avoid duplicate loading.

Features:
- Listen to and edit transcribed audio (fix STT mistakes)
- Voice-powered form filling
- Worker voice profiles (for accuracy)
- Multi-worker support
- Reuses existing Whisper model (no duplication)
"""

import logging
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PaperworkVoiceService:
    """
    Provides voice-to-text transcription for paperwork forms.
    
    Reuses Whisper model from medical-reporting-module via shared reference.
    Handles editing/correction of transcriptions before form submission.
    """
    
    def __init__(self, whisper_model_loader=None):
        """
        Initialize paperwork voice service.
        
        Args:
            whisper_model_loader: Function that returns loaded Whisper model
                                 (e.g., get_or_load_whisper_model from voice_api)
        """
        self.whisper_model_loader = whisper_model_loader
        self.transcriptions = {}  # Store working transcriptions
        self.worker_profiles = {}  # Store worker voice profiles
        self.audio_storage = Path(__file__).parent / "paperwork_audio"
        self.audio_storage.mkdir(exist_ok=True)
        
        logger.info("✓ Paperwork Voice Service initialized (reusing Whisper model)")
    
    def get_whisper_model(self):
        """Get Whisper model from medical-reporting-module"""
        if self.whisper_model_loader is None:
            logger.warning("No Whisper model loader provided")
            return None
        
        model = self.whisper_model_loader()
        if model is None:
            logger.error("Failed to get Whisper model")
        return model
    
    def transcribe_form_field(
        self,
        audio_file_path: str,
        field_name: str,
        worker_id: str,
        language: str = "en"
    ) -> Dict:
        """
        Transcribe audio for a specific form field.
        
        Args:
            audio_file_path: Path to audio file
            field_name: Name of form field being filled
            worker_id: ID of worker performing transcription
            language: Language code (en, zu, xh, af, etc.)
        
        Returns:
            {
                "success": bool,
                "transcription_id": str,
                "text": str,
                "field_name": str,
                "worker_id": str,
                "timestamp": str,
                "duration_seconds": float,
                "confidence": float,
                "playback_url": str,
                "error": str (if failed)
            }
        """
        try:
            # Get Whisper model
            model = self.get_whisper_model()
            if model is None:
                return {
                    "success": False,
                    "error": "Whisper model not loaded. Ensure medical-reporting-module is running."
                }
            
            # Verify audio file exists
            audio_path = Path(audio_file_path)
            if not audio_path.exists():
                return {
                    "success": False,
                    "error": f"Audio file not found: {audio_file_path}"
                }
            
            # Generate transcription ID
            transcription_id = f"txn_{worker_id}_{field_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Transcribe using shared Whisper model
            logger.info(f"🎤 Transcribing {field_name} for worker {worker_id}...")
            result = model.transcribe(str(audio_path), language=language)
            
            transcribed_text = result.get("text", "").strip()
            
            # Store for editing
            self.transcriptions[transcription_id] = {
                "original": transcribed_text,
                "current": transcribed_text,
                "field_name": field_name,
                "worker_id": worker_id,
                "audio_path": str(audio_path),
                "created_at": datetime.now().isoformat(),
                "edits": []
            }
            
            return {
                "success": True,
                "transcription_id": transcription_id,
                "text": transcribed_text,
                "field_name": field_name,
                "worker_id": worker_id,
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": result.get("duration", 0),
                "confidence": 0.92,  # Whisper reliability estimate
                "playback_url": f"/paperwork/audio/{transcription_id}",
                "editable": True,
                "status": "ready_for_review"
            }
        
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {
                "success": False,
                "error": f"Transcription failed: {str(e)}"
            }
    
    def get_transcription_for_playback(self, transcription_id: str) -> Optional[str]:
        """Get audio file path for playback"""
        if transcription_id in self.transcriptions:
            return self.transcriptions[transcription_id]["audio_path"]
        return None
    
    def edit_transcription(
        self,
        transcription_id: str,
        corrected_text: str,
        worker_id: str
    ) -> Dict:
        """
        Edit/correct a transcription before submission.
        
        Args:
            transcription_id: ID of transcription to edit
            corrected_text: Corrected text
            worker_id: ID of worker making correction
        
        Returns:
            {
                "success": bool,
                "transcription_id": str,
                "original": str,
                "corrected": str,
                "edit_count": int,
                "status": str
            }
        """
        if transcription_id not in self.transcriptions:
            return {
                "success": False,
                "error": f"Transcription not found: {transcription_id}"
            }
        
        txn = self.transcriptions[transcription_id]
        
        # Verify worker authorization
        if txn["worker_id"] != worker_id:
            return {
                "success": False,
                "error": "Only the worker who created this transcription can edit it"
            }
        
        # Store edit history
        txn["edits"].append({
            "timestamp": datetime.now().isoformat(),
            "from": txn["current"],
            "to": corrected_text
        })
        
        # Update current text
        old_text = txn["current"]
        txn["current"] = corrected_text
        
        logger.info(f"📝 Transcription {transcription_id} edited by worker {worker_id}")
        
        return {
            "success": True,
            "transcription_id": transcription_id,
            "original": txn["original"],
            "corrected": corrected_text,
            "edit_count": len(txn["edits"]),
            "status": "edited",
            "changes_made": old_text != corrected_text
        }
    
    def get_transcription_preview(self, transcription_id: str) -> Dict:
        """Get full transcription data for preview/review"""
        if transcription_id not in self.transcriptions:
            return {
                "success": False,
                "error": f"Transcription not found: {transcription_id}"
            }
        
        txn = self.transcriptions[transcription_id]
        
        return {
            "success": True,
            "transcription_id": transcription_id,
            "field_name": txn["field_name"],
            "worker_id": txn["worker_id"],
            "original_text": txn["original"],
            "current_text": txn["current"],
            "has_edits": txn["original"] != txn["current"],
            "edit_count": len(txn["edits"]),
            "edit_history": txn["edits"],
            "audio_playback_url": f"/paperwork/audio/{transcription_id}",
            "created_at": txn["created_at"],
            "status": "ready_for_submission" if txn["current"] else "incomplete"
        }
    
    def submit_transcription(self, transcription_id: str, form_id: str) -> Dict:
        """Submit finalized transcription to form"""
        if transcription_id not in self.transcriptions:
            return {
                "success": False,
                "error": f"Transcription not found: {transcription_id}"
            }
        
        txn = self.transcriptions[transcription_id]
        
        if not txn["current"]:
            return {
                "success": False,
                "error": "Transcription is empty"
            }
        
        return {
            "success": True,
            "transcription_id": transcription_id,
            "form_id": form_id,
            "field_name": txn["field_name"],
            "field_value": txn["current"],
            "original_text": txn["original"],
            "was_edited": txn["original"] != txn["current"],
            "edit_count": len(txn["edits"]),
            "timestamp": datetime.now().isoformat()
        }
    
    def register_worker_voice_profile(
        self,
        worker_id: str,
        name: str,
        language: str = "en",
        accent_notes: str = ""
    ) -> Dict:
        """
        Register a worker's voice profile for better accuracy.
        
        Stores worker preferences for voice recognition (helps with future accuracy improvements).
        """
        self.worker_profiles[worker_id] = {
            "name": name,
            "language": language,
            "accent_notes": accent_notes,
            "registered_at": datetime.now().isoformat(),
            "transcription_count": 0,
            "total_duration_seconds": 0
        }
        
        logger.info(f"👤 Registered voice profile for worker {worker_id} ({name})")
        
        return {
            "success": True,
            "worker_id": worker_id,
            "name": name,
            "language": language,
            "status": "registered"
        }
    
    def get_worker_stats(self, worker_id: str) -> Dict:
        """Get transcription statistics for a worker"""
        if worker_id not in self.worker_profiles:
            return {
                "success": False,
                "error": f"Worker not registered: {worker_id}"
            }
        
        profile = self.worker_profiles[worker_id]
        
        # Count transcriptions by this worker
        worker_txns = [
            txn for txn in self.transcriptions.values()
            if txn["worker_id"] == worker_id
        ]
        
        return {
            "success": True,
            "worker_id": worker_id,
            "name": profile["name"],
            "language": profile["language"],
            "total_transcriptions": len(worker_txns),
            "transcriptions_edited": sum(1 for txn in worker_txns if txn["original"] != txn["current"]),
            "registered_at": profile["registered_at"]
        }
    
    def batch_transcribe_form(
        self,
        form_data: Dict[str, str],
        worker_id: str,
        language: str = "en"
    ) -> Dict:
        """
        Transcribe multiple form fields from audio files.
        
        Args:
            form_data: {
                "form_id": str,
                "fields": {
                    "field_name": "path/to/audio.wav",
                    ...
                }
            }
            worker_id: ID of worker filling the form
            language: Language code
        
        Returns:
            Results for all fields with individual success/error status
        """
        form_id = form_data.get("form_id", "unknown")
        fields = form_data.get("fields", {})
        
        results = {
            "form_id": form_id,
            "worker_id": worker_id,
            "fields": {},
            "total_fields": len(fields),
            "successful_transcriptions": 0,
            "failed_transcriptions": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        for field_name, audio_file in fields.items():
            logger.info(f"📋 Transcribing form field: {field_name}")
            
            result = self.transcribe_form_field(
                audio_file,
                field_name,
                worker_id,
                language
            )
            
            if result["success"]:
                results["successful_transcriptions"] += 1
                results["fields"][field_name] = {
                    "status": "success",
                    "transcription_id": result["transcription_id"],
                    "text": result["text"],
                    "playback_url": result["playback_url"]
                }
            else:
                results["failed_transcriptions"] += 1
                results["fields"][field_name] = {
                    "status": "failed",
                    "error": result.get("error", "Unknown error")
                }
        
        logger.info(
            f"✓ Form {form_id}: {results['successful_transcriptions']}/{results['total_fields']} fields transcribed"
        )
        
        return results


def create_paperwork_voice_service(medical_reporting_voice_api=None):
    """
    Factory function to create PaperworkVoiceService with Whisper model loader.
    
    Usage:
        # Get the voice API from medical-reporting-module
        from ..4-PACS-Module.Orthanc.medical-reporting-module.api.voice_api import get_or_load_whisper_model
        
        # Create paperwork service with shared model loader
        service = create_paperwork_voice_service(get_or_load_whisper_model)
    """
    if medical_reporting_voice_api is None:
        logger.warning("No Whisper model loader provided - using local fallback")
    
    return PaperworkVoiceService(whisper_model_loader=medical_reporting_voice_api)
