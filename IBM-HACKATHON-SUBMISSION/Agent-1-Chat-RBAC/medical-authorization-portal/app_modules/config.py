"""
Configuration Module - Centralized Settings & Constants
========================================================
All configuration, environment variables, and constants in one place
Easy to manage, easy to override for different environments
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# ENVIRONMENT SETTINGS
# ============================================================================

ENV = os.environ.get('FLASK_ENV', 'development')
DEBUG = ENV == 'development'

# ============================================================================
# FLASK CONFIGURATION
# ============================================================================

class FlaskConfig:
    """Flask application configuration"""
    SECRET_KEY = 'medical-portal-secret-key-2025'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # Set True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    JSON_SORT_KEYS = False

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

class DatabaseConfig:
    """Database settings"""
    DATABASE_FILE = 'users.db'
    TIMEOUT = 5  # Connection timeout in seconds
    AUTOCOMMIT = False

# ============================================================================
# GOOGLE OAUTH CONFIGURATION
# ============================================================================

class GoogleOAuthConfig:
    """Google OAuth settings"""
    CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'your-google-client-id.apps.googleusercontent.com')
    CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', 'your-google-client-secret')
    REDIRECT_URI = 'http://localhost:8080/auth/google/callback'
    AUTHORIZATION_BASE_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    TOKEN_URL = 'https://www.googleapis.com/oauth2/v4/token'
    SCOPE = ['email', 'profile']

# ============================================================================
# MICROSOFT OAUTH CONFIGURATION
# ============================================================================

class MicrosoftOAuthConfig:
    """Microsoft OAuth settings"""
    CLIENT_ID = os.environ.get('MICROSOFT_CLIENT_ID', 'your-microsoft-client-id')
    CLIENT_SECRET = os.environ.get('MICROSOFT_CLIENT_SECRET', 'your-microsoft-client-secret')
    TENANT_ID = os.environ.get('MICROSOFT_TENANT_ID', 'fba55b68-1de1-4d10-a7cc-efa55942f829')
    REDIRECT_URI = 'http://localhost:8080/auth/microsoft/callback'
    AUTHORIZATION_BASE_URL = f'https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize'
    TOKEN_URL = f'https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token'
    SCOPE = ['User.Read', 'Mail.Read']

# ============================================================================
# API CONFIGURATION
# ============================================================================

class APIConfig:
    """API settings"""
    REQUEST_TIMEOUT = 30  # seconds
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    JSON_ENCODER = 'default'

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================

class SecurityConfig:
    """Security settings"""
    HASH_ALGORITHM = 'sha256'
    SESSION_TIMEOUT = 24  # hours
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION = 15  # minutes
    PASSWORD_MIN_LENGTH = 8

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

class LoggingConfig:
    """Logging settings"""
    LEVEL = 'DEBUG' if DEBUG else 'INFO'
    FORMAT = '[%(asctime)s] %(levelname)s: %(message)s'
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    LOG_FILE = 'app.log'

# ============================================================================
# UI/THEME CONFIGURATION
# ============================================================================

class ThemeConfig:
    """UI theme colors and styling"""
    # South African theme colors
    PRIMARY_GREEN = '#006533'
    ACCENT_GOLD = '#FFB81C'
    MEDICAL_BLUE = '#005580'
    
    # Status colors
    SUCCESS_GREEN = '#10b981'
    WARNING_YELLOW = '#f59e0b'
    ERROR_RED = '#ef4444'
    
    # Structural colors
    TEXT_DARK = '#1f2937'
    TEXT_LIGHT = '#6b7280'
    BORDER_LIGHT = '#e5e7eb'

# ============================================================================
# ROLE CONFIGURATION
# ============================================================================

class RoleConfig:
    """User roles and permissions"""
    ROLES = {
        'admin': ['create_user', 'delete_user', 'view_all', 'manage_settings'],
        'doctor': ['view_patients', 'create_preauth', 'approve_preauth', 'view_history'],
        'patient': ['view_own_data', 'request_preauth', 'schedule_appointment', 'view_benefits'],
        'clinician': ['view_all', 'create_preauth', 'request_data']
    }
    DEFAULT_ROLE = 'patient'

# ============================================================================
# EMAIL DOMAIN ROLE MAPPING
# ============================================================================

class EmailDomainRoleMapping:
    """Auto-detect role from email domain"""
    MAPPINGS = {
        'admin@': 'admin',
        'doctor@': 'doctor',
        '@hospital.': 'doctor',
        '@clinic.': 'doctor',
        'default': 'patient'
    }

# ============================================================================
# FEATURE FLAGS
# ============================================================================

class FeatureFlags:
    """Feature toggles"""
    ENABLE_GOOGLE_OAUTH = True
    ENABLE_MICROSOFT_OAUTH = True
    ENABLE_AI_COPILOT = True
    ENABLE_APPOINTMENTS = True
    ENABLE_PREAUTH = True
    ENABLE_EMAIL_NOTIFICATIONS = False  # Enable in production
    DEBUG_MODE = DEBUG

# ============================================================================
# PAGINATION CONFIGURATION
# ============================================================================

class PaginationConfig:
    """Pagination settings"""
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100
    DEFAULT_PAGE = 1

# ============================================================================
# API RESPONSE TEMPLATES
# ============================================================================

class ResponseTemplates:
    """Standard API response formats"""
    SUCCESS = {
        'success': True,
        'data': None,
        'message': 'Operation completed successfully'
    }
    
    ERROR = {
        'success': False,
        'error': None,
        'message': 'An error occurred'
    }

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_config_dict():
    """Get all configurations as dictionary for easy inspection"""
    return {
        'flask': vars(FlaskConfig),
        'database': vars(DatabaseConfig),
        'google_oauth': vars(GoogleOAuthConfig),
        'microsoft_oauth': vars(MicrosoftOAuthConfig),
        'api': vars(APIConfig),
        'security': vars(SecurityConfig),
        'logging': vars(LoggingConfig),
        'theme': vars(ThemeConfig),
        'roles': vars(RoleConfig),
        'features': vars(FeatureFlags),
        'pagination': vars(PaginationConfig),
    }

def get_role_permissions(role):
    """Get permissions for a specific role"""
    return RoleConfig.ROLES.get(role, [])

def get_theme_colors():
    """Get theme colors dictionary"""
    return {
        'primary': ThemeConfig.PRIMARY_GREEN,
        'accent': ThemeConfig.ACCENT_GOLD,
        'secondary': ThemeConfig.MEDICAL_BLUE,
        'success': ThemeConfig.SUCCESS_GREEN,
        'warning': ThemeConfig.WARNING_YELLOW,
        'error': ThemeConfig.ERROR_RED,
    }
