"""
REFACTORED Medical Authorization Portal
=========================================
Flask application entry point with modular architecture
All business logic extracted into separate modules

Module Structure:
- config.py: Configuration management
- database.py: Database operations (SQLite)
- auth.py: OAuth & authentication flows
- copilot.py: AI intent matching & responses
- routes.py: Flask route definitions
- utils.py: Helper functions & utilities
"""

import os
import sys
from flask import Flask
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import modular components
from app_modules.config import FlaskConfig, LoggingConfig
from app_modules.database import db
from app_modules.routes import register_all_routes
from app_modules.utils import log_info, log_error

# ============================================================================
# CREATE FLASK APPLICATION
# ============================================================================

def create_app():
    """Create and configure Flask application"""
    
    # Initialize Flask
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )
    
    # Apply configuration
    app.config.update({
        'SECRET_KEY': FlaskConfig.SECRET_KEY,
        'PERMANENT_SESSION_LIFETIME': timedelta(hours=24),
        'SESSION_COOKIE_SECURE': FlaskConfig.SESSION_COOKIE_SECURE,
        'SESSION_COOKIE_HTTPONLY': FlaskConfig.SESSION_COOKIE_HTTPONLY,
        'SESSION_COOKIE_SAMESITE': FlaskConfig.SESSION_COOKIE_SAMESITE,
        'JSON_SORT_KEYS': False
    })
    
    return app

# ============================================================================
# INITIALIZE APPLICATION
# ============================================================================

# Create Flask app
app = create_app()

# Initialize database
try:
    db.initialize()
    log_info("Database initialized successfully")
except Exception as e:
    log_error("Database initialization failed", e)

# Register all routes
try:
    register_all_routes(app)
    log_info("All routes registered successfully")
except Exception as e:
    log_error("Route registration failed", e)

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("MEDICAL AUTHORIZATION PORTAL - REFACTORED".center(70))
    print("="*70)
    print("\n[✓] Modular Architecture Active")
    print("    ├─ app_modules/config.py (250 lines) - Configuration")
    print("    ├─ app_modules/database.py (400 lines) - Database Layer")
    print("    ├─ app_modules/auth.py (380 lines) - Authentication")
    print("    ├─ app_modules/copilot.py (420 lines) - AI Assistant")
    print("    ├─ app_modules/routes.py (430 lines) - Endpoints")
    print("    └─ app_modules/utils.py (270 lines) - Utilities")
    
    print("\n[✓] Features Enabled:")
    print("    ├─ Google OAuth integration")
    print("    ├─ Microsoft OAuth integration")
    print("    ├─ Local authentication")
    print("    ├─ GitHub Copilot AI chat")
    print("    ├─ Patient dashboard")
    print("    ├─ Appointment scheduling")
    print("    ├─ Insurance benefits tracking")
    print("    └─ Medical records management")
    
    print("\n[✓] Application Structure:")
    print("    ├─ Single Responsibility: Each module has one clear purpose")
    print("    ├─ No Circular Dependencies: Modules depend on config/database")
    print("    ├─ Easy Testing: Each module can be tested independently")
    print("    ├─ Easy Debugging: Issues isolate to specific modules")
    print("    └─ Scalable: Easy to add new features and modules")
    
    print("\n[✓] Database:")
    print("    ├─ SQLite: users.db (local)")
    print("    ├─ Tables: users, chat_history, authorizations, appointments, audit_log")
    print("    └─ Operations: Full CRUD with transaction support")
    
    print("\n[✓] Configuration:")
    print("    ├─ Flask settings from config.py")
    print("    ├─ OAuth credentials from .env file")
    print("    ├─ Theme colors: South African green (#006533) & gold (#FFB81C)")
    print("    └─ Role-based access control: admin, doctor, patient, clinician")
    
    print("\n[!] Starting on http://localhost:8080 (debug mode)")
    print("="*70)
    print()
    
    # Run Flask development server
    app.run(debug=True, port=8080, threaded=True, use_reloader=True)
