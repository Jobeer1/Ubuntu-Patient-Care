#!/usr/bin/env python3
"""
🇿🇦 SA Medical Reporting - Typist API Endpoints

REST API endpoints for the typist workflow system.
Provides queue management, report claiming, and correction workflow.
"""

from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin
import logging
from datetime import datetime
from typing import Dict, Any

try:
    from .typist_queue_manager import typist_queue_manager
    from .database_migrations import db_migrator
    from .auth_2fa import require_auth
except ImportError:
    # Fallback to absolute imports
    from typist_queue_manager import typist_queue_manager
    from database_migrations import db_migrator
    try:
        from auth_2fa import require_auth
    except ImportError:
        # Simple auth fallback
        def require_auth(f):
            def wrapper(*args, **kwargs):
                if not session.get('user_id'):
                    return jsonify({'error': 'Authentication required'}), 401
                return f(*args, **kwargs)
            return wrapper

logger = logging.getLogger(__name__)

# Create blueprint for typist endpoints
typist_api_bp = Blueprint('typist_api', __name__, url_prefix='/api/reporting/typist')

def require_typist_role():
    """Check if user has typist or admin role"""
    user_role = session.get('role', 'user')
    if user_role not in ['typist', 'admin']:
        return jsonify({'error': 'Typist role required'}), 403
    return None

# ============================================================================
# QUEUE MANAGEMENT ENDPOINTS
# ============================================================================

@typist_api_bp.route('/queue', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_typist_queue():
    """Get pending reports in the typist queue"""
    try:
        # Check role
        role_check = require_typist_role()
        if role_check:
            return role_check
        
        user_id = session.get('user_id')
        priority = request.args.get('priority')  # urgent, routine, low
        
        # Get pending reports
        queue_items = typist_queue_manager.get_pending_reports(
            typist_id=user_id, 
            priority=priority
        )
        
        return jsonify({
            'success': True,
            'queue_items': [item.to_dict() for item in queue_items],
            'count': len(queue_items),
            'filters': {
                'priority': priority
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting typist queue: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@typist_api_bp.route('/claim/<session_id>', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
def claim_report(session_id: str):
    """Claim a report for correction"""
    try:
        # Check role
        role_check = require_typist_role()
        if role_check:
            return role_check
        
        user_id = session.get('user_id')
        
        # Claim the report
        success, message = typist_queue_manager.claim_report(session_id, user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'session_id': session_id,
                'claimed_by': user_id,
                'claimed_at': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Error claiming report: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@typist_api_bp.route('/release/<session_id>', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
def release_report(session_id: str):
    """Release a claimed report back to the queue"""
    try:
        # Check role
        role_check = require_typist_role()
        if role_check:
            return role_check
        
        user_id = session.get('user_id')
        
        # Release the report
        success, message = typist_queue_manager.release_report(session_id, user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'session_id': session_id
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Error releasing report: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@typist_api_bp.route('/stats', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_queue_statistics():
    """Get queue statistics and metrics"""
    try:
        # Check role
        role_check = require_typist_role()
        if role_check:
            return role_check
        
        user_id = session.get('user_id')
        
        # Get queue statistics
        queue_stats = typist_queue_manager.get_queue_statistics()
        
        # Get personal statistics
        personal_stats = typist_queue_manager.get_typist_statistics(user_id)
        
        return jsonify({
            'success': True,
            'queue_statistics': queue_stats,
            'personal_statistics': personal_stats.to_dict()
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting queue statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# CORRECTION WORKFLOW ENDPOINTS
# ============================================================================

@typist_api_bp.route('/session/<session_id>/correction', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_session_for_correction(session_id: str):
    """Get session details for correction workflow"""
    try:
        # Check role
        role_check = require_typist_role()
        if role_check:
            return role_check
        
        user_id = session.get('user_id')
        
        # Get session from reporting module
        from reporting_module import reporting_module
        session_data = reporting_module.get_dictation_session(session_id)
        
        if not session_data:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Check if user has claimed this session
        if session_data.claimed_by and session_data.claimed_by != user_id:
            return jsonify({
                'success': False,
                'error': 'Session not claimed by this user'
            }), 403
        
        return jsonify({
            'success': True,
            'session': session_data.to_dict(),
            'audio_available': bool(session_data.audio_file_path),
            'transcript_available': bool(session_data.raw_transcript)
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting session for correction: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@typist_api_bp.route('/session/<session_id>/corrections', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
def save_corrections(session_id: str):
    """Save typist corrections for a session"""
    try:
        # Check role
        role_check = require_typist_role()
        if role_check:
            return role_check
        
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data or 'corrected_text' not in data:
            return jsonify({
                'success': False,
                'error': 'Corrected text required'
            }), 400
        
        corrected_text = data['corrected_text']
        notes = data.get('notes', '')
        
        # Save corrections using reporting module
        from reporting_module import reporting_module
        success, message = reporting_module.update_dictation_correction(
            session_id, corrected_text, user_id, notes
        )
        
        if success:
            # Update correction end time
            import sqlite3
            conn = sqlite3.connect(typist_queue_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE dictation_sessions 
                SET correction_end_time = ?, updated_date = ?
                WHERE session_id = ?
            ''', (datetime.now().isoformat(), datetime.now().isoformat(), session_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': message,
                'session_id': session_id
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Error saving corrections: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@typist_api_bp.route('/session/<session_id>/submit-qa', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
def submit_for_qa(session_id: str):
    """Submit corrected report for QA review"""
    try:
        # Check role
        role_check = require_typist_role()
        if role_check:
            return role_check
        
        user_id = session.get('user_id')
        data = request.get_json() or {}
        
        # Update session status for QA
        import sqlite3
        conn = sqlite3.connect(typist_queue_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE dictation_sessions 
            SET status = 'qa_pending', qa_status = 'pending', 
                correction_end_time = ?, updated_date = ?
            WHERE session_id = ? AND claimed_by = ?
        ''', (datetime.now().isoformat(), datetime.now().isoformat(), session_id, user_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Session not found or not claimed by user'
            }), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Report submitted for QA review',
            'session_id': session_id,
            'status': 'qa_pending'
        })
        
    except Exception as e:
        logger.error(f"❌ Error submitting for QA: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# AUDIO AND TRANSCRIPT ENDPOINTS
# ============================================================================

@typist_api_bp.route('/session/<session_id>/audio-segments', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_audio_segments(session_id: str):
    """Get audio segments with timestamps for synchronization"""
    try:
        # Check role
        role_check = require_typist_role()
        if role_check:
            return role_check
        
        # Get session data
        from reporting_module import reporting_module
        session_data = reporting_module.get_dictation_session(session_id)
        
        if not session_data or not session_data.audio_file_path:
            return jsonify({
                'success': False,
                'error': 'Audio not available for this session'
            }), 404
        
        # For now, return basic audio info
        # In a full implementation, this would process audio into segments
        return jsonify({
            'success': True,
            'audio_file': session_data.audio_file_path,
            'duration': session_data.audio_duration,
            'segments': [
                {
                    'start_time': 0,
                    'end_time': session_data.audio_duration,
                    'text': session_data.raw_transcript or ''
                }
            ]
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting audio segments: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# SYSTEM MANAGEMENT ENDPOINTS
# ============================================================================

@typist_api_bp.route('/system/migrate', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
def run_database_migrations():
    """Run database migrations (admin only)"""
    try:
        # Check admin role
        if session.get('role') != 'admin':
            return jsonify({
                'success': False,
                'error': 'Admin role required'
            }), 403
        
        # Run migrations
        success = db_migrator.run_all_migrations()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Database migrations completed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Migration failed - check logs for details'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Error running migrations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@typist_api_bp.route('/system/status', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_system_status():
    """Get typist workflow system status"""
    try:
        # Check migration status
        migration_status = db_migrator.check_migration_status()
        
        # Get queue statistics
        queue_stats = typist_queue_manager.get_queue_statistics()
        
        return jsonify({
            'success': True,
            'system_status': {
                'migrations_applied': migration_status,
                'queue_operational': bool(queue_stats),
                'last_check': datetime.now().isoformat()
            },
            'queue_summary': queue_stats
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting system status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500