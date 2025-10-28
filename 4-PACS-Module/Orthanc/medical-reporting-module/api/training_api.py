"""
Training Data API
Endpoints for collecting and managing training data for Whisper fine-tuning

Two databases:
1. RawTranscriptions: voice files + raw STT output (archived, not actively used)
2. STTTrainingData: corrected transcriptions + metadata (high-quality training pairs)
"""

import logging
import json
import os
import tempfile
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file
from pathlib import Path

logger = logging.getLogger(__name__)

training_bp = Blueprint("training", __name__)


def calculate_error_count(original, corrected):
    """Calculate number of word-level differences between transcriptions"""
    if not original or not corrected:
        return 0
    
    orig_words = original.lower().split()
    corr_words = corrected.lower().split()
    
    # Simple Levenshtein-like distance
    errors = 0
    max_len = max(len(orig_words), len(corr_words))
    
    for i in range(max_len):
        orig_word = orig_words[i] if i < len(orig_words) else ""
        corr_word = corr_words[i] if i < len(corr_words) else ""
        
        if orig_word != corr_word:
            errors += 1
    
    return errors


def calculate_quality_score(original, corrected, error_count):
    """
    Calculate quality score (0-1) based on corrections
    Higher score = fewer corrections needed
    """
    if not original:
        return 0.0
    
    orig_words = len(original.split())
    if orig_words == 0:
        return 0.0
    
    # Error rate: errors / total words
    error_rate = error_count / orig_words
    
    # Quality = 1 - error_rate, capped at 1.0
    quality = max(0.0, 1.0 - error_rate)
    
    return round(quality, 3)


@training_bp.route("/save-transcription", methods=["POST"])
def save_training_sample():
    """
    Save a transcription sample for training
    Saves both:
    1. Raw transcription to RawTranscriptions archive
    2. Corrected version to STTTrainingData (if corrected)
    
    Request body:
    {
        "session_id": "uuid",
        "original_transcription": "raw whisper output",
        "corrected_transcription": "user-corrected version",
        "audio_file_path": "/path/to/audio.wav",
        "audio_duration": 12.5,
        "audio_filename": "recording_20231025.wav",
        "tags": "medical,cardiology"
    }
    """
    try:
        from models.training_samples import TrainingDataSample
        from models.raw_transcriptions import RawTranscription
        from models.database import db
        from core.user_manager import get_current_user_id
        
        data = request.get_json() or {}
        user_id = get_current_user_id()
        
        original = data.get('original_transcription', '')
        corrected = data.get('corrected_transcription', '')
        audio_path = data.get('audio_file_path', '')
        audio_filename = data.get('audio_filename', '')
        audio_duration = data.get('audio_duration', 0.0)
        session_id = data.get('session_id')
        tags = data.get('tags', '')
        
        if not original:
            return jsonify({'error': 'original_transcription required'}), 400
        
        # Step 1: Save raw transcription to archive (lightweight DB)
        raw_record = RawTranscription(
            session_id=session_id,
            user_id=user_id,
            audio_file_path=audio_path,
            audio_filename=audio_filename,
            audio_duration=audio_duration,
            raw_transcription=original,
            confidence_score=data.get('original_confidence', 0.9)
        )
        db.session.add(raw_record)
        db.session.flush()
        
        logger.info(f"📦 Raw transcription archived: {raw_record.id}")
        
        # Calculate error metrics
        is_corrected = corrected and corrected != original
        error_count = calculate_error_count(original, corrected) if is_corrected else 0
        quality_score = calculate_quality_score(original, corrected, error_count)
        
        # Check if medical terms were corrected
        medical_terms = ['blood pressure', 'heart rate', 'temperature', 'tuberculosis', 
                        'pneumonia', 'diabetes', 'hypertension', 'ecg', 'x-ray']
        medical_corrected = False
        if is_corrected:
            for term in medical_terms:
                if term in original.lower() and term not in (corrected or '').lower():
                    medical_corrected = True
                    break
        
        # Step 2: Save to STT Training Data (only if corrected or explicitly requested)
        # Only high-quality corrected pairs are saved here
        if is_corrected or data.get('save_as_training', False):
            sample = TrainingDataSample(
                user_id=user_id,
                session_id=session_id,
                original_transcription=original,
                corrected_transcription=corrected or original,  # Use corrected or original
                audio_file_path=audio_path,
                audio_duration=audio_duration,
                audio_filename=audio_filename,
                original_confidence=data.get('original_confidence', 0.9),
                error_count=error_count,
                medical_terms_corrected=medical_corrected,
                quality_score=quality_score,
                is_corrected=is_corrected,
                corrected_at=datetime.utcnow() if is_corrected else None,
                tags=tags,
                notes=data.get('notes', '')
            )
            
            db.session.add(sample)
            db.session.flush()
            
            logger.info(f"✅ Training sample saved: {sample.id} (quality: {quality_score}, errors: {error_count})")
            
            training_id = sample.id
        else:
            training_id = None
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'raw_id': raw_record.id,
            'training_sample_id': training_id,
            'error_count': error_count if is_corrected else 0,
            'quality_score': quality_score if is_corrected else 0,
            'is_corrected': is_corrected,
            'timestamp': datetime.utcnow().isoformat()
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to save training sample: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to save training sample'}), 500


@training_bp.route("/update-transcription/<sample_id>", methods=["PUT"])
def update_training_sample(sample_id):
    """
    Update a transcription sample with user corrections
    
    Request body:
    {
        "corrected_transcription": "corrected text",
        "notes": "optional notes about the correction"
    }
    """
    try:
        from models.training_samples import TrainingDataSample
        from models.database import db
        from core.user_manager import get_current_user_id
        
        user_id = get_current_user_id()
        
        sample = TrainingDataSample.query.filter_by(id=sample_id, user_id=user_id).first()
        if not sample:
            return jsonify({'error': 'Sample not found'}), 404
        
        data = request.get_json() or {}
        corrected = data.get('corrected_transcription')
        
        if not corrected:
            return jsonify({'error': 'corrected_transcription required'}), 400
        
        # Recalculate metrics
        error_count = calculate_error_count(sample.original_transcription, corrected)
        quality_score = calculate_quality_score(sample.original_transcription, corrected, error_count)
        
        sample.corrected_transcription = corrected
        sample.error_count = error_count
        sample.quality_score = quality_score
        sample.is_corrected = True
        sample.corrected_at = datetime.utcnow()
        sample.notes = data.get('notes', '')
        
        db.session.commit()
        
        logger.info(f"✅ Training sample updated: {sample_id} (quality: {quality_score})")
        
        return jsonify({
            'success': True,
            'sample_id': sample_id,
            'error_count': error_count,
            'quality_score': quality_score,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to update training sample: {e}")
        return jsonify({'error': 'Failed to update training sample'}), 500


@training_bp.route("/samples", methods=["GET"])
def get_training_samples():
    """
    Get training samples with filters
    
    Query params:
    - limit: max results (default: 50)
    - offset: pagination offset (default: 0)
    - corrected_only: only corrected samples (default: false)
    - min_quality: minimum quality score (0-1)
    - tags: filter by tags (comma-separated)
    """
    try:
        from models.training_samples import TrainingDataSample
        from core.user_manager import get_current_user_id
        
        user_id = get_current_user_id()
        
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        corrected_only = request.args.get('corrected_only', 'false').lower() == 'true'
        min_quality = float(request.args.get('min_quality', 0.0))
        tags_filter = request.args.get('tags', '')
        
        query = TrainingDataSample.query.filter_by(user_id=user_id)
        
        if corrected_only:
            query = query.filter_by(is_corrected=True)
        
        if min_quality > 0:
            query = query.filter(TrainingDataSample.quality_score >= min_quality)
        
        if tags_filter:
            tag_list = [t.strip() for t in tags_filter.split(',')]
            for tag in tag_list:
                query = query.filter(TrainingDataSample.tags.contains(tag))
        
        total = query.count()
        samples = query.order_by(TrainingDataSample.created_at.desc()).limit(limit).offset(offset).all()
        
        return jsonify({
            'success': True,
            'total': total,
            'limit': limit,
            'offset': offset,
            'samples': [s.to_dict() for s in samples]
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get training samples: {e}")
        return jsonify({'error': 'Failed to get training samples'}), 500


@training_bp.route("/stats", methods=["GET"])
def get_training_stats():
    """Get training data collection statistics"""
    try:
        from models.training_samples import TrainingDataSample, TrainingDataStats
        from models.database import db
        from core.user_manager import get_current_user_id
        from datetime import timedelta
        from sqlalchemy import func
        
        user_id = get_current_user_id()
        
        # Query basic stats
        total = TrainingDataSample.query.filter_by(user_id=user_id).count()
        corrected = TrainingDataSample.query.filter_by(user_id=user_id, is_corrected=True).count()
        total_duration = db.session.query(func.sum(TrainingDataSample.audio_duration)).filter_by(user_id=user_id).scalar() or 0
        avg_quality = db.session.query(func.avg(TrainingDataSample.quality_score)).filter_by(user_id=user_id).scalar() or 0.0
        
        # Time-based stats
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        
        today_count = TrainingDataSample.query.filter_by(user_id=user_id).filter(
            TrainingDataSample.created_at >= today_start
        ).count()
        
        week_count = TrainingDataSample.query.filter_by(user_id=user_id).filter(
            TrainingDataSample.created_at >= week_start
        ).count()
        
        month_count = TrainingDataSample.query.filter_by(user_id=user_id).filter(
            TrainingDataSample.created_at >= month_start
        ).count()
        
        return jsonify({
            'success': True,
            'total_samples': total,
            'corrected_samples': corrected,
            'correction_rate': (corrected / total * 100) if total > 0 else 0,
            'total_duration_hours': round(total_duration / 3600, 1),
            'average_quality_score': round(avg_quality, 3),
            'samples_today': today_count,
            'samples_this_week': week_count,
            'samples_this_month': month_count,
            'ready_for_training': corrected >= 100,  # Minimum 100 corrected samples
            'training_readiness': min(100, corrected) / 100  # 0-1 scale
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get training stats: {e}")
        return jsonify({'error': 'Failed to get training stats'}), 500


@training_bp.route("/export", methods=["GET"])
def export_training_data():
    """
    Export training data as JSONL for Whisper fine-tuning
    
    Query params:
    - min_quality: minimum quality score (default: 0.7)
    - corrected_only: only corrected samples (default: true)
    """
    try:
        from models.training_samples import TrainingDataSample
        from core.user_manager import get_current_user_id
        
        user_id = get_current_user_id()
        min_quality = float(request.args.get('min_quality', 0.7))
        corrected_only = request.args.get('corrected_only', 'true').lower() == 'true'
        
        query = TrainingDataSample.query.filter_by(user_id=user_id)
        
        if corrected_only:
            query = query.filter_by(is_corrected=True)
        
        if min_quality > 0:
            query = query.filter(TrainingDataSample.quality_score >= min_quality)
        
        samples = query.all()
        
        if not samples:
            return jsonify({'error': 'No samples to export'}), 404
        
        # Create JSONL content
        jsonl_lines = []
        for sample in samples:
            jsonl_lines.append(json.dumps(sample.to_jsonl()))
        
        jsonl_content = '\n'.join(jsonl_lines)
        
        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.jsonl')
        try:
            os.write(temp_fd, jsonl_content.encode('utf-8'))
            os.close(temp_fd)
            
            logger.info(f"✅ Exported {len(samples)} training samples for fine-tuning")
            
            return send_file(
                temp_path,
                mimetype='application/jsonl',
                as_attachment=True,
                download_name=f'whisper_training_data_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.jsonl'
            )
        finally:
            # Note: file is deleted after response is sent
            pass
        
    except Exception as e:
        logger.error(f"Failed to export training data: {e}")
        return jsonify({'error': 'Failed to export training data'}), 500


@training_bp.route("/sample/<sample_id>", methods=["GET"])
def get_training_sample(sample_id):
    """Get a single training sample"""
    try:
        from models.training_samples import TrainingDataSample
        from core.user_manager import get_current_user_id
        
        user_id = get_current_user_id()
        
        sample = TrainingDataSample.query.filter_by(id=sample_id, user_id=user_id).first()
        if not sample:
            return jsonify({'error': 'Sample not found'}), 404
        
        return jsonify({
            'success': True,
            'sample': sample.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get training sample: {e}")
        return jsonify({'error': 'Failed to get training sample'}), 500


@training_bp.route("/delete/<sample_id>", methods=["DELETE"])
def delete_training_sample(sample_id):
    """Delete a training sample"""
    try:
        from models.training_samples import TrainingDataSample
        from models.database import db
        from core.user_manager import get_current_user_id
        
        user_id = get_current_user_id()
        
        sample = TrainingDataSample.query.filter_by(id=sample_id, user_id=user_id).first()
        if not sample:
            return jsonify({'error': 'Sample not found'}), 404
        
        db.session.delete(sample)
        db.session.commit()
        
        logger.info(f"✅ Training sample deleted: {sample_id}")
        
        return jsonify({
            'success': True,
            'message': 'Sample deleted'
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to delete training sample: {e}")
        return jsonify({'error': 'Failed to delete training sample'}), 500


# ============================================================================
# Raw Transcriptions Database - Lightweight Archive (not actively used)
# ============================================================================

@training_bp.route("/raw/save", methods=["POST"])
def save_raw_transcription():
    """
    Save raw transcription (voice + uncorrected STT output) to archive database
    
    Request body:
    {
        "session_id": "uuid",
        "audio_file_path": "/path/to/audio.wav",
        "audio_duration": 12.5,
        "raw_transcription": "raw whisper output",
        "audio_filename": "recording_20231025.wav",
        "confidence_score": 0.95
    }
    """
    try:
        from models.raw_transcriptions import RawTranscription
        from models.database import db
        from core.user_manager import get_current_user_id
        
        user_id = get_current_user_id()
        data = request.get_json() or {}
        
        session_id = data.get('session_id')
        audio_path = data.get('audio_file_path', '')
        audio_filename = data.get('audio_filename', '')
        raw_transcription = data.get('raw_transcription', '')
        audio_duration = data.get('audio_duration', 0.0)
        confidence = data.get('confidence_score', 0.0)
        
        if not session_id or not raw_transcription:
            return jsonify({'error': 'session_id and raw_transcription required'}), 400
        
        # Save to raw transcriptions archive
        raw_record = RawTranscription(
            session_id=session_id,
            user_id=user_id,
            audio_file_path=audio_path,
            audio_filename=audio_filename,
            audio_duration=audio_duration,
            raw_transcription=raw_transcription,
            confidence_score=confidence
        )
        
        db.session.add(raw_record)
        db.session.commit()
        
        logger.info(f"📦 Raw transcription archived: {raw_record.id} (session: {session_id})")
        
        return jsonify({
            'success': True,
            'raw_id': raw_record.id,
            'message': 'Raw transcription archived'
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to save raw transcription: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to save raw transcription'}), 500


# ============================================================================
# Audio Playback - Serve voice files for editing modal
# ============================================================================

@training_bp.route("/audio/<session_id>", methods=["GET"])
def get_audio_for_session(session_id):
    """
    Serve audio file for a transcription session
    Used by the edit modal to allow users to listen to their recording or download it
    
    User can only access their own audio (user_id matching)
    
    Query parameters:
    - download=1 or download=true: Return as downloadable attachment (instead of inline)
    """
    try:
        from models.raw_transcriptions import RawTranscription
        from models.training_samples import TrainingDataSample
        from models.database import db
        from core.user_manager import get_current_user_id
        
        user_id = get_current_user_id()
        
        logger.info(f"🔊 Audio request: session={session_id}, user={user_id}")
        
        # Try to find the audio in raw transcriptions first
        raw_record = RawTranscription.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        
        if raw_record and raw_record.audio_file_path:
            logger.info(f"✅ Found audio in RawTranscription: {raw_record.audio_file_path}")
            audio_path = raw_record.audio_file_path
            filename = raw_record.audio_filename or f"{session_id}.wav"
            
            # Verify file exists
            if not os.path.exists(audio_path):
                logger.warning(f"⚠️ Audio file not found at path: {audio_path}")
                return jsonify({'error': 'Audio file not found'}), 404
        else:
            logger.info(f"⚠️ Not found in RawTranscription, checking TrainingDataSample...")
            # Fall back to training data samples
            sample = TrainingDataSample.query.filter_by(
                session_id=session_id,
                user_id=user_id
            ).first()
            
            if not sample or not sample.audio_file_path:
                logger.warning(f"❌ Audio not found for session {session_id}")
                return jsonify({'error': 'Audio not found'}), 404
            
            audio_path = sample.audio_file_path
            filename = sample.audio_filename or f"{session_id}.wav"
            
            # Verify file exists
            if not os.path.exists(audio_path):
                logger.warning(f"⚠️ Audio file not found at path: {audio_path}")
                return jsonify({'error': 'Audio file not found'}), 404
        
        # Check if this is a download request or inline playback
        is_download = request.args.get('download', '').lower() in ('1', 'true', 'yes')
        
        if is_download:
            logger.info(f"� Serving audio for download: {audio_path} to user {user_id}")
        else:
            logger.info(f"�🔊 Serving audio inline: {audio_path} to user {user_id}")
        
        return send_file(
            audio_path,
            mimetype='audio/wav',
            as_attachment=is_download,
            download_name=filename if is_download else None
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to serve audio: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to serve audio'}), 500


@training_bp.route("/session/<session_id>", methods=["GET"])
def get_session_data(session_id):
    """
    Get all data for a transcription session (for edit modal)
    Includes transcription text and audio metadata
    
    User can only access their own sessions (user_id matching)
    """
    try:
        from models.raw_transcriptions import RawTranscription
        from models.training_samples import TrainingDataSample
        from core.user_manager import get_current_user_id
        
        user_id = get_current_user_id()
        
        # Find raw transcription first
        raw = RawTranscription.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        
        if not raw:
            return jsonify({'error': 'Session not found'}), 404
        
        # Check if there's a corrected version in STT Training Data
        training_sample = TrainingDataSample.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'raw_transcription': raw.raw_transcription,
            'corrected_transcription': training_sample.corrected_transcription if training_sample else None,
            'audio_filename': raw.audio_filename,
            'audio_duration': raw.audio_duration,
            'confidence_score': raw.confidence_score,
            'has_audio': os.path.exists(raw.audio_file_path) if raw.audio_file_path else False,
            'audio_url': f'/api/training/audio/{session_id}'
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get session data: {e}")
        return jsonify({'error': 'Failed to get session data'}), 500
