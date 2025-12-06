#!/usr/bin/env python3
"""
DICOM API for Medical Reporting Module
Handles DICOM file processing and integration with Orthanc
"""

from flask import Blueprint, request, jsonify, Response, current_app, stream_with_context
import logging
import requests
import json
from datetime import datetime

logger = logging.getLogger(__name__)

dicom_api = Blueprint('dicom', __name__)


dicom_api = Blueprint('dicom', __name__)


def _get_orthanc_config():
    """Get Orthanc configuration from app config"""
    orthanc_url = current_app.config.get('ORTHANC_URL', 'http://localhost:8042')
    orthanc_auth = current_app.config.get('ORTHANC_AUTH')
    return orthanc_url, orthanc_auth


def _validate_session():
    """Validate user session for DICOM access"""
    # TODO: implement proper session validation
    # For now, return True (development mode)
    return True


@dicom_api.route('/qido', methods=['GET'])
def qido_proxy():
    """Proxy QIDO-RS queries to Orthanc for study/series search"""
    try:
        if not _validate_session():
            return jsonify({'error': 'Unauthorized'}), 401
        
        orthanc_url, orthanc_auth = _get_orthanc_config()
        
        # Get query parameters
        q = request.args.get('q', '')
        limit = int(request.args.get('limit', 50))
        date_from = request.args.get('from')
        date_to = request.args.get('to')
        
        # Try Orthanc tools/find endpoint first (if available)
        try:
            # Build query for Orthanc tools/find
            query_params = {}
            if q:
                # Search in patient name or ID
                query_params['PatientName'] = f'*{q}*'
            if date_from:
                query_params['StudyDate'] = f'{date_from}-{date_to or date_from}'
            
            orthanc_endpoint = f"{orthanc_url}/tools/find"
            auth = tuple(orthanc_auth.split(':')) if orthanc_auth else None
            
            response = requests.post(
                orthanc_endpoint,
                json={
                    'Level': 'Study',
                    'Query': query_params,
                    'Expand': True
                },
                auth=auth,
                timeout=10
            )
            
            if response.status_code == 200:
                orthanc_studies = response.json()
                
                # Transform to our format
                studies = []
                for study in orthanc_studies[:limit]:
                    main_tags = study.get('MainDicomTags', {})
                    patient_tags = study.get('PatientMainDicomTags', {})
                    
                    studies.append({
                        'studyInstanceUid': study.get('ID'),
                        'patientName': patient_tags.get('PatientName', 'Unknown'),
                        'patientId': patient_tags.get('PatientID', ''),
                        'studyDate': main_tags.get('StudyDate', ''),
                        'modalitiesInStudy': main_tags.get('ModalitiesInStudy', ''),
                        'seriesCount': len(study.get('Series', [])),
                        'studyDescription': main_tags.get('StudyDescription', ''),
                        'accessionNumber': main_tags.get('AccessionNumber', '')
                    })
                
                return jsonify({'success': True, 'studies': studies})
        
        except Exception as e:
            logger.warning(f"Orthanc query failed: {e}")
        
        # Fallback to demo data if Orthanc is not available
        demo_studies = [
            {
                'studyInstanceUid': 'demo-study-001',
                'patientName': 'Botha, A',
                'patientId': 'SA12345678',
                'studyDate': '2025-09-06',
                'modalitiesInStudy': 'CR',
                'seriesCount': 2,
                'studyDescription': 'Chest X-Ray AP/LAT',
                'accessionNumber': 'ACC001'
            },
            {
                'studyInstanceUid': 'demo-study-002',
                'patientName': 'van der Merwe, M',
                'patientId': 'SA87654321',
                'studyDate': '2025-09-05',
                'modalitiesInStudy': 'CT',
                'seriesCount': 4,
                'studyDescription': 'Abdomen CT with contrast',
                'accessionNumber': 'ACC002'
            }
        ]
        
        # Filter demo data if query provided
        if q:
            q_lower = q.lower()
            demo_studies = [s for s in demo_studies if 
                          q_lower in s['patientName'].lower() or 
                          q_lower in s['patientId'].lower()]
        
        return jsonify({'success': True, 'studies': demo_studies[:limit]})
        
    except Exception as e:
        logger.exception('QIDO proxy error')
        return jsonify({'success': False, 'error': 'Search failed'}), 500


@dicom_api.route('/metadata/<study_id>', methods=['GET'])
def study_metadata(study_id):
    """Get detailed study metadata including series and instances"""
    try:
        if not _validate_session():
            return jsonify({'error': 'Unauthorized'}), 401
        
        orthanc_url, orthanc_auth = _get_orthanc_config()
        
        # Try to get from Orthanc
        try:
            auth = tuple(orthanc_auth.split(':')) if orthanc_auth else None
            response = requests.get(f"{orthanc_url}/studies/{study_id}", auth=auth, timeout=10)
            
            if response.status_code == 200:
                study_data = response.json()
                
                # Get series details
                series_list = []
                for series_id in study_data.get('Series', []):
                    series_resp = requests.get(f"{orthanc_url}/series/{series_id}", auth=auth, timeout=5)
                    if series_resp.status_code == 200:
                        series_data = series_resp.json()
                        series_tags = series_data.get('MainDicomTags', {})
                        
                        instances = []
                        for instance_id in series_data.get('Instances', []):
                            instances.append({
                                'sopInstanceUid': instance_id,
                                'wadoUrl': f'/api/dicom/wado/{study_id}/{series_id}/{instance_id}',
                                'thumbnailUrl': f'/api/dicom/thumbnail/{study_id}/{series_id}/{instance_id}'
                            })
                        
                        series_list.append({
                            'seriesInstanceUid': series_id,
                            'seriesNumber': series_tags.get('SeriesNumber', ''),
                            'modality': series_tags.get('Modality', ''),
                            'seriesDescription': series_tags.get('SeriesDescription', ''),
                            'instanceCount': len(instances),
                            'instances': instances
                        })
                
                study_tags = study_data.get('MainDicomTags', {})
                patient_tags = study_data.get('PatientMainDicomTags', {})
                
                return jsonify({
                    'success': True,
                    'study': {
                        'studyInstanceUid': study_id,
                        'patientName': patient_tags.get('PatientName', 'Unknown'),
                        'patientId': patient_tags.get('PatientID', ''),
                        'studyDate': study_tags.get('StudyDate', ''),
                        'studyDescription': study_tags.get('StudyDescription', ''),
                        'modalitiesInStudy': study_tags.get('ModalitiesInStudy', '')
                    },
                    'series': series_list
                })
        
        except Exception as e:
            logger.warning(f"Orthanc metadata query failed: {e}")
        
        # Demo fallback data
        if study_id == 'demo-study-001':
            return jsonify({
                'success': True,
                'study': {
                    'studyInstanceUid': study_id,
                    'patientName': 'Botha, A',
                    'patientId': 'SA12345678',
                    'studyDate': '2025-09-06',
                    'studyDescription': 'Chest X-Ray AP/LAT'
                },
                'series': [
                    {
                        'seriesInstanceUid': 'demo-series-001-1',
                        'seriesNumber': '1',
                        'modality': 'CR',
                        'seriesDescription': 'Chest AP',
                        'instanceCount': 1,
                        'instances': [{'sopInstanceUid': 'demo-instance-001-1-1', 'wadoUrl': '/api/dicom/wado/demo-study-001/demo-series-001-1/demo-instance-001-1-1', 'thumbnailUrl': '/api/dicom/thumbnail/demo-study-001/demo-series-001-1/demo-instance-001-1-1'}]
                    },
                    {
                        'seriesInstanceUid': 'demo-series-001-2',
                        'seriesNumber': '2',
                        'modality': 'CR',
                        'seriesDescription': 'Chest LAT',
                        'instanceCount': 1,
                        'instances': [{'sopInstanceUid': 'demo-instance-001-2-1', 'wadoUrl': '/api/dicom/wado/demo-study-001/demo-series-001-2/demo-instance-001-2-1', 'thumbnailUrl': '/api/dicom/thumbnail/demo-study-001/demo-series-001-2/demo-instance-001-2-1'}]
                    }
                ]
            })
        
        return jsonify({'success': False, 'error': 'Study not found'}), 404
        
    except Exception as e:
        logger.exception('Metadata query error')
        return jsonify({'success': False, 'error': 'Metadata query failed'}), 500


@dicom_api.route('/wado/<study_id>/<series_id>/<instance_id>', methods=['GET'])
def wado_proxy(study_id, series_id, instance_id):
    """Proxy WADO-RS requests to Orthanc for DICOM image retrieval"""
    try:
        if not _validate_session():
            return jsonify({'error': 'Unauthorized'}), 401
        
        orthanc_url, orthanc_auth = _get_orthanc_config()
        
        # Try Orthanc WADO or preview endpoint
        try:
            auth = tuple(orthanc_auth.split(':')) if orthanc_auth else None
            
            # Use Orthanc preview endpoint for JPEG images
            preview_url = f"{orthanc_url}/instances/{instance_id}/preview"
            response = requests.get(preview_url, auth=auth, timeout=30, stream=True)
            
            if response.status_code == 200:
                def generate():
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            yield chunk
                
                return Response(
                    stream_with_context(generate()),
                    content_type='image/jpeg',
                    headers={'Content-Disposition': f'inline; filename="{instance_id}.jpg"'}
                )
        
        except Exception as e:
            logger.warning(f"Orthanc WADO query failed: {e}")
        
        # Demo fallback: return a placeholder image
        from flask import send_file
        import io
        import base64
        
        # 1x1 transparent PNG as placeholder
        placeholder_png = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4//8/AwAI/AL+9qg8WQAAAABJRU5ErkJggg=='
        )
        
        return Response(
            placeholder_png,
            content_type='image/png',
            headers={'Content-Disposition': f'inline; filename="{instance_id}.png"'}
        )
        
    except Exception as e:
        logger.exception('WADO proxy error')
        return jsonify({'error': 'Image retrieval failed'}), 500


@dicom_api.route('/thumbnail/<study_id>/<series_id>/<instance_id>', methods=['GET'])
def thumbnail_proxy(study_id, series_id, instance_id):
    """Get thumbnail for DICOM instance"""
    try:
        if not _validate_session():
            return jsonify({'error': 'Unauthorized'}), 401
        
        # For now, use the same WADO endpoint but could be optimized with smaller size
        return wado_proxy(study_id, series_id, instance_id)
        
    except Exception as e:
        logger.exception('Thumbnail proxy error')
        return jsonify({'error': 'Thumbnail retrieval failed'}), 500


@dicom_api.route('/studies', methods=['GET'])
def list_studies():
    """List DICOM studies"""
    try:
        patient_id = request.args.get('patient_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Mock DICOM studies - in real implementation, query DICOM server
        studies = [
            {
                'study_uid': '1.2.3.4.5.6.7.8.9.1',
                'patient_id': 'PAT001',
                'patient_name': 'Test Patient',
                'study_date': '2024-09-03',
                'study_time': '10:30:00',
                'modality': 'CT',
                'study_description': 'Chest CT',
                'series_count': 3,
                'images_count': 150
            },
            {
                'study_uid': '1.2.3.4.5.6.7.8.9.2',
                'patient_id': 'PAT002',
                'patient_name': 'Another Patient',
                'study_date': '2024-09-03',
                'study_time': '14:15:00',
                'modality': 'MR',
                'study_description': 'Brain MRI',
                'series_count': 5,
                'images_count': 200
            }
        ]
        
        # Filter by patient_id if provided
        if patient_id:
            studies = [s for s in studies if s['patient_id'] == patient_id]
        
        return jsonify({
            'studies': studies,
            'total': len(studies)
        })
        
    except Exception as e:
        logger.error(f"Error listing DICOM studies: {e}")
        return jsonify({'error': 'Failed to list studies'}), 500


@dicom_api.route('/studies/<study_uid>', methods=['GET'])
def get_study(study_uid):
    """Get specific DICOM study details"""
    try:
        # Mock study details
        study = {
            'study_uid': study_uid,
            'patient_id': 'PAT001',
            'patient_name': 'Test Patient',
            'patient_birth_date': '1980-01-01',
            'patient_sex': 'M',
            'study_date': '2024-09-03',
            'study_time': '10:30:00',
            'modality': 'CT',
            'study_description': 'Chest CT',
            'referring_physician': 'Dr. Smith',
            'institution': 'Test Hospital',
            'series': [
                {
                    'series_uid': '1.2.3.4.5.6.7.8.9.1.1',
                    'series_number': 1,
                    'modality': 'CT',
                    'series_description': 'Axial',
                    'images_count': 50
                },
                {
                    'series_uid': '1.2.3.4.5.6.7.8.9.1.2',
                    'series_number': 2,
                    'modality': 'CT',
                    'series_description': 'Coronal',
                    'images_count': 50
                }
            ]
        }
        
        return jsonify(study)
        
    except Exception as e:
        logger.error(f"Error getting DICOM study {study_uid}: {e}")
        return jsonify({'error': 'Study not found'}), 404


@dicom_api.route('/studies/<study_uid>/series/<series_uid>/images', methods=['GET'])
def list_images(study_uid, series_uid):
    """List images in a DICOM series"""
    try:
        # Mock image list
        images = []
        for i in range(1, 51):  # 50 images
            images.append({
                'image_uid': f'{series_uid}.{i}',
                'instance_number': i,
                'image_position': [0, 0, i * 5],  # Mock position
                'slice_thickness': 5.0,
                'pixel_spacing': [0.5, 0.5]
            })
        
        return jsonify({
            'study_uid': study_uid,
            'series_uid': series_uid,
            'images': images,
            'total': len(images)
        })
        
    except Exception as e:
        logger.error(f"Error listing images for series {series_uid}: {e}")
        return jsonify({'error': 'Failed to list images'}), 500


@dicom_api.route('/viewer/<study_uid>', methods=['GET'])
def get_viewer_url(study_uid):
    """Get DICOM viewer URL for a study"""
    try:
        # Mock viewer URL - in real implementation, integrate with OHIF or similar
        viewer_url = f"http://localhost:3000/viewer/{study_uid}"
        
        return jsonify({
            'study_uid': study_uid,
            'viewer_url': viewer_url,
            'viewer_type': 'OHIF'
        })
        
    except Exception as e:
        logger.error(f"Error getting viewer URL for study {study_uid}: {e}")
        return jsonify({'error': 'Failed to get viewer URL'}), 500


@dicom_api.route('/upload', methods=['POST'])
def upload_dicom():
    """Upload DICOM files"""
    try:
        if 'dicom_file' not in request.files:
            return jsonify({'error': 'No DICOM file provided'}), 400
        
        dicom_file = request.files['dicom_file']
        
        if dicom_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Mock upload processing
        result = {
            'filename': dicom_file.filename,
            'size': len(dicom_file.read()),
            'status': 'uploaded',
            'study_uid': '1.2.3.4.5.6.7.8.9.999',
            'message': 'DICOM file uploaded successfully'
        }
        
        return jsonify(result), 201
        
    except Exception as e:
        logger.error(f"Error uploading DICOM file: {e}")
        return jsonify({'error': 'Failed to upload DICOM file'}), 500


@dicom_api.route('/search', methods=['POST'])
def search_studies():
    """Search DICOM studies with filters"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Search criteria required'}), 400
        
        # Mock search results
        results = [
            {
                'study_uid': '1.2.3.4.5.6.7.8.9.1',
                'patient_id': data.get('patient_id', 'PAT001'),
                'patient_name': 'Test Patient',
                'study_date': '2024-09-03',
                'modality': data.get('modality', 'CT'),
                'study_description': 'Chest CT',
                'match_score': 0.95
            }
        ]
        
        return jsonify({
            'results': results,
            'total': len(results),
            'search_criteria': data
        })
        
    except Exception as e:
        logger.error(f"Error searching DICOM studies: {e}")
        return jsonify({'error': 'Failed to search studies'}), 500


@dicom_api.route('/config', methods=['GET'])
def get_dicom_config():
    """Get DICOM service configuration"""
    config = {
        'server_host': 'localhost',
        'server_port': 11112,
        'ae_title': 'MEDICAL_REPORTING',
        'max_associations': 10,
        'supported_transfer_syntaxes': [
            'Implicit VR Little Endian',
            'Explicit VR Little Endian',
            'Explicit VR Big Endian'
        ],
        'supported_sop_classes': [
            'CT Image Storage',
            'MR Image Storage',
            'Digital X-Ray Image Storage'
        ]
    }
    
    return jsonify({'config': config})


@dicom_api.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'DICOM resource not found'}), 404


@dicom_api.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'DICOM service error'}), 500