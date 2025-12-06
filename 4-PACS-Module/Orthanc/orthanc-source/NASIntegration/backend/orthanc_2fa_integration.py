"""
Orthanc 2FA Integration Module
Integrates 2FA authentication with the main Orthanc NAS application
"""

from flask import Flask, session, request, jsonify
from functools import wraps
import time
from typing import Optional, Dict, Any
from auth_2fa import TwoFactorAuth
from api_2fa_endpoints import auth_2fa_bp

class OrthancTwoFactorIntegration:
    """Main integration class for 2FA with Orthanc"""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.two_factor_auth = TwoFactorAuth()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize the 2FA integration with Flask app"""
        self.app = app
        
        # Register the 2FA blueprint
        app.register_blueprint(auth_2fa_bp)
        
        # Add 2FA middleware to existing routes
        self._setup_middleware()
        
        # Initialize default configuration if not exists
        self._init_default_config()
    
    def _setup_middleware(self):
        """Setup middleware to enforce 2FA on protected routes"""
        
        @self.app.before_request
        def enforce_2fa():
            """Middleware to enforce 2FA on protected routes"""
            
            # Skip 2FA enforcement for certain routes
            skip_routes = [
                '/api/login',
                '/api/logout', 
                '/api/2fa/',  # All 2FA routes
                '/static/',   # Static files
                '/favicon.ico'
            ]
            
            # Check if current route should skip 2FA
            if any(request.path.startswith(route) for route in skip_routes):
                return
            
            # Skip for non-API routes (static content, etc.)
            if not request.path.startswith('/api/'):
                return
            
            # Check if user is authenticated
            user_id = session.get('user_id')
            if not user_id:
                return  # Let the regular auth handle this
            
            # Get 2FA configuration
            config = self.two_factor_auth.get_config()
            if not config['enabled']:
                return  # 2FA is disabled system-wide
            
            user_role = session.get('role', 'user')
            
            # Check if 2FA is required for this user type
            requires_2fa = (
                (user_role == 'admin' and config['required_for_admin']) or
                (user_role == 'user' and config['required_for_users'])
            )
            
            if not requires_2fa:
                return  # 2FA not required for this user type
            
            # Check if user has completed 2FA setup
            user_status = self.two_factor_auth.get_user_2fa_status(user_id)
            if not user_status['setup_complete']:
                return jsonify({
                    'error': '2FA setup required',
                    'requires_2fa_setup': True,
                    'redirect': '/2fa/setup'
                }), 403
            
            # Check if 2FA is verified in current session
            if not session.get('2fa_verified'):
                return jsonify({
                    'error': '2FA verification required',
                    'requires_2fa': True,
                    'redirect': '/2fa/verify'
                }), 403
            
            # Check if 2FA verification has expired (8 hours)
            verified_at = session.get('2fa_verified_at', 0)
            current_time = int(time.time())
            if current_time - verified_at > 28800:  # 8 hours
                session.pop('2fa_verified', None)
                session.pop('2fa_verified_at', None)
                return jsonify({
                    'error': '2FA verification expired',
                    'requires_2fa': True,
                    'redirect': '/2fa/verify'
                }), 403
    
    def _init_default_config(self):
        """Initialize default 2FA configuration if none exists"""
        try:
            config = self.two_factor_auth.get_config()
            
            # If config is empty or has default values, set up initial config
            if not config.get('enabled', False):
                default_config = {
                    'enabled': False,  # Start disabled by default
                    'required_for_admin': True,
                    'required_for_users': False,
                    'allowed_methods': ['totp', 'backup_codes'],
                    'totp_issuer': 'Orthanc NAS',
                    'code_validity_seconds': 300,
                    'backup_codes_count': 10,
                    'max_failed_attempts': 3,
                    'lockout_duration_minutes': 15
                }
                
                self.two_factor_auth.update_config(default_config)
                
        except Exception as e:
            print(f"Warning: Could not initialize default 2FA config: {e}")
    
    def require_2fa(self, f):
        """Decorator to require 2FA verification for specific routes"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({'error': 'Authentication required'}), 401
            
            config = self.two_factor_auth.get_config()
            if not config['enabled']:
                return f(*args, **kwargs)  # 2FA disabled, proceed normally
            
            user_role = session.get('role', 'user')
            requires_2fa = (
                (user_role == 'admin' and config['required_for_admin']) or
                (user_role == 'user' and config['required_for_users'])
            )
            
            if not requires_2fa:
                return f(*args, **kwargs)  # 2FA not required for this user
            
            # Check 2FA setup and verification
            user_status = self.two_factor_auth.get_user_2fa_status(user_id)
            if not user_status['setup_complete']:
                return jsonify({
                    'error': '2FA setup required',
                    'requires_2fa_setup': True
                }), 403
            
            if not session.get('2fa_verified'):
                return jsonify({
                    'error': '2FA verification required',
                    'requires_2fa': True
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    def is_2fa_required_for_user(self, user_id: str, user_role: str = 'user') -> bool:
        """Check if 2FA is required for a specific user"""
        config = self.two_factor_auth.get_config()
        
        if not config['enabled']:
            return False
        
        return (
            (user_role == 'admin' and config['required_for_admin']) or
            (user_role == 'user' and config['required_for_users'])
        )
    
    def get_user_2fa_requirements(self, user_id: str, user_role: str = 'user') -> Dict[str, Any]:
        """Get 2FA requirements and status for a user"""
        config = self.two_factor_auth.get_config()
        user_status = self.two_factor_auth.get_user_2fa_status(user_id)
        
        requires_2fa = self.is_2fa_required_for_user(user_id, user_role)
        
        return {
            'system_enabled': config['enabled'],
            'required_for_user': requires_2fa,
            'setup_complete': user_status['setup_complete'],
            'needs_setup': requires_2fa and not user_status['setup_complete'],
            'needs_verification': requires_2fa and user_status['setup_complete'] and not session.get('2fa_verified'),
            'allowed_methods': config['allowed_methods'],
            'enabled_methods': user_status['enabled_methods'],
            'has_backup_codes': user_status['has_backup_codes'],
            'backup_codes_remaining': user_status['backup_codes_remaining']
        }
    
    def clear_2fa_session(self):
        """Clear 2FA verification from current session"""
        session.pop('2fa_verified', None)
        session.pop('2fa_verified_at', None)
    
    def mark_2fa_verified(self):
        """Mark 2FA as verified in current session"""
        session['2fa_verified'] = True
        session['2fa_verified_at'] = int(time.time())

# Utility functions for integration with existing auth system

def integrate_2fa_with_login(login_function):
    """Decorator to integrate 2FA with existing login function"""
    @wraps(login_function)
    def wrapper(*args, **kwargs):
        # Call original login function
        result = login_function(*args, **kwargs)
        
        # If login was successful, check 2FA requirements
        if hasattr(result, 'status_code') and result.status_code == 200:
            user_id = session.get('user_id')
            user_role = session.get('role', 'user')
            
            if user_id:
                integration = OrthancTwoFactorIntegration()
                requirements = integration.get_user_2fa_requirements(user_id, user_role)
                
                # Modify response to include 2FA requirements
                if hasattr(result, 'json') and result.json:
                    response_data = result.json
                    response_data['2fa_requirements'] = requirements
                    return jsonify(response_data)
        
        return result
    
    return wrapper

def create_2fa_middleware(app: Flask) -> OrthancTwoFactorIntegration:
    """Create and configure 2FA middleware for the Flask app"""
    integration = OrthancTwoFactorIntegration(app)
    return integration

# Example usage in main app.py:
"""
from orthanc_2fa_integration import create_2fa_middleware, integrate_2fa_with_login

app = Flask(__name__)
# ... other app configuration ...

# Initialize 2FA integration
two_factor_integration = create_2fa_middleware(app)

# Integrate with existing login endpoint
@app.route('/api/login', methods=['POST'])
@integrate_2fa_with_login
def login():
    # Your existing login logic here
    pass

# Use 2FA decorator on protected routes
@app.route('/api/admin/users', methods=['GET'])
@two_factor_integration.require_2fa
def admin_users():
    # Admin functionality that requires 2FA
    pass
"""