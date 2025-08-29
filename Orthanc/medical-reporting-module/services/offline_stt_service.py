"""
Offline-first Speech-to-Text Service for Medical Reporting Module
Uses OpenAI Whisper for local speech recognition with medical terminology optimization
"""

import logging
import threading
import queue
import json
import time
import os
import tempfile
from typing import Dict, List, Any, Optional, Callable, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import uuid
import re

logger = logging.getLogger(__name__)

class STTMode(Enum):
    """STT operation modes"""
    OFFLINE_ONLY = "offline_only"
    ONLINE_PREFERRED = "online_preferred"
    HYBRID = "hybrid"

class AudioQuality(Enum):
    """Audio quality levels"""
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"

@dataclass
class STTResult:
    """Speech-to-text result"""
    text: str
    confidence: float
    timestamp: datetime
    audio_quality: AudioQuality
    processing_time: float
    mode_used: STTMode
    alternatives: List[str] = None
    
    def __post_init__(self):
        if self.alternatives is None:
            self.alternatives = []

@dataclass
class STTConfig:
    """STT configuration for offline-first operation"""
    mode: STTMode = STTMode.OFFLINE_ONLY
    language: str = "en"  # English only for South Africa
    model_size: str = "tiny"  # Whisper model: tiny (fastest), base, small, medium, large
    enable_medical_terminology: bool = True
    enable_learning: bool = True
    confidence_threshold: float = 0.6  # Lower threshold for tiny model
    
    # Online fallback settings (when available)
    azure_key: Optional[str] = None
    azure_region: Optional[str] = None
    google_credentials_path: Optional[str] = None
    
    # Audio processing
    sample_rate: int = 16000
    chunk_duration: float = 3.0  # Shorter chunks for faster processing

class OfflineSTTEngine:
    """Offline-first STT engine using OpenAI Whisper"""
    
    def __init__(self, config: STTConfig = None):
        self.config = config or STTConfig()
        self.whisper_model = None
        self.is_initialized = False
        
        # Medical terminology for English
        self.medical_vocabulary = self._load_medical_vocabulary()
        self.medical_corrections = {}
        
        # Processing queue
        self.audio_queue = queue.Queue()
        self.processing_thread = None
        self.is_processing = False
        
        # Callbacks
        self.transcription_callbacks: List[Callable] = []
        
        logger.info(f"Offline STT engine initialized with model size: {self.config.model_size}")
    
    def initialize(self) -> bool:
        """Initialize the Whisper model using standard Whisper loading"""
        try:
            # Try to import whisper
            try:
                import whisper
                self.whisper = whisper
            except ImportError:
                logger.error("OpenAI Whisper not installed. Install with: pip install openai-whisper")
                return False
            
            # Use Whisper's built-in model loading (handles download automatically)
            logger.info(f"Loading Whisper model: {self.config.model_size}")
            self.whisper_model = whisper.load_model(self.config.model_size)
            
            self.is_initialized = True
            logger.info(f"Whisper model {self.config.model_size} loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Whisper model: {e}")
            return False
    
    def _load_medical_vocabulary(self) -> Dict[str, str]:
        """Load medical vocabulary optimized for South African medical context"""
        return {
            # Respiratory conditions (high priority in SA)
            "tuberculosis": "tuberculosis",
            "tb": "tuberculosis", 
            "pneumonia": "pneumonia",
            "pneumoconiosis": "pneumoconiosis",
            "silicosis": "silicosis",
            "asbestosis": "asbestosis",
            
            # HIV-related (high prevalence in SA)
            "pneumocystis": "Pneumocystis",
            "pcp": "PCP",
            "kaposi": "Kaposi's",
            "sarcoma": "sarcoma",
            
            # Trauma (high incidence)
            "fracture": "fracture",
            "gunshot": "gunshot",
            "gsw": "GSW",
            "motor vehicle": "motor vehicle",
            "mva": "MVA",
            
            # Common findings
            "consolidation": "consolidation",
            "atelectasis": "atelectasis",
            "pleural effusion": "pleural effusion",
            "pneumothorax": "pneumothorax",
            "bilateral": "bilateral",
            "unilateral": "unilateral",
            
            # Standard phrases
            "within normal limits": "within normal limits",
            "no acute abnormality": "no acute abnormality",
            "unremarkable": "unremarkable",
            "consistent with": "consistent with",
            "suggestive of": "suggestive of",
            
            # Anatomical terms
            "right upper lobe": "right upper lobe",
            "right middle lobe": "right middle lobe", 
            "right lower lobe": "right lower lobe",
            "left upper lobe": "left upper lobe",
            "left lower lobe": "left lower lobe",
            "mediastinum": "mediastinum",
            "hilum": "hilum",
            "hila": "hila",
            "cardiac silhouette": "cardiac silhouette",
            "costophrenic": "costophrenic",
            "diaphragm": "diaphragm"
        }
    
    def start_processing(self) -> bool:
        """Start audio processing thread"""
        try:
            if not self.is_initialized:
                if not self.initialize():
                    return False
            
            if self.is_processing:
                return True
            
            self.is_processing = True
            self.processing_thread = threading.Thread(target=self._process_audio_loop)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            
            logger.info("Started offline STT processing")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start STT processing: {e}")
            return False
    
    def stop_processing(self) -> bool:
        """Stop audio processing thread"""
        try:
            self.is_processing = False
            
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=5.0)
            
            logger.info("Stopped offline STT processing")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop STT processing: {e}")
            return False
    
    def transcribe_audio_file(self, audio_file_path: str, user_id: str = None) -> Optional[str]:
        """Transcribe audio file directly - simplified version for demo with Windows compatibility"""
        try:
            if not self.is_initialized:
                if not self.initialize():
                    logger.error("STT engine not initialized")
                    return None
            
            # Verify file exists and is accessible
            if not os.path.exists(audio_file_path):
                logger.error(f"Audio file does not exist: {audio_file_path}")
                return None
            
            if not os.access(audio_file_path, os.R_OK):
                logger.error(f"Audio file not readable: {audio_file_path}")
                return None
            
            # For Windows compatibility, create a copy with a simple path
            import shutil
            temp_dir = tempfile.gettempdir()
            simple_filename = f"whisper_input_{int(time.time() * 1000)}.wav"
            simple_path = os.path.join(temp_dir, simple_filename)
            
            try:
                # Copy to simple path to avoid Windows path issues
                shutil.copy2(audio_file_path, simple_path)
                
                # Transcribe with Whisper using the simple path
                result = self.whisper_model.transcribe(
                    simple_path,
                    language=self.config.language,
                    task="transcribe",
                    fp16=False  # Ensure CPU compatibility
                )
                
            finally:
                # Clean up the copy
                try:
                    if os.path.exists(simple_path):
                        os.unlink(simple_path)
                except:
                    pass
            
            raw_text = result["text"].strip()
            
            if not raw_text:
                return None
            
            # Apply medical vocabulary corrections
            corrected_text = self._apply_medical_corrections(raw_text)
            
            logger.info(f"Transcribed audio file: '{raw_text}' -> '{corrected_text}'")
            return corrected_text
            
        except Exception as e:
            logger.error(f"Failed to transcribe audio file: {e}")
            return None

    def transcribe_audio(self, audio_data: bytes, user_id: str = None) -> Optional[STTResult]:
        """Transcribe audio using offline Whisper model"""
        try:
            if not self.is_initialized:
                logger.error("STT engine not initialized")
                return None
            
            start_time = time.time()
            
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_audio_path = temp_file.name
            
            try:
                # Transcribe with Whisper
                result = self.whisper_model.transcribe(
                    temp_audio_path,
                    language=self.config.language,
                    task="transcribe"
                )
                
                raw_text = result["text"].strip()
                
                if not raw_text:
                    return None
                
                # Apply medical vocabulary corrections
                corrected_text = self._apply_medical_corrections(raw_text)
                
                # Apply learned corrections if available
                if user_id and user_id in self.medical_corrections:
                    corrected_text = self._apply_learned_corrections(corrected_text, user_id)
                
                # Assess audio quality (simplified)
                audio_quality = self._assess_audio_quality(audio_data)
                
                # Calculate confidence (Whisper doesn't provide this directly)
                confidence = self._estimate_confidence(result, corrected_text)
                
                processing_time = time.time() - start_time
                
                stt_result = STTResult(
                    text=corrected_text,
                    confidence=confidence,
                    timestamp=datetime.utcnow(),
                    audio_quality=audio_quality,
                    processing_time=processing_time,
                    mode_used=STTMode.OFFLINE_ONLY
                )
                
                logger.info(f"Transcribed audio offline: {corrected_text[:50]}...")
                return stt_result
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_audio_path)
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Failed to transcribe audio offline: {e}")
            return None
    
    def _apply_medical_corrections(self, text: str) -> str:
        """Apply medical vocabulary corrections"""
        try:
            corrected_text = text.lower()
            
            # Apply medical vocabulary
            for term, correction in self.medical_vocabulary.items():
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(term.lower()) + r'\b'
                corrected_text = re.sub(pattern, correction, corrected_text, flags=re.IGNORECASE)
            
            # Capitalize sentences
            sentences = corrected_text.split('. ')
            capitalized_sentences = [s.capitalize() for s in sentences if s.strip()]
            corrected_text = '. '.join(capitalized_sentences)
            
            return corrected_text
            
        except Exception as e:
            logger.error(f"Failed to apply medical corrections: {e}")
            return text
    
    def _apply_learned_corrections(self, text: str, user_id: str) -> str:
        """Apply learned corrections from typist feedback"""
        try:
            if user_id not in self.medical_corrections:
                return text
            
            corrected_text = text
            user_corrections = self.medical_corrections[user_id]
            
            # Apply most recent corrections first
            for correction in reversed(user_corrections[-50:]):  # Last 50 corrections
                original = correction.get("original", "").lower()
                corrected = correction.get("corrected", "")
                
                if original and corrected and original in corrected_text.lower():
                    corrected_text = re.sub(
                        re.escape(original), 
                        corrected, 
                        corrected_text, 
                        flags=re.IGNORECASE
                    )
            
            return corrected_text
            
        except Exception as e:
            logger.error(f"Failed to apply learned corrections: {e}")
            return text
    
    def _assess_audio_quality(self, audio_data: bytes) -> AudioQuality:
        """Assess audio quality (simplified implementation)"""
        try:
            data_size = len(audio_data)
            
            # Simple heuristic based on data size and basic analysis
            if data_size < 1000:
                return AudioQuality.POOR
            elif data_size < 5000:
                return AudioQuality.FAIR
            elif data_size < 15000:
                return AudioQuality.GOOD
            else:
                return AudioQuality.EXCELLENT
                
        except Exception as e:
            logger.error(f"Failed to assess audio quality: {e}")
            return AudioQuality.FAIR
    
    def _estimate_confidence(self, whisper_result: dict, corrected_text: str) -> float:
        """Estimate confidence score from Whisper result"""
        try:
            # Whisper doesn't provide confidence directly
            # Use heuristics based on result characteristics
            
            base_confidence = 0.8  # Default confidence
            
            # Adjust based on text length (longer text usually more reliable)
            text_length = len(corrected_text.split())
            if text_length > 10:
                base_confidence += 0.1
            elif text_length < 3:
                base_confidence -= 0.2
            
            # Adjust based on medical vocabulary matches
            medical_matches = sum(1 for term in self.medical_vocabulary.keys() 
                                if term.lower() in corrected_text.lower())
            if medical_matches > 0:
                base_confidence += min(0.1, medical_matches * 0.02)
            
            # Ensure confidence is within bounds
            return max(0.1, min(0.95, base_confidence))
            
        except Exception as e:
            logger.error(f"Failed to estimate confidence: {e}")
            return 0.7
    
    def _process_audio_loop(self):
        """Main audio processing loop"""
        while self.is_processing:
            try:
                # Get audio from queue with timeout
                audio_item = self.audio_queue.get(timeout=1.0)
                
                if audio_item:
                    audio_data = audio_item.get("audio_data")
                    user_id = audio_item.get("user_id")
                    
                    if audio_data:
                        result = self.transcribe_audio(audio_data, user_id)
                        if result:
                            self._notify_transcription_callbacks(result)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in audio processing loop: {e}")
    
    def queue_audio(self, audio_data: bytes, user_id: str = None):
        """Queue audio for processing"""
        try:
            audio_item = {
                "audio_data": audio_data,
                "user_id": user_id,
                "timestamp": datetime.utcnow()
            }
            
            self.audio_queue.put(audio_item)
            
        except Exception as e:
            logger.error(f"Failed to queue audio: {e}")
    
    def record_correction(self, user_id: str, original_text: str, corrected_text: str) -> bool:
        """Record a correction for learning"""
        try:
            if user_id not in self.medical_corrections:
                self.medical_corrections[user_id] = []
            
            correction = {
                "original": original_text,
                "corrected": corrected_text,
                "timestamp": datetime.utcnow().isoformat(),
                "correction_id": str(uuid.uuid4())
            }
            
            self.medical_corrections[user_id].append(correction)
            
            # Keep only last 100 corrections per user to manage memory
            if len(self.medical_corrections[user_id]) > 100:
                self.medical_corrections[user_id] = self.medical_corrections[user_id][-100:]
            
            logger.info(f"Recorded correction for user {user_id}: '{original_text}' -> '{corrected_text}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record correction: {e}")
            return False
    
    def add_transcription_callback(self, callback: Callable):
        """Add callback for transcription results"""
        self.transcription_callbacks.append(callback)
    
    def _notify_transcription_callbacks(self, result: STTResult):
        """Notify transcription callbacks"""
        for callback in self.transcription_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in transcription callback: {e}")
    
    def get_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get STT engine statistics"""
        try:
            stats = {
                "mode": self.config.mode.value,
                "model_size": self.config.model_size,
                "language": self.config.language,
                "is_initialized": self.is_initialized,
                "is_processing": self.is_processing,
                "medical_vocabulary_size": len(self.medical_vocabulary),
                "queue_size": self.audio_queue.qsize()
            }
            
            if user_id and user_id in self.medical_corrections:
                stats["user_corrections"] = len(self.medical_corrections[user_id])
            
            total_corrections = sum(len(corrections) for corrections in self.medical_corrections.values())
            stats["total_corrections"] = total_corrections
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get STT stats: {e}")
            return {}

# Global offline STT engine instance
offline_stt_engine = OfflineSTTEngine()

# Initialize and start the engine
def initialize_offline_stt():
    """Initialize the offline STT engine"""
    return offline_stt_engine.initialize()

# Create a service instance for easy import
offline_stt_service = offline_stt_engine