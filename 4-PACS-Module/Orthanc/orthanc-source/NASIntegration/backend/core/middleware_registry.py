#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - Middleware Registry

Centralized middleware registration for clean application setup.
"""

import logging
from flask import request, session

logger = logging.getLogger(__name__)

class MiddlewareRegistry:
    """Manages registration of all Flask middleware"""
    
    def __init__(self, app):
        self.app = app
        self.middleware_count = 0
    
    def register_all(self):
        """Register all application middleware"""
        try:
            # System initialization middleware
            self._register_system_init_middleware()
            
            # Security middleware
            self._register_security_middleware()
            
            # 2FA middleware
            self._register_2fa_middleware()
            
            # Request logging middleware
            self._register_logging_middleware()
            
            logger.info(f"✅ Registered {self.middleware_count} middleware components")
            
        except Exception as e:
            logger.error(f"❌ Middleware registration failed: {e}")
            raise
    
    def _register_system_init_middleware(self):
        """Register system initialization middleware"""
        @self.app.before_request
        def initialize_system():
            """Initialize the system on first request"""
            if not hasattr(initialize_system, 'initialized'):
                initialize_system.initialized = True
                try:
                    # Initialize NAS connection if enabled
                    from nas_connector import nas_connector
                    if nas_connector.config.get('enabled', False):
                        nas_connector.connect()
                        logger.info("NAS connector initialized")
                    
                    logger.info("System initialization completed")
                    
                except Exception as e:
                    logger.error(f"System initialization failed: {e}")
        
        self.middleware_count += 1
        logger.info("✅ System initialization middleware registered")
    
    def _register_security_middleware(self):
        """Register security-related middleware"""
        @self.app.after_request
        def add_security_headers(response):
            """Add security headers to all responses"""
            # Basic security headers
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # Content Security Policy (basic)
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "connect-src 'self'"
            )
            
            return response
        
        self.middleware_count += 1
        logger.info("✅ Security headers middleware registered")
    
    def _register_2fa_middleware(self):
        """Register 2FA middleware"""
        try:
            from orthanc_2fa_integration import create_2fa_middleware
            two_factor_integration = create_2fa_middleware(self.app)
            self.middleware_count += 1
            logger.info("✅ 2FA middleware registered")
        except ImportError as e:
            logger.debug(f"⚠️ 2FA middleware not available: {e}")
        except Exception as e:
            # Handle blueprint name conflicts gracefully
            if "already registered" in str(e):
                logger.debug("⚠️ 2FA blueprint already registered, skipping")
            else:
                logger.warning(f"❌ 2FA middleware registration failed: {e}")
    
    def _register_logging_middleware(self):
        """Register request logging middleware"""
        @self.app.before_request
        def log_request_info():
            """Log request information for debugging"""
            if self.app.debug:
                logger.debug(f"Request: {request.method} {request.path}")
                if request.json:
                    logger.debug(f"JSON data: {request.json}")
        
        @self.app.after_request
        def log_response_info(response):
            """Log response information for debugging"""
            if self.app.debug:
                logger.debug(f"Response: {response.status_code}")
            return response
        
        self.middleware_count += 1
        logger.info("✅ Request logging middleware registered")