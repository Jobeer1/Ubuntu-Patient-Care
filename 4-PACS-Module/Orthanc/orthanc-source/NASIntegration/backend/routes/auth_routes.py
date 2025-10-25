"""
Authentication routes blueprint for the South African Medical Imaging System
"""

from flask import Blueprint, request, jsonify, session, redirect, url_for
import logging
import os
import requests
from urllib.parse import urlencode
import jwt
import json
from pathlib import Path

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# MCP Server Configuration
MCP_SERVER_URL = os.environ.get('MCP_SERVER_URL', 'http://localhost:8080')
MCP_JWT_SECRET = os.environ.get('MCP_JWT_SECRET', '7e2d9c8b7a6f5e4d3c2b1a9f8e7d6c5b4a3f2e1d9c8b7a6f5e4d3c2b1a0f9e8d')

# OAuth Configuration
MICROSOFT_CLIENT_ID = os.environ.get('MICROSOFT_CLIENT_ID', '')
MICROSOFT_CLIENT_SECRET = os.environ.get('MICROSOFT_CLIENT_SECRET', '')
MICROSOFT_TENANT_ID = os.environ.get('MICROSOFT_TENANT_ID', 'common')
MICROSOFT_REDIRECT_URI = os.environ.get('MICROSOFT_REDIRECT_URI', 'http://localhost:5000/auth/microsoft/callback')

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')

# SSO Configuration File
SSO_CONFIG_FILE = Path('backend/sso_config.json')

def get_sso_status():
    """Get current SSO enabled/disabled status"""
    try:
        if SSO_CONFIG_FILE.exists():
            with open(SSO_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('enabled', True)
        return True  # Default to enabled
    except Exception as e:
        logger.error(f"Error reading SSO config: {e}")
        return True

def set_sso_status(enabled):
    """Set SSO enabled/disabled status"""
    try:
        SSO_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        config = {'enabled': enabled}
        with open(SSO_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"SSO status set to: {enabled}")
        return True
    except Exception as e:
        logger.error(f"Error writing SSO config: {e}")
        return False

def validate_mcp_token(token):
    """Validate MCP server JWT token"""
    try:
        payload = jwt.decode(token, MCP_JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        logger.error("MCP token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid MCP token: {e}")
        return None

@auth_bp.route('/get-mcp-token', methods=['GET'])
def get_mcp_token():
    """Get MCP token for frontend access control"""
    try:
        if 'authenticated' not in session or not session.get('authenticated'):
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Generate MCP token from session data
        from datetime import datetime, timedelta
        
        payload = {
            'email': session.get('email', session.get('user_id')),
            'name': session.get('username', 'User'),
            'role': session.get('role', 'user'),
            'user_id': session.get('user_id'),
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        
        mcp_token = jwt.encode(payload, MCP_JWT_SECRET, algorithm='HS256')
        
        return jsonify({
            'token': mcp_token,
            'user': {
                'email': payload['email'],
                'name': payload['name'],
                'role': payload['role'],
                'user_id': payload['user_id']
            }
        })
    except Exception as e:
        logger.error(f"Error generating MCP token: {e}")
        return jsonify({'error': 'Failed to generate token'}), 500

@auth_bp.route('/mcp-token', methods=['POST'])
def exchange_mcp_token():
    """Exchange MCP token for PACS session"""
    try:
        data = request.get_json()
        mcp_token = data.get('mcp_token')
        
        if not mcp_token:
            return jsonify({'error': 'No MCP token provided'}), 400
        
        # Validate MCP token
        payload = validate_mcp_token(mcp_token)
        if not payload:
            return jsonify({'error': 'Invalid or expired MCP token'}), 401
        
        # Create PACS session from MCP token
        session['user_id'] = payload.get('email')
        session['username'] = payload.get('name')
        session['email'] = payload.get('email')
        session['role'] = payload.get('role', 'user')
        session['is_admin'] = payload.get('role') == 'Admin'
        session['user_type'] = 'admin' if payload.get('role') == 'Admin' else 'user'
        session['authenticated'] = True
        session['oauth_provider'] = 'mcp'
        
        logger.info(f"MCP SSO successful for {payload.get('email')}")
        
        return jsonify({
            'success': True,
            'user': {
                'email': payload.get('email'),
                'name': payload.get('name'),
                'role': payload.get('role'),
                'is_admin': payload.get('role') == 'Admin'
            }
        })
        
    except Exception as e:
        logger.error(f"MCP token exchange error: {e}")
        return jsonify({'error': 'Token exchange failed'}), 500

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


# ============================================================================
# OAuth Routes - Microsoft and Google Authentication
# ============================================================================

@auth_bp.route('/microsoft', methods=['GET'])
def microsoft_login():
    """Initiate Microsoft OAuth login"""
    # Check if SSO is enabled
    if not get_sso_status():
        return redirect('/login?error=SSO is currently disabled by administrator')
    
    if not MICROSOFT_CLIENT_ID:
        return redirect('/login?error=Microsoft OAuth not configured')
    
    # Microsoft OAuth authorization URL
    auth_url = f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}/oauth2/v2.0/authorize"
    
    params = {
        'client_id': MICROSOFT_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': MICROSOFT_REDIRECT_URI,
        'response_mode': 'query',
        'scope': 'openid profile email User.Read',
        'state': 'microsoft_oauth'
    }
    
    authorization_url = f"{auth_url}?{urlencode(params)}"
    return redirect(authorization_url)


@auth_bp.route('/microsoft/callback', methods=['GET'])
def microsoft_callback():
    """Handle Microsoft OAuth callback"""
    try:
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            logger.error(f"Microsoft OAuth error: {error}")
            return redirect(f'/login?error=Microsoft login failed: {error}')
        
        if not code:
            return redirect('/login?error=No authorization code received')
        
        # Exchange code for token
        token_url = f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
        
        token_data = {
            'client_id': MICROSOFT_CLIENT_ID,
            'client_secret': MICROSOFT_CLIENT_SECRET,
            'code': code,
            'redirect_uri': MICROSOFT_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        
        if 'access_token' not in token_json:
            logger.error(f"Token exchange failed: {token_json}")
            return redirect('/login?error=Failed to get access token')
        
        access_token = token_json['access_token']
        
        # Get user info from Microsoft Graph API
        graph_url = 'https://graph.microsoft.com/v1.0/me'
        headers = {'Authorization': f'Bearer {access_token}'}
        user_response = requests.get(graph_url, headers=headers)
        user_info = user_response.json()
        
        # Create session
        email = user_info.get('mail') or user_info.get('userPrincipalName')
        username = email.split('@')[0] if email else user_info.get('displayName', 'user')
        
        session['user_id'] = user_info.get('id')
        session['username'] = username
        session['email'] = email
        session['name'] = user_info.get('displayName', username)
        session['oauth_provider'] = 'microsoft'
        session['is_admin'] = False  # Default to non-admin for OAuth users
        session['role'] = 'user'
        session['user_type'] = 'user'
        session['authenticated'] = True
        
        logger.info(f"Microsoft OAuth login successful: {email}")
        return redirect('/dashboard')
        
    except Exception as e:
        logger.error(f"Microsoft OAuth callback error: {e}")
        return redirect(f'/login?error=Microsoft authentication failed')


@auth_bp.route('/google', methods=['GET'])
def google_login():
    """Initiate Google OAuth login"""
    # Check if SSO is enabled
    if not get_sso_status():
        return redirect('/login?error=SSO is currently disabled by administrator')
    
    if not GOOGLE_CLIENT_ID:
        return redirect('/login?error=Google OAuth not configured')
    
    # Google OAuth authorization URL
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': GOOGLE_REDIRECT_URI,
        'scope': 'openid profile email',
        'access_type': 'offline',
        'state': 'google_oauth'
    }
    
    authorization_url = f"{auth_url}?{urlencode(params)}"
    return redirect(authorization_url)


@auth_bp.route('/google/callback', methods=['GET'])
def google_callback():
    """Handle Google OAuth callback"""
    try:
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            logger.error(f"Google OAuth error: {error}")
            return redirect(f'/login?error=Google login failed: {error}')
        
        if not code:
            return redirect('/login?error=No authorization code received')
        
        # Exchange code for token
        token_url = "https://oauth2.googleapis.com/token"
        
        token_data = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'code': code,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        
        if 'access_token' not in token_json:
            logger.error(f"Token exchange failed: {token_json}")
            return redirect('/login?error=Failed to get access token')
        
        access_token = token_json['access_token']
        
        # Get user info from Google
        userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        user_response = requests.get(userinfo_url, headers=headers)
        user_info = user_response.json()
        
        # Create session
        email = user_info.get('email')
        username = email.split('@')[0] if email else user_info.get('name', 'user')
        
        session['user_id'] = user_info.get('id')
        session['username'] = username
        session['email'] = email
        session['name'] = user_info.get('name', username)
        session['oauth_provider'] = 'google'
        session['is_admin'] = False  # Default to non-admin for OAuth users
        session['role'] = 'user'
        session['user_type'] = 'user'
        session['authenticated'] = True
        
        logger.info(f"Google OAuth login successful: {email}")
        return redirect('/dashboard')
        
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        return redirect(f'/login?error=Google authentication failed')


# ============================================================================
# SSO Admin Control Routes
# ============================================================================

@auth_bp.route('/sso/status', methods=['GET'])
def get_sso_config():
    """Get SSO configuration status"""
    try:
        enabled = get_sso_status()
        return jsonify({
            'enabled': enabled,
            'microsoft_configured': bool(MICROSOFT_CLIENT_ID),
            'google_configured': bool(GOOGLE_CLIENT_ID)
        })
    except Exception as e:
        logger.error(f"Error getting SSO status: {e}")
        return jsonify({'error': 'Failed to get SSO status'}), 500


@auth_bp.route('/sso/toggle', methods=['POST'])
def toggle_sso():
    """Toggle SSO enabled/disabled (Admin only)"""
    try:
        # Check if user is authenticated and is admin
        if not session.get('authenticated'):
            return jsonify({'error': 'Not authenticated'}), 401
        
        if not session.get('is_admin') and session.get('user_type') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        enabled = data.get('enabled', True)
        
        if set_sso_status(enabled):
            logger.info(f"SSO toggled to {enabled} by {session.get('username')}")
            return jsonify({
                'success': True,
                'enabled': enabled,
                'message': f"SSO {'enabled' if enabled else 'disabled'} successfully"
            })
        else:
            return jsonify({'error': 'Failed to update SSO status'}), 500
            
    except Exception as e:
        logger.error(f"Error toggling SSO: {e}")
        return jsonify({'error': 'Failed to toggle SSO'}), 500