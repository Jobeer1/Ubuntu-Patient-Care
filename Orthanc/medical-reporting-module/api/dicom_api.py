#!/usr/bin/env python3
"""
DICOM API for Medical Reporting Module
RESTful API for DICOM operations and Orthanc integration
"""

import logging
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
import tempfile
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Create blueprint
dicom_api = Blueprint('dicom_api', __name__, url_prefix='/api/dicom')

@dicom_api.route('/validate', methods=['POST'])
def validate_dicom():
    """Validate uploaded DICOM file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        file.save(temp_path)
        
        try:
            from services.dicom_service import dicom_service
            is_valid, validation_result = dicom_service.validate_dicom_file(temp_path)
            
            return jsonify({
                'valid': is_valid,
                'validation_result': validation_result,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        logger.error(f"DICOM validation error: {e}")
        return jsonify({
            'error': 'Failed to validate DICOM file',
            'details': str(e)
        }), 500

@dicom_api.route('/upload', methods=['POST'])
def upload_dicom():
    """Upload DICOM file to Orthanc PACS"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        file.save(temp_path)
        
        try:
            from services.dicom_service import dicom_service
            
            # Validate first
            is_valid, validation_result = dicom_service.validate_dicom_file(temp_path)
            if not is_valid:
                return jsonify({
                    'error': 'Invalid DICOM file',
                    'validation_result': validation_result
                }), 400
            
            # Send to Orthanc
            success, result = dicom_service.send_to_orthanc(temp_path)
            
            if success:
                return jsonify({
                    'success': True,
                    'orthanc_id': result.get('orthanc_id'),
                    'message': 'DICOM file uploaded successfully',
                    'timestamp': datetime.utcnow().isoformat()
                })
            else:
                return jsonify({
                    'error': 'Failed to upload to Orthanc',
                    'details': result.get('error')
                }), 500
                
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        logger.error(f"DICOM upload error: {e}")
        return jsonify({
            'error': 'Failed to upload DICOM file',
            'details': str(e)
        }), 500

@dicom_api.route('/studies', methods=['GET'])
def search_studies():
    """Search for studies in Orthanc PACS"""
    try:
        # Get query parameters
        query_params = {
            'patient_id': request.args.get('patient_id', ''),
            'patient_name': request.args.get('patient_name', ''),
            'study_date': request.args.get('study_date', ''),
            'study_description': request.args.get('study_description', ''),
            'modality': request.args.get('modality', '')
        }
        
        # Remove empty parameters
        query_params = {k: v for k, v in query_params.items() if v}
        
        from services.dicom_service import dicom_service
        studies = dicom_service.query_orthanc_studies(query_params)
        
        return jsonify({
            'studies': studies,
            'count': len(studies),
            'query_params': query_params,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Study search error: {e}")
        return jsonify({
            'error': 'Failed to search studies',
            'details': str(e)
        }), 500

@dicom_api.route('/studies/<study_id>', methods=['GET'])
def get_study_details(study_id):
    """Get detailed information about a specific study"""
    try:
        from services.dicom_service import dicom_service
        study_details = dicom_service.get_study_details(study_id)
        
        if study_details:
            return jsonify({
                'study': study_details,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'error': 'Study not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Study details error: {e}")
        return jsonify({
            'error': 'Failed to get study details',
            'details': str(e)
        }), 500

@dicom_api.route('/instances/<instance_id>/preview', methods=['GET'])
def get_instance_preview(instance_id):
    """Get preview image for DICOM instance"""
    try:
        from services.dicom_service import dicom_service
        preview_data = dicom_service.get_instance_preview(instance_id)
        
        if preview_data:
            # Create temporary file for preview
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_file.write(preview_data)
            temp_file.close()
            
            return send_file(
                temp_file.name,
                mimetype='image/png',
                as_attachment=False,
                download_name=f'preview_{instance_id}.png'
            )
        else:
            return jsonify({
                'error': 'Preview not available'
            }), 404
            
    except Exception as e:
        logger.error(f"Instance preview error: {e}")
        return jsonify({
            'error': 'Failed to get instance preview',
            'details': str(e)
        }), 500

@dicom_api.route('/reports/create-sr', methods=['POST'])
def create_structured_report():
    """Create DICOM Structured Report from medical report"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['patient_id', 'content']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        from services.dicom_service import dicom_service
        sr_file_path = dicom_service.create_dicom_sr(data)
        
        if sr_file_path:
            # Optionally send to Orthanc
            if data.get('send_to_orthanc', False):
                success, result = dicom_service.send_to_orthanc(sr_file_path)
                
                return jsonify({
                    'success': True,
                    'sr_file_path': sr_file_path,
                    'orthanc_upload': success,
                    'orthanc_result': result if success else None,
                    'timestamp': datetime.utcnow().isoformat()
                })
            else:
                return jsonify({
                    'success': True,
                    'sr_file_path': sr_file_path,
                    'message': 'DICOM SR created successfully',
                    'timestamp': datetime.utcnow().isoformat()
                })
        else:
            return jsonify({
                'error': 'Failed to create DICOM SR'
            }), 500
            
    except Exception as e:
        logger.error(f"DICOM SR creation error: {e}")
        return jsonify({
            'error': 'Failed to create DICOM SR',
            'details': str(e)
        }), 500

@dicom_api.route('/orthanc/status', methods=['GET'])
def check_orthanc_status():
    """Check Orthanc PACS connection status"""
    try:
        from services.dicom_service import dicom_service
        connected, status_info = dicom_service.check_orthanc_connection()
        
        return jsonify({
            'connected': connected,
            'status': status_info,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Orthanc status check error: {e}")
        return jsonify({
            'error': 'Failed to check Orthanc status',
            'details': str(e)
        }), 500

@dicom_api.route('/orthanc/statistics', methods=['GET'])
def get_orthanc_statistics():
    """Get Orthanc PACS statistics"""
    try:
        import requests
        from services.dicom_service import dicom_service
        
        response = requests.get(f"{dicom_service.orthanc_url}/statistics", timeout=10)
        
        if response.status_code == 200:
            stats = response.json()
            return jsonify({
                'statistics': stats,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'error': 'Failed to get Orthanc statistics',
                'status_code': response.status_code
            }), 500
            
    except Exception as e:
        logger.error(f"Orthanc statistics error: {e}")
        return jsonify({
            'error': 'Failed to get Orthanc statistics',
            'details': str(e)
        }), 500

@dicom_api.route('/cleanup', methods=['POST'])
def cleanup_temp_files():
    """Clean up temporary DICOM files"""
    try:
        from services.dicom_service import dicom_service
        dicom_service.cleanup_temp_files()
        
        return jsonify({
            'success': True,
            'message': 'Temporary files cleaned up',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        return jsonify({
            'error': 'Failed to cleanup temporary files',
            'details': str(e)
        }), 500

# Error handlers
@dicom_api.errorhandler(413)
def file_too_large(error):
    return jsonify({
        'error': 'File too large',
        'message': 'The uploaded file exceeds the maximum allowed size'
    }), 413

@dicom_api.errorhandler(400)
def bad_request(error):
    return jsonify({
        'error': 'Bad request',
        'message': 'Invalid request format or parameters'
    }), 400

@dicom_api.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500