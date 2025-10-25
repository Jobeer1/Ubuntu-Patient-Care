"""
Updated Main Application File
Uses refactored service modules for better maintainability
"""

import os
import sys
from flask import Flask, jsonify, render_template
import logging

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import the clean routes
from routes.nas_routes_clean import nas_bp

def create_app():
    """Create Flask application with modular architecture"""
    app = Flask(__name__)
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Register the clean NAS routes blueprint
    app.register_blueprint(nas_bp, url_prefix='/api/nas')
    
    @app.route('/')
    def index():
        """Main dashboard"""
        return render_template('index.html')
    
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'architecture': 'modular_services',
            'services': [
                'database_operations',
                'patient_search', 
                'dicom_integration',
                'medical_sharing',
                'file_operations'
            ]
        })
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    logger.info("🏥 Medical application initialized with modular architecture")
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)