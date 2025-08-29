#!/usr/bin/env python3
"""
Service Manager for Medical Reporting Module
Centralized service initialization and management
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ServiceManager:
    """Manages all application services"""
    
    def __init__(self):
        self.services: Dict[str, Any] = {}
        self.initialized = False
    
    def initialize_all_services(self):
        """Initialize all application services"""
        
        if self.initialized:
            logger.info("Services already initialized")
            return
        
        logger.info("Initializing application services...")
        
        # Core services
        self._initialize_whisper_services()
        self._initialize_voice_services()
        self._initialize_ssl_services()
        self._initialize_reporting_services()
        self._initialize_integration_services()
        self._initialize_security_services()
        
        self.initialized = True
        logger.info("All services initialized successfully")
    
    def _initialize_whisper_services(self):
        """Initialize Whisper and STT services"""
        try:
            from services.whisper_model_manager import whisper_model_manager
            from services.offline_stt_service import offline_stt_service
            
            # Setup Whisper environment with BASE model for fast startup
            from services.whisper_model_manager import ModelSize
            success, model_size = whisper_model_manager.setup_whisper_environment(ModelSize.BASE)
            if success:
                logger.info(f"Whisper model setup successful: {model_size.value}")
                self.services['whisper_manager'] = whisper_model_manager
                
                # Initialize STT service
                if offline_stt_service.initialize():
                    offline_stt_service.start_processing()
                    self.services['stt_service'] = offline_stt_service
                    logger.info("Offline STT service initialized")
                else:
                    logger.warning("Failed to initialize STT service")
            else:
                logger.warning("Whisper model setup failed")
                
        except Exception as e:
            logger.error(f"Failed to initialize Whisper services: {e}")
    
    def _initialize_voice_services(self):
        """Initialize voice processing services"""
        try:
            from services.voice_engine import voice_engine
            from services.stt_service import stt_service
            from services.typist_service import typist_service
            
            self.services['voice_engine'] = voice_engine
            self.services['stt_service'] = stt_service
            self.services['typist_service'] = typist_service
            
            logger.info("Voice services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize voice services: {e}")
    
    def _initialize_ssl_services(self):
        """Initialize SSL and security services"""
        try:
            from services.ssl_manager import ssl_manager
            
            # Setup SSL for development
            if ssl_manager.setup_development_ssl():
                self.services['ssl_manager'] = ssl_manager
                logger.info("SSL services initialized")
            else:
                logger.warning("SSL setup failed")
                
        except Exception as e:
            logger.error(f"Failed to initialize SSL services: {e}")
    
    def _initialize_reporting_services(self):
        """Initialize reporting and template services"""
        try:
            from services.template_manager import template_manager
            from services.layout_manager import layout_manager, LayoutManager
            from services.viewport_manager import ViewportManager
            from services.cache_service import cache_service
            from services.offline_manager import offline_manager
            from core.reporting_engine import reporting_engine
            
            self.services['template_manager'] = template_manager
            
            # Initialize layout_manager if it's None
            if layout_manager is None:
                viewport_manager = ViewportManager()
                layout_manager_instance = LayoutManager(viewport_manager)
                self.services['layout_manager'] = layout_manager_instance
            else:
                self.services['layout_manager'] = layout_manager
                
            self.services['cache_service'] = cache_service
            self.services['offline_manager'] = offline_manager
            self.services['reporting_engine'] = reporting_engine
            
            logger.info("Reporting services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize reporting services: {e}")
    
    def _initialize_integration_services(self):
        """Initialize integration services"""
        try:
            from integrations.orthanc_client import orthanc_client
            from integrations.ris_client import ris_client
            from services.sa_localization_manager import sa_localization_manager
            
            self.services['orthanc_client'] = orthanc_client
            self.services['ris_client'] = ris_client
            self.services['sa_localization'] = sa_localization_manager
            
            logger.info("Integration services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize integration services: {e}")
    
    def _initialize_security_services(self):
        """Initialize security and audit services"""
        try:
            from services.audit_service import init_audit_service
            from services.security_service import security_service
            from services.websocket_service import WebSocketService
            from flask import current_app
            
            # Initialize audit service with app context
            try:
                audit_service = init_audit_service(current_app)
                self.services['audit_service'] = audit_service
                
                # Log system startup
                audit_service.log_system_startup()
            except Exception as e:
                logger.warning(f"Audit service initialization failed: {e}")
                # Create a mock audit service for fallback
                self.services['audit_service'] = None
            
            self.services['security_service'] = security_service
            
            # Initialize WebSocket service
            try:
                from core.app_factory import socketio
                websocket_service = WebSocketService(None, socketio)  # App will be set later
                self.services['websocket_service'] = websocket_service
            except Exception as e:
                logger.warning(f"WebSocket service initialization failed: {e}")
            
            logger.info("Security services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize security services: {e}")
    
    def get_service(self, service_name: str) -> Optional[Any]:
        """Get a service by name"""
        return self.services.get(service_name)
    
    def get_all_services(self) -> Dict[str, Any]:
        """Get all services"""
        return self.services.copy()
    
    def is_service_available(self, service_name: str) -> bool:
        """Check if a service is available"""
        return service_name in self.services
    
    def get_service_status(self) -> Dict[str, bool]:
        """Get status of all services"""
        return {name: service is not None for name, service in self.services.items()}