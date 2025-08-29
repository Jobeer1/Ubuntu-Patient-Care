#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - Refactored Main Application

Modular Flask application with organized blueprint structure.
All functionality split into logical modules for better maintainability.
"""

import os
import sys
import logging
import warnings
from flask import Flask, jsonify
from flask_cors import CORS

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Setup clean logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Configure the application
    from config import config
    app.config.from_object(config[config_name])
    
    # Setup CORS
    CORS(app, 
         origins=app.config['CORS_ORIGINS'],
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    
    # Initialize device manager
    from device_management import DeviceManager
    device_manager = DeviceManager()
    
    # Import and register blueprints
    from routes.auth_routes import auth_bp
    from routes.admin_routes import admin_bp
    from routes.device_routes import device_bp, init_device_routes
    from routes.nas_core import nas_core_bp  # Direct import from modular structure
    # Optional: simple Orthanc management API
    try:
        from orthanc_simple_api import orthanc_api
        app.register_blueprint(orthanc_api, url_prefix='/api/orthanc')
    except Exception:
        # Keep app running even if orthanc management API cannot be imported
        logger.info('orthanc_simple_api not available; continuing without it')
    from routes.web_routes import web_bp
    
    # Register blueprints with their URL prefixes
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(device_bp, url_prefix='/api/devices')
    app.register_blueprint(nas_core_bp, url_prefix='/api/nas')  # Direct import from modular structure
    # Reporting API (optional)
    try:
        from reporting_api_endpoints import reporting_api_bp
        app.register_blueprint(reporting_api_bp, url_prefix='/api/reporting')
    except Exception:
        logger.info('reporting_api_endpoints not available; continuing without it')
    app.register_blueprint(web_bp)  # No prefix for web routes
    
    # Initialize device routes with app context
    init_device_routes(device_manager)
    
    # Health check endpoint
    @app.route('/api/health')
    def health_check():
        return jsonify({
            "status": "healthy",
            "message": "🇿🇦 South African Medical Imaging System is running",
            "version": "3.0.0",
            "system": "operational"
        })
    
    return app

def initialize_system():
    """Initialize all system components"""
    try:
        # Import required modules to trigger initialization
        from device_management import DeviceManager
        
        logger.info("✅ Device database initialized")
        logger.info("✅ Device manager initialized")
        logger.info("✅ Application initialized successfully")
        
        return True
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        return False

def print_startup_banner():
    """Print the startup banner"""
    print("\n🇿🇦 South African Medical Imaging System")
    print("=" * 41)
    print("✅ Flask Backend Server Starting...")
    print(f"🌐 Server: http://localhost:5000")
    print(f"📊 Health Check: http://localhost:5000/api/health")
    print(f"🔐 Login: POST /api/auth/login (admin/admin)")
    print("=" * 41)

# Application initialization
app = create_app()

if __name__ == '__main__':
    # Initialize system
    if not initialize_system():
        logger.error("❌ System initialization failed")
        sys.exit(1)
    
    # Print startup information
    print_startup_banner()
    
    # Start the application
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)
