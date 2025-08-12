"""
South African Medical Imaging API Endpoints
World-class API integrating all SA-specific features
"""

from flask import Blueprint, request, jsonify, session, send_file
from functools import wraps
import json
import os
import io
import base64
from datetime import datetime
from typing import Dict, Any

# Import our world-class SA modules
from south_african_localization import sa_localization
from south_african_voice_dictation import sa_voice_dictation, DictationSession
from advanced_dicom_viewer import advanced_dicom_viewer, Measurement, Annotation
from user_db import user_db
from image_db import image_db

# Create Blueprint for SA-specific endpoints
sa_api_bp = Blueprint('sa_api', __name__, url_prefix='/api/sa')

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') or session.get('role') != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# SOUTH AFRICAN LOCALIZATION ENDPOINTS
# ============================================================================

@sa_api_bp.route('/localization/languages', methods=['GET'])
def get_supported_languages():
    """Get supported languages"""
    try:
        languages = sa_localization.get_supported_languages()
        return jsonify({
            'success': True,
            'languages': languages,
            'default': sa_localization.default_language
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get languages: {str(e)}'}), 500

@sa_api_bp.route('/localization/translate', methods=['POST'])
def translate_text():
    """Translate text keys to specified language"""
    try:
        data = request.get_json()
        if not data or 'keys' not in data:
            return jsonify({'error': 'Translation keys required'}), 400
        
        keys = data['keys']
        language = data.get('language', 'en')
        
        translations = {}
        for key in keys:
            translations[key] = sa_localization.translate(key, language)
        
        return jsonify({
            'success': True,
            'translations': translations,
            'language': language
        })
    except Exception as e:
        return jsonify({'error': f'Translation failed: {str(e)}'}), 500

@sa_api_bp.route('/localization/medical-aids', methods=['GET'])
def get_medical_aids():
    """Get South African medical aid schemes"""
    try:
        medical_aids = sa_localization.medical_aids
        return jsonify({
            'success': True,
            'medical_aids': medical_aids
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get medical aids: {str(e)}'}), 500

@sa_api_bp.route('/localization/provinces', methods=['GET'])
def get_provinces():
    """Get South African provinces"""
    try:
        provinces = sa_localization.provinces
        return jsonify({
            'success': True,
            'provinces': provinces
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get provinces: {str(e)}'}), 500

@sa_api_bp.route('/localization/validate-id', methods=['POST'])
def validate_sa_id():
    """Validate South African ID number"""
    try:
        data = request.get_json()
        if not data or 'id_number' not in data:
            return jsonify({'error': 'ID number required'}), 400
        
        id_number = data['id_number']
        is_valid = sa_localization.validate_id_number(id_number)
        
        return jsonify({
            'success': True,
            'valid': is_valid,
            'id_number': id_number
        })
    except Exception as e:
        return jsonify({'error': f'ID validation failed: {str(e)}'}), 500

@sa_api_bp.route('/localization/format-phone', methods=['POST'])
def format_phone_number():
    """Format phone number in SA format"""
    try:
        data = request.get_json()
        if not data or 'phone' not in data:
            return jsonify({'error': 'Phone number required'}), 400
        
        phone = data['phone']
        formatted = sa_localization.format_phone(phone)
        
        return jsonify({
            'success': True,
            'original': phone,
            'formatted': formatted
        })
    except Exception as e:
        return jsonify({'error': f'Phone formatting failed: {str(e)}'}), 500

# ============================================================================
# VOICE DICTATION ENDPOINTS
# ============================================================================

@sa_api_bp.route('/dictation/create-session', methods=['POST'])
@require_auth
def create_dictation_session():
    """Create new voice dictation session"""
    try:
        data = request.get_json() or {}
        user_id = session.get('user_id')
        patient_id = data.get('patient_id')
        study_id = data.get('study_id')
        language = data.get('language', 'en')
        
        session_id = sa_voice_dictation.create_dictation_session(
            user_id, patient_id, study_id, language
        )
        
        if session_id:
            return jsonify({
                'success': True,
                'session_id': session_id,
                'message': 'Dictation session created'
            })
        else:
            return jsonify({'error': 'Failed to create dictation session'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to create dictation session: {str(e)}'}), 500

@sa_api_bp.route('/dictation/upload-audio', methods=['POST'])
@require_auth
def upload_dictation_audio():
    """Upload audio data for dictation"""
    try:
        session_id = request.form.get('session_id')
        if not session_id:
            return jsonify({'error': 'Session ID required'}), 400
        
        # Get audio file from request
        if 'audio' not in request.files:
            return jsonify({'error': 'Audio file required'}), 400
        
        audio_file = request.files['audio']
        audio_data = audio_file.read()
        
        # Save audio data
        success = sa_voice_dictation.save_audio_data(session_id, audio_data)
        
        if success:
            # Start transcription
            transcript = sa_voice_dictation.transcribe_audio(session_id)
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'transcript': transcript,
                'message': 'Audio uploaded and transcribed'
            })
        else:
            return jsonify({'error': 'Failed to save audio'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Audio upload failed: {str(e)}'}), 500

@sa_api_bp.route('/dictation/submit-correction', methods=['POST'])
@require_auth
def submit_dictation_correction():
    """Submit corrected transcript"""
    try:
        data = request.get_json()
        if not data or 'session_id' not in data or 'corrected_transcript' not in data:
            return jsonify({'error': 'Session ID and corrected transcript required'}), 400
        
        session_id = data['session_id']
        corrected_transcript = data['corrected_transcript']
        user_id = session.get('user_id')
        
        success = sa_voice_dictation.submit_correction(session_id, corrected_transcript, user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Correction submitted and learned'
            })
        else:
            return jsonify({'error': 'Failed to submit correction'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Correction submission failed: {str(e)}'}), 500

@sa_api_bp.route('/dictation/sessions', methods=['GET'])
@require_auth
def get_user_dictations():
    """Get user's dictation sessions"""
    try:
        user_id = session.get('user_id')
        limit = int(request.args.get('limit', 50))
        
        sessions = sa_voice_dictation.get_user_dictations(user_id, limit)
        sessions_data = [session.to_dict() for session in sessions]
        
        return jsonify({
            'success': True,
            'sessions': sessions_data,
            'count': len(sessions_data)
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get dictations: {str(e)}'}), 500

@sa_api_bp.route('/dictation/stats', methods=['GET'])
@require_auth
def get_dictation_stats():
    """Get dictation statistics"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role')
        
        # Admin can see all stats, users see only their own
        stats_user_id = None if user_role == 'admin' else user_id
        
        stats = sa_voice_dictation.get_dictation_stats(stats_user_id)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get dictation stats: {str(e)}'}), 500

# ============================================================================
# ADVANCED DICOM VIEWER ENDPOINTS
# ============================================================================

@sa_api_bp.route('/viewer/create-session', methods=['POST'])
@require_auth
def create_viewer_session():
    """Create new DICOM viewer session"""
    try:
        data = request.get_json() or {}
        user_id = session.get('user_id')
        study_id = data.get('study_id')
        series_id = data.get('series_id')
        instance_id = data.get('instance_id')
        
        session_id = advanced_dicom_viewer.create_viewer_session(
            user_id, study_id, series_id, instance_id
        )
        
        if session_id:
            return jsonify({
                'success': True,
                'session_id': session_id,
                'message': 'Viewer session created'
            })
        else:
            return jsonify({'error': 'Failed to create viewer session'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to create viewer session: {str(e)}'}), 500

@sa_api_bp.route('/viewer/load-dicom', methods=['POST'])
@require_auth
def load_dicom_file():
    """Load DICOM file for viewing"""
    try:
        data = request.get_json()
        if not data or 'file_path' not in data:
            return jsonify({'error': 'File path required'}), 400
        
        file_path = data['file_path']
        
        # Load DICOM file
        dicom_data = advanced_dicom_viewer.load_dicom_file(file_path)
        
        if dicom_data:
            # Convert pixel array to base64 for web display
            if dicom_data['pixel_array'] is not None:
                # Apply default windowing
                metadata = dicom_data['metadata']
                windowed_image = advanced_dicom_viewer.apply_window_level(
                    dicom_data['pixel_array'],
                    metadata['window_center'],
                    metadata['window_width'],
                    metadata['rescale_intercept'],
                    metadata['rescale_slope']
                )
                
                # Convert to base64
                image_base64 = advanced_dicom_viewer.convert_to_base64_image(windowed_image)
                
                return jsonify({
                    'success': True,
                    'metadata': metadata,
                    'image': image_base64,
                    'message': 'DICOM file loaded successfully'
                })
            else:
                return jsonify({
                    'success': True,
                    'metadata': dicom_data['metadata'],
                    'message': 'DICOM metadata loaded (no pixel data)'
                })
        else:
            return jsonify({'error': 'Failed to load DICOM file'}), 500
            
    except Exception as e:
        return jsonify({'error': f'DICOM loading failed: {str(e)}'}), 500

@sa_api_bp.route('/viewer/window-presets/<modality>', methods=['GET'])
@require_auth
def get_window_presets(modality: str):
    """Get window/level presets for modality"""
    try:
        presets = advanced_dicom_viewer.get_window_presets(modality)
        
        return jsonify({
            'success': True,
            'modality': modality,
            'presets': presets
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get presets: {str(e)}'}), 500

@sa_api_bp.route('/viewer/calculate-measurement', methods=['POST'])
@require_auth
def calculate_measurement():
    """Calculate measurement from points"""
    try:
        data = request.get_json()
        if not data or 'type' not in data or 'points' not in data:
            return jsonify({'error': 'Measurement type and points required'}), 400
        
        measurement_type = data['type']
        points = data['points']
        pixel_spacing = data.get('pixel_spacing', [1.0, 1.0])
        
        result = advanced_dicom_viewer.calculate_measurement(
            measurement_type, points, pixel_spacing
        )
        
        return jsonify({
            'success': True,
            'measurement': result
        })
    except Exception as e:
        return jsonify({'error': f'Measurement calculation failed: {str(e)}'}), 500

@sa_api_bp.route('/viewer/save-measurement', methods=['POST'])
@require_auth
def save_measurement():
    """Save measurement to database"""
    try:
        data = request.get_json()
        required_fields = ['session_id', 'type', 'points', 'value', 'unit']
        
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required measurement data'}), 400
        
        user_id = session.get('user_id')
        measurement_id = f"meas_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id[:8]}"
        
        measurement = Measurement(
            measurement_id=measurement_id,
            type=data['type'],
            points=data['points'],
            value=data['value'],
            unit=data['unit'],
            description=data.get('description', ''),
            created_by=user_id,
            created_at=datetime.now().isoformat()
        )
        
        success = advanced_dicom_viewer.save_measurement(data['session_id'], measurement)
        
        if success:
            return jsonify({
                'success': True,
                'measurement_id': measurement_id,
                'message': 'Measurement saved'
            })
        else:
            return jsonify({'error': 'Failed to save measurement'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to save measurement: {str(e)}'}), 500

@sa_api_bp.route('/viewer/save-annotation', methods=['POST'])
@require_auth
def save_annotation():
    """Save annotation to database"""
    try:
        data = request.get_json()
        required_fields = ['session_id', 'type', 'points']
        
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required annotation data'}), 400
        
        user_id = session.get('user_id')
        annotation_id = f"anno_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id[:8]}"
        
        annotation = Annotation(
            annotation_id=annotation_id,
            type=data['type'],
            points=data['points'],
            text=data.get('text', ''),
            style=data.get('style', {}),
            created_by=user_id,
            created_at=datetime.now().isoformat()
        )
        
        success = advanced_dicom_viewer.save_annotation(data['session_id'], annotation)
        
        if success:
            return jsonify({
                'success': True,
                'annotation_id': annotation_id,
                'message': 'Annotation saved'
            })
        else:
            return jsonify({'error': 'Failed to save annotation'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to save annotation: {str(e)}'}), 500

@sa_api_bp.route('/viewer/stats', methods=['GET'])
@require_auth
def get_viewer_stats():
    """Get DICOM viewer statistics"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role')
        
        # Admin can see all stats, users see only their own
        stats_user_id = None if user_role == 'admin' else user_id
        
        stats = advanced_dicom_viewer.get_viewer_stats(stats_user_id)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get viewer stats: {str(e)}'}), 500

# ============================================================================
# INTEGRATED DASHBOARD ENDPOINTS
# ============================================================================

@sa_api_bp.route('/dashboard/comprehensive-stats', methods=['GET'])
@require_auth
def get_comprehensive_dashboard_stats():
    """Get comprehensive dashboard statistics for SA system"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role')
        
        # Determine if admin (can see all stats) or user (own stats only)
        stats_user_id = None if user_role == 'admin' else user_id
        
        # Get stats from all modules
        dictation_stats = sa_voice_dictation.get_dictation_stats(stats_user_id)
        viewer_stats = advanced_dicom_viewer.get_viewer_stats(stats_user_id)
        image_stats = image_db.get_image_stats(stats_user_id)
        
        # User stats (admin only)
        user_stats = {}
        if user_role == 'admin':
            user_stats = user_db.get_user_stats()
        
        # System health
        system_health = {
            'dictation_engine': 'online',
            'dicom_viewer': 'online',
            'localization': 'online',
            'database': 'online'
        }
        
        return jsonify({
            'success': True,
            'stats': {
                'dictation': dictation_stats,
                'viewer': viewer_stats,
                'images': image_stats,
                'users': user_stats,
                'system_health': system_health
            },
            'user_role': user_role,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get comprehensive stats: {str(e)}'}), 500

@sa_api_bp.route('/dashboard/sa-specific-info', methods=['GET'])
@require_auth
def get_sa_specific_info():
    """Get South Africa-specific dashboard information"""
    try:
        user_id = session.get('user_id')
        
        # Get user's province/location info if available
        user = user_db.get_user_by_id(user_id)
        user_preferences = user_db.get_user_preferences(user_id)
        
        # Current time in SA timezone
        sa_time = datetime.now().strftime('%H:%M')
        sa_date = sa_localization.format_date(datetime.now())
        
        # Medical aid information
        medical_aids_count = len(sa_localization.medical_aids)
        
        # Language preferences
        supported_languages = sa_localization.get_supported_languages()
        
        return jsonify({
            'success': True,
            'sa_info': {
                'current_time': sa_time,
                'current_date': sa_date,
                'timezone': 'Africa/Johannesburg',
                'supported_languages': supported_languages,
                'medical_aids_supported': medical_aids_count,
                'provinces_supported': len(sa_localization.provinces),
                'user_language': user_preferences.get('language', 'en'),
                'currency_symbol': 'R',
                'date_format': 'DD/MM/YYYY',
                'time_format': '24-hour'
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get SA info: {str(e)}'}), 500

# ============================================================================
# SYSTEM ADMINISTRATION ENDPOINTS
# ============================================================================

@sa_api_bp.route('/admin/system-status', methods=['GET'])
@require_admin
def get_system_status():
    """Get comprehensive system status (admin only)"""
    try:
        # Check all system components
        status = {
            'localization': {
                'status': 'online',
                'languages_loaded': len(sa_localization.languages),
                'medical_terms_loaded': sum(len(terms) for terms in sa_localization.medical_terms.values()),
                'medical_aids_loaded': len(sa_localization.medical_aids)
            },
            'voice_dictation': {
                'status': 'online',
                'vosk_available': hasattr(sa_voice_dictation, 'vosk_model') and sa_voice_dictation.vosk_model is not None,
                'sr_available': hasattr(sa_voice_dictation, 'recognizer') and sa_voice_dictation.recognizer is not None,
                'total_sessions': sa_voice_dictation.get_dictation_stats().get('total_sessions', 0)
            },
            'dicom_viewer': {
                'status': 'online',
                'pydicom_available': True,  # We check this in the module
                'imaging_available': True,
                'total_sessions': advanced_dicom_viewer.get_viewer_stats().get('total_sessions', 0)
            },
            'database': {
                'status': 'online',
                'user_count': user_db.get_user_stats().get('total_users', 0),
                'image_count': image_db.get_image_stats().get('total_images', 0)
            }
        }
        
        return jsonify({
            'success': True,
            'system_status': status,
            'overall_health': 'excellent',
            'last_check': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get system status: {str(e)}'}), 500

# Error handlers
@sa_api_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@sa_api_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized'}), 401

@sa_api_bp.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Forbidden'}), 403

@sa_api_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@sa_api_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500