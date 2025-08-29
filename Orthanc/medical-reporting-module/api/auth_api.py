"""
Authentication API for Medical Reporting Module
Handles user authentication and session management
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
import logging
from datetime import datetime, timedelta
import hashlib
import secrets

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

# Mock user database (in production, use proper database)
MOCK_USERS = {
    'doctor1': {
        'id': '1',
        'username': 'doctor1',
        'password_hash': hashlib.sha256('password123'.encode()).hexdigest(),
        'full_name': 'Dr. John Smith',
        'email': 'john.smith@hospital.co.za',
        'role': 'radiologist',
        'hpcsa_number': 'MP123456',
        'department': 'Radiology',
        'active': True
    },
    'doctor2': {
        'id': '2',
        'username': 'doctor2',
        'password_hash': hashlib.sha256('password123'.encode()).hexdigest(),
        'full_name': 'Dr. Sarah Johnson',
        'email': 'sarah.johnson@hospital.co.za',
        'role': 'radiologist',
        'hpcsa_number': 'MP789012',
        'department': 'Radiology',
        'active': True
    },
    'typist1': {
        'id': '3',
        'username': 'typist1',
        'password_hash': hashlib.sha256('password123'.encode()).hexdigest(),
        'full_name': 'Mary Williams',
        'email': 'mary.williams@hospital.co.za',
        'role': 'typist',
        'department': 'Radiology',
        'active': True
    }
}

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_role(role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Authentication required'}), 401
            
            user_id = session['user_id']
            user = next((u for u in MOCK_USERS.values() if u['id'] == user_id), None)
            
            if not user or user['role'] != role:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Username and password required'}), 400
        
        username = data['username']
        password = data['password']
        
        # Check user credentials
        user = MOCK_USERS.get(username)
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Verify password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if password_hash != user['password_hash']:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check if user is active
        if not user['active']:
            return jsonify({'error': 'Account is inactive'}), 401
        
        # Create session
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['login_time'] = datetime.utcnow().isoformat()
        
        # Generate session token
        session_token = secrets.token_urlsafe(32)
        session['token'] = session_token
        
        logger.info(f"User {username} logged in successfully")
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'full_name': user['full_name'],
                'email': user['email'],
                'role': user['role'],
                'department': user.get('department'),
                'hpcsa_number': user.get('hpcsa_number')
            },
            'token': session_token,
            'expires_at': (datetime.utcnow() + timedelta(hours=8)).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """User logout endpoint"""
    try:
        username = session.get('username')
        
        # Clear session
        session.clear()
        
        logger.info(f"User {username} logged out")
        
        return jsonify({'success': True, 'message': 'Logged out successfully'})
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({'error': 'Logout failed'}), 500

@auth_bp.route('/validate', methods=['GET'])
def validate_session():
    """Validate current session"""
    try:
        if 'user_id' not in session:
            return jsonify({'valid': False, 'error': 'No active session'}), 401
        
        user_id = session['user_id']
        user = next((u for u in MOCK_USERS.values() if u['id'] == user_id), None)
        
        if not user or not user['active']:
            session.clear()
            return jsonify({'valid': False, 'error': 'User not found or inactive'}), 401
        
        return jsonify({
            'valid': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'full_name': user['full_name'],
                'email': user['email'],
                'role': user['role'],
                'department': user.get('department'),
                'hpcsa_number': user.get('hpcsa_number')
            },
            'session': {
                'login_time': session.get('login_time'),
                'token': session.get('token')
            }
        })
        
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return jsonify({'valid': False, 'error': 'Validation failed'}), 500

@auth_bp.route('/profile', methods=['GET'])
@require_auth
def get_profile():
    """Get user profile information"""
    try:
        user_id = session['user_id']
        user = next((u for u in MOCK_USERS.values() if u['id'] == user_id), None)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user': {
                'id': user['id'],
                'username': user['username'],
                'full_name': user['full_name'],
                'email': user['email'],
                'role': user['role'],
                'department': user.get('department'),
                'hpcsa_number': user.get('hpcsa_number'),
                'active': user['active']
            }
        })
        
    except Exception as e:
        logger.error(f"Profile retrieval error: {e}")
        return jsonify({'error': 'Failed to retrieve profile'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@require_auth
def change_password():
    """Change user password"""
    try:
        data = request.get_json()
        
        if not data or 'current_password' not in data or 'new_password' not in data:
            return jsonify({'error': 'Current and new password required'}), 400
        
        user_id = session['user_id']
        username = session['username']
        user = MOCK_USERS.get(username)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Verify current password
        current_password_hash = hashlib.sha256(data['current_password'].encode()).hexdigest()
        if current_password_hash != user['password_hash']:
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Validate new password
        new_password = data['new_password']
        if len(new_password) < 8:
            return jsonify({'error': 'New password must be at least 8 characters'}), 400
        
        # Update password
        new_password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        user['password_hash'] = new_password_hash
        
        logger.info(f"Password changed for user {username}")
        
        return jsonify({'success': True, 'message': 'Password changed successfully'})
        
    except Exception as e:
        logger.error(f"Password change error: {e}")
        return jsonify({'error': 'Failed to change password'}), 500

@auth_bp.route('/users', methods=['GET'])
@require_role('radiologist')
def list_users():
    """List all users (radiologists only)"""
    try:
        users = []
        for user in MOCK_USERS.values():
            users.append({
                'id': user['id'],
                'username': user['username'],
                'full_name': user['full_name'],
                'email': user['email'],
                'role': user['role'],
                'department': user.get('department'),
                'hpcsa_number': user.get('hpcsa_number'),
                'active': user['active']
            })
        
        return jsonify({'users': users})
        
    except Exception as e:
        logger.error(f"User listing error: {e}")
        return jsonify({'error': 'Failed to retrieve users'}), 500