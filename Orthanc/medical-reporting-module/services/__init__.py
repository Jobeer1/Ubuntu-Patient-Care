# Services module initialization

# Import classes without initializing global instances that require database
from .voice_engine import VoiceEngine
from .stt_service import STTService, VoiceCommandProcessor, STTLearningEngine
from .typist_service import TypistService
from .template_manager import TemplateManager
from .layout_manager import LayoutManager
from .offline_manager import OfflineManager
from .cache_service import CacheService
from .dicom_image_service import DicomImageService

# Only import global instances when explicitly requested
def get_voice_engine():
    """Get global voice engine instance"""
    from .voice_engine import voice_engine
    return voice_engine

def get_stt_service():
    """Get global STT service instance"""
    from .stt_service import stt_service
    return stt_service

def get_typist_service():
    """Get global typist service instance"""
    from .typist_service import typist_service
    return typist_service

__all__ = [
    'VoiceEngine', 'get_voice_engine',
    'STTService', 'get_stt_service', 'VoiceCommandProcessor', 'STTLearningEngine',
    'TypistService', 'get_typist_service',
    'TemplateManager',
    'LayoutManager', 
    'OfflineManager',
    'CacheService',
    'DicomImageService'
]