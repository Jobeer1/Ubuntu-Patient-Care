"""
Authentication API for South African Healthcare System
Provides login, logout, and session management endpoints
"""

from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin
from datetime import datetime, timedelta
import secrets
import logging
from werkzeug.exceptions import BadRequest, Unauthorized

logger = logging.getLogger(__name__)

# Create blueprint
auth_api = Blueprint('sa_auth_api', __name__, url_prefix='/api/auth')

# Mock user database for development
DEMO_USERS = {
    'admin': {
        'id': 'admin_001',
        'username': 'admin',
        'password': 'admin123',  # In production, use bcrypt
        'name': 'System Administrator',
        'email': 'admin@hospital.co.za',
        'role': 'admin',
        'facility': 'Gauteng Provincial Hospital',
        'province': 'Gauteng'
    },
    'doctor': {
        'id': 'doc_001',
        'username': 'doctor',
        'password': 'doctor123',
        'name': 'Dr. Sarah Mthembu',
        'email': 'sarah.mthembu@hospital.co.za',
        'role': 'radiologist',
        'facility': 'Chris Hani Baragwanath Hospital',
        'province': 'Gauteng'
    },
    'nurse': {
        'id': 'nurse_001',
        'username': 'nurse',
        'password': 'nurse123',
        'name': 'Sister Nomsa Dlamini',
        'email': 'nomsa.dlamini@clinic.co.za',
        'role': 'nursing_sister',
        'facility': 'Soweto Community Clinic',
        'province': 'Gauteng'
    }
}

@auth_api.route('/test', methods=['GET', 'POST'])
@cross_origin()
def test_endpoint():
    """Test endpoint to verify API connectivity"""
    return jsonify({
        'success': True,
        'message': 'South African Healthcare Auth API is working!',
        'method': request.method,
        'timestamp': datetime.now().isoformat(),
        'demo_users': ['admin', 'doctor', 'nurse']
    })

@auth_api.route('/login', methods=['POST'])
@cross_origin(supports_credentials=True, origins='*', allow_headers=['Content-Type', 'Authorization'])
def login():
    """User login endpoint"""
    try:
        # Debug: Log all request info
        logger.info(f"Login attempt - Content-Type: {request.content_type}")
        logger.info(f"Request is_json: {request.is_json}")
        logger.info(f"Request form: {dict(request.form)}")
        logger.info(f"Request json: {request.get_json(silent=True)}")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        
        # Handle multiple content types
        data = None
        if request.is_json:
            data = request.get_json()
            logger.info("Using JSON data")
        elif request.form:
            data = request.form.to_dict()
            logger.info("Using form data")
        elif request.content_type and 'text/plain' in request.content_type:
            # Handle plain text data
            try:
                import json
                data = json.loads(request.get_data(as_text=True))
                logger.info("Using plain text JSON data")
            except:
                logger.error("Failed to parse plain text as JSON")
        
        if not data:
            # Try to get any data we can
            try:
                data = request.get_json(force=True, silent=True)
                if data:
                    logger.info("Using forced JSON parsing")
            except:
                pass
        
        if not data:
            logger.error("No data received in request")
            raise BadRequest("No login data provided")
        
        username = data.get('username', '').strip()
        # Try multiple possible password field names
        password = (data.get('password', '') or 
                   data.get('pin', '') or 
                   data.get('passwd', '') or 
                   data.get('pwd', '')).strip()
        
        logger.info(f"Parsed credentials - username: '{username}', password length: {len(password)}")
        logger.info(f"Available fields in request: {list(data.keys())}")
        
        if not username or not password:
            logger.error(f"Missing credentials - username: '{username}', password: {'present' if password else 'missing'}")
            return jsonify({
                'error': 'Username and password are required', 
                'debug': {
                    'username': username, 
                    'password_length': len(password), 
                    'available_fields': list(data.keys()),
                    'data': data
                }
            }), 400
        
        # Check demo users
        user = DEMO_USERS.get(username)
        if not user or user['password'] != password:
            logger.error(f"Invalid credentials for user: {username}")
            return jsonify({'error': 'Invalid username or password'}), 401
        
        # Create session
        session_token = secrets.token_urlsafe(32)
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']  # Store role in session for authorization
        session['session_token'] = session_token
        session['login_time'] = datetime.now().isoformat()
        
        # Debug session creation
        logger.info(f"Session created - Keys: {list(session.keys())}")
        logger.info(f"Session user_id: {session.get('user_id')}")
        logger.info(f"Session username: {session.get('username')}")
        logger.info(f"Session permanent: {session.permanent}")
        
        # Make session permanent so it persists
        session.permanent = True
        
        # Return user info (without password)
        user_info = {
            'id': user['id'],
            'username': user['username'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'facility': user['facility'],
            'province': user['province'],
            'session_token': session_token,
            'login_time': session['login_time']
        }
        
        logger.info(f"User {username} logged in successfully")
        
        response_data = {
            'success': True,  # Add explicit success flag
            'message': 'Login successful',
            'status': 'authenticated',
            'user': user_info
        }
        
        logger.info(f"Sending login response: {response_data}")
        
        return jsonify(response_data)
        
    except BadRequest as e:
        logger.error(f"Bad request: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': str(e)}), 500

@auth_api.route('/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    try:
        username = session.get('username', 'Unknown')
        
        # Clear session
        session.clear()
        
        logger.info(f"User {username} logged out")
        
        return jsonify({'message': 'Logout successful'})
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({'error': str(e)}), 500

@auth_api.route('/session', methods=['GET'])
def get_session():
    """Get current session info"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'No active session'}), 401
        
        username = session.get('username')
        user = DEMO_USERS.get(username)
        
        if not user:
            session.clear()
            return jsonify({'error': 'Invalid session'}), 401
        
        user_info = {
            'id': user['id'],
            'username': user['username'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'facility': user['facility'],
            'province': user['province'],
            'session_token': session.get('session_token'),
            'login_time': session.get('login_time')
        }
        
        return jsonify({'user': user_info})
        
    except Exception as e:
        logger.error(f"Session check error: {e}")
        return jsonify({'error': str(e)}), 500

@auth_api.route('/validate', methods=['POST'])
def validate_session():
    """Validate session token"""
    try:
        data = request.get_json()
        token = data.get('session_token') if data else None
        
        if not token:
            return jsonify({'valid': False, 'error': 'No token provided'}), 400
        
        session_token = session.get('session_token')
        if not session_token or session_token != token:
            return jsonify({'valid': False, 'error': 'Invalid token'}), 401
        
        return jsonify({'valid': True})
        
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return jsonify({'valid': False, 'error': str(e)}), 500

@auth_api.route('/users', methods=['GET'])
def get_demo_users():
    """Get list of demo users (for development only)"""
    try:
        # Return demo users without passwords
        demo_users = []
        for username, user in DEMO_USERS.items():
            demo_users.append({
                'username': username,
                'name': user['name'],
                'role': user['role'],
                'facility': user['facility'],
                'province': user['province']
            })
        
        return jsonify({'demo_users': demo_users})
        
    except Exception as e:
        logger.error(f"Error getting demo users: {e}")
        return jsonify({'error': str(e)}), 500

@auth_api.route('/profile', methods=['GET'])
def get_user_profile():
    """Get current user's profile"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        username = session.get('username')
        user = DEMO_USERS.get(username)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        profile = {
            'id': user['id'],
            'username': user['username'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'facility': user['facility'],
            'province': user['province'],
            'login_time': session.get('login_time'),
            'session_duration': _calculate_session_duration()
        }
        
        return jsonify({'profile': profile})
        
    except Exception as e:
        logger.error(f"Profile error: {e}")
        return jsonify({'error': str(e)}), 500

def _calculate_session_duration():
    """Calculate how long the user has been logged in"""
    try:
        login_time_str = session.get('login_time')
        if not login_time_str:
            return None
        
        login_time = datetime.fromisoformat(login_time_str)
        duration = datetime.now() - login_time
        
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)
        
        return f"{hours}h {minutes}m"
        
    except Exception:
        return None

# Error handlers
@auth_api.errorhandler(BadRequest)
def handle_bad_request(e):
    return jsonify({'error': str(e)}), 400

@auth_api.errorhandler(Unauthorized)
def handle_unauthorized(e):
    return jsonify({'error': 'Authentication required'}), 401
