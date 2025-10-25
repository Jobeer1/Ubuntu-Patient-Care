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
from flask import Flask, jsonify, redirect
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
    
    # Debug: Log SECRET_KEY to verify it's consistent
    logger.info(f"🔑 SECRET_KEY configured: {app.config['SECRET_KEY'][:20]}...")
    logger.info(f"🍪 SESSION_COOKIE_SAMESITE: {app.config.get('SESSION_COOKIE_SAMESITE')}")
    
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
    
    # PACS API for high-performance patient search
    try:
        from pacs_api import pacs_bp
        app.register_blueprint(pacs_bp, url_prefix='/api/pacs')
        logger.info("✅ PACS API registered")
    except Exception as e:
        logger.warning(f"⚠️ PACS API not available: {e}")
    
    # Enterprise Multi-NAS PACS API
    try:
        from enterprise_pacs_api import enterprise_pacs_bp
        app.register_blueprint(enterprise_pacs_bp, url_prefix='/api/enterprise-pacs')
        logger.info("✅ Enterprise Multi-NAS PACS API registered")
    except Exception as e:
        logger.warning(f"⚠️ Enterprise PACS API not available: {e}")
    
    # Enterprise NAS Shared Folders Configuration API
    try:
        from api.enterprise_nas_api import enterprise_nas_bp
        app.register_blueprint(enterprise_nas_bp, url_prefix='/api/enterprise-nas')
        logger.info("✅ Enterprise NAS Shared Folders API registered")
    except Exception as e:
        logger.warning(f"⚠️ Enterprise NAS Shared Folders API not available: {e}")
    
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
    
    # OneDrive Integration
    try:
        from routes.onedrive_routes import onedrive_bp
        app.register_blueprint(onedrive_bp)
        logger.info("✅ OneDrive integration registered")
    except Exception as e:
        logger.warning(f"⚠️ OneDrive integration not available: {e}")
    
    # Google Drive Integration (stub)
    try:
        from routes.gdrive_routes import gdrive_bp
        app.register_blueprint(gdrive_bp)
        logger.info("✅ Google Drive integration registered")
    except Exception as e:
        logger.warning(f"⚠️ Google Drive integration not available: {e}")
    
    # Reporting API (optional)
    try:
        from reporting_api_endpoints import reporting_api_bp
        app.register_blueprint(reporting_api_bp, url_prefix='/api/reporting')
    except Exception:
        logger.info('reporting_api_endpoints not available; continuing without it')
    app.register_blueprint(web_bp)  # No prefix for web routes

    # Backwards compatible redirects for legacy OneDrive URLs
    @app.route('/onedrive/<path:sub>')
    def _global_onedrive_redirect(sub):
        return redirect(f"/api/nas/onedrive/{sub}")

    @app.route('/onedrive')
    def _global_onedrive_root():
        return redirect('/api/nas/onedrive/setup')
    
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
        # Log which metadata DB will be used (helps troubleshoot wrong DB issues)
        try:
            from backend.metadata_db import get_metadata_db_path
            resolved_db = get_metadata_db_path()
        except Exception:
            try:
                from metadata_db import get_metadata_db_path
                resolved_db = get_metadata_db_path()
            except Exception:
                resolved_db = 'nas_patient_index.db (fallback)'

        logger.info(f"🔎 Resolved metadata DB path: {resolved_db}")
        logger.info(f"🔐 USE_ORTHANC_INTERNAL_INDEX = {os.environ.get('USE_ORTHANC_INTERNAL_INDEX', 'false')}")
        
        # Start NAS→Orthanc auto-import service
        try:
            from services.nas_orthanc_importer import get_importer
            importer = get_importer()
            importer.start_background_import()
            logger.info("✅ NAS→Orthanc auto-import service started")
        except Exception as e:
            logger.warning(f"⚠️ Auto-import service not started: {e}")
        
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
