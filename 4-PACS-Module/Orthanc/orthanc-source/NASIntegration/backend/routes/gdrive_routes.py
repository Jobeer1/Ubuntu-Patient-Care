"""
Google Drive Integration Routes
Handles Google Drive OAuth and file upload functionality
"""
import os
import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, redirect, render_template
import requests

logger = logging.getLogger(__name__)

gdrive_bp = Blueprint('gdrive', __name__, url_prefix='/api/nas/gdrive')

# Configuration
GDRIVE_CLIENT_ID = os.getenv('GDRIVE_CLIENT_ID', '')
GDRIVE_CLIENT_SECRET = os.getenv('GDRIVE_CLIENT_SECRET', '')
GDRIVE_REDIRECT_URI = os.getenv('GDRIVE_REDIRECT_URI', 'http://localhost:5000/api/nas/gdrive/callback')
GDRIVE_SCOPES = 'https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/userinfo.email'

# Token storage path
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '..', 'instance', 'gdrive_token.json')

def load_token():
    """Load Google Drive token from file"""
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load Google Drive token: {e}")
    return None

def save_token(token_data):
    """Save Google Drive token to file"""
    try:
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f, indent=2)
        logger.info("Google Drive token saved successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to save Google Drive token: {e}")
        return False

def is_token_valid(token_data):
    """Check if token is still valid"""
    if not token_data or 'expires_at' not in token_data:
        return False
    try:
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        return datetime.now() < expires_at
    except:
        return False

def refresh_access_token(refresh_token):
    """Refresh the access token using refresh token"""
    try:
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'client_id': GDRIVE_CLIENT_ID,
            'client_secret': GDRIVE_CLIENT_SECRET,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        token_response = response.json()
        
        # Calculate new expiration
        expires_in = token_response.get('expires_in', 3600)
        expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
        
        return {
            'access_token': token_response['access_token'],
            'expires_at': expires_at
        }
    except Exception as e:
        logger.error(f"Failed to refresh Google Drive token: {e}")
        return None

@gdrive_bp.route('/config', methods=['GET'])
def get_config():
    """Get Google Drive configuration status"""
    configured = bool(GDRIVE_CLIENT_ID and GDRIVE_CLIENT_SECRET)
    return jsonify({
        'configured': configured,
        'redirect_uri': GDRIVE_REDIRECT_URI,
        'client_id_set': bool(GDRIVE_CLIENT_ID)
    })

@gdrive_bp.route('/status', methods=['GET'])
def get_status():
    """Get Google Drive connection status"""
    # Check for MCP token in query params (from MCP server redirect)
    mcp_token = request.args.get('mcp_token')
    if mcp_token:
        try:
            import jwt
            decoded = jwt.decode(mcp_token, options={"verify_signature": False})
            email = decoded.get('email', 'unknown')
            name = decoded.get('name', 'unknown')
            exp = decoded.get('exp', 0)
            
            expires_at = datetime.fromtimestamp(exp).isoformat() if exp else 'n/a'
            
            token_storage = {
                'mcp_token': mcp_token,
                'access_token': None,
                'expires_at': expires_at,
                'account_email': email,
                'account_name': name,
                'source': 'mcp'
            }
            save_token(token_storage)
            
            return jsonify({
                'connected': True,
                'account_email': email,
                'expires_at': expires_at,
                'source': 'mcp'
            })
        except Exception as e:
            logger.error(f"Failed to decode MCP token: {e}")
    
    # Check stored token
    token_data = load_token()
    
    if token_data:
        # If we have MCP token but no Google Drive token
        if token_data.get('source') == 'mcp' and not token_data.get('access_token'):
            return jsonify({
                'connected': True,
                'account_email': token_data.get('account_email', 'unknown'),
                'expires_at': token_data.get('expires_at', 'n/a'),
                'needs_gdrive': True,
                'message': 'Authenticated via MCP. Click "Connect Google Drive" to link your Google Drive account.'
            })
        
        # Check if token needs refresh
        if not is_token_valid(token_data) and token_data.get('refresh_token'):
            refreshed = refresh_access_token(token_data['refresh_token'])
            if refreshed:
                token_data.update(refreshed)
                save_token(token_data)
        
        if is_token_valid(token_data):
            return jsonify({
                'connected': True,
                'account_email': token_data.get('account_email', 'unknown'),
                'expires_at': token_data.get('expires_at', 'n/a')
            })
    
    return jsonify({
        'connected': False,
        'account_email': None,
        'expires_at': None
    })

@gdrive_bp.route('/login', methods=['GET'])
def login():
    """Initiate Google Drive OAuth flow"""
    if not GDRIVE_CLIENT_ID:
        return jsonify({'error': 'Google Drive client not configured'}), 400
    
    # Google OAuth authorization URL
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GDRIVE_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={GDRIVE_REDIRECT_URI}"
        f"&scope={GDRIVE_SCOPES}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    
    return redirect(auth_url)

@gdrive_bp.route('/callback', methods=['GET'])
def callback():
    """Handle Google Drive OAuth callback"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        logger.error(f"Google Drive OAuth error: {error}")
        return f"Google Drive authentication failed: {error}", 400
    
    if not code:
        return "No authorization code received", 400
    
    # Exchange code for token
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        'client_id': GDRIVE_CLIENT_ID,
        'client_secret': GDRIVE_CLIENT_SECRET,
        'code': code,
        'redirect_uri': GDRIVE_REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    
    try:
        response = requests.post(token_url, data=token_data)
        response.raise_for_status()
        token_response = response.json()
        
        # Get user info
        access_token = token_response['access_token']
        user_info = get_user_info(access_token)
        
        # Calculate expiration
        expires_in = token_response.get('expires_in', 3600)
        expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
        
        # Save token
        token_storage = {
            'access_token': access_token,
            'refresh_token': token_response.get('refresh_token'),
            'expires_at': expires_at,
            'account_email': user_info.get('email', 'unknown'),
            'account_name': user_info.get('name', 'unknown')
        }
        
        save_token(token_storage)
        
        logger.info(f"Google Drive connected successfully for {token_storage['account_email']}")
        
        # Redirect back to patients page
        return redirect('/patients')
        
    except Exception as e:
        logger.error(f"Failed to exchange Google Drive code for token: {e}")
        return f"Failed to connect Google Drive: {str(e)}", 500

def get_user_info(access_token):
    """Get user information from Google API"""
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        return {}

@gdrive_bp.route('/disconnect', methods=['POST'])
def disconnect():
    """Disconnect Google Drive"""
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        logger.info("Google Drive disconnected")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Failed to disconnect Google Drive: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@gdrive_bp.route('/manual_token', methods=['POST'])
def manual_token():
    """Save manually provided access token (for testing)"""
    try:
        data = request.json
        access_token = data.get('access_token', '').strip()
        
        if not access_token:
            return jsonify({'success': False, 'error': 'No token provided'}), 400
        
        # Try to get user info to validate token
        user_info = get_user_info(access_token)
        
        # Save token (expires in 1 hour by default)
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
        token_storage = {
            'access_token': access_token,
            'expires_at': expires_at,
            'account_email': user_info.get('email', 'manual'),
            'account_name': user_info.get('name', 'Manual Token')
        }
        
        save_token(token_storage)
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Failed to save manual token: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@gdrive_bp.route('/upload', methods=['POST'])
def upload_file():
    """Upload a file to Google Drive"""
    token_data = load_token()
    
    if not token_data or not is_token_valid(token_data):
        return jsonify({'success': False, 'error': 'Not connected to Google Drive'}), 401
    
    try:
        # Get file from request
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        filename = file.filename
        
        # Upload to Google Drive
        access_token = token_data['access_token']
        
        # Step 1: Create file metadata
        metadata = {
            'name': filename,
            'mimeType': 'application/octet-stream'
        }
        
        # Step 2: Upload file
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        files = {
            'data': ('metadata', json.dumps(metadata), 'application/json; charset=UTF-8'),
            'file': (filename, file.read(), 'application/octet-stream')
        }
        
        response = requests.post(
            'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart',
            headers=headers,
            files=files
        )
        response.raise_for_status()
        
        result = response.json()
        
        logger.info(f"File uploaded to Google Drive: {filename}")
        
        return jsonify({
            'success': True,
            'file_id': result.get('id'),
            'web_url': f"https://drive.google.com/file/d/{result.get('id')}/view",
            'name': result.get('name')
        })
        
    except Exception as e:
        logger.error(f"Failed to upload to Google Drive: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@gdrive_bp.route('/setup', methods=['GET'])
def setup_page():
    """Render Google Drive setup page"""
    return render_template('gdrive_setup.html')
