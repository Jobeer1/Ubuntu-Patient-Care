#!/usr/bin/env python3
"""
Application Factory for Medical Reporting Module
Clean, modular Flask application setup
"""

import os
import logging
from flask import Flask
from flask_cors import CORS

from flask_socketio import SocketIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global extensions
from models.database import db
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
        app.register_blueprint(reporting_bp, url_prefix='/api/reporting')
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
        app.register_blueprint(layout_bp, url_prefix='/api/layout')
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
        from api.system_api import system_bp
        app.register_blueprint(system_bp, url_prefix='/api/system')
        logger.info("Registered system API")
    except ImportError:
        logger.warning("System API not available")
    
    try:
        from api.dicom_api import dicom_api
        app.register_blueprint(dicom_api, url_prefix='/api/dicom')
        logger.info("Registered DICOM API")
    except ImportError:
        logger.warning("DICOM API not available")
    
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
        from api.auth_api import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        logger.info("Registered authentication API")
    except ImportError:
        logger.warning("Authentication API not available")
    
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
    
    try:
        from api.training_api import training_bp
        app.register_blueprint(training_bp, url_prefix='/api/training')
        logger.info("Registered training data API")
    except ImportError:
        logger.warning("Training data API not available")


def _initialize_services(app):
    """Initialize application services"""
    
    with app.app_context():
        # Import models to ensure they're registered with SQLAlchemy
        try:
            from models.database import Report, VoiceSession
            from models.training_data import TrainingSession, MedicalTerm, UserTrainingProgress
            from models.training_samples import TrainingDataSample
            from models.raw_transcriptions import RawTranscription
            from models.voice_shortcuts import VoiceShortcut, ShortcutUsage
            from core.user_manager import User, UserSession
            logger.info("Models imported successfully")
        except Exception as e:
            logger.error(f"Model import failed: {e}")
        
        # Initialize database tables
        try:
            db.create_all()
            logger.info("Database tables created successfully")
            
            # Seed medical terms if needed
            from models.database import seed_medical_terms
            seed_medical_terms()
            logger.info("Medical terms seeded")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
        
        # Pre-load Whisper model for voice transcription to avoid long delays on first use
        try:
            logger.info("Pre-loading Whisper speech recognition model (this may take 1-2 minutes)...")
            from api.voice_api import get_or_load_whisper_model, check_ffmpeg_availability
            
            # Check FFmpeg availability first
            if check_ffmpeg_availability():
                logger.info("✅ FFmpeg is available")
            else:
                logger.warning("⚠️ FFmpeg not available - audio conversion will be limited")
            
            # Pre-load Whisper
            model = get_or_load_whisper_model()
            if model:
                logger.info("✅ Whisper model pre-loaded successfully - voice transcription ready")
            else:
                logger.warning("⚠️ Whisper model failed to load - voice transcription may be unavailable")
        except Exception as e:
            logger.warning(f"⚠️ Failed to pre-load Whisper model: {e}")
            logger.warning("Voice transcription will attempt to load on first use (may be slow)")
        
        # Initialize basic services (simplified)
        logger.info("Basic services initialized")


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