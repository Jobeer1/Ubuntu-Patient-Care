"""
Training Data Models for Whisper Fine-tuning
Stores audio samples with corrected transcriptions for model improvement
"""

from datetime import datetime
import json
import uuid
from models.database import db


class TrainingDataSample(db.Model):
    """
    Stores a single training sample:
    - Original audio file
    - Original (imperfect) transcription
    - Corrected transcription (user-edited)
    - Metadata for Whisper fine-tuning
    """
    __tablename__ = 'training_data_samples'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Audio information
    audio_filename = db.Column(db.String(255), nullable=False)
    audio_duration = db.Column(db.Float, nullable=True)  # seconds
    audio_file_path = db.Column(db.String(512), nullable=False)  # encrypted storage path
    audio_hash = db.Column(db.String(64), nullable=True)  # SHA256 for deduplication
    
    # Transcription data
    original_transcription = db.Column(db.Text, nullable=False)  # Raw Whisper output
    corrected_transcription = db.Column(db.Text, nullable=True)  # User-corrected version
    
    # Quality metrics
    original_confidence = db.Column(db.Float, default=0.0)
    error_count = db.Column(db.Integer, default=0)  # Words corrected
    medical_terms_corrected = db.Column(db.Boolean, default=False)
    quality_score = db.Column(db.Float, default=0.0)  # 0-1 scale
    
    # Metadata
    user_id = db.Column(db.String(255), nullable=False, index=True)
    session_id = db.Column(db.String(36), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    corrected_at = db.Column(db.DateTime, nullable=True)
    
    # Status
    is_corrected = db.Column(db.Boolean, default=False, index=True)
    is_used_for_training = db.Column(db.Boolean, default=False)
    training_version = db.Column(db.Integer, nullable=True)  # Which fine-tuning version used this
    
    # Notes
    notes = db.Column(db.Text, nullable=True)
    tags = db.Column(db.String(255), nullable=True)  # comma-separated: "medical,cardiology,test"
    
    def to_dict(self):
        return {
            'id': self.id,
            'audio_filename': self.audio_filename,
            'audio_duration': self.audio_duration,
            'original_transcription': self.original_transcription,
            'corrected_transcription': self.corrected_transcription,
            'error_count': self.error_count,
            'is_corrected': self.is_corrected,
            'created_at': self.created_at.isoformat(),
            'corrected_at': self.corrected_at.isoformat() if self.corrected_at else None,
            'quality_score': self.quality_score,
            'tags': self.tags
        }
    
    def to_jsonl(self):
        """
        Export as JSONL format for Whisper fine-tuning
        Format: {"audio": "path/to/audio.wav", "transcription": "corrected text"}
        """
        return {
            "audio": self.audio_file_path,
            "text": self.corrected_transcription or self.original_transcription,
            "metadata": {
                "sample_id": self.id,
                "duration": self.audio_duration,
                "quality_score": self.quality_score,
                "is_corrected": self.is_corrected,
                "tags": self.tags.split(',') if self.tags else []
            }
        }


class TrainingDataSession(db.Model):
    """
    Tracks training data collection sessions
    Useful for organizing and versioning fine-tuning datasets
    """
    __tablename__ = 'training_data_sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Session info
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Statistics
    total_samples = db.Column(db.Integer, default=0)
    corrected_samples = db.Column(db.Integer, default=0)
    total_duration = db.Column(db.Float, default=0.0)  # seconds
    average_quality_score = db.Column(db.Float, default=0.0)
    
    # Configuration
    min_quality_score = db.Column(db.Float, default=0.7)  # Only use samples >= this
    tags_filter = db.Column(db.String(255), nullable=True)  # Only include samples with these tags
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    finalized_at = db.Column(db.DateTime, nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    export_count = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'total_samples': self.total_samples,
            'corrected_samples': self.corrected_samples,
            'total_duration': self.total_duration,
            'average_quality_score': self.average_quality_score,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active
        }


class TrainingDataStats(db.Model):
    """
    Pre-computed statistics for quick dashboard display
    Cached to avoid expensive aggregations
    """
    __tablename__ = 'training_data_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Overall stats
    total_samples = db.Column(db.Integer, default=0)
    corrected_samples = db.Column(db.Integer, default=0)
    total_duration_hours = db.Column(db.Float, default=0.0)
    average_quality_score = db.Column(db.Float, default=0.0)
    
    # Daily stats
    samples_today = db.Column(db.Integer, default=0)
    samples_this_week = db.Column(db.Integer, default=0)
    samples_this_month = db.Column(db.Integer, default=0)
    
    # By domain
    medical_samples = db.Column(db.Integer, default=0)
    cardiology_samples = db.Column(db.Integer, default=0)
    respiratory_samples = db.Column(db.Integer, default=0)
    other_samples = db.Column(db.Integer, default=0)
    
    # Last updated
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'total_samples': self.total_samples,
            'corrected_samples': self.corrected_samples,
            'correction_rate': (self.corrected_samples / self.total_samples * 100) if self.total_samples > 0 else 0,
            'total_duration_hours': round(self.total_duration_hours, 1),
            'average_quality_score': round(self.average_quality_score, 3),
            'samples_today': self.samples_today,
            'samples_this_week': self.samples_this_week,
            'samples_this_month': self.samples_this_month,
            'by_domain': {
                'medical': self.medical_samples,
                'cardiology': self.cardiology_samples,
                'respiratory': self.respiratory_samples,
                'other': self.other_samples
            }
        }


