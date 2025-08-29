"""
Configuration settings for Medical Reporting Module
"""

import os
from datetime import timedelta

class BaseConfig:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'medical-reporting-dev-key-2024')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File upload configuration
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    
    # Voice processing configuration
    VOICE_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'voice')
    MAX_VOICE_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    SUPPORTED_AUDIO_FORMATS = ['wav', 'mp3', 'ogg', 'flac']
    
    # DICOM configuration
    DICOM_CACHE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cache', 'dicom')
    MAX_CACHE_SIZE_GB = 10
    
    # Integration endpoints
    ORTHANC_URL = os.environ.get('ORTHANC_URL', 'http://localhost:8042')
    ORTHANC_USERNAME = os.environ.get('ORTHANC_USERNAME', 'orthanc')
    ORTHANC_PASSWORD = os.environ.get('ORTHANC_PASSWORD', 'orthanc')
    
    SA_MEDICAL_SYSTEM_URL = os.environ.get('SA_MEDICAL_SYSTEM_URL', 'http://localhost:5000')
    
    # NAS configuration
    NAS_MOUNT_POINT = os.environ.get('NAS_MOUNT_POINT', '/mnt/nas')
    NAS_BACKUP_ENABLED = os.environ.get('NAS_BACKUP_ENABLED', 'true').lower() == 'true'

class DevelopmentConfig(BaseConfig):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL', 'sqlite:///medical_reporting_dev.db')
    SESSION_COOKIE_SECURE = False
    
    # Logging
    LOG_LEVEL = 'DEBUG'
    LOG_FILE = 'logs/medical_reporting_dev.log'

class ProductionConfig(BaseConfig):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://user:pass@localhost/medical_reporting')
    
    # Security
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_ENABLED = True
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/medical_reporting.log'
    
    # Performance
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 120,
        'pool_pre_ping': True
    }

class TestingConfig(BaseConfig):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False