"""
Ubuntu Patient Care - PACS DICOM Viewer
Flask backend for multi-user LAN access

Usage:
    python app.py
    
Then open: http://localhost:8080 (or your-server-ip:8080 on LAN)
"""

from flask import Flask, render_template, jsonify, request, send_file, session
import os
import sys
import json
import requests
from datetime import datetime
from io import BytesIO
import base64

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

app.config['SECRET_KEY'] = 'ubuntu-pacs-viewer-2025'
app.config['DEBUG'] = True

# Orthanc PACS Configuration
ORTHANC_URL = os.environ.get('ORTHANC_URL', 'http://localhost:8042')
ORTHANC_USER = os.environ.get('ORTHANC_USER', 'orthanc')
ORTHANC_PASS = os.environ.get('ORTHANC_PASS', 'orthanc')


def orthanc_request(endpoint, method='GET', data=None):
    """Make authenticated request to Orthanc PACS"""
    url = f"{ORTHANC_URL}/{endpoint}"
    auth = (ORTHANC_USER, ORTHANC_PASS)
    
    try:
        if method == 'GET':
            response = requests.get(url, auth=auth, timeout=10)
        elif method == 'POST':
            response = requests.post(url, auth=auth, json=data, timeout=10)
        else:
            return None
        
        if response.status_code == 200:
            return response
        return None
    except Exception as e:
        print(f"Orthanc request error: {e}")
        return None


@app.route('/')
def index():
    """Main DICOM viewer page"""
    return render_template('viewer.html')


@app.route('/api/health')
def health():
    """Health check endpoint"""
    # Check Orthanc connectivity
    orthanc_status = 'connected'
    try:
        response = orthanc_request('system')
        if not response:
            orthanc_status = 'disconnected'
    except:
        orthanc_status = 'disconnected'
    
    return jsonify({
        'status': 'healthy',
        'service': 'Ubuntu Patient Care PACS Viewer',
        'version': '1.0.0',
        'orthanc': orthanc_status,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/studies')
def get_studies():
    """Get list of all studies from Orthanc"""
    response = orthanc_request('studies')
    if not response:
        return jsonify({'error': 'Failed to connect to PACS'}), 500
    
    study_ids = response.json()
    studies = []
    
    for study_id in study_ids[:50]:  # Limit to 50 most recent
        study_response = orthanc_request(f'studies/{study_id}')
        if study_response:
            study_data = study_response.json()
            studies.append({
                'id': study_id,
                'patient_name': study_data.get('PatientMainDicomTags', {}).get('PatientName', 'Unknown'),
                'patient_id': study_data.get('PatientMainDicomTags', {}).get('PatientID', ''),
                'study_date': study_data.get('MainDicomTags', {}).get('StudyDate', ''),
                'study_time': study_data.get('MainDicomTags', {}).get('StudyTime', ''),
                'study_description': study_data.get('MainDicomTags', {}).get('StudyDescription', ''),
                'modality': study_data.get('MainDicomTags', {}).get('ModalitiesInStudy', ''),
                'series_count': len(study_data.get('Series', []))
            })
    
    return jsonify({'studies': studies})


@app.route('/api/study/<study_id>')
def get_study(study_id):
    """Get detailed study information"""
    response = orthanc_request(f'studies/{study_id}')
    if not response:
        return jsonify({'error': 'Study not found'}), 404
    
    study_data = response.json()
    
    # Get series information
    series_list = []
    for series_id in study_data.get('Series', []):
        series_response = orthanc_request(f'series/{series_id}')
        if series_response:
            series_data = series_response.json()
            series_list.append({
                'id': series_id,
                'description': series_data.get('MainDicomTags', {}).get('SeriesDescription', ''),
                'modality': series_data.get('MainDicomTags', {}).get('Modality', ''),
                'instance_count': len(series_data.get('Instances', [])),
                'instances': series_data.get('Instances', [])
            })
    
    return jsonify({
        'id': study_id,
        'patient_name': study_data.get('PatientMainDicomTags', {}).get('PatientName', 'Unknown'),
        'patient_id': study_data.get('PatientMainDicomTags', {}).get('PatientID', ''),
        'patient_birth_date': study_data.get('PatientMainDicomTags', {}).get('PatientBirthDate', ''),
        'patient_sex': study_data.get('PatientMainDicomTags', {}).get('PatientSex', ''),
        'study_date': study_data.get('MainDicomTags', {}).get('StudyDate', ''),
        'study_time': study_data.get('MainDicomTags', {}).get('StudyTime', ''),
        'study_description': study_data.get('MainDicomTags', {}).get('StudyDescription', ''),
        'modality': study_data.get('MainDicomTags', {}).get('ModalitiesInStudy', ''),
        'series': series_list
    })


@app.route('/api/instance/<instance_id>/image')
def get_instance_image(instance_id):
    """Get DICOM instance as PNG image"""
    response = orthanc_request(f'instances/{instance_id}/preview')
    if not response:
        return jsonify({'error': 'Image not found'}), 404
    
    return send_file(
        BytesIO(response.content),
        mimetype='image/png',
        as_attachment=False
    )


@app.route('/api/instance/<instance_id>/metadata')
def get_instance_metadata(instance_id):
    """Get DICOM instance metadata"""
    response = orthanc_request(f'instances/{instance_id}/simplified-tags')
    if not response:
        return jsonify({'error': 'Instance not found'}), 404
    
    tags = response.json()
    
    return jsonify({
        'instance_id': instance_id,
        'patient_name': tags.get('PatientName', ''),
        'patient_id': tags.get('PatientID', ''),
        'study_date': tags.get('StudyDate', ''),
        'modality': tags.get('Modality', ''),
        'series_description': tags.get('SeriesDescription', ''),
        'instance_number': tags.get('InstanceNumber', ''),
        'slice_location': tags.get('SliceLocation', ''),
        'image_position': tags.get('ImagePositionPatient', ''),
        'image_orientation': tags.get('ImageOrientationPatient', ''),
        'rows': tags.get('Rows', ''),
        'columns': tags.get('Columns', ''),
        'pixel_spacing': tags.get('PixelSpacing', ''),
        'slice_thickness': tags.get('SliceThickness', ''),
        'window_center': tags.get('WindowCenter', ''),
        'window_width': tags.get('WindowWidth', '')
    })


@app.route('/api/series/<series_id>/instances')
def get_series_instances(series_id):
    """Get all instances in a series with sorting"""
    response = orthanc_request(f'series/{series_id}')
    if not response:
        return jsonify({'error': 'Series not found'}), 404
    
    series_data = response.json()
    instances = []
    
    for instance_id in series_data.get('Instances', []):
        metadata_response = orthanc_request(f'instances/{instance_id}/simplified-tags')
        if metadata_response:
            tags = metadata_response.json()
            instances.append({
                'id': instance_id,
                'instance_number': int(tags.get('InstanceNumber', 0)),
                'slice_location': float(tags.get('SliceLocation', 0)) if tags.get('SliceLocation') else None,
                'image_position': tags.get('ImagePositionPatient', ''),
                'acquisition_time': tags.get('AcquisitionTime', '')
            })
    
    # Sort instances intelligently
    instances = sort_instances(instances)
    
    return jsonify({'instances': instances})


def sort_instances(instances):
    """Intelligent DICOM instance sorting"""
    if not instances:
        return []
    
    # Try sorting by slice location first
    if any(inst.get('slice_location') is not None for inst in instances):
        instances.sort(key=lambda x: x.get('slice_location', 0))
    # Fallback to instance number
    elif any(inst.get('instance_number') for inst in instances):
        instances.sort(key=lambda x: x.get('instance_number', 0))
    # Last resort: acquisition time
    else:
        instances.sort(key=lambda x: x.get('acquisition_time', ''))
    
    return instances


@app.route('/api/audit/log', methods=['POST'])
def log_audit():
    """Log viewer actions for audit trail"""
    data = request.get_json() or {}
    
    # In production, this would write to Qubic blockchain
    # For now, just log to console
    print(f"[AUDIT] {data.get('action')} - {data.get('details')}")
    
    return jsonify({'success': True})


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


def main():
    """Main entry point"""
    host = os.environ.get('HOST', '0.0.0.0')  # Listen on all interfaces for LAN access
    port = int(os.environ.get('PORT', 8080))
    
    print("\n" + "="*70)
    print("  🏥 UBUNTU PATIENT CARE - PACS DICOM VIEWER")
    print("="*70)
    print("  Starting Flask server for multi-user LAN access...")
    print("  ")
    print(f"  📍 Local URL:    http://localhost:{port}")
    print(f"  📍 LAN URL:      http://YOUR-IP:{port}")
    print(f"  📍 Orthanc PACS: {ORTHANC_URL}")
    print("  ")
    print("  🔐 Multi-user: Enabled (Flask sessions)")
    print("  📱 Mobile: Responsive design")
    print("  🌐 LAN Access: Enabled (0.0.0.0)")
    print("  ")
    print("  Press Ctrl+C to stop the server")
    print("="*70 + "\n")
    
    app.run(
        host=host,
        port=port,
        debug=True,
        threaded=True  # Enable multi-threading for concurrent users
    )


if __name__ == '__main__':
    main()
