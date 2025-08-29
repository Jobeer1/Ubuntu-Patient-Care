#!/usr/bin/env python3
"""
Application Factory for Medical Reporting Module
Clean, modular Flask application setup
"""

import os
import logging
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global extensions
db = SQLAlchemy()
socketio = SocketIO()

def create_app(config_name='development'):
    """Create and configure Flask application"""
    
    # Create Flask app
    app = Flask(__name__, 
                template_folder='../templates', 
                static_folder='../frontend/static')
    
    # Load configuration
    _configure_app(app, config_name)
    
    # Initialize extensions
    _initialize_extensions(app)
    
    # Register blueprints
    _register_blueprints(app)
    
    # Initialize services
    _initialize_services(app)
    
    # Setup error handlers
    _setup_error_handlers(app)
    
    logger.info("Medical Reporting Module application created successfully")
    return app

def _configure_app(app, config_name):
    """Configure Flask application"""
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'medical-reporting-dev-key-2024')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///medical_reporting.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB for DICOM files
    
    # Environment-specific configuration
    try:
        if config_name == 'production':
            from config.settings import ProductionConfig
            app.config.from_object(ProductionConfig)
        else:
            from config.settings import DevelopmentConfig
            app.config.from_object(DevelopmentConfig)
    except ImportError:
        logger.warning("Configuration modules not found, using defaults")

def _initialize_extensions(app):
    """Initialize Flask extensions"""
    
    # Database
    db.init_app(app)
    
    # CORS
    CORS(app, supports_credentials=True)
    
    # SocketIO
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    
    logger.info("Flask extensions initialized")

def _register_blueprints(app):
    """Register application blueprints"""
    
    # Core routes
    from core.routes import core_bp
    app.register_blueprint(core_bp)
    
    # API blueprints
    try:
        from api.reporting_api import reporting_bp
        app.register_blueprint(reporting_bp, url_prefix='/api/reports')
        logger.info("Registered reporting API")
    except ImportError:
        logger.warning("Reporting API not available")
    
    try:
        from api.voice_api import voice_bp
        app.register_blueprint(voice_bp, url_prefix='/api/voice')
        logger.info("Registered voice API")
    except ImportError:
        logger.warning("Voice API not available")
    
    try:
        from api.layout_api import layout_bp
        app.register_blueprint(layout_bp, url_prefix='/api/layouts')
        logger.info("Registered layout API")
    except ImportError:
        logger.warning("Layout API not available")
    
    try:
        from api.sync_api import sync_bp
        app.register_blueprint(sync_bp, url_prefix='/api/sync')
        logger.info("Registered sync API")
    except ImportError:
        logger.warning("Sync API not available")
    
    try:
        from api.realtime_api import realtime_bp
        app.register_blueprint(realtime_bp, url_prefix='/api/realtime')
        logger.info("Registered real-time API")
    except ImportError:
        logger.warning("Real-time API not available")
    
    try:
        from api.system_api import system_api
        app.register_blueprint(system_api)
        logger.info("Registered system API")
    except ImportError:
        logger.warning("System API not available")
    
    try:
        from api.dicom_api import dicom_api
        app.register_blueprint(dicom_api)
        logger.info("Registered DICOM API")
    except ImportError:
        logger.warning("DICOM API not available")
        logger.info("Registered real-time API")
    except ImportError:
        logger.warning("Real-time API not available")
    
    try:
        from api.security_api import security_bp
        app.register_blueprint(security_bp, url_prefix='/api/security')
        logger.info("Registered security API")
    except ImportError:
        logger.warning("Security API not available")
    
    try:
        from api.demo_api import demo_bp
        app.register_blueprint(demo_bp, url_prefix='/api/demo')
        logger.info("Registered demo API")
    except ImportError:
        logger.warning("Demo API not available")
    
    try:
        from api.medical_api import medical_bp
        app.register_blueprint(medical_bp, url_prefix='/api/medical')
        logger.info("Registered medical standards API")
    except ImportError:
        logger.warning("Medical standards API not available")
    
    try:
        from api.reports_api import reports_bp
        app.register_blueprint(reports_bp, url_prefix='/api/reports')
        logger.info("Registered reports API")
    except ImportError:
        logger.warning("Reports API not available")

def _initialize_services(app):
    """Initialize application services"""
    
    with app.app_context():
        # Initialize database
        try:
            from models.database import init_db
            init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
        
        # Initialize core services
        from core.service_manager import ServiceManager
        service_manager = ServiceManager()
        service_manager.initialize_all_services()
        
        # Store service manager in app context
        app.service_manager = service_manager

def _setup_error_handlers(app):
    """Setup application error handlers"""
    
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f"Unhandled exception: {e}")
        return {'error': 'An unexpected error occurred'}, 500