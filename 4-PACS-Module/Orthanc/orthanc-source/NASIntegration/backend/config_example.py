"""
Configuration example for Orthanc 2FA Integration
Copy this file to config.py and modify as needed
"""

import os

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # Database configuration
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'orthanc_2fa.db'
    
    # 2FA Configuration
    TWO_FACTOR_CONFIG = {
        'enabled': False,  # Set to True to enable 2FA system-wide
        'required_for_admin': True,  # Require 2FA for admin users
        'required_for_users': False,  # Require 2FA for regular users
        'allowed_methods': ['totp', 'backup_codes'],  # Available 2FA methods
        'totp_issuer': 'Orthanc NAS',  # Name shown in authenticator apps
        'code_validity_seconds': 300,  # How long codes are valid (5 minutes)
        'backup_codes_count': 10,  # Number of backup codes to generate
        'max_failed_attempts': 3,  # Max failed attempts before lockout
        'lockout_duration_minutes': 15  # How long to lock out after max failures
    }
    
    # Session configuration
    SESSION_TIMEOUT_HOURS = 8  # How long 2FA verification lasts
    
    # CORS configuration
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:8042']  # Add your frontend URLs
    
    # Logging configuration
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'orthanc_2fa.log'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TWO_FACTOR_CONFIG = Config.TWO_FACTOR_CONFIG.copy()
    TWO_FACTOR_CONFIG['enabled'] = True  # Enable 2FA in development for testing

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Must be set in production
    
    # Production 2FA settings
    TWO_FACTOR_CONFIG = Config.TWO_FACTOR_CONFIG.copy()
    TWO_FACTOR_CONFIG.update({
        'enabled': True,
        'required_for_admin': True,
        'required_for_users': True,  # Require 2FA for all users in production
        'max_failed_attempts': 5,
        'lockout_duration_minutes': 30
    })

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_PATH = ':memory:'  # Use in-memory database for tests
    TWO_FACTOR_CONFIG = Config.TWO_FACTOR_CONFIG.copy()
    TWO_FACTOR_CONFIG['enabled'] = False  # Disable 2FA for tests

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}