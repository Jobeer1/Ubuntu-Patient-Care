"""
Speech-to-Text Service for Medical Reporting Module
Handles real-time speech recognition with medical terminology and South African accent support
"""

import logging
import threading
import queue
import json
import time
from typing import Dict, List, Any, Optional, Callable, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import uuid
import re

logger = logging.getLogger(__name__)

class STTProvider(Enum):
    """Available STT providers"""
    MOCK = "mock"
    GOOGLE = "google"
    AZURE = "azure"
    AWS = "aws"

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
    alternatives: List[str] = None
    
    def __post_init__(self):
        if self.alternatives is None:
            self.alternatives = []

@dataclass
class STTConfig:
    """STT configuration"""
    provider: STTProvider = STTProvider.MOCK
    language_code: str = "en-ZA"  # South African English
    sample_rate: int = 16000
    encoding: str = "LINEAR16"
    enable_automatic_punctuation: bool = True
    enable_word_time_offsets: bool = True
    model: str = "medical"
    use_enhanced: bool = True
    profanity_filter: bool = False
    speech_contexts: List[str] = None
    
    def __post_init__(self):
        if self.speech_contexts is None:
            self.speech_contexts = []

class VoiceCommandProcessor:
    """Processes voice commands for template selection and system control"""
    
    def __init__(self):
        self.command_patterns: Dict[str, Dict[str, Any]] = {}
        self.template_mappings: Dict[str, str] = {}
        self.confidence_threshold = 0.7
        
        self._initialize_command_patterns()
        self._initialize_template_mappings()
        
        logger.info("Voice command processor initialized")
    
    def _initialize_command_patterns(self):
        """Initialize voice command patterns"""
        self.command_patterns = {
            # Template loading patterns
            "load_template": {
                "patterns": [
                    r"load\s+(.*?)\s+template",
                    r"use\s+(.*?)\s+template",
                    r"open\s+(.*?)\s+template",
                    r"switch\s+to\s+(.*?)\s+template"
                ],
                "action": "load_template",
                "extract_parameter": True
            },
            
            # Navigation patterns
            "navigate_section": {
                "patterns": [
                    r"go\s+to\s+(.*?)(?:\s+section)?",
                    r"move\s+to\s+(.*?)(?:\s+section)?",
                    r"jump\s+to\s+(.*?)(?:\s+section)?"
                ],
                "action": "navigate_section",
                "extract_parameter": True
            },
            
            # Dictation control patterns
            "dictation_control": {
                "patterns": [
                    r"(start|begin|resume)\s+dictation",
                    r"(stop|end|finish)\s+dictation",
                    r"(pause|hold)\s+dictation"
                ],
                "action": "dictation_control",
                "extract_parameter": True
            },
            
            # System control patterns
            "system_control": {
                "patterns": [
                    r"(save|store)\s+report",
                    r"(submit|send)\s+report",
                    r"(delete|remove)\s+report",
                    r"(new|create)\s+report"
                ],
                "action": "system_control",
                "extract_parameter": True
            },
            
            # Quick fill patterns
            "quick_fill": {
                "patterns": [
                    r"normal\s+(.*?)(?:\s+study|\s+exam|\s+examination)?",
                    r"no\s+acute\s+(.*?)",
                    r"within\s+normal\s+limits",
                    r"unremarkable\s+(.*?)"
                ],
                "action": "quick_fill",
                "extract_parameter": True
            }
        }
    
    def _initialize_template_mappings(self):
        """Initialize template name mappings"""
        self.template_mappings = {
            # Chest imaging
            "chest x-ray": "chest_xray_template",
            "chest xray": "chest_xray_template",
            "cxr": "chest_xray_template",
            "chest radiograph": "chest_xray_template",
            
            "ct chest": "ct_chest_template",
            "chest ct": "ct_chest_template",
            "computed tomography chest": "ct_chest_template",
            
            # Abdominal imaging
            "abdominal x-ray": "abdominal_xray_template",
            "abd xray": "abdominal_xray_template",
            "kub": "kub_template",
            
            "ct abdomen": "ct_abdomen_template",
            "abdominal ct": "ct_abdomen_template",
            
            # Musculoskeletal
            "bone x-ray": "bone_xray_template",
            "orthopedic": "orthopedic_template",
            "fracture": "fracture_template",
            
            # Neurological
            "ct head": "ct_head_template",
            "head ct": "ct_head_template",
            "brain ct": "ct_brain_template",
            
            # South African specific
            "tb screening": "tb_screening_template",
            "tuberculosis": "tb_screening_template",
            "silicosis": "silicosis_template",
            "pneumoconiosis": "pneumoconiosis_template"
        }
    
    def process_command(self, text: str) -> Optional[Dict[str, Any]]:
        """Process text for voice commands"""
        try:
            text_lower = text.lower().strip()
            
            for command_type, config in self.command_patterns.items():
                for pattern in config["patterns"]:
                    match = re.search(pattern, text_lower)
                    if match:
                        command = {
                            "type": command_type,
                            "action": config["action"],
                            "original_text": text,
                            "confidence": 0.9  # Mock confidence
                        }
                        
                        if config.get("extract_parameter") and match.groups():
                            parameter = match.group(1).strip()
                            command["parameter"] = parameter
                            
                            # Map template names
                            if command_type == "load_template":
                                template_id = self.template_mappings.get(parameter)
                                if template_id:
                                    command["template_id"] = template_id
                        
                        logger.info(f"Detected voice command: {command}")
                        return command
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to process voice command: {e}")
            return None

class STTLearningEngine:
    """Adaptive learning engine for STT improvement from corrections"""
    
    def __init__(self):
        self.correction_history: List[Dict[str, Any]] = []
        self.user_corrections: Dict[str, List[Dict[str, Any]]] = {}
        self.medical_term_corrections: Dict[str, str] = {}
        self.accent_adaptations: Dict[str, str] = {}
        
        logger.info("STT learning engine initialized")
    
    def record_correction(self, user_id: str, original_text: str, 
                         corrected_text: str, context: str = "") -> bool:
        """Record a correction for learning"""
        try:
            correction = {
                "correction_id": str(uuid.uuid4()),
                "user_id": user_id,
                "original_text": original_text,
                "corrected_text": corrected_text,
                "context": context,
                "timestamp": datetime.utcnow(),
                "processed": False
            }
            
            self.correction_history.append(correction)
            
            # Add to user-specific corrections
            if user_id not in self.user_corrections:
                self.user_corrections[user_id] = []
            self.user_corrections[user_id].append(correction)
            
            # Process correction immediately
            self._process_correction(correction)
            
            logger.info(f"Recorded correction for user {user_id}: '{original_text}' -> '{corrected_text}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record correction: {e}")
            return False
    
    def _process_correction(self, correction: Dict[str, Any]):
        """Process a correction to extract learning patterns"""
        try:
            original = correction["original_text"].lower()
            corrected = correction["corrected_text"].lower()
            
            # Extract word-level corrections
            original_words = original.split()
            corrected_words = corrected.split()
            
            # Simple alignment for word corrections
            if len(original_words) == len(corrected_words):
                for i, (orig_word, corr_word) in enumerate(zip(original_words, corrected_words)):
                    if orig_word != corr_word:
                        # Check if it's a medical term
                        if self._is_medical_term(corr_word):
                            self.medical_term_corrections[orig_word] = corr_word
                        
                        # Check if it's an accent-related correction
                        if self._is_accent_correction(orig_word, corr_word):
                            self.accent_adaptations[orig_word] = corr_word
            
            correction["processed"] = True
            
        except Exception as e:
            logger.error(f"Failed to process correction: {e}")
    
    def _is_medical_term(self, word: str) -> bool:
        """Check if word is likely a medical term"""
        medical_indicators = [
            "osis", "itis", "emia", "uria", "pathy", "ology", "scopy",
            "gram", "graphy", "metry", "tomy", "ectomy", "plasty"
        ]
        
        return any(word.endswith(indicator) for indicator in medical_indicators)
    
    def _is_accent_correction(self, original: str, corrected: str) -> bool:
        """Check if correction is accent-related"""
        # Common South African English pronunciation patterns
        accent_patterns = [
            ("th", "f"),  # "think" -> "fink"
            ("th", "d"),  # "this" -> "dis"
            ("er", "a"),  # "water" -> "wata"
            ("ing", "in"), # "running" -> "runnin"
        ]
        
        for pattern_from, pattern_to in accent_patterns:
            if pattern_from in corrected and pattern_to in original:
                return True
        
        return False
    
    def apply_learned_corrections(self, text: str, user_id: str = None) -> str:
        """Apply learned corrections to text"""
        try:
            corrected_text = text.lower()
            
            # Apply medical term corrections
            for original, correction in self.medical_term_corrections.items():
                corrected_text = re.sub(r'\b' + re.escape(original) + r'\b', 
                                      correction, corrected_text)
            
            # Apply accent adaptations
            for original, correction in self.accent_adaptations.items():
                corrected_text = re.sub(r'\b' + re.escape(original) + r'\b', 
                                      correction, corrected_text)
            
            # Apply user-specific corrections if available
            if user_id and user_id in self.user_corrections:
                for correction in self.user_corrections[user_id][-10:]:  # Last 10 corrections
                    if correction["processed"]:
                        original = correction["original_text"].lower()
                        corrected = correction["corrected_text"].lower()
                        
                        # Simple substring replacement
                        if original in corrected_text:
                            corrected_text = corrected_text.replace(original, corrected)
            
            return corrected_text
            
        except Exception as e:
            logger.error(f"Failed to apply learned corrections: {e}")
            return text
    
    def get_learning_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get learning statistics"""
        try:
            stats = {
                "total_corrections": len(self.correction_history),
                "medical_term_corrections": len(self.medical_term_corrections),
                "accent_adaptations": len(self.accent_adaptations),
                "processed_corrections": sum(1 for c in self.correction_history if c["processed"])
            }
            
            if user_id and user_id in self.user_corrections:
                stats["user_corrections"] = len(self.user_corrections[user_id])
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get learning stats: {e}")
            return {}

class STTService:
    """Speech-to-Text service with medical terminology and South African accent support"""
    
    def __init__(self, config: STTConfig = None):
        self.config = config or STTConfig()
        self.command_processor = VoiceCommandProcessor()
        self.learning_engine = STTLearningEngine()
        
        # Audio processing
        self.audio_queue = queue.Queue()
        self.processing_thread = None
        self.is_processing = False
        
        # Callbacks
        self.transcription_callbacks: List[Callable] = []
        self.command_callbacks: List[Callable] = []
        
        # Medical vocabulary for South African context
        self.medical_vocabulary = self._load_medical_vocabulary()
        
        logger.info(f"STT service initialized with provider: {self.config.provider.value}")
    
    def _load_medical_vocabulary(self) -> Dict[str, str]:
        """Load medical vocabulary with South African context"""
        return {
            # Respiratory conditions (common in SA due to mining, TB)
            "pneumoconiosis": "pneumoconiosis",
            "silicosis": "silicosis",
            "asbestosis": "asbestosis",
            "tuberculosis": "tuberculosis",
            "multidrug resistant tuberculosis": "multidrug-resistant tuberculosis",
            "mdr tb": "MDR-TB",
            "extensively drug resistant tuberculosis": "extensively drug-resistant tuberculosis",
            "xdr tb": "XDR-TB",
            
            # HIV-related conditions
            "pneumocystis pneumonia": "Pneumocystis pneumonia",
            "pcp": "PCP",
            "kaposi sarcoma": "Kaposi's sarcoma",
            "cryptococcal meningitis": "cryptococcal meningitis",
            
            # Trauma (high incidence in SA)
            "gunshot wound": "gunshot wound",
            "gsw": "GSW",
            "stab wound": "stab wound",
            "motor vehicle accident": "motor vehicle accident",
            "mva": "MVA",
            
            # Common anatomical terms with SA pronunciation
            "bilateral": "bilateral",
            "unilateral": "unilateral",
            "consolidation": "consolidation",
            "atelectasis": "atelectasis",
            "pleural effusion": "pleural effusion",
            "pneumothorax": "pneumothorax",
            
            # Common findings
            "within normal limits": "within normal limits",
            "no acute abnormality": "no acute abnormality",
            "unremarkable": "unremarkable",
            "consistent with": "consistent with",
            "suggestive of": "suggestive of"
        }
    
    def start_processing(self) -> bool:
        """Start audio processing thread"""
        try:
            if self.is_processing:
                return True
            
            self.is_processing = True
            self.processing_thread = threading.Thread(target=self._process_audio_loop)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            
            logger.info("Started STT audio processing")
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
            
            logger.info("Stopped STT audio processing")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop STT processing: {e}")
            return False
    
    def process_audio(self, audio_data: bytes, user_id: str = None) -> Optional[STTResult]:
        """Process audio data and return transcription"""
        try:
            start_time = time.time()
            
            # Assess audio quality
            audio_quality = self._assess_audio_quality(audio_data)
            
            # Perform STT based on provider
            if self.config.provider == STTProvider.MOCK:
                text, confidence = self._mock_stt(audio_data)
            elif self.config.provider == STTProvider.GOOGLE:
                text, confidence = self._google_stt(audio_data)
            elif self.config.provider == STTProvider.AZURE:
                text, confidence = self._azure_stt(audio_data)
            elif self.config.provider == STTProvider.AWS:
                text, confidence = self._aws_stt(audio_data)
            else:
                logger.error(f"Unsupported STT provider: {self.config.provider}")
                return None
            
            if not text:
                return None
            
            # Apply medical vocabulary corrections
            corrected_text = self._apply_medical_vocabulary(text)
            
            # Apply learned corrections
            if user_id:
                corrected_text = self.learning_engine.apply_learned_corrections(
                    corrected_text, user_id)
            
            processing_time = time.time() - start_time
            
            result = STTResult(
                text=corrected_text,
                confidence=confidence,
                timestamp=datetime.utcnow(),
                audio_quality=audio_quality,
                processing_time=processing_time
            )
            
            # Check for voice commands
            command = self.command_processor.process_command(corrected_text)
            if command:
                self._notify_command_callbacks(command)
            else:
                self._notify_transcription_callbacks(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process audio: {e}")
            return None
    
    def _assess_audio_quality(self, audio_data: bytes) -> AudioQuality:
        """Assess audio quality (simplified implementation)"""
        try:
            # In production, would analyze:
            # - Signal-to-noise ratio
            # - Frequency distribution
            # - Volume levels
            # - Background noise
            
            # Mock assessment based on data size
            data_size = len(audio_data)
            
            if data_size < 1000:
                return AudioQuality.POOR
            elif data_size < 5000:
                return AudioQuality.FAIR
            elif data_size < 10000:
                return AudioQuality.GOOD
            else:
                return AudioQuality.EXCELLENT
                
        except Exception as e:
            logger.error(f"Failed to assess audio quality: {e}")
            return AudioQuality.FAIR
    
    def _mock_stt(self, audio_data: bytes) -> Tuple[Optional[str], float]:
        """Mock STT disabled to prevent random text generation"""
        try:
            # Don't generate random text - return None to indicate no transcription
            logger.debug("Mock STT disabled - no transcription generated")
            return None, 0.0
            
        except Exception as e:
            logger.error(f"Mock STT failed: {e}")
            return None, 0.0
    
    def _google_stt(self, audio_data: bytes) -> Tuple[Optional[str], float]:
        """Google Speech-to-Text processing (placeholder)"""
        # In production, would use Google Cloud Speech-to-Text API
        logger.debug("Google STT not implemented")
        return None, 0.0
    
    def _azure_stt(self, audio_data: bytes) -> Tuple[Optional[str], float]:
        """Azure Speech Services processing (placeholder)"""
        # In production, would use Azure Cognitive Services Speech
        logger.debug("Azure STT not implemented")
        return None, 0.0
    
    def _aws_stt(self, audio_data: bytes) -> Tuple[Optional[str], float]:
        """AWS Transcribe processing (placeholder)"""
        # In production, would use Amazon Transcribe
        logger.debug("AWS STT not implemented")
        return None, 0.0
    
    def _apply_medical_vocabulary(self, text: str) -> str:
        """Apply medical vocabulary corrections"""
        try:
            corrected_text = text.lower()
            
            for term, correction in self.medical_vocabulary.items():
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(term) + r'\b'
                corrected_text = re.sub(pattern, correction, corrected_text, flags=re.IGNORECASE)
            
            # Capitalize first letter of sentences
            sentences = corrected_text.split('. ')
            capitalized_sentences = [s.capitalize() for s in sentences]
            corrected_text = '. '.join(capitalized_sentences)
            
            return corrected_text
            
        except Exception as e:
            logger.error(f"Failed to apply medical vocabulary: {e}")
            return text
    
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
                        result = self.process_audio(audio_data, user_id)
                        if result:
                            logger.debug(f"Processed audio: {result.text[:50]}...")
                
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
    
    def add_transcription_callback(self, callback: Callable):
        """Add callback for transcription results"""
        self.transcription_callbacks.append(callback)
    
    def add_command_callback(self, callback: Callable):
        """Add callback for voice commands"""
        self.command_callbacks.append(callback)
    
    def _notify_transcription_callbacks(self, result: STTResult):
        """Notify transcription callbacks"""
        for callback in self.transcription_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in transcription callback: {e}")
    
    def _notify_command_callbacks(self, command: Dict[str, Any]):
        """Notify command callbacks"""
        for callback in self.command_callbacks:
            try:
                callback(command)
            except Exception as e:
                logger.error(f"Error in command callback: {e}")
    
    def record_correction(self, user_id: str, original_text: str, 
                         corrected_text: str, context: str = "") -> bool:
        """Record a correction for learning"""
        return self.learning_engine.record_correction(
            user_id, original_text, corrected_text, context)
    
    def get_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get STT service statistics"""
        try:
            stats = {
                "provider": self.config.provider.value,
                "language_code": self.config.language_code,
                "medical_vocabulary_size": len(self.medical_vocabulary),
                "is_processing": self.is_processing,
                "queue_size": self.audio_queue.qsize()
            }
            
            # Add learning engine stats
            learning_stats = self.learning_engine.get_learning_stats(user_id)
            stats.update(learning_stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get STT stats: {e}")
            return {}

# Global STT service instance
stt_service = STTService()