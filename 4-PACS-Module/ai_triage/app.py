from flask import Flask, render_template, jsonify, request, redirect, url_for, send_from_directory
import os
import json
import uuid
import pydicom
from werkzeug.utils import secure_filename
from audit_service import AuditService

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB limit for large CTs

audit_service = AuditService()

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Mock Data for Demonstration (In production, this would come from a DB or Orthanc)
MOCK_STUDIES = [
    {
        "id": "study_1",
        "patient_name": "John Doe",
        "modality": "CT",
        "date": "2025-11-28",
        "status": "Critical",
        "critical_slices": [2, 5],
        "total_slices": 100,
        "preview_image": "https://placehold.co/150x150?text=CT+Scan"
    },
    {
        "id": "study_2",
        "patient_name": "Jane Smith",
        "modality": "MRI",
        "date": "2025-11-28",
        "status": "Normal",
        "critical_slices": [],
        "total_slices": 250,
        "preview_image": "https://placehold.co/150x150?text=MRI+Scan"
    },
    {
        "id": "study_3",
        "patient_name": "Bob Johnson",
        "modality": "X-Ray",
        "date": "2025-11-27",
        "status": "Low Priority",
        "critical_slices": [],
        "total_slices": 1,
        "preview_image": "https://placehold.co/150x150?text=X-Ray"
    }
]

def get_dicom_z_position(filepath):
    """Extracts the Z-position from a DICOM file for sorting."""
    try:
        ds = pydicom.dcmread(filepath, stop_before_pixels=True)
        # ImagePositionPatient is [x, y, z]
        if hasattr(ds, 'ImagePositionPatient'):
            return float(ds.ImagePositionPatient[2])
        # Fallback to InstanceNumber
        if hasattr(ds, 'InstanceNumber'):
            return float(ds.InstanceNumber)
        return 0
    except Exception:
        return 0

@app.route('/')
def index():
    """Dashboard Home"""
    stats = audit_service.get_stats()
    return render_template('index.html', stats=stats, studies=MOCK_STUDIES)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    
    files = request.files.getlist('file')
    
    if not files or files[0].filename == '':
        return redirect(request.url)

    study_id = str(uuid.uuid4())
    study_dir = os.path.join(app.config['UPLOAD_FOLDER'], study_id)
    os.makedirs(study_dir, exist_ok=True)
    
    saved_files = []
    for file in files:
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(study_dir, filename)
            file.save(file_path)
            saved_files.append(filename)

    # Add to mock studies so it appears in the list
    new_study = {
        "id": study_id,
        "patient_name": "Uploaded Patient (3D)",
        "modality": "CT", # Assume CT for now
        "date": "2025-11-28",
        "status": "Pending Analysis",
        "critical_slices": [],
        "total_slices": len(saved_files),
        "preview_image": "https://placehold.co/150x150?text=3D+Volume",
        "files": saved_files # This list might be unsorted here, but we sort on retrieval
    }
    MOCK_STUDIES.insert(0, new_study)
    
    return redirect(url_for('viewer', study_id=study_id))

@app.route('/api/studies/<study_id>/files')
def get_study_files(study_id):
    """Returns a sorted list of file URLs for the study."""
    study_dir = os.path.join(app.config['UPLOAD_FOLDER'], study_id)
    if not os.path.exists(study_dir):
        return jsonify([])
    
    files = os.listdir(study_dir)
    # Sort files by Z-position
    files_with_z = []
    for f in files:
        full_path = os.path.join(study_dir, f)
        z = get_dicom_z_position(full_path)
        files_with_z.append((f, z))
    
    # Sort by Z
    files_with_z.sort(key=lambda x: x[1])
    
    sorted_filenames = [f[0] for f in files_with_z]
    
    # Generate full URLs
    file_urls = [url_for('uploaded_file', study_id=study_id, filename=f) for f in sorted_filenames]
    
    return jsonify(file_urls)

@app.route('/api/stats')
def get_stats():
    """API endpoint for live stats updates"""
    return jsonify(audit_service.get_stats())

@app.route('/uploads/<study_id>/<filename>')
def uploaded_file(study_id, filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], study_id), filename)

@app.route('/viewer/<study_id>')
def viewer(study_id):
    """Doctor's Viewer for a specific study"""
    study = next((s for s in MOCK_STUDIES if s['id'] == study_id), None)
    if not study:
        return "Study not found", 404
    return render_template('viewer.html', study=study)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
