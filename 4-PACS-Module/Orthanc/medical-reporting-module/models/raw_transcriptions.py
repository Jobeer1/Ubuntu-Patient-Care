"""
Raw Transcriptions Archive Model
Lightweight database for voice files + raw STT transcriptions
Reserved for future use - stores raw data without corrections
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

# Import the shared db instance from models.database
from models.database import db


class RawTranscription(db.Model):
    """
    Lightweight storage for raw transcriptions
    - Voice audio file
    - Raw STT output (uncorrected)
    - User ID for access control
    
    This database is for archival/future use. Currently not actively queried.
    """
    __tablename__ = 'raw_transcriptions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Session reference
    session_id = db.Column(db.String(36), nullable=False, index=True)
    
    # Audio file information
    audio_filename = db.Column(db.String(255), nullable=False)
    audio_file_path = db.Column(db.String(512), nullable=False)  # Path to stored voice file
    audio_duration = db.Column(db.Float, nullable=True)  # Duration in seconds
    audio_hash = db.Column(db.String(64), nullable=True)  # SHA256 for deduplication
    
    # Raw transcription (direct from Whisper, no corrections)
    raw_transcription = db.Column(db.Text, nullable=False)
    
    # Metadata
    user_id = db.Column(db.String(255), nullable=False, index=True)
    whisper_model = db.Column(db.String(50), default='base')  # Model used: base, small, medium, etc.
    confidence_score = db.Column(db.Float, nullable=True)  # Optional confidence from Whisper
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Status/flags
    is_archived = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'audio_filename': self.audio_filename,
            'audio_duration': self.audio_duration,
            'raw_transcription': self.raw_transcription,
            'user_id': self.user_id,
            'confidence_score': self.confidence_score,
            'created_at': self.created_at.isoformat(),
            'is_archived': self.is_archived
        }
