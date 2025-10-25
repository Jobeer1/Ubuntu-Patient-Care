#!/usr/bin/env python3
"""
Configuration settings for Medical Reporting Module
"""

import os
from datetime import timedelta


class BaseConfig:
    """Base configuration with common settings"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'medical-reporting-dev-key-2024')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    
    # Orthanc configuration
    ORTHANC_URL = os.environ.get('ORTHANC_URL', 'http://localhost:8042')
    ORTHANC_AUTH = os.environ.get('ORTHANC_AUTH')  # format: "username:password"


class DevelopmentConfig(BaseConfig):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///medical_reporting.db')
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development


class ProductionConfig(BaseConfig):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://user:pass@localhost/medical_reporting')
    
    # Production security settings
    SESSION_COOKIE_SAMESITE = 'Strict'
