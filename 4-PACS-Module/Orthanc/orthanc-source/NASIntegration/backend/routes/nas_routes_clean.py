"""
Clean NAS Integration Routes - Refactored
Handles main API endpoints with service layer separation
"""

from flask import Blueprint, request, jsonify, render_template, redirect, send_file
import logging
from datetime import datetime
import os

# Import service modules
from services import (
    search_patient_comprehensive,
    generate_secure_share_link,
    verify_share_access,
    get_indexing_status,
    get_patient_name_from_study,
    get_patient_files,
    create_download_archive,
    serve_file_securely,
    convert_dicom_to_png
)

logger = logging.getLogger(__name__)

# Create blueprint
nas_bp = Blueprint('nas_routes_clean', __name__)

# ==================== PATIENT SEARCH ROUTES ====================

@nas_bp.route('/search/patient', methods=['POST'])
def search_patient_images():
    """Search for patient images across all sources"""
    try:
        data = request.get_json() or {}
        
        logger.info(f"🔍 Patient search request: {data}")
        
        # Use comprehensive search service
        results = search_patient_comprehensive(data)
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Patient search error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'patients': [],
            'total_found': 0
        }), 500

# ==================== MEDICAL SHARING ROUTES ====================

@nas_bp.route('/share/generate', methods=['POST'])
def generate_share_link():
    """Generate secure sharing link for patient images"""
    try:
        data = request.get_json() or {}
        
        # Use medical sharing service
        result = generate_secure_share_link(data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Share link generation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@nas_bp.route('/medical-share/<share_id>', methods=['GET', 'POST'])
def verify_share_access_route(share_id):
    """Secure medical image sharing portal"""
    try:
        if request.method == 'GET':
            # Return the sharing portal page
            return render_template('medical_share_portal.html', share_id=share_id)
        
        # POST request - verify access code
        data = request.get_json() or {}
        access_code = data.get('access_code', '').upper()
        
        # Use medical sharing service
        result = verify_share_access(share_id, access_code)
        
        if result['success'] and result['share_data'].get('orthanc_study_uid'):
            # Redirect to professional DICOM viewer
            study_uid = result['share_data']['orthanc_study_uid']
            return jsonify({
                'success': True,
                'redirect_url': f'/api/nas/dicom-viewer?studyUID={study_uid}&shareId={share_id}',
                'share_data': result['share_data']
            })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Share verification error: {e}")
        return jsonify({
            'success': False,
            'message': f'Verification error: {str(e)}'
        }), 500

@nas_bp.route('/dicom-viewer', methods=['GET'])
def dicom_viewer():
    """Professional DICOM viewer for medical images"""
    try:
        study_uid = request.args.get('studyUID')
        share_id = request.args.get('shareId', '')
        
        if not study_uid:
            return "Study UID required", 400
        
        logger.info(f"🏥 Opening DICOM viewer for Study UID: {study_uid}")
        
        # Get patient name from Orthanc
        patient_name = get_patient_name_from_study(study_uid)
        
        # Render the professional DICOM viewer
        return render_template('professional_dicom_viewer.html', 
                             study_uid=study_uid, 
                             share_id=share_id,
                             patient_name=patient_name,
                             orthanc_url='http://localhost:8042')
        
    except Exception as e:
        logger.error(f"DICOM viewer error: {e}")
        return f"Viewer error: {str(e)}", 500

# ==================== FILE OPERATIONS ROUTES ====================

@nas_bp.route('/medical-share/<share_id>/files', methods=['GET'])
def get_share_files(share_id):
    """Get list of files for a medical share"""
    try:
        # Verify share exists and get patient folder
        # This is a simplified version - in full implementation,
        # would verify share access and get patient folder path
        
        return jsonify({
            'success': True,
            'files': [],
            'message': 'File listing functionality'
        })
        
    except Exception as e:
        logger.error(f"Error getting share files: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@nas_bp.route('/medical-share/<share_id>/download', methods=['POST'])
def download_share_files(share_id):
    """Download files from a medical share"""
    try:
        data = request.get_json() or {}
        format_type = data.get('format', 'dicom')
        
        # This would use the file operations service
        # to create and serve the download archive
        
        return jsonify({
            'success': True,
            'message': f'Download in {format_type} format prepared'
        })
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@nas_bp.route('/medical-share/<share_id>/view/<path:file_path>', methods=['GET'])
def view_share_file(share_id, file_path):
    """View a specific file from a medical share"""
    try:
        # This would use the file operations service
        # to serve the file securely
        
        return "File viewing functionality", 200
        
    except Exception as e:
        logger.error(f"File view error: {e}")
        return f"View error: {str(e)}", 500

# ==================== STATUS ROUTES ====================

@nas_bp.route('/indexing/status', methods=['GET'])
def get_indexing_status_route():
    """Get current indexing status"""
    try:
        status = get_indexing_status()
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Status error: {e}")
        return jsonify({
            'total_patients': 0,
            'is_running': False,
            'progress': 0,
            'error': str(e)
        }), 500

@nas_bp.route('/orthanc/status', methods=['GET'])
def get_orthanc_status():
    """Get Orthanc connection status"""
    try:
        from services.dicom_integration import check_orthanc_connection
        
        is_connected = check_orthanc_connection()
        
        return jsonify({
            'connected': is_connected,
            'url': 'http://localhost:8042',
            'message': 'Connected' if is_connected else 'Not connected'
        })
        
    except Exception as e:
        logger.error(f"Orthanc status error: {e}")
        return jsonify({
            'connected': False,
            'error': str(e)
        }), 500

@nas_bp.route('/dashboard/status', methods=['GET'])
def get_dashboard_status():
    """Get overall dashboard status"""
    try:
        indexing_status = get_indexing_status()
        
        return jsonify({
            'indexing': indexing_status,
            'timestamp': datetime.now().isoformat(),
            'system_status': 'operational'
        })
        
    except Exception as e:
        logger.error(f"Dashboard status error: {e}")
        return jsonify({
            'error': str(e),
            'system_status': 'error'
        }), 500