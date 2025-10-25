#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - System Initializer

Handles initialization of all system components in the correct order.
"""

import logging
import os
from typing import List, Tuple

logger = logging.getLogger(__name__)

class SystemInitializer:
    """Manages initialization of all system components"""
    
    def __init__(self, app):
        self.app = app
        self.initialized_components = []
    
    def initialize_all(self):
        """Initialize all system components"""
        try:
            # Create necessary directories
            self._create_directories()
            
            # Initialize databases
            self._initialize_databases()
            
            # Initialize South African modules
            self._initialize_sa_modules()
            
            # Initialize feature modules
            self._initialize_feature_modules()
            
            logger.info(f"✅ Initialized {len(self.initialized_components)} system components")
            
        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}")
            raise
    
    def _create_directories(self):
        """Create necessary application directories"""
        directories = [
            'data',
            'logs',
            'audio_recordings',
            'dicom_cache',
            'models',
            'temp'
        ]
        
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                logger.debug(f"✅ Directory created/verified: {directory}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to create directory {directory}: {e}")
        
        self.initialized_components.append(('directories', 'File system directories'))
        logger.info("✅ Directory structure initialized")
    
    def _initialize_databases(self):
        """Initialize all database components"""
        database_modules = [
            ('user_db', 'user_db', 'User database'),
            ('image_db', 'image_db', 'Image database'),
        ]
        
        for module_name, component_name, description in database_modules:
            self._safe_initialize_component(module_name, component_name, description)
    
    def _initialize_sa_modules(self):
        """Initialize South African specific modules"""
        sa_modules = [
            ('south_african_localization', 'sa_localization', 'SA localization system'),
            ('south_african_voice_dictation', 'sa_voice_dictation', 'SA voice dictation'),
            ('advanced_dicom_viewer', 'advanced_dicom_viewer', 'Advanced DICOM viewer'),
        ]
        
        for module_name, component_name, description in sa_modules:
            self._safe_initialize_component(module_name, component_name, description)
    
    def _initialize_feature_modules(self):
        """Initialize feature-specific modules"""
        feature_modules = [
            ('ai_diagnosis_engine', 'ai_diagnosis_engine', 'AI diagnosis engine'),
            ('face_recognition_auth', 'face_recognition_auth', 'Face recognition auth'),
            ('secure_link_sharing', 'secure_link_sharing', 'Secure link sharing'),
            ('device_management', 'device_manager', 'Device management'),
            ('reporting_module', 'reporting_module', 'Reporting module'),
        ]
        
        for module_name, component_name, description in feature_modules:
            self._safe_initialize_component(module_name, component_name, description)
    
    def _safe_initialize_component(self, module_name: str, component_name: str, description: str):
        """Safely initialize a system component with error handling"""
        try:
            # Try absolute import first
            try:
                module = __import__(module_name, fromlist=[component_name])
            except ImportError:
                # Try importing from current directory
                import sys
                import os
                sys.path.insert(0, os.getcwd())
                module = __import__(module_name, fromlist=[component_name])
            
            component = getattr(module, component_name)
            
            # Try to call init method if it exists
            if hasattr(component, 'init_database'):
                component.init_database()
            elif hasattr(component, 'init_system'):
                component.init_system()
            elif hasattr(component, 'initialize'):
                component.initialize()
            
            self.initialized_components.append((module_name, description))
            logger.info(f"✅ Initialized: {description}")
            
        except ImportError as e:
            logger.debug(f"⚠️ Component {module_name}.{component_name} not available: {e}")
        except AttributeError as e:
            logger.debug(f"⚠️ Component {component_name} not found in {module_name}: {e}")
        except Exception as e:
            logger.warning(f"❌ Failed to initialize {module_name}.{component_name}: {e}")
    
    def get_initialized_components(self) -> List[Tuple[str, str]]:
        """Get list of successfully initialized components"""
        return self.initialized_components.copy()
    
    def get_system_status(self) -> dict:
        """Get overall system status"""
        return {
            'status': 'initialized',
            'components_count': len(self.initialized_components),
            'components': [
                {'module': module, 'description': desc} 
                for module, desc in self.initialized_components
            ]
        }