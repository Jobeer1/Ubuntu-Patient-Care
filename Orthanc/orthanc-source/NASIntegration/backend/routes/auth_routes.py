"""
Authentication routes blueprint for the South African Medical Imaging System
"""

from flask import Blueprint, request, jsonify, session
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        logger.info(f"Login attempt - Raw data: {data}")
        
        if not data:
            logger.error("No JSON data received")
            return jsonify({'error': 'No data received'}), 400
            
        username = data.get('username')
        password = data.get('password')
        user_type = data.get('user_type')  # Get user type from login form
        
        logger.info(f"Login attempt - Username: {username}, Password: {'*' * len(password) if password else 'None'}, Type: {user_type}")
        
        if not username or not password or not user_type:
            logger.error("Missing username, password, or user type")
            return jsonify({'error': 'Username, password, and user type required'}), 400
        
        # Enhanced authentication with user types
        user_credentials = {
            'admin': {'password': 'admin', 'is_admin': True, 'role': 'admin', 'name': 'System Administrator', 'facility': 'Central Hospital'},
            'doctor': {'password': 'doctor', 'is_admin': False, 'role': 'doctor', 'name': 'Dr. Medical Professional', 'facility': 'Medical Ward'},
            'user': {'password': 'user', 'is_admin': False, 'role': 'user', 'name': 'Healthcare Staff', 'facility': 'General Access'}
        }
        
        if username in user_credentials and password == user_credentials[username]['password'] and user_type == username:
            user_info = user_credentials[username]
            
            session['user_id'] = username
            session['username'] = username
            session['is_admin'] = user_info['is_admin']
            session['role'] = user_info['role']
            session['user_type'] = user_type
            session['authenticated'] = True  # Add the authenticated flag
            
            logger.info(f"Login successful for {user_type} user: {username}")
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': username,
                    'username': username,
                    'email': f'{username}@hospital.co.za',
                    'name': user_info['name'],
                    'role': user_info['role'],
                    'facility': user_info['facility'],
                    'province': 'Gauteng',
                    'is_admin': user_info['is_admin']
                }
            })
        else:
            logger.error(f"Invalid credentials for user: {username}")
            return jsonify({'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    session.clear()
    return jsonify({'message': 'Logged out successfully'})

@auth_bp.route('/session', methods=['GET'])
def get_session():
    """Get current session info"""
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': session.get('user_id'),
                'username': session.get('username'),
                'is_admin': session.get('is_admin', False),
                'role': session.get('role', 'user'),
                'user_type': session.get('user_type', 'user')
            }
        })
    else:
        return jsonify({'authenticated': False})

@auth_bp.route('/simple-login', methods=['POST'])
def simple_login():
    """Simple login for basic authentication"""
    try:
        data = request.get_json()
        username = data.get('username', '')
        password = data.get('password', '')
        
        # Basic authentication
        if username == 'admin' and password == 'admin':
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'redirect': '/dashboard'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid credentials'
            }), 401
    except Exception as e:
        logger.error(f"Simple login error: {e}")
        return jsonify({
            'success': False,
            'message': 'Login failed'
        }), 500

@auth_bp.route('/status', methods=['GET'])
def auth_status():
    """Check authentication status"""
    try:
        if 'authenticated' in session and session['authenticated']:
            return jsonify({
                'authenticated': True,
                'user': {
                    'username': session.get('username'),
                    'role': session.get('role'),
                    'is_admin': session.get('is_admin', False),
                    'user_type': session.get('user_type')
                }
            })
        else:
            return jsonify({
                'authenticated': False
            })
    except Exception as e:
        logger.error(f"Auth status error: {e}")
        return jsonify({
            'authenticated': False,
            'error': str(e)
        }), 500

@auth_bp.route('/activity', methods=['POST'])
def log_activity():
    """Log user activity"""
    try:
        # Accept JSON, form data, or empty body without raising noisy warnings.
        data = {}
        if request.is_json:
            try:
                data = request.get_json(silent=True) or {}
            except Exception:
                # silent parse failure -> fallback to empty
                data = {}
        else:
            # Try form data or raw body as a fallback
            if request.form:
                data = request.form.to_dict()
            else:
                raw = request.get_data(as_text=True) or ''
                # If raw looks like JSON, try a safe parse
                if raw.strip().startswith('{'):
                    try:
                        import json as _json
                        data = _json.loads(raw)
                    except Exception:
                        data = {}

        activity_type = data.get('activity') or data.get('type') or 'page_load'
        
        if 'authenticated' in session and session['authenticated']:
            logger.info(f"User activity: {session.get('username')} - {activity_type}")
            return jsonify({'success': True, 'message': 'Activity logged'})
        else:
            return jsonify({
                'success': False,
                'error': 'Not authenticated'
            }), 401
            
    except Exception as e:
        logger.error(f"Activity logging error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500