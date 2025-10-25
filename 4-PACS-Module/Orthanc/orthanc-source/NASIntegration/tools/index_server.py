from flask import Flask, jsonify, request, send_from_directory
import json
import os
import subprocess
import threading
import time
from datetime import datetime
import logging

app = Flask(__name__)
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_FILE = os.path.join(TOOLS_DIR, "index_status.json")
INDEX_FILE = os.path.join(TOOLS_DIR, "index.json")
ENUMERATION_FILE = os.path.join(TOOLS_DIR, "nas_dicom_files.txt")

# Configure logging for South African healthcare context
logging.basicConfig(
    filename=os.path.join(TOOLS_DIR, 'sa_pacs.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# South African healthcare configuration
SA_CONFIG = {
    'timezone': 'Africa/Johannesburg',
    'medical_aids': [
        'Discovery Health', 'Momentum Health', 'Bonitas', 'Medihelp',
        'Fedhealth', 'Bestmed', 'Liberty Health', 'KeyHealth'
    ],
    'hospitals': [
        'Netcare', 'Life Healthcare', 'Mediclinic', 'Chris Hani Baragwanath',
        'Groote Schuur', 'Charlotte Maxeke', 'Steve Biko', 'Dr George Mukhari'
    ],
    'supported_formats': {
        'dicom': ['.dcm', '.dicom', '.ima', ''],
        'jpeg2000': ['.jp2', '.j2k', '.jpf', '.jpx', '.jpm'],
        'mixed': ['.dcm', '.dicom', '.ima', '.jp2', '.j2k', '']
    }
}

def update_status(status, message, details=None, nas_type='dicom'):
    """Helper to write to the status file with South African context."""
    status_data = {
        "status": status,
        "message": message,
        "details": details,
        "nas_type": nas_type,
        "timestamp": datetime.now().isoformat(),
        "sa_context": {
            "timezone": SA_CONFIG['timezone'],
            "supported_formats": SA_CONFIG['supported_formats'][nas_type]
        }
    }

    with open(STATUS_FILE, "w") as f:
        json.dump(status_data, f, indent=2)

    # Log to South African healthcare log
    logging.info(f"Status Update - {status}: {message}")

def get_nas_type_from_request():
    """Get NAS type from request or default to DICOM."""
    return request.args.get('nas_type', 'dicom')

def run_indexing_process(nas_type='dicom'):
    """The background thread function to run enumeration and indexing."""
    try:
        logging.info(f"Starting indexing process for NAS type: {nas_type}")

        # Step 1: Fast File Enumeration based on NAS type
        update_status("enumerating", f"Starting enumeration for {nas_type.upper()} format...", nas_type=nas_type)

        if nas_type == 'dicom':
            # Pure DICOM files on network share
            enum_script = os.path.join(TOOLS_DIR, "enum_nas_getchild.ps1")
            subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", enum_script],
                check=True, capture_output=True, text=True
            )
        elif nas_type == 'jpeg2000':
            # JPEG2000 files in Firebird database
            logging.info("JPEG2000/Firebird database indexing not yet implemented")
            update_status("error", "JPEG2000/Firebird support coming soon", nas_type=nas_type)
            return
        elif nas_type == 'mixed':
            # Mixed formats
            logging.info("Mixed format indexing - using DICOM enumerator")
            enum_script = os.path.join(TOOLS_DIR, "enum_nas_getchild.ps1")
            subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", enum_script],
                check=True, capture_output=True, text=True
            )

        file_count = len(open(ENUMERATION_FILE).readlines()) if os.path.exists(ENUMERATION_FILE) else 0
        update_status("indexing", f"Enumeration complete. Found {file_count} files. Starting indexer.", nas_type=nas_type)

        # Step 2: Concurrent Indexing with South African context
        index_script = os.path.join(TOOLS_DIR, "build_index.py")
        result = subprocess.run(
            ["python", index_script, "--list", ENUMERATION_FILE, "--out", INDEX_FILE],
            check=True, capture_output=True, text=True
        )

        # Log successful indexing
        logging.info(f"Indexing completed successfully for {nas_type} format")

        update_status("complete", f"Indexing process finished successfully for {nas_type.upper()} format.", nas_type=nas_type)

    except subprocess.CalledProcessError as e:
        error_message = f"An error occurred during {nas_type} indexing: {e.stderr}"
        logging.error(error_message)
        update_status("error", error_message, nas_type=nas_type)
    except Exception as e:
        error_message = f"A critical error occurred: {str(e)}"
        logging.error(error_message)
        update_status("error", error_message, nas_type=nas_type)

@app.route('/')
def serve_ui():
    """Serves the main UI file with South African healthcare branding."""
    return send_from_directory(TOOLS_DIR, 'ui.html')

@app.route('/api/index/start', methods=['POST'])
def start_indexing():
    """Starts the background indexing process with NAS type support."""
    nas_type = request.json.get('nas_type', 'dicom') if request.is_json else 'dicom'

    current_status = get_status().get_json()
    if current_status.get('status') in ['enumerating', 'indexing']:
        return jsonify({"status": "error", "message": "Indexing is already in progress."}), 409

    # Validate NAS type
    if nas_type not in SA_CONFIG['supported_formats']:
        return jsonify({"status": "error", "message": f"Unsupported NAS type: {nas_type}"}), 400

    thread = threading.Thread(target=run_indexing_process, args=(nas_type,))
    thread.daemon = True
    thread.start()

    logging.info(f"Indexing started for NAS type: {nas_type}")
    return jsonify({
        "status": "ok",
        "message": f"Indexing process started for {nas_type.upper()} format.",
        "nas_type": nas_type
    })

@app.route('/api/index/status', methods=['GET'])
def get_status():
    """Returns the current status of the indexing process with SA context."""
    if not os.path.exists(STATUS_FILE):
        return jsonify({
            "status": "idle",
            "message": "System ready for South African healthcare operations.",
            "sa_context": SA_CONFIG
        })

    with open(STATUS_FILE, "r") as f:
        status_data = json.load(f)

    # Add South African context if not present
    if 'sa_context' not in status_data:
        status_data['sa_context'] = SA_CONFIG

    return jsonify(status_data)

@app.route('/api/search', methods=['GET'])
def search_index():
    """Searches the completed index with South African healthcare context."""
    query = request.args.get('q', '').lower().strip()
    nas_type = request.args.get('nas_type', 'dicom')

    if not query:
        return jsonify([])

    if not os.path.exists(INDEX_FILE):
        return jsonify({
            "status": "error",
            "message": "Index not found. Please run the indexing process.",
            "sa_suggestion": "Use the Start Full Indexing button to create the patient database."
        }), 404

    with open(INDEX_FILE, 'r') as f:
        index_data = json.load(f)

    # Enhanced search for South African healthcare context
    results = []
    for series in index_data:
        searchable_text = ' '.join([
            series.get('PatientName', ''),
            series.get('PatientID', ''),
            series.get('StudyDescription', ''),
            series.get('SeriesDescription', ''),
            series.get('InstitutionName', ''),
            series.get('ReferringPhysicianName', ''),
            series.get('Modality', '')
        ]).lower()

        # Check for South African medical aid schemes
        for medical_aid in SA_CONFIG['medical_aids']:
            if medical_aid.lower() in searchable_text:
                series['MedicalAid'] = medical_aid
                break

        # Check for South African hospitals
        for hospital in SA_CONFIG['hospitals']:
            if hospital.lower() in searchable_text:
                series['Hospital'] = hospital
                break

        if query in searchable_text:
            # Add South African context
            series['SA_Timezone'] = SA_CONFIG['timezone']
            series['NAS_Type'] = nas_type
            results.append(series)

    logging.info(f"Search completed: {len(results)} results for query '{query}' in {nas_type} format")
    return jsonify(results)

@app.route('/api/config', methods=['GET'])
def get_config():
    """Returns South African healthcare configuration."""
    return jsonify({
        "sa_config": SA_CONFIG,
        "supported_nas_types": list(SA_CONFIG['supported_formats'].keys()),
        "medical_aids": SA_CONFIG['medical_aids'],
        "hospitals": SA_CONFIG['hospitals']
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for South African PACS system."""
    return jsonify({
        "status": "healthy",
        "system": "SA PACS",
        "timezone": SA_CONFIG['timezone'],
        "supported_formats": list(SA_CONFIG['supported_formats'].keys()),
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    update_status("idle", "South African PACS system ready for healthcare operations")
    logging.info("SA PACS Flask server starting up")
    app.run(host='0.0.0.0', port=5001, debug=True)
