"""
Ubuntu Patient Care - Demo Flask Application
Run this to launch the interactive demo dashboard.

Usage:
    python app.py
    
Then open: http://localhost:5000
"""

from flask import Flask, render_template, jsonify, request
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__, 
            template_folder='demo/templates',
            static_folder='demo/static')

# Configuration
app.config['SECRET_KEY'] = 'ubuntu-patient-care-demo-2025'
app.config['DEBUG'] = True


@app.route('/')
def index():
    """
    Main demo dashboard page.
    """
    return render_template('index.html')


@app.route('/api/health')
def health():
    """
    Health check endpoint.
    """
    return jsonify({
        'status': 'healthy',
        'service': 'Ubuntu Patient Care Demo',
        'version': '1.0.0'
    })


@app.route('/api/simulate-upload', methods=['POST'])
def simulate_upload():
    """
    API endpoint to simulate clinic data upload.
    In production, this would trigger the actual drive_monitor.py
    """
    data = request.get_json() or {}
    
    return jsonify({
        'success': True,
        'message': 'Data upload simulated',
        'records': data.get('records', 50),
        'timestamp': '2025-11-17T10:30:00Z'
    })


@app.route('/api/start-training', methods=['POST'])
def start_training():
    """
    API endpoint to start training job.
    In production, this would trigger vertex_pipeline_definition.py
    """
    data = request.get_json() or {}
    
    return jsonify({
        'success': True,
        'job_id': f'vertex-ai-job-{os.urandom(4).hex()}',
        'message': 'Training job submitted',
        'accelerator': 'NVIDIA_TESLA_T4',
        'machine_type': 'n1-highmem-8'
    })


@app.route('/api/generate-audit', methods=['POST'])
def generate_audit():
    """
    API endpoint to generate audit artifact.
    In production, this would trigger opus_audit_artifact.py
    """
    data = request.get_json() or {}
    
    return jsonify({
        'success': True,
        'artifact_id': f'audit-{os.urandom(4).hex()}',
        'workflow_id': 'STT-OPTIMIZER-PIPELINE-V1',
        'validation_score': 0.963,
        'review_action': 'NO_HUMAN_REVIEW_NEEDED',
        'popia_compliant': True
    })


@app.errorhandler(404)
def not_found(error):
    """
    404 error handler.
    """
    return jsonify({
        'error': 'Not found',
        'message': 'The requested resource was not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """
    500 error handler.
    """
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500


def main():
    """
    Main entry point for the Flask application.
    """
    print("\n" + "="*70)
    print("  🏥 UBUNTU PATIENT CARE - DEMO DASHBOARD")
    print("="*70)
    print("  Starting Flask server...")
    print("  ")
    print("  📍 Local URL:  http://localhost:5000")
    print("  📍 Network URL: http://127.0.0.1:5000")
    print("  ")
    print("  Press Ctrl+C to stop the server")
    print("="*70 + "\n")
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=True
    )


if __name__ == '__main__':
    main()
