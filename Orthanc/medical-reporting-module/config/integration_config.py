"""
Integration configuration for external systems
"""

import os

class IntegrationConfig:
    """Configuration for external system integrations"""
    
    # Orthanc DICOM Server
    ORTHANC_CONFIG = {
        'url': os.environ.get('ORTHANC_URL', 'http://localhost:8042'),
        'username': os.environ.get('ORTHANC_USERNAME', 'orthanc'),
        'password': os.environ.get('ORTHANC_PASSWORD', 'orthanc'),
        'timeout': 30,
        'retry_attempts': 3,
        'retry_delay': 1,
    }
    
    # SA Medical System
    SA_MEDICAL_CONFIG = {
        'url': os.environ.get('SA_MEDICAL_SYSTEM_URL', 'http://localhost:5000'),
        'api_key': os.environ.get('SA_MEDICAL_API_KEY', ''),
        'timeout': 15,
        'auth_endpoint': '/api/auth/validate',
        'user_endpoint': '/api/users',
    }
    
    # NAS Storage
    NAS_CONFIG = {
        'mount_point': os.environ.get('NAS_MOUNT_POINT', '/mnt/nas'),
        'backup_enabled': os.environ.get('NAS_BACKUP_ENABLED', 'true').lower() == 'true',
        'backup_path': os.environ.get('NAS_BACKUP_PATH', '/mnt/nas/medical_reports'),
        'connection_timeout': 10,
        'read_timeout': 60,
        'write_timeout': 120,
    }
    
    # RIS System
    RIS_CONFIG = {
        'url': os.environ.get('RIS_URL', ''),
        'username': os.environ.get('RIS_USERNAME', ''),
        'password': os.environ.get('RIS_PASSWORD', ''),
        'enabled': os.environ.get('RIS_ENABLED', 'false').lower() == 'true',
        'timeout': 20,
        'hl7_enabled': os.environ.get('HL7_ENABLED', 'false').lower() == 'true',
    }
    
    # Speech-to-Text Service
    STT_CONFIG = {
        'provider': os.environ.get('STT_PROVIDER', 'local'),  # 'local', 'azure', 'google'
        'model_path': os.environ.get('STT_MODEL_PATH', 'models/stt_sa_medical.model'),
        'language': os.environ.get('STT_LANGUAGE', 'en-ZA'),  # South African English
        'confidence_threshold': 0.7,
        'chunk_duration': 5,  # seconds
        'sample_rate': 16000,
    }
    
    # Typist Queue System
    TYPIST_CONFIG = {
        'queue_enabled': True,
        'auto_assign': True,
        'max_queue_size': 100,
        'priority_levels': ['urgent', 'high', 'normal', 'low'],
        'notification_email': os.environ.get('TYPIST_NOTIFICATION_EMAIL', ''),
        'sms_enabled': os.environ.get('TYPIST_SMS_ENABLED', 'false').lower() == 'true',
    }
    
    # API Rate Limiting
    RATE_LIMITS = {
        'orthanc': '100/minute',
        'sa_medical': '200/minute',
        'voice_upload': '10/minute',
        'report_creation': '50/minute',
    }
    
    # Circuit Breaker Configuration
    CIRCUIT_BREAKER = {
        'failure_threshold': 5,
        'recovery_timeout': 60,
        'expected_exception': Exception,
    }