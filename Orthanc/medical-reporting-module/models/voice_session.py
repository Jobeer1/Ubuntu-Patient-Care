"""
Voice session data model for Medical Reporting Module
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
import uuid

# Import unified base
from .database import Base

class VoiceSessionStatus(Enum):
    """Voice session status enumeration"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class VoiceSession(Base):
    """Voice session model for tracking dictation sessions"""
    __tablename__ = 'voice_sessions'
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign keys
    user_id = Column(String(36), nullable=False, index=True)
    report_id = Column(String(36), ForeignKey('reports.id'), nullable=True)
    
    # Session details
    session_name = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default=VoiceSessionStatus.ACTIVE.value)
    
    # Audio information
    audio_file_path = Column(String(255), nullable=True)
    audio_format = Column(String(10), nullable=False, default='wav')  # wav, mp3, ogg
    audio_duration_seconds = Column(Float, nullable=True)
    audio_size_bytes = Column(Integer, nullable=True)
    sample_rate = Column(Integer, nullable=False, default=16000)
    
    # Transcription
    transcription = Column(Text, nullable=True)
    transcription_confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    transcription_language = Column(String(10), nullable=False, default='en-ZA')
    
    # Voice commands
    commands_executed = Column(JSON, nullable=False, default=list)
    template_commands = Column(JSON, nullable=False, default=list)
    navigation_commands = Column(JSON, nullable=False, default=list)
    
    # Processing status
    is_processed = Column(Boolean, nullable=False, default=False)
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    processing_error = Column(Text, nullable=True)
    
    # Quality metrics
    audio_quality_score = Column(Float, nullable=True)  # 0.0 to 1.0
    background_noise_level = Column(Float, nullable=True)
    speech_clarity_score = Column(Float, nullable=True)
    
    # Timestamps
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    report = relationship("Report", back_populates="voice_sessions")
    audio_segments = relationship("AudioSegment", back_populates="voice_session")
    voice_commands = relationship("VoiceCommand", back_populates="voice_session")
    
    def __repr__(self):
        return f"<VoiceSession(id='{self.id}', user_id='{self.user_id}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert voice session to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'report_id': self.report_id,
            'session_name': self.session_name,
            'status': self.status,
            'audio_file_path': self.audio_file_path,
            'audio_format': self.audio_format,
            'audio_duration_seconds': self.audio_duration_seconds,
            'audio_size_bytes': self.audio_size_bytes,
            'sample_rate': self.sample_rate,
            'transcription': self.transcription,
            'transcription_confidence': self.transcription_confidence,
            'transcription_language': self.transcription_language,
            'commands_executed': self.commands_executed,
            'template_commands': self.template_commands,
            'navigation_commands': self.navigation_commands,
            'is_processed': self.is_processed,
            'processing_started_at': self.processing_started_at.isoformat() if self.processing_started_at else None,
            'processing_completed_at': self.processing_completed_at.isoformat() if self.processing_completed_at else None,
            'processing_error': self.processing_error,
            'audio_quality_score': self.audio_quality_score,
            'background_noise_level': self.background_noise_level,
            'speech_clarity_score': self.speech_clarity_score,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def end_session(self):
        """End the voice session"""
        self.end_time = datetime.utcnow()
        self.status = VoiceSessionStatus.COMPLETED.value
        self.updated_at = datetime.utcnow()
    
    def pause_session(self):
        """Pause the voice session"""
        self.status = VoiceSessionStatus.PAUSED.value
        self.updated_at = datetime.utcnow()
    
    def resume_session(self):
        """Resume the voice session"""
        self.status = VoiceSessionStatus.ACTIVE.value
        self.updated_at = datetime.utcnow()
    
    def add_command(self, command_type, command_text, result=None):
        """Add a voice command to the session"""
        command = {
            'type': command_type,
            'text': command_text,
            'result': result,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if command_type == 'template':
            self.template_commands.append(command)
        elif command_type == 'navigation':
            self.navigation_commands.append(command)
        else:
            self.commands_executed.append(command)
        
        self.updated_at = datetime.utcnow()
    
    def get_duration_seconds(self):
        """Get session duration in seconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.utcnow() - self.start_time).total_seconds()
        return 0

class AudioSegment(Base):
    """Audio segment model for chunked audio processing"""
    __tablename__ = 'audio_segments'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    voice_session_id = Column(String(36), ForeignKey('voice_sessions.id'), nullable=False)
    
    # Segment details
    segment_index = Column(Integer, nullable=False)
    start_time_seconds = Column(Float, nullable=False)
    end_time_seconds = Column(Float, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    
    # Audio data
    audio_data_path = Column(String(255), nullable=True)
    audio_data_base64 = Column(Text, nullable=True)  # For small segments
    
    # Transcription
    transcription = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Processing
    is_processed = Column(Boolean, nullable=False, default=False)
    processing_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    voice_session = relationship("VoiceSession", back_populates="audio_segments")
    
    def __repr__(self):
        return f"<AudioSegment(id='{self.id}', session_id='{self.voice_session_id}', index={self.segment_index})>"

class VoiceCommand(Base):
    """Voice command model for tracking executed commands"""
    __tablename__ = 'voice_commands'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    voice_session_id = Column(String(36), ForeignKey('voice_sessions.id'), nullable=False)
    
    # Command details
    command_type = Column(String(50), nullable=False)  # template, navigation, action
    command_text = Column(String(200), nullable=False)
    recognized_intent = Column(String(100), nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Execution
    is_executed = Column(Boolean, nullable=False, default=False)
    execution_result = Column(JSON, nullable=True)
    execution_error = Column(Text, nullable=True)
    
    # Context
    context_data = Column(JSON, nullable=True)  # Additional context for command
    
    # Timestamps
    recognized_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)
    
    # Relationships
    voice_session = relationship("VoiceSession", back_populates="voice_commands")
    
    def __repr__(self):
        return f"<VoiceCommand(id='{self.id}', type='{self.command_type}', text='{self.command_text}')>"
    
    def execute_command(self, result=None, error=None):
        """Mark command as executed with result"""
        self.is_executed = True
        self.executed_at = datetime.utcnow()
        if result:
            self.execution_result = result
        if error:
            self.execution_error = error