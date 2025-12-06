#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - Application Factory

Clean Flask application factory with modular configuration.
"""

from flask import Flask
from flask_cors import CORS
import os
import secrets
import logging

from .blueprint_registry import BlueprintRegistry
from .middleware_registry import MiddlewareRegistry

logger = logging.getLogger(__name__)

def create_app(config_name='default'):
    """
    Create and configure Flask application
    
    Args:
        config_name: Configuration environment name
        
    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)
    
    # Configure app
    _configure_app(app, config_name)
    
    # Setup CORS
    _setup_cors(app)
    
    # Register middleware
    middleware_registry = MiddlewareRegistry(app)
    middleware_registry.register_all()
    
    # Register blueprints
    blueprint_registry = BlueprintRegistry(app)
    blueprint_registry.register_all()
    
    # Register basic routes
    _register_basic_routes(app)
    
    logger.info("✅ Flask application created successfully")
    return app

def _configure_app(app, config_name):
    """Configure Flask application settings"""
    # Basic configuration
    app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    
    # Security settings
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # File upload settings
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
    
    # Database settings
    app.config['DATABASE_PATH'] = os.path.join(os.getcwd(), 'data')
    
    logger.info(f"✅ App configured for environment: {config_name}")

def _setup_cors(app):
    """Setup CORS for frontend integration"""
    CORS(app, 
         supports_credentials=True, 
         origins=[
             'http://localhost:3000',  # React dev server
             'http://localhost:8042',  # Orthanc
             'http://localhost:5000'   # Flask dev server
         ])
    logger.info("✅ CORS configured")

def _register_basic_routes(app):
    """Register basic application routes"""
    
    @app.route('/favicon.ico')
    def favicon():
        """Serve favicon"""
        return '', 204
    
    @app.route('/health')
    def health_check():
        """Basic health check endpoint"""
        return {
            'status': 'healthy',
            'system': 'South African Medical Imaging System',
            'version': '1.0.0'
        }
    
    logger.info("✅ Basic routes registered")