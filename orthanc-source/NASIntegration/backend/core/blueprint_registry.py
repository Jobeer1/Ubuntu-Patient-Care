#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - Blueprint Registry

Centralized blueprint registration for clean modular architecture.
"""

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

class BlueprintRegistry:
    """Manages registration of all Flask blueprints"""
    
    def __init__(self, app):
        self.app = app
        self.blueprints = []
    
    def register_all(self):
        """Register all application blueprints"""
        try:
            # Register authentication first (highest priority)
            self._register_auth_blueprint()
            
            # Core API blueprints
            self._register_core_blueprints()
            
            # South African specific blueprints
            self._register_sa_blueprints()
            
            # Feature-specific blueprints
            self._register_feature_blueprints()
            
            # Web interface blueprints
            self._register_web_blueprints()
            
            logger.info(f"✅ Registered {len(self.blueprints)} blueprints successfully")
            
        except Exception as e:
            logger.error(f"❌ Blueprint registration failed: {e}")
            raise
    
    def _register_core_blueprints(self):
        """Register core API blueprints"""
        blueprints = [
            ('api_endpoints', 'api_bp', 'Core API endpoints'),
            # Note: 2FA blueprint is registered by middleware, skip here to avoid conflicts
        ]
        
        for module_name, blueprint_name, description in blueprints:
            self._safe_register_blueprint(module_name, blueprint_name, description)
    
    def _register_sa_blueprints(self):
        """Register South African specific blueprints"""
        blueprints = [
            ('south_african_api_endpoints', 'sa_api_bp', 'South African specific endpoints'),
        ]
        
        for module_name, blueprint_name, description in blueprints:
            self._safe_register_blueprint(module_name, blueprint_name, description)
    
    def _register_feature_blueprints(self):
        """Register feature-specific blueprints"""
        blueprints = [
            ('device_api_endpoints', 'device_api_bp', 'Device management endpoints'),
            ('nas_discovery_api_endpoints', 'nas_discovery_bp', 'NAS discovery endpoints'),
            ('reporting_api_endpoints', 'reporting_api_bp', 'Reporting module endpoints'),
            ('typist_api_endpoints', 'typist_api_bp', 'Typist workflow endpoints'),
            ('sa_templates_api', 'sa_templates_api_bp', 'SA Medical Templates endpoints'),
            ('multi_hospital_api_endpoints', 'multi_hospital_bp', 'Multi-hospital network endpoints'),
            ('collaboration_api_endpoints', 'collaboration_bp', 'Real-time collaboration endpoints'),
            ('telemedicine_api_endpoints', 'telemedicine_bp', 'Telemedicine integration endpoints'),
            ('orthanc_simple_api', 'orthanc_api', 'Simple Orthanc PACS management'),
        ]
        
        for module_name, blueprint_name, description in blueprints:
            self._safe_register_blueprint(module_name, blueprint_name, description)
        
        # Register admin API specifically
        self._register_admin_blueprint()
    
    def _register_admin_blueprint(self):
        """Register admin management blueprint"""
        try:
            import sys
            import os
            
            # Add backend directory to path
            backend_dir = os.path.dirname(os.path.dirname(__file__))
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
            
            from admin_api import admin_api
            self.app.register_blueprint(admin_api)
            self.blueprints.append(('admin_api', 'sa_admin_api', 'Admin API for user and share management'))
            logger.info("✅ Registered admin API blueprint")
            
        except ImportError as e:
            logger.warning(f"⚠️ Could not import admin blueprint: {e}")
            self._create_fallback_admin_routes()
    
    def _register_auth_blueprint(self):
        """Register authentication blueprint"""
        try:
            import sys
            import os
            
            # Add backend directory to path
            backend_dir = os.path.dirname(os.path.dirname(__file__))
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
            
            from auth_api import auth_api
            self.app.register_blueprint(auth_api)
            self.blueprints.append(('auth_api', 'sa_auth_api', 'Authentication API'))
            logger.info("✅ Registered authentication API blueprint")
            
        except ImportError as e:
            logger.warning(f"⚠️ Could not import auth blueprint: {e}")
            self._create_fallback_auth_routes()
    
    def _create_fallback_admin_routes(self):
        """Create fallback admin routes if blueprint fails to load"""
        from flask import jsonify
        
        @self.app.route('/api/admin/status')
        def admin_status():
            return jsonify({
                'status': 'Admin system not available',
                'message': 'Admin blueprint failed to load'
            })
    
    def _create_fallback_auth_routes(self):
        """Create fallback auth routes if blueprint fails to load"""
        from flask import jsonify
        
        @self.app.route('/api/auth/login', methods=['POST'])
        def fallback_login():
            return jsonify({
                'error': 'Authentication system not available',
                'message': 'Auth blueprint failed to load'
            }), 503
    
    def _register_web_blueprints(self):
        """Register web interface blueprints"""
        try:
            from web_interfaces.interface_blueprint import web_bp
            self.app.register_blueprint(web_bp)
            self.blueprints.append(('web_interfaces', 'web_bp', 'Web interfaces'))
            logger.info("✅ Web interface blueprint registered")
        except ImportError as e:
            logger.warning(f"⚠️ Web interface blueprint not available: {e}")
    
    def _safe_register_blueprint(self, module_name: str, blueprint_name: str, description: str):
        """Safely register a blueprint with error handling"""
        try:
            # Try absolute import first
            try:
                module = __import__(module_name, fromlist=[blueprint_name])
            except ImportError:
                # Try importing from current directory
                import sys
                import os
                backend_dir = os.path.dirname(os.path.dirname(__file__))
                if backend_dir not in sys.path:
                    sys.path.insert(0, backend_dir)
                module = __import__(module_name, fromlist=[blueprint_name])
            
            blueprint = getattr(module, blueprint_name)
            self.app.register_blueprint(blueprint)
            self.blueprints.append((module_name, blueprint_name, description))
            logger.info(f"✅ Registered: {description}")
        except ImportError as e:
            logger.warning(f"⚠️ Blueprint {module_name}.{blueprint_name} not available: {e}")
        except AttributeError as e:
            logger.warning(f"⚠️ Blueprint {blueprint_name} not found in {module_name}: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to register {module_name}.{blueprint_name}: {e}")
    
    def get_registered_blueprints(self) -> List[Tuple[str, str, str]]:
        """Get list of successfully registered blueprints"""
        return self.blueprints.copy()