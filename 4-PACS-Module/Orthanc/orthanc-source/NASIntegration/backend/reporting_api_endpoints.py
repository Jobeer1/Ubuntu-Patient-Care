#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - Reporting API Endpoints

REST API endpoints for the advanced reporting module with voice dictation,
STT, typist workflow, and custom image layouts.
"""

from flask import Blueprint, request, jsonify, session, send_file
from functools import wraps
import logging
import base64
import io
import json

import time
from datetime import datetime
from typing import Dict, Any

try:
    from .reporting_module import reporting_module
    from .auth_2fa import require_auth, require_admin
except ImportError:
    # Fallback to absolute imports
    from reporting_module import reporting_module
    from auth_2fa import require_auth, require_admin

logger = logging.getLogger(__name__)

# Create blueprint for reporting endpoints
reporting_api_bp = Blueprint('reporting_api', __name__, url_prefix='/api/reporting')

# ============================================================================
# DICTATION SESSION ENDPOINTS
# ============================================================================

@reporting_api_bp.route('/sessions', methods=['POST'])
@require_auth
def create_dictation_session():
    """Create new dictation session"""
    try:
        data = request.get_json() or {}
        user_id = session.get('user_id')
        
        patient_id = data.get('patient_id', '')
        study_id = data.get('study_id', '')
        image_ids = data.get('image_ids', [])
        language = data.get('language', 'en-ZA')
        
        # Create session
        dictation_session = reporting_module.create_dictation_session(
            user_id, patient_id, study_id, image_ids, language
        )
        
        return jsonify({
            'success': True,
            'session': dictation_session.to_dict(),
            'message': 'Dictation session created successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"❌ Error creating dictation session: {e}")
        return jsonify({'error': f'Failed to create session: {str(e)}'}), 500

@reporting_api_bp.route('/sessions/<session_id>', methods=['GET'])
@require_auth
def get_dictation_session(session_id: str):
    """Get dictation session by ID"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role')
        
        dictation_session = reporting_module.get_dictation_session(session_id)
        
        if not dictation_session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Check permissions (user can only access their own sessions, admin can access all)
        if user_role != 'admin' and dictation_session.user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({
            'success': True,
            'session': dictation_session.to_dict()
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting dictation session: {e}")
        return jsonify({'error': f'Failed to get session: {str(e)}'}), 500

@reporting_api_bp.route('/sessions', methods=['GET'])
@require_auth
def get_user_dictation_sessions():
    """Get user's dictation sessions"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role')
        
        # Query parameters
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        target_user_id = request.args.get('user_id')
        
        # Admin can view any user's sessions
        if user_role == 'admin' and target_user_id:
            query_user_id = target_user_id
        else:
            query_user_id = user_id
        
        sessions = reporting_module.get_user_dictation_sessions(query_user_id, status, limit)
        
        return jsonify({
            'success': True,
            'sessions': [s.to_dict() for s in sessions],
            'count': len(sessions)
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting user dictation sessions: {e}")
        return jsonify({'error': f'Failed to get sessions: {str(e)}'}), 500

@reporting_api_bp.route('/sessions/<session_id>/audio', methods=['POST'])
@require_auth
def upload_audio_recording(session_id: str):
    """Upload audio recording for dictation session"""
    try:
        user_id = session.get('user_id')
        
        # Verify session ownership
        dictation_session = reporting_module.get_dictation_session(session_id)
        if not dictation_session or dictation_session.user_id != user_id:
            return jsonify({'error': 'Session not found or access denied'}), 403
        
        # Get audio data
        if 'audio' in request.files:
            # File upload
            audio_file = request.files['audio']
            audio_data = audio_file.read()
        elif request.json and 'audio_data' in request.json:
            # Base64 encoded audio
            audio_data = base64.b64decode(request.json['audio_data'])
        else:
            return jsonify({'error': 'No audio data provided'}), 400
        
        # Save audio
        success, message = reporting_module.save_audio_recording(session_id, audio_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({'error': message}), 500
            
    except Exception as e:
        logger.error(f"❌ Error uploading audio: {e}")
        return jsonify({'error': f'Failed to upload audio: {str(e)}'}), 500

@reporting_api_bp.route('/sessions/<session_id>/audio', methods=['GET'])
@require_auth
def get_audio_recording(session_id: str):
    """Get audio recording for dictation session"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role')
        
        # Get session
        dictation_session = reporting_module.get_dictation_session(session_id)
        if not dictation_session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Check permissions
        if user_role != 'admin' and dictation_session.user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Check if audio file exists
        if not dictation_session.audio_file_path:
            return jsonify({'error': 'No audio recording found'}), 404
        
        # Return audio file
        return send_file(
            dictation_session.audio_file_path,
            mimetype='audio/wav',
            as_attachment=True,
            download_name=f"{session_id}.wav"
        )
        
    except Exception as e:
        logger.error(f"❌ Error getting audio recording: {e}")
        return jsonify({'error': f'Failed to get audio: {str(e)}'}), 500

@reporting_api_bp.route('/sessions/<session_id>/audio/start', methods=['POST'])
@require_auth
def start_audio_recording(session_id: str):
    """Start audio recording for a session"""
    try:
        user_id = session.get('user_id')
        
        # Verify session ownership
        dictation_session = reporting_module.get_dictation_session(session_id)
        if not dictation_session or dictation_session.user_id != user_id:
            return jsonify({'error': 'Session not found or access denied'}), 403
        
        # Start recording (in a real implementation, this would initialize the recording state)
        success, message = reporting_module.start_audio_recording(session_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Recording started',
                'session_id': session_id
            })
        else:
            return jsonify({'error': message}), 500
        
    except Exception as e:
        logger.error(f"❌ Error starting audio recording: {e}")
        return jsonify({'error': f'Failed to start recording: {str(e)}'}), 500

@reporting_api_bp.route('/sessions/<session_id>/audio/stop', methods=['POST'])
@require_auth
def stop_audio_recording(session_id: str):
    """Stop audio recording for a session"""
    try:
        user_id = session.get('user_id')
        
        # Verify session ownership
        dictation_session = reporting_module.get_dictation_session(session_id)
        if not dictation_session or dictation_session.user_id != user_id:
            return jsonify({'error': 'Session not found or access denied'}), 403
        
        # Stop recording
        success, message = reporting_module.stop_audio_recording(session_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Recording stopped',
                'session_id': session_id
            })
        else:
            return jsonify({'error': message}), 500
        
    except Exception as e:
        logger.error(f"❌ Error stopping audio recording: {e}")
        return jsonify({'error': f'Failed to stop recording: {str(e)}'}), 500

@reporting_api_bp.route('/sessions/<session_id>/save', methods=['POST'])
@require_auth
def save_report_draft(session_id: str):
    """Save report draft with measurements"""
    try:
        user_id = session.get('user_id')
        data = request.get_json() or {}
        
        # Verify session ownership
        dictation_session = reporting_module.get_dictation_session(session_id)
        if not dictation_session or dictation_session.user_id != user_id:
            return jsonify({'error': 'Session not found or access denied'}), 403
        
        # Extract data
        report_text = data.get('report_text', '')
        measurements = data.get('measurements', [])
        
        # Save the report draft
        success, message = reporting_module.save_report_draft(session_id, report_text, measurements)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Report draft saved successfully',
                'session_id': session_id
            })
        else:
            return jsonify({'error': message}), 500
        
    except Exception as e:
        logger.error(f"❌ Error saving report draft: {e}")
        return jsonify({'error': f'Failed to save report: {str(e)}'}), 500

# ============================================================================
# TYPIST WORKFLOW ENDPOINTS
# ============================================================================

@reporting_api_bp.route('/typist/queue', methods=['GET'])
@require_auth
def get_typist_queue():
    """Get dictation sessions in typist queue"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role')
        
        # Only typists and admins can access the queue
        if user_role not in ['admin', 'typist']:
            return jsonify({'error': 'Access denied - typist role required'}), 403
        
        sessions = reporting_module.get_typist_queue(user_id if user_role == 'typist' else None)
        
        return jsonify({
            'success': True,
            'sessions': [s.to_dict() for s in sessions],
            'count': len(sessions)
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting typist queue: {e}")
        return jsonify({'error': f'Failed to get typist queue: {str(e)}'}), 500

@reporting_api_bp.route('/sessions/<session_id>/correction', methods=['POST'])
@require_auth
def update_dictation_correction():
    """Update dictation with typist corrections"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role')
        
        # Only typists and admins can make corrections
        if user_role not in ['admin', 'typist']:
            return jsonify({'error': 'Access denied - typist role required'}), 403
        
        data = request.get_json()
        if not data or 'corrected_text' not in data:
            return jsonify({'error': 'Corrected text required'}), 400
        
        session_id = request.view_args['session_id']
        corrected_text = data['corrected_text']
        notes = data.get('notes', '')
        
        # Update correction
        success, message = reporting_module.update_dictation_correction(
            session_id, corrected_text, user_id, notes
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"❌ Error updating dictation correction: {e}")
        return jsonify({'error': f'Failed to update correction: {str(e)}'}), 500

# ============================================================================
# REPORT TEMPLATES ENDPOINTS
# ============================================================================

@reporting_api_bp.route('/templates', methods=['GET'])
@require_auth
def get_report_templates():
    """Get report templates"""
    try:
        modality = request.args.get('modality')
        body_part = request.args.get('body_part')
        language = request.args.get('language', 'en')
        
        # TODO: Implement template retrieval from database
        # For now, return sample templates
        sample_templates = [
            {
                'template_id': 'chest_xray_en',
                'name': 'Chest X-Ray Report',
                'modality': 'XR',
                'body_part': 'CHEST',
                'language': 'en',
                'template_content': '''CHEST X-RAY REPORT

CLINICAL HISTORY: {clinical_history}

FINDINGS:
The heart size is {heart_size}. The mediastinal contours are {mediastinal_contours}.
The lungs are {lung_findings}. No pleural effusion or pneumothorax is seen.
The bony thorax is {bone_findings}.

IMPRESSION:
{impression}

Reported by: {radiologist_name}
Date: {report_date}''',
                'placeholders': ['clinical_history', 'heart_size', 'mediastinal_contours', 
                               'lung_findings', 'bone_findings', 'impression', 
                               'radiologist_name', 'report_date']
            },
            {
                'template_id': 'chest_xray_af',
                'name': 'Bors X-straal Verslag',
                'modality': 'XR',
                'body_part': 'CHEST',
                'language': 'af',
                'template_content': '''BORS X-STRAAL VERSLAG

KLINIESE GESKIEDENIS: {clinical_history}

BEVINDINGE:
Die hartgrootte is {heart_size}. Die mediastinale kontoere is {mediastinal_contours}.
Die longe is {lung_findings}. Geen pleurale effusie of pneumotoraks word gesien nie.
Die beenrige toraks is {bone_findings}.

INDRUK:
{impression}

Gerapporteer deur: {radiologist_name}
Datum: {report_date}''',
                'placeholders': ['clinical_history', 'heart_size', 'mediastinal_contours', 
                               'lung_findings', 'bone_findings', 'impression', 
                               'radiologist_name', 'report_date']
            }
        ]
        
        # Filter templates based on query parameters
        filtered_templates = sample_templates
        if modality:
            filtered_templates = [t for t in filtered_templates if t['modality'] == modality]
        if body_part:
            filtered_templates = [t for t in filtered_templates if t['body_part'] == body_part]
        if language:
            filtered_templates = [t for t in filtered_templates if t['language'] == language]
        
        return jsonify({
            'success': True,
            'templates': filtered_templates,
            'count': len(filtered_templates)
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting report templates: {e}")
        return jsonify({'error': f'Failed to get templates: {str(e)}'}), 500

# ============================================================================
# IMAGE LAYOUT ENDPOINTS
# ============================================================================

@reporting_api_bp.route('/layouts', methods=['GET'])
@require_auth
def get_image_layouts():
    """Get user's image layouts"""
    try:
        user_id = session.get('user_id')
        
        # TODO: Implement layout retrieval from database
        # For now, return sample layouts
        sample_layouts = [
            {
                'layout_id': 'single_view',
                'name': 'Single Image View',
                'user_id': user_id,
                'layout_type': 'single',
                'grid_rows': 1,
                'grid_cols': 1,
                'is_default': True
            },
            {
                'layout_id': 'comparison_2x1',
                'name': 'Side-by-Side Comparison',
                'user_id': user_id,
                'layout_type': 'comparison',
                'grid_rows': 1,
                'grid_cols': 2,
                'is_default': False
            },
            {
                'layout_id': 'grid_2x2',
                'name': '2x2 Grid View',
                'user_id': user_id,
                'layout_type': 'grid',
                'grid_rows': 2,
                'grid_cols': 2,
                'is_default': False
            }
        ]
        
        return jsonify({
            'success': True,
            'layouts': sample_layouts,
            'count': len(sample_layouts)
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting image layouts: {e}")
        return jsonify({'error': f'Failed to get layouts: {str(e)}'}), 500

@reporting_api_bp.route('/layouts', methods=['POST'])
@require_auth
def create_image_layout():
    """Create new image layout"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({'error': 'Layout name required'}), 400
        
        # TODO: Implement layout creation in database
        layout_id = f"layout_{user_id}_{int(time.time())}"
        
        layout = {
            'layout_id': layout_id,
            'name': data['name'],
            'user_id': user_id,
            'layout_type': data.get('layout_type', 'grid'),
            'grid_rows': data.get('grid_rows', 1),
            'grid_cols': data.get('grid_cols', 1),
            'image_positions': data.get('image_positions', []),
            'window_settings': data.get('window_settings', {}),
            'zoom_settings': data.get('zoom_settings', {}),
            'is_default': data.get('is_default', False),
            'created_date': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'layout': layout,
            'message': 'Layout created successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"❌ Error creating image layout: {e}")
        return jsonify({'error': f'Failed to create layout: {str(e)}'}), 500

# ============================================================================
# STATISTICS AND REPORTING ENDPOINTS
# ============================================================================

@reporting_api_bp.route('/statistics', methods=['GET'])
@require_auth
def get_reporting_statistics():
    """Get reporting statistics"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role')
        
        # Admin can see all stats, users see only their own
        stats_user_id = None if user_role == 'admin' else user_id
        
        stats = reporting_module.get_reporting_statistics(stats_user_id)
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting reporting statistics: {e}")
        return jsonify({'error': f'Failed to get statistics: {str(e)}'}), 500

@reporting_api_bp.route('/health', methods=['GET'])
@require_auth
def get_reporting_health():
    """Get reporting system health status"""
    try:
        health_status = {
            'stt_engine': 'available' if reporting_module.stt_engine.model else 'unavailable',
            'audio_processing': 'available' if reporting_module.stt_engine else 'unavailable',
            'database': 'connected',
            'background_processing': 'running',
            'supported_languages': ['en-ZA', 'af-ZA', 'zu-ZA'],
            'audio_formats': ['wav', 'mp3', 'ogg'],
            'max_audio_duration': 1800  # 30 minutes
        }
        
        return jsonify({
            'success': True,
            'health': health_status
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting reporting health: {e}")
        return jsonify({'error': f'Failed to get health status: {str(e)}'}), 500

# ============================================================================
# SOUTH AFRICAN SPECIFIC ENDPOINTS
# ============================================================================

@reporting_api_bp.route('/sa/medical-terms', methods=['GET'])
@require_auth
def get_sa_medical_terms():
    """Get South African medical terminology"""
    try:
        language = request.args.get('language', 'en')
        category = request.args.get('category')  # common_terms, anatomy, findings
        
        terms = reporting_module.sa_medical_terms.get(language, reporting_module.sa_medical_terms['en'])
        
        if category and category in terms:
            result = {category: terms[category]}
        else:
            result = terms
        
        return jsonify({
            'success': True,
            'language': language,
            'medical_terms': result
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting SA medical terms: {e}")
        return jsonify({'error': f'Failed to get medical terms: {str(e)}'}), 500

@reporting_api_bp.route('/sa/languages', methods=['GET'])
@require_auth
def get_supported_languages():
    """Get supported languages for SA reporting"""
    try:
        languages = [
            {
                'code': 'en-ZA',
                'name': 'English (South Africa)',
                'native_name': 'English',
                'flag': '🇿🇦'
            },
            {
                'code': 'af-ZA',
                'name': 'Afrikaans (South Africa)',
                'native_name': 'Afrikaans',
                'flag': '🇿🇦'
            },
            {
                'code': 'zu-ZA',
                'name': 'isiZulu (South Africa)',
                'native_name': 'isiZulu',
                'flag': '🇿🇦'
            }
        ]
        
        return jsonify({
            'success': True,
            'languages': languages
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting supported languages: {e}")
        return jsonify({'error': f'Failed to get languages: {str(e)}'}), 500