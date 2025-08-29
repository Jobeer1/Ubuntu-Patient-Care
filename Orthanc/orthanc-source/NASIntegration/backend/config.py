#!/usr/bin/env python3
"""
Configuration module for the South African Medical Imaging System
"""

import os
import secrets
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Basic Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size
    
    # Database configuration
    DATABASE_PATH = 'backend/orthanc_management.db'
    
    # Security settings
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_PERMANENT_LIFETIME = timedelta(hours=24)
    
    # CORS configuration
    CORS_ORIGINS = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:3001',
        'http://127.0.0.1:3001',
        'http://localhost:3002',
        'http://127.0.0.1:3002'
    ]
    
    # Application settings
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Backwards-compatible constants used by refactored device management modules
DB_PATH = os.environ.get('DEVICE_DB_PATH', 'medical_devices.db')
DEFAULT_DICOM_PORTS = [104, 11112, 2762, 2761]
DEFAULT_SCAN_PORTS = DEFAULT_DICOM_PORTS + [80, 443, 22, 23, 8042]
DEFAULT_SCAN_THREADS = int(os.environ.get('DEFAULT_SCAN_THREADS', 50))
ARP_COMMAND_TIMEOUT = int(os.environ.get('ARP_COMMAND_TIMEOUT', 10))
PING_TIMEOUT = int(os.environ.get('PING_TIMEOUT', 2))
SOCKET_TIMEOUT = int(os.environ.get('SOCKET_TIMEOUT', 3))
