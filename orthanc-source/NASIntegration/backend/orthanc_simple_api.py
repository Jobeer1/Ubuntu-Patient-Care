"""
Simple Orthanc Management API Endpoints
Practical, user-friendly API for South African healthcare facilities
"""

from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin
import logging
from datetime import datetime, timedelta
from orthanc_simple_manager import orthanc_manager

logger = logging.getLogger(__name__)

# Create blueprint
orthanc_api = Blueprint('orthanc_simple_api', __name__, url_prefix='/api/orthanc')

def require_admin():
    """Simple admin check"""
    if not session.get('user_id'):
        return jsonify({'error': 'Authentication required'}), 401
    if session.get('role') != 'admin':
        return jsonify({'error': 'Admin privileges required'}), 403
    return None

# ===== SERVER MANAGEMENT =====

@orthanc_api.route('/status', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_server_status():
    """Get Orthanc server status - simple and clear"""
    try:
        status = orthanc_manager.get_server_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@orthanc_api.route('/start', methods=['POST'])
@cross_origin(supports_credentials=True)
def start_server():
    """Start Orthanc server"""
    try:
        auth_error = require_admin()
        if auth_error:
            return auth_error
        
        result = orthanc_manager.start_orthanc()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@orthanc_api.route('/stop', methods=['POST'])
@cross_origin(supports_credentials=True)
def stop_server():
    """Stop Orthanc server"""
    try:
        auth_error = require_admin()
        if auth_error:
            return auth_error
        
        result = orthanc_manager.stop_orthanc()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error stopping server: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@orthanc_api.route('/restart', methods=['POST'])
@cross_origin(supports_credentials=True)
def restart_server():
    """Restart Orthanc server"""
    try:
        auth_error = require_admin()
        if auth_error:
            return auth_error
        
        result = orthanc_manager.restart_orthanc()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error restarting server: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@orthanc_api.route('/quick-stats', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_quick_stats():
    """Get quick dashboard stats"""
    try:
        stats = orthanc_manager.get_quick_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting quick stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Compatibility alias expected by some UIs
@orthanc_api.route('/statistics', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_statistics_compat():
    """Compatibility endpoint mapping /api/orthanc/statistics -> quick-stats"""
    return get_quick_stats()

# ===== CONFIGURATION =====

@orthanc_api.route('/config', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_config():
    """Get current Orthanc configuration"""
    try:
        auth_error = require_admin()
        if auth_error:
            return auth_error
        
        import json
        import os
        
        config_path = orthanc_manager.config_path
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = orthanc_manager.get_basic_config()
        
        return jsonify({
            'success': True,
            'config': config
        })
        
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@orthanc_api.route('/config', methods=['PUT'])
@cross_origin(supports_credentials=True)
def update_config():
    """Update Orthanc configuration"""
    try:
        auth_error = require_admin()
        if auth_error:
            return auth_error
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No configuration data provided'
            }), 400
        
        result = orthanc_manager.update_config(data)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== PATIENT SHARING =====

@orthanc_api.route('/patient-shares', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_patient_shares():
    """Get all patient shares"""
    try:
        auth_error = require_admin()
        if auth_error:
            return auth_error
        
        shares = orthanc_manager.get_patient_shares()
        return jsonify({
            'success': True,
            'shares': shares
        })
        
    except Exception as e:
        logger.error(f"Error getting patient shares: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@orthanc_api.route('/patient-shares', methods=['POST'])
@cross_origin(supports_credentials=True)
def create_patient_share():
    """Create new patient share"""
    try:
        auth_error = require_admin()
        if auth_error:
            return auth_error
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No patient data provided'
            }), 400
        
        # Add current user info
        data['created_by'] = session.get('username', 'admin')
        
        result = orthanc_manager.create_patient_share(data)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error creating patient share: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== REFERRING DOCTORS =====

@orthanc_api.route('/doctors', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_doctors():
    """Get all referring doctors"""
    try:
        auth_error = require_admin()
        if auth_error:
            return auth_error
        
        doctors = orthanc_manager.get_referring_doctors()
        return jsonify({
            'success': True,
            'doctors': doctors
        })
        
    except Exception as e:
        logger.error(f"Error getting doctors: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@orthanc_api.route('/doctors', methods=['POST'])
@cross_origin(supports_credentials=True)
def add_doctor():
    """Add new referring doctor"""
    try:
        auth_error = require_admin()
        if auth_error:
            return auth_error
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No doctor data provided'
            }), 400
        
        result = orthanc_manager.add_referring_doctor(data)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error adding doctor: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ===== PATIENTS LIST (compatibility) =====
@orthanc_api.route('/patients', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_patients_compat():
    """Compatibility endpoint to return patient list expected by some UIs."""
    try:
        # Try orthanc_manager.get_patients() if available
        if hasattr(orthanc_manager, 'get_patients'):
            patients = orthanc_manager.get_patients()
        elif hasattr(orthanc_manager, 'list_patients'):
            patients = orthanc_manager.list_patients()
        else:
            # Fallback: try to derive from quick stats or return empty list
            try:
                stats = orthanc_manager.get_quick_stats()
                patients = stats.get('patients', []) if isinstance(stats, dict) else []
            except Exception:
                patients = []

        return jsonify({
            'success': True,
            'patients': patients
        })
    except Exception as e:
        logger.error(f"Error getting patients compat: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ===== QUICK SETUP ENDPOINTS =====

@orthanc_api.route('/quick-setup', methods=['POST'])
@cross_origin(supports_credentials=True)
def quick_setup():
    """Quick setup for new installations"""
    try:
        auth_error = require_admin()
        if auth_error:
            return auth_error
        
        data = request.get_json() or {}
        
        # Create basic configuration
        config_updates = {
            'Name': data.get('hospital_name', 'SA Healthcare PACS'),
            'HttpPort': data.get('web_port', 8042),
            'DicomPort': data.get('dicom_port', 4242),
            'DicomAet': data.get('aet_title', 'ORTHANC'),
            'StorageDirectory': data.get('storage_path', './orthanc-storage'),
            'RemoteAccessAllowed': data.get('allow_remote', True)
        }
        
        # Update configuration
        config_result = orthanc_manager.update_config(config_updates)
        if not config_result['success']:
            return jsonify(config_result)
        
        # Try to start Orthanc
        start_result = orthanc_manager.start_orthanc()
        
        return jsonify({
            'success': True,
            'message': 'Quick setup completed successfully',
            'config_updated': True,
            'server_started': start_result['success'],
            'web_url': f"http://localhost:{config_updates['HttpPort']}",
            'dicom_port': config_updates['DicomPort']
        })
        
    except Exception as e:
        logger.error(f"Error in quick setup: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@orthanc_api.route('/health-check', methods=['GET'])
@cross_origin(supports_credentials=True)
def health_check():
    """Simple health check endpoint"""
    try:
        status = orthanc_manager.get_server_status()
        is_healthy = status['status'] == 'running'
        
        return jsonify({
            'success': True,
            'healthy': is_healthy,
            'status': status['status'],
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return jsonify({
            'success': False,
            'healthy': False,
            'error': str(e)
        }), 500