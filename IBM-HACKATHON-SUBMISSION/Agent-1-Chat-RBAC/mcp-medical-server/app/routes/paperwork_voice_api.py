"""
Paperwork Voice API Endpoints

Integrates with medical-reporting-module's Whisper model to provide
voice-to-text transcription for form filling with edit/correction capabilities.
"""

from flask import Blueprint, request, jsonify, send_file
import logging
from pathlib import Path
import os
from app.ml.paperwork_voice_service import create_paperwork_voice_service

logger = logging.getLogger(__name__)

paperwork_voice_bp = Blueprint('paperwork_voice', __name__, url_prefix='/api/paperwork/voice')

# Global service instance (will be initialized with Whisper model reference)
paperwork_voice_service = None


def init_paperwork_voice_service(whisper_model_loader):
    """
    Initialize paperwork voice service with Whisper model from medical-reporting-module.
    
    Call this during app startup:
        from app.routes.paperwork_voice_api import init_paperwork_voice_service
        from path_to.voice_api import get_or_load_whisper_model
        
        init_paperwork_voice_service(get_or_load_whisper_model)
    """
    global paperwork_voice_service
    paperwork_voice_service = create_paperwork_voice_service(whisper_model_loader)
    logger.info("✓ Paperwork Voice Service initialized with shared Whisper model")


@paperwork_voice_bp.route('/transcribe-field', methods=['POST'])
def transcribe_field():
    """
    Transcribe audio for a form field.
    
    Request JSON:
    {
        "audio_file": "path/to/audio.wav",
        "field_name": "patient_name",
        "worker_id": "W001",
        "language": "en"
    }
    """
    if paperwork_voice_service is None:
        return jsonify({"error": "Voice service not initialized"}), 500
    
    try:
        data = request.get_json()
        
        # Validate inputs
        if not data.get('audio_file'):
            return jsonify({"error": "Missing audio_file"}), 400
        if not data.get('field_name'):
            return jsonify({"error": "Missing field_name"}), 400
        if not data.get('worker_id'):
            return jsonify({"error": "Missing worker_id"}), 400
        
        # Transcribe
        result = paperwork_voice_service.transcribe_form_field(
            audio_file_path=data['audio_file'],
            field_name=data['field_name'],
            worker_id=data['worker_id'],
            language=data.get('language', 'en')
        )
        
        return jsonify(result), 200 if result['success'] else 400
    
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return jsonify({"error": str(e)}), 500


@paperwork_voice_bp.route('/edit-transcription', methods=['POST'])
def edit_transcription():
    """
    Edit/correct a transcription.
    
    Request JSON:
    {
        "transcription_id": "txn_W001_patient_name_20240116_120000",
        "corrected_text": "John Smith",
        "worker_id": "W001"
    }
    """
    if paperwork_voice_service is None:
        return jsonify({"error": "Voice service not initialized"}), 500
    
    try:
        data = request.get_json()
        
        if not data.get('transcription_id'):
            return jsonify({"error": "Missing transcription_id"}), 400
        if not data.get('corrected_text'):
            return jsonify({"error": "Missing corrected_text"}), 400
        if not data.get('worker_id'):
            return jsonify({"error": "Missing worker_id"}), 400
        
        result = paperwork_voice_service.edit_transcription(
            transcription_id=data['transcription_id'],
            corrected_text=data['corrected_text'],
            worker_id=data['worker_id']
        )
        
        return jsonify(result), 200 if result['success'] else 400
    
    except Exception as e:
        logger.error(f"Edit error: {e}")
        return jsonify({"error": str(e)}), 500


@paperwork_voice_bp.route('/preview/<transcription_id>', methods=['GET'])
def preview_transcription(transcription_id):
    """Get full transcription with edit history for preview"""
    if paperwork_voice_service is None:
        return jsonify({"error": "Voice service not initialized"}), 500
    
    try:
        result = paperwork_voice_service.get_transcription_preview(transcription_id)
        return jsonify(result), 200 if result['success'] else 404
    
    except Exception as e:
        logger.error(f"Preview error: {e}")
        return jsonify({"error": str(e)}), 500


@paperwork_voice_bp.route('/submit', methods=['POST'])
def submit_transcription():
    """Submit finalized transcription to form"""
    if paperwork_voice_service is None:
        return jsonify({"error": "Voice service not initialized"}), 500
    
    try:
        data = request.get_json()
        
        if not data.get('transcription_id'):
            return jsonify({"error": "Missing transcription_id"}), 400
        if not data.get('form_id'):
            return jsonify({"error": "Missing form_id"}), 400
        
        result = paperwork_voice_service.submit_transcription(
            transcription_id=data['transcription_id'],
            form_id=data['form_id']
        )
        
        return jsonify(result), 200 if result['success'] else 400
    
    except Exception as e:
        logger.error(f"Submit error: {e}")
        return jsonify({"error": str(e)}), 500


@paperwork_voice_bp.route('/batch-transcribe', methods=['POST'])
def batch_transcribe():
    """
    Transcribe multiple form fields at once.
    
    Request JSON:
    {
        "form_id": "FORM001",
        "worker_id": "W001",
        "language": "en",
        "fields": {
            "patient_name": "path/to/patient_name.wav",
            "date_of_birth": "path/to/dob.wav",
            "procedure": "path/to/procedure.wav"
        }
    }
    """
    if paperwork_voice_service is None:
        return jsonify({"error": "Voice service not initialized"}), 500
    
    try:
        data = request.get_json()
        
        if not data.get('form_id'):
            return jsonify({"error": "Missing form_id"}), 400
        if not data.get('worker_id'):
            return jsonify({"error": "Missing worker_id"}), 400
        if not data.get('fields'):
            return jsonify({"error": "Missing fields"}), 400
        
        result = paperwork_voice_service.batch_transcribe_form(
            form_data={
                "form_id": data['form_id'],
                "fields": data['fields']
            },
            worker_id=data['worker_id'],
            language=data.get('language', 'en')
        )
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Batch transcribe error: {e}")
        return jsonify({"error": str(e)}), 500


@paperwork_voice_bp.route('/register-worker', methods=['POST'])
def register_worker():
    """
    Register a worker's voice profile.
    
    Request JSON:
    {
        "worker_id": "W001",
        "name": "Dr. John Smith",
        "language": "en",
        "accent_notes": "South African English"
    }
    """
    if paperwork_voice_service is None:
        return jsonify({"error": "Voice service not initialized"}), 500
    
    try:
        data = request.get_json()
        
        if not data.get('worker_id'):
            return jsonify({"error": "Missing worker_id"}), 400
        if not data.get('name'):
            return jsonify({"error": "Missing name"}), 400
        
        result = paperwork_voice_service.register_worker_voice_profile(
            worker_id=data['worker_id'],
            name=data['name'],
            language=data.get('language', 'en'),
            accent_notes=data.get('accent_notes', '')
        )
        
        return jsonify(result), 200 if result['success'] else 400
    
    except Exception as e:
        logger.error(f"Worker registration error: {e}")
        return jsonify({"error": str(e)}), 500


@paperwork_voice_bp.route('/worker-stats/<worker_id>', methods=['GET'])
def get_worker_stats(worker_id):
    """Get transcription statistics for a worker"""
    if paperwork_voice_service is None:
        return jsonify({"error": "Voice service not initialized"}), 500
    
    try:
        result = paperwork_voice_service.get_worker_stats(worker_id)
        return jsonify(result), 200 if result['success'] else 404
    
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({"error": str(e)}), 500


@paperwork_voice_bp.route('/audio/<transcription_id>', methods=['GET'])
def get_audio_playback(transcription_id):
    """Get audio file for playback"""
    if paperwork_voice_service is None:
        return jsonify({"error": "Voice service not initialized"}), 500
    
    try:
        audio_path = paperwork_voice_service.get_transcription_for_playback(transcription_id)
        
        if not audio_path or not Path(audio_path).exists():
            return jsonify({"error": "Audio file not found"}), 404
        
        return send_file(audio_path, mimetype='audio/wav')
    
    except Exception as e:
        logger.error(f"Audio playback error: {e}")
        return jsonify({"error": str(e)}), 500


@paperwork_voice_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    if paperwork_voice_service is None:
        return jsonify({"status": "not_initialized", "whisper": "not_ready"}), 503
    
    whisper_model = paperwork_voice_service.get_whisper_model()
    
    return jsonify({
        "status": "ready",
        "whisper": "ready" if whisper_model else "not_loaded",
        "service": "paperwork_voice"
    }), 200
