"""
Voice Engine for Medical Reporting Module
Real-time speech-to-text with medical terminology and South African accent support
"""

import logging
import threading
import queue
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import re

# Import offline STT components
from services.offline_stt_service import offline_stt_engine, STTResult, STTConfig, STTMode
from services.offline_voice_commands import offline_voice_commands, VoiceCommand as OfflineVoiceCommand
from utils.voice_utils import preprocess_south_african_text, analyze_voice_audio

logger = logging.getLogger(__name__)

class VoiceCommandType(Enum):
    """Types of voice commands"""
    LOAD_TEMPLATE = "load_template"
    FILL_FIELD = "fill_field"
    NAVIGATE_SECTION = "navigate_section"
    DICTATION_CONTROL = "dictation_control"
    SYSTEM_CONTROL = "system_control"

class DictationState(Enum):
    """States of dictation session"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    PAUSED = "paused"
    ERROR = "error"

@dataclass
class VoiceCommand:
    """Voice command configuration"""
    command_id: str
    command_text: str
    command_type: VoiceCommandType
    target_id: str = ""
    parameters: Dict[str, Any] = None
    confidence_threshold: float = 0.8
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}

@dataclass
class VoiceSession:
    """Voice dictation session"""
    session_id: str
    user_id: str
    report_id: Optional[str] = None
    template_id: Optional[str] = None
    state: DictationState = DictationState.IDLE
    start_time: datetime = None
    end_time: Optional[datetime] = None
    transcription_segments: List[Dict[str, Any]] = None
    commands_executed: List[VoiceCommand] = None
    
    def __post_init__(self):
        if self.transcription_segments is None:
            self.transcription_segments = []
        if self.commands_executed is None:
            self.commands_executed = []
        if self.start_time is None:
            self.start_time = datetime.utcnow()

class VoiceEngine:
    """Voice processing engine with medical terminology support"""
    
    def __init__(self):
        self.current_session: Optional[VoiceSession] = None
        self.voice_commands: Dict[str, VoiceCommand] = {}
        self.medical_vocabulary: Dict[str, str] = {}
        
        # Offline-first STT configuration
        self.offline_mode = True
        self.stt_config = STTConfig(
            mode=STTMode.OFFLINE_ONLY,
            language="en",
            model_size="base",
            enable_medical_terminology=True,
            enable_learning=True,
            confidence_threshold=0.7
        )
        
        # Mock STT for demo (in production would use real STT service)
        self.mock_stt_enabled = True
        self.mock_responses = []
        self.mock_response_index = 0
        
        # Callbacks
        self.transcription_callbacks: List[Callable] = []
        self.command_callbacks: List[Callable] = []
        self.session_callbacks: List[Callable] = []
        
        # Initialize offline STT engine
        self._initialize_offline_stt()
        
        # Initialize medical vocabulary and commands
        self._initialize_medical_vocabulary()
        self._initialize_voice_commands()
        
        logger.info("Voice engine initialized with offline-first STT")
    
    def _initialize_medical_vocabulary(self):
        """Initialize medical terminology dictionary"""
        self.medical_vocabulary = {
            # Common medical terms
            "pneumonia": "pneumonia",
            "consolidation": "consolidation",
            "atelectasis": "atelectasis",
            "pleural effusion": "pleural effusion",
            "pneumothorax": "pneumothorax",
            "cardiomegaly": "cardiomegaly",
            "pulmonary edema": "pulmonary edema",
            "infiltrate": "infiltrate",
            "nodule": "nodule",
            "mass": "mass",
            "fracture": "fracture",
            "dislocation": "dislocation",
            
            # South African specific terms
            "tuberculosis": "tuberculosis",
            "tb": "tuberculosis",
            "silicosis": "silicosis",
            "pneumoconiosis": "pneumoconiosis",
            "mesothelioma": "mesothelioma",
            
            # Anatomical terms
            "bilateral": "bilateral",
            "unilateral": "unilateral",
            "anterior": "anterior",
            "posterior": "posterior",
            "superior": "superior",
            "inferior": "inferior",
            "medial": "medial",
            "lateral": "lateral",
            
            # Common phrases
            "no acute": "no acute",
            "within normal limits": "within normal limits",
            "unremarkable": "unremarkable",
            "consistent with": "consistent with",
            "suggestive of": "suggestive of",
            "cannot exclude": "cannot exclude"
        }
        
        logger.info(f"Loaded {len(self.medical_vocabulary)} medical terms")
    
    def _initialize_voice_commands(self):
        """Initialize voice commands for template and system control"""
        commands = [
            # Template commands
            VoiceCommand(
                command_id="load_chest_xray",
                command_text="load chest x-ray template",
                command_type=VoiceCommandType.LOAD_TEMPLATE,
                target_id="chest_xray_template"
            ),
            VoiceCommand(
                command_id="load_ct_chest",
                command_text="load ct chest template",
                command_type=VoiceCommandType.LOAD_TEMPLATE,
                target_id="ct_chest_template"
            ),
            VoiceCommand(
                command_id="normal_chest",
                command_text="normal chest study",
                command_type=VoiceCommandType.FILL_FIELD,
                target_id="impression_text",
                parameters={"text": "Normal chest radiograph."}
            ),
            
            # Navigation commands
            VoiceCommand(
                command_id="go_to_findings",
                command_text="go to findings",
                command_type=VoiceCommandType.NAVIGATE_SECTION,
                target_id="findings"
            ),
            VoiceCommand(
                command_id="go_to_impression",
                command_text="go to impression",
                command_type=VoiceCommandType.NAVIGATE_SECTION,
                target_id="impression"
            ),
            
            # Dictation control
            VoiceCommand(
                command_id="start_dictation",
                command_text="start dictation",
                command_type=VoiceCommandType.DICTATION_CONTROL,
                parameters={"action": "start"}
            ),
            VoiceCommand(
                command_id="stop_dictation",
                command_text="stop dictation",
                command_type=VoiceCommandType.DICTATION_CONTROL,
                parameters={"action": "stop"}
            ),
            VoiceCommand(
                command_id="pause_dictation",
                command_text="pause dictation",
                command_type=VoiceCommandType.DICTATION_CONTROL,
                parameters={"action": "pause"}
            ),
            
            # System control
            VoiceCommand(
                command_id="save_report",
                command_text="save report",
                command_type=VoiceCommandType.SYSTEM_CONTROL,
                parameters={"action": "save"}
            ),
            VoiceCommand(
                command_id="submit_report",
                command_text="submit report",
                command_type=VoiceCommandType.SYSTEM_CONTROL,
                parameters={"action": "submit"}
            )
        ]
        
        for command in commands:
            self.voice_commands[command.command_id] = command
        
        logger.info(f"Initialized {len(commands)} voice commands")
    
    def _initialize_offline_stt(self):
        """Initialize offline STT engine"""
        try:
            # Initialize the offline STT engine
            if offline_stt_engine.initialize():
                offline_stt_engine.start_processing()
                
                # Add callback for transcription results
                offline_stt_engine.add_transcription_callback(self._handle_offline_transcription)
                
                logger.info("Offline STT engine initialized successfully")
            else:
                logger.warning("Failed to initialize offline STT engine, falling back to mock")
                self.offline_mode = False
                
        except Exception as e:
            logger.error(f"Failed to initialize offline STT: {e}")
            self.offline_mode = False
    
    def _handle_offline_transcription(self, result: STTResult):
        """Handle transcription result from offline STT engine"""
        try:
            if not self.current_session:
                return
            
            # Process the transcription
            processed_text = preprocess_south_african_text(result.text, "medical")
            
            # Check for voice commands first
            command_result = offline_voice_commands.process_command(processed_text)
            
            if command_result:
                # Handle voice command
                self._handle_offline_voice_command(command_result)
            else:
                # Add to transcription segments
                segment = {
                    'timestamp': result.timestamp.isoformat(),
                    'original_text': result.text,
                    'processed_text': processed_text,
                    'confidence': result.confidence,
                    'audio_quality': result.audio_quality.value,
                    'processing_time': result.processing_time,
                    'mode_used': result.mode_used.value
                }
                self.current_session.transcription_segments.append(segment)
                
                # Notify transcription callbacks
                self._notify_transcription(processed_text, segment)
                
        except Exception as e:
            logger.error(f"Failed to handle offline transcription: {e}")
    
    def _handle_offline_voice_command(self, command: OfflineVoiceCommand):
        """Handle voice command from offline processor"""
        try:
            logger.info(f"Processing offline voice command: {command.action} - {command.parameter}")
            
            # Convert to internal voice command format
            internal_command = VoiceCommand(
                command_id=command.command_id,
                command_text=command.original_text,
                command_type=self._map_command_type(command.command_type),
                target_id=command.template_id or command.parameter or "",
                parameters={"action": command.action, "parameter": command.parameter}
            )
            
            # Execute the command
            self._execute_voice_command(internal_command)
            
        except Exception as e:
            logger.error(f"Failed to handle offline voice command: {e}")
    
    def _map_command_type(self, offline_command_type) -> VoiceCommandType:
        """Map offline command type to internal command type"""
        from services.offline_voice_commands import CommandType
        
        mapping = {
            CommandType.TEMPLATE_LOAD: VoiceCommandType.LOAD_TEMPLATE,
            CommandType.NAVIGATION: VoiceCommandType.NAVIGATE_SECTION,
            CommandType.DICTATION_CONTROL: VoiceCommandType.DICTATION_CONTROL,
            CommandType.SYSTEM_CONTROL: VoiceCommandType.SYSTEM_CONTROL,
            CommandType.QUICK_FILL: VoiceCommandType.FILL_FIELD
        }
        
        return mapping.get(offline_command_type, VoiceCommandType.DICTATION_CONTROL)
    
    def start_session(self, user_id: str, report_id: Optional[str] = None, 
                     template_id: Optional[str] = None) -> VoiceSession:
        """Start a new voice dictation session"""
        try:
            if self.current_session and self.current_session.state != DictationState.IDLE:
                self.end_session()
            
            session = VoiceSession(
                session_id=str(uuid.uuid4()),
                user_id=user_id,
                report_id=report_id,
                template_id=template_id,
                state=DictationState.IDLE
            )
            
            self.current_session = session
            
            # Initialize mock responses for demo
            if self.mock_stt_enabled:
                self._setup_mock_responses()
            
            # Notify callbacks
            self._notify_session_change('started', session)
            
            logger.info(f"Started voice session: {session.session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to start voice session: {e}")
            raise
    
    def _setup_mock_responses(self):
        """Setup mock STT responses for demo"""
        self.mock_responses = [
            "The lungs are clear bilaterally with no focal consolidation.",
            "The cardiac silhouette is normal in size and configuration.",
            "No pleural effusion or pneumothorax is identified.",
            "The mediastinum and hila appear normal.",
            "No acute osseous abnormality is seen.",
            "Impression: Normal chest radiograph."
        ]
        self.mock_response_index = 0
    
    def start_listening(self) -> bool:
        """Start listening for voice input"""
        try:
            if not self.current_session:
                logger.error("No active session to start listening")
                return False
            
            self.current_session.state = DictationState.LISTENING
            
            # Notify callbacks
            self._notify_session_change('listening_started', self.current_session)
            
            logger.info("Started listening for voice input")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start listening: {e}")
            return False
    
    def stop_listening(self) -> bool:
        """Stop listening for voice input"""
        try:
            if not self.current_session:
                return False
            
            self.current_session.state = DictationState.IDLE
            
            # Notify callbacks
            self._notify_session_change('listening_stopped', self.current_session)
            
            logger.info("Stopped listening for voice input")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop listening: {e}")
            return False
    
    def process_audio_chunk(self, audio_data: bytes) -> Optional[str]:
        """Process audio chunk and return transcription"""
        try:
            if not self.current_session or self.current_session.state != DictationState.LISTENING:
                return None
            
            self.current_session.state = DictationState.PROCESSING
            
            # Analyze audio quality first
            audio_analysis = analyze_voice_audio(audio_data)
            logger.debug(f"Audio quality: {audio_analysis.get('quality', 'unknown')}")
            
            # Use offline STT if available, otherwise fall back to mock
            if self.offline_mode and offline_stt_engine.is_initialized:
                # Queue audio for offline processing
                offline_stt_engine.queue_audio(audio_data, self.current_session.user_id)
                
                # The transcription will be handled asynchronously by _handle_offline_transcription
                self.current_session.state = DictationState.LISTENING
                return "Processing..."  # Placeholder response
                
            elif self.mock_stt_enabled:
                transcription = self._mock_stt_process(audio_data)
            else:
                # In production, would call real STT service
                transcription = self._real_stt_process(audio_data)
            
            if transcription and transcription != "Processing...":
                # Process medical terminology
                processed_text = self._process_medical_terminology(transcription)
                
                # Check for voice commands
                command_result = self._check_for_commands(processed_text)
                
                if not command_result:
                    # Add to transcription segments
                    segment = {
                        'timestamp': datetime.utcnow().isoformat(),
                        'original_text': transcription,
                        'processed_text': processed_text,
                        'confidence': 0.95,  # Mock confidence
                        'audio_quality': audio_analysis.get('quality', 'unknown')
                    }
                    self.current_session.transcription_segments.append(segment)
                    
                    # Notify transcription callbacks
                    self._notify_transcription(processed_text, segment)
                
                self.current_session.state = DictationState.LISTENING
                return processed_text
            
            self.current_session.state = DictationState.LISTENING
            return transcription
            
        except Exception as e:
            logger.error(f"Failed to process audio chunk: {e}")
            if self.current_session:
                self.current_session.state = DictationState.ERROR
            return None
    
    def _mock_stt_process(self, audio_data: bytes) -> Optional[str]:
        """Mock STT processing - disabled to prevent random text generation"""
        try:
            # Don't generate random text - return None to indicate no transcription
            logger.debug("Mock STT disabled - no transcription generated")
            return None
            
        except Exception as e:
            logger.error(f"Mock STT processing failed: {e}")
            return None
    
    def _real_stt_process(self, audio_data: bytes) -> Optional[str]:
        """Real STT processing (placeholder for production implementation)"""
        # In production, this would:
        # 1. Send audio to STT service (Google Speech-to-Text, Azure Speech, etc.)
        # 2. Handle South African English accent models
        # 3. Apply medical vocabulary customization
        # 4. Return transcribed text
        
        logger.debug("Real STT processing not implemented")
        return None
    
    def _process_medical_terminology(self, text: str) -> str:
        """Process text to correct medical terminology"""
        try:
            processed_text = text.lower()
            
            # Apply medical vocabulary corrections
            for term, correction in self.medical_vocabulary.items():
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(term) + r'\b'
                processed_text = re.sub(pattern, correction, processed_text, flags=re.IGNORECASE)
            
            # Capitalize first letter of sentences
            sentences = processed_text.split('. ')
            capitalized_sentences = [s.capitalize() for s in sentences]
            processed_text = '. '.join(capitalized_sentences)
            
            return processed_text
            
        except Exception as e:
            logger.error(f"Failed to process medical terminology: {e}")
            return text
    
    def _check_for_commands(self, text: str) -> bool:
        """Check if text contains voice commands"""
        try:
            text_lower = text.lower().strip()
            
            for command_id, command in self.voice_commands.items():
                if command.command_text.lower() in text_lower:
                    # Execute command
                    self._execute_voice_command(command)
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check for commands: {e}")
            return False
    
    def _execute_voice_command(self, command: VoiceCommand):
        """Execute a voice command"""
        try:
            logger.info(f"Executing voice command: {command.command_text}")
            
            # Add to executed commands
            if self.current_session:
                self.current_session.commands_executed.append(command)
            
            # Notify command callbacks
            self._notify_command_executed(command)
            
        except Exception as e:
            logger.error(f"Failed to execute voice command: {e}")
    
    def simulate_dictation(self, text: str) -> bool:
        """Simulate dictation input for demo purposes"""
        try:
            if not self.current_session:
                logger.error("No active session for simulation")
                return False
            
            # Process as if it came from STT
            processed_text = self._process_medical_terminology(text)
            
            # Check for commands
            command_result = self._check_for_commands(processed_text)
            
            if not command_result:
                # Add to transcription segments
                segment = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'original_text': text,
                    'processed_text': processed_text,
                    'confidence': 1.0,
                    'simulated': True
                }
                self.current_session.transcription_segments.append(segment)
                
                # Notify transcription callbacks
                self._notify_transcription(processed_text, segment)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to simulate dictation: {e}")
            return False
    
    def get_session_transcription(self) -> str:
        """Get complete transcription from current session"""
        try:
            if not self.current_session:
                return ""
            
            transcription_parts = []
            for segment in self.current_session.transcription_segments:
                transcription_parts.append(segment['processed_text'])
            
            return " ".join(transcription_parts)
            
        except Exception as e:
            logger.error(f"Failed to get session transcription: {e}")
            return ""
    
    def end_session(self) -> Optional[VoiceSession]:
        """End the current voice session"""
        try:
            if not self.current_session:
                return None
            
            session = self.current_session
            session.end_time = datetime.utcnow()
            session.state = DictationState.IDLE
            
            # Notify callbacks
            self._notify_session_change('ended', session)
            
            logger.info(f"Ended voice session: {session.session_id}")
            
            # Clear current session
            self.current_session = None
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to end voice session: {e}")
            return None
    
    def add_transcription_callback(self, callback: Callable):
        """Add callback for transcription events"""
        self.transcription_callbacks.append(callback)
    
    def add_command_callback(self, callback: Callable):
        """Add callback for command events"""
        self.command_callbacks.append(callback)
    
    def add_session_callback(self, callback: Callable):
        """Add callback for session events"""
        self.session_callbacks.append(callback)
    
    def _notify_transcription(self, text: str, segment: Dict[str, Any]):
        """Notify transcription callbacks"""
        for callback in self.transcription_callbacks:
            try:
                callback(text, segment)
            except Exception as e:
                logger.error(f"Error in transcription callback: {e}")
    
    def _notify_command_executed(self, command: VoiceCommand):
        """Notify command callbacks"""
        for callback in self.command_callbacks:
            try:
                callback(command)
            except Exception as e:
                logger.error(f"Error in command callback: {e}")
    
    def _notify_session_change(self, event: str, session: VoiceSession):
        """Notify session callbacks"""
        for callback in self.session_callbacks:
            try:
                callback(event, session)
            except Exception as e:
                logger.error(f"Error in session callback: {e}")
    
    def get_available_commands(self) -> List[VoiceCommand]:
        """Get list of available voice commands"""
        return list(self.voice_commands.values())
    
    def record_correction(self, user_id: str, original_text: str, corrected_text: str) -> bool:
        """Record a correction for STT learning"""
        try:
            if self.offline_mode and offline_stt_engine.is_initialized:
                return offline_stt_engine.record_correction(user_id, original_text, corrected_text)
            else:
                logger.info(f"Recorded correction (mock): '{original_text}' -> '{corrected_text}'")
                return True
                
        except Exception as e:
            logger.error(f"Failed to record correction: {e}")
            return False
    
    def get_stt_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get STT engine statistics"""
        try:
            if self.offline_mode and offline_stt_engine.is_initialized:
                return offline_stt_engine.get_stats(user_id)
            else:
                return {
                    "mode": "mock",
                    "offline_available": False,
                    "mock_enabled": self.mock_stt_enabled
                }
                
        except Exception as e:
            logger.error(f"Failed to get STT stats: {e}")
            return {}
    
    def get_available_templates(self) -> List[Dict[str, str]]:
        """Get available voice-activated templates"""
        try:
            return offline_voice_commands.get_available_templates()
        except Exception as e:
            logger.error(f"Failed to get available templates: {e}")
            return []
    
    def get_command_examples(self) -> List[Dict[str, Any]]:
        """Get voice command examples"""
        try:
            return offline_voice_commands.get_command_examples()
        except Exception as e:
            logger.error(f"Failed to get command examples: {e}")
            return []
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get current session information"""
        if not self.current_session:
            return None
        
        return {
            'session_id': self.current_session.session_id,
            'user_id': self.current_session.user_id,
            'state': self.current_session.state.value,
            'start_time': self.current_session.start_time.isoformat(),
            'transcription_segments': len(self.current_session.transcription_segments),
            'commands_executed': len(self.current_session.commands_executed),
            'current_transcription': self.get_session_transcription(),
            'offline_mode': self.offline_mode,
            'stt_stats': self.get_stt_stats(self.current_session.user_id)
        }

# Global voice engine instance
voice_engine = VoiceEngine()