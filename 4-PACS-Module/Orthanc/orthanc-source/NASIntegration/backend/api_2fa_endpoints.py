"""
REST API endpoints for 2FA functionality
Integrates with the main Flask application for Orthanc NAS integration
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
import json
import time
from typing import Dict, Any
from auth_2fa import TwoFactorAuth, TwoFactorMethod

# Create Blueprint for 2FA endpoints
auth_2fa_bp = Blueprint('auth_2fa', __name__, url_prefix='/api/2fa')

# Initialize 2FA handler
two_factor_auth = TwoFactorAuth()

def require_admin(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') or session.get('role') != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_2fa_if_enabled(f):
    """Decorator to require 2FA verification if enabled for user"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        config = two_factor_auth.get_config()
        user_role = session.get('role', 'user')
        
        # Check if 2FA is required for this user type
        requires_2fa = (
            config['enabled'] and 
            ((user_role == 'admin' and config['required_for_admin']) or
             (user_role == 'user' and config['required_for_users']))
        )
        
        if requires_2fa and not session.get('2fa_verified'):
            return jsonify({'error': '2FA verification required', 'requires_2fa': True}), 403
        
        return f(*args, **kwargs)
    return decorated_function

@auth_2fa_bp.route('/config', methods=['GET'])
@require_admin
def get_2fa_config():
    """Get current 2FA configuration (admin only)"""
    try:
        config = two_factor_auth.get_config()
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get 2FA config: {str(e)}'}), 500

@auth_2fa_bp.route('/config', methods=['POST'])
@require_admin
@require_2fa_if_enabled
def update_2fa_config():
    """Update 2FA configuration (admin only)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No configuration data provided'}), 400
        
        # Validate required fields
        valid_fields = {
            'enabled', 'required_for_admin', 'required_for_users',
            'allowed_methods', 'totp_issuer', 'code_validity_seconds',
            'backup_codes_count', 'max_failed_attempts', 'lockout_duration_minutes'
        }
        
        config_update = {k: v for k, v in data.items() if k in valid_fields}
        
        if two_factor_auth.update_config(config_update):
            return jsonify({
                'success': True,
                'message': '2FA configuration updated successfully'
            })
        else:
            return jsonify({'error': 'Failed to update 2FA configuration'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to update 2FA config: {str(e)}'}), 500

@auth_2fa_bp.route('/setup/totp', methods=['POST'])
@require_auth
def setup_totp():
    """Setup TOTP for current user"""
    try:
        user_id = session.get('user_id')
        setup_data = two_factor_auth.setup_totp_for_user(user_id)
        
        return jsonify({
            'success': True,
            'setup_data': {
                'qr_code': setup_data['qr_code'],
                'manual_entry_key': setup_data['manual_entry_key'],
                'issuer': two_factor_auth.config.totp_issuer
            }
        })
    except Exception as e:
        return jsonify({'error': f'Failed to setup TOTP: {str(e)}'}), 500

@auth_2fa_bp.route('/setup/totp/verify', methods=['POST'])
@require_auth
def verify_totp_setup():
    """Verify TOTP setup with initial code"""
    try:
        data = request.get_json()
        if not data or 'code' not in data:
            return jsonify({'error': 'Verification code required'}), 400
        
        user_id = session.get('user_id')
        code = data['code'].strip()
        
        if two_factor_auth.verify_totp_setup(user_id, code):
            return jsonify({
                'success': True,
                'message': 'TOTP setup completed successfully'
            })
        else:
            return jsonify({'error': 'Invalid verification code'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Failed to verify TOTP setup: {str(e)}'}), 500

@auth_2fa_bp.route('/backup-codes/generate', methods=['POST'])
@require_auth
def generate_backup_codes():
    """Generate new backup codes for current user"""
    try:
        user_id = session.get('user_id')
        
        # Check if user has completed 2FA setup
        status = two_factor_auth.get_user_2fa_status(user_id)
        if not status['setup_complete']:
            return jsonify({'error': 'Complete 2FA setup first'}), 400
        
        codes = two_factor_auth.generate_backup_codes(user_id)
        
        return jsonify({
            'success': True,
            'backup_codes': codes,
            'message': 'New backup codes generated. Save these codes securely.'
        })
    except Exception as e:
        return jsonify({'error': f'Failed to generate backup codes: {str(e)}'}), 500

@auth_2fa_bp.route('/verify', methods=['POST'])
def verify_2fa():
    """Verify 2FA code for authentication"""
    try:
        data = request.get_json()
        if not data or 'code' not in data or 'method' not in data:
            return jsonify({'error': 'Code and method required'}), 400
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        code = data['code'].strip()
        method = data['method']
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        # Validate method
        valid_methods = [m.value for m in TwoFactorMethod]
        if method not in valid_methods:
            return jsonify({'error': 'Invalid 2FA method'}), 400
        
        success, message = two_factor_auth.verify_2fa_code(
            user_id, code, method, ip_address, user_agent
        )
        
        if success:
            # Mark 2FA as verified in session
            session['2fa_verified'] = True
            session['2fa_verified_at'] = int(time.time())
            
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'2FA verification failed: {str(e)}'}), 500

@auth_2fa_bp.route('/status', methods=['GET'])
@require_auth
def get_user_2fa_status():
    """Get 2FA status for current user"""
    try:
        user_id = session.get('user_id')
        status = two_factor_auth.get_user_2fa_status(user_id)
        
        # Add system configuration info
        config = two_factor_auth.get_config()
        user_role = session.get('role', 'user')
        
        status['system_enabled'] = config['enabled']
        status['required_for_user'] = (
            config['enabled'] and 
            ((user_role == 'admin' and config['required_for_admin']) or
             (user_role == 'user' and config['required_for_users']))
        )
        status['allowed_methods'] = config['allowed_methods']
        status['session_2fa_verified'] = session.get('2fa_verified', False)
        
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get 2FA status: {str(e)}'}), 500

@auth_2fa_bp.route('/disable', methods=['POST'])
@require_auth
@require_2fa_if_enabled
def disable_user_2fa():
    """Disable 2FA for current user"""
    try:
        user_id = session.get('user_id')
        
        if two_factor_auth.disable_2fa_for_user(user_id):
            # Clear 2FA verification from session
            session.pop('2fa_verified', None)
            session.pop('2fa_verified_at', None)
            
            return jsonify({
                'success': True,
                'message': '2FA disabled successfully'
            })
        else:
            return jsonify({'error': 'Failed to disable 2FA'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to disable 2FA: {str(e)}'}), 500

@auth_2fa_bp.route('/admin/disable-user', methods=['POST'])
@require_admin
@require_2fa_if_enabled
def admin_disable_user_2fa():
    """Admin endpoint to disable 2FA for any user"""
    try:
        data = request.get_json()
        if not data or 'user_id' not in data:
            return jsonify({'error': 'User ID required'}), 400
        
        target_user_id = data['user_id']
        
        if two_factor_auth.disable_2fa_for_user(target_user_id):
            return jsonify({
                'success': True,
                'message': f'2FA disabled for user {target_user_id}'
            })
        else:
            return jsonify({'error': 'Failed to disable 2FA for user'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to disable user 2FA: {str(e)}'}), 500

@auth_2fa_bp.route('/admin/stats', methods=['GET'])
@require_admin
@require_2fa_if_enabled
def get_2fa_stats():
    """Get 2FA usage statistics for admin dashboard"""
    try:
        stats = two_factor_auth.get_2fa_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get 2FA stats: {str(e)}'}), 500

@auth_2fa_bp.route('/admin/users', methods=['GET'])
@require_admin
@require_2fa_if_enabled
def get_users_2fa_status():
    """Get 2FA status for all users (admin only)"""
    try:
        # This would need to integrate with your user management system
        # For now, return a placeholder response
        return jsonify({
            'success': True,
            'message': 'This endpoint needs integration with user management system',
            'users': []
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get users 2FA status: {str(e)}'}), 500

# Middleware to check 2FA session timeout
@auth_2fa_bp.before_request
def check_2fa_session_timeout():
    """Check if 2FA verification has expired"""
    if session.get('2fa_verified'):
        verified_at = session.get('2fa_verified_at', 0)
        current_time = int(time.time())
        
        # 2FA verification expires after 8 hours
        if current_time - verified_at > 28800:  # 8 hours in seconds
            session.pop('2fa_verified', None)
            session.pop('2fa_verified_at', None)

# Error handlers
@auth_2fa_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@auth_2fa_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized'}), 401

@auth_2fa_bp.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Forbidden'}), 403

@auth_2fa_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500