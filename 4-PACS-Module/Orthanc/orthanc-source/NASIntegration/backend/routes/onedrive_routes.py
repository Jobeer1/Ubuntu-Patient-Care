"""
OneDrive Integration Routes
Handles Microsoft OneDrive OAuth and file upload functionality
"""
import os
import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, redirect, session, render_template
import requests

logger = logging.getLogger(__name__)

onedrive_bp = Blueprint('onedrive', __name__, url_prefix='/api/nas/onedrive')

# Configuration
ONEDRIVE_CLIENT_ID = os.getenv('ONEDRIVE_CLIENT_ID', '')
ONEDRIVE_CLIENT_SECRET = os.getenv('ONEDRIVE_CLIENT_SECRET', '')
ONEDRIVE_REDIRECT_URI = os.getenv('ONEDRIVE_REDIRECT_URI', 'http://localhost:5000/api/nas/onedrive/callback')
ONEDRIVE_TENANT_ID = os.getenv('ONEDRIVE_TENANT_ID', 'common')  # Use 'common' for multi-tenant or specific tenant ID
ONEDRIVE_SCOPES = 'Files.ReadWrite.All offline_access User.Read'

# Token storage path
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '..', 'instance', 'onedrive_token.json')

def load_token():
    """Load OneDrive token from file"""
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load OneDrive token: {e}")
    return None

def save_token(token_data):
    """Save OneDrive token to file"""
    try:
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f, indent=2)
        logger.info("OneDrive token saved successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to save OneDrive token: {e}")
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

@onedrive_bp.route('/config', methods=['GET'])
def get_config():
    """Get OneDrive configuration status"""
    configured = bool(ONEDRIVE_CLIENT_ID and ONEDRIVE_CLIENT_SECRET)
    return jsonify({
        'configured': configured,
        'redirect_uri': ONEDRIVE_REDIRECT_URI,
        'client_id_set': bool(ONEDRIVE_CLIENT_ID)
    })

@onedrive_bp.route('/status', methods=['GET'])
def get_status():
    """Get OneDrive connection status"""
    # Check for MCP token in query params (from MCP server redirect)
    mcp_token = request.args.get('mcp_token')
    if mcp_token:
        # Decode and use MCP token to get user info
        try:
            import jwt
            decoded = jwt.decode(mcp_token, options={"verify_signature": False})
            email = decoded.get('email', 'unknown')
            name = decoded.get('name', 'unknown')
            exp = decoded.get('exp', 0)
            
            # Convert exp timestamp to ISO format
            from datetime import datetime
            expires_at = datetime.fromtimestamp(exp).isoformat() if exp else 'n/a'
            
            # Save this as a connected state
            token_storage = {
                'mcp_token': mcp_token,
                'access_token': None,  # We don't have OneDrive token yet
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
        # If we have MCP token but no OneDrive token, show as partially connected
        if token_data.get('source') == 'mcp' and not token_data.get('access_token'):
            return jsonify({
                'connected': True,
                'account_email': token_data.get('account_email', 'unknown'),
                'expires_at': token_data.get('expires_at', 'n/a'),
                'needs_onedrive': True,
                'message': 'Authenticated via MCP. Click "Connect OneDrive" to link your OneDrive account.'
            })
        
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

@onedrive_bp.route('/login', methods=['GET'])
def login():
    """Initiate OneDrive OAuth flow"""
    if not ONEDRIVE_CLIENT_ID:
        return jsonify({'error': 'OneDrive client not configured'}), 400
    
    # Microsoft OAuth authorization URL (use tenant ID if configured)
    auth_url = (
        f"https://login.microsoftonline.com/{ONEDRIVE_TENANT_ID}/oauth2/v2.0/authorize"
        f"?client_id={ONEDRIVE_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={ONEDRIVE_REDIRECT_URI}"
        f"&scope={ONEDRIVE_SCOPES}"
        f"&response_mode=query"
    )
    
    return redirect(auth_url)

@onedrive_bp.route('/callback', methods=['GET'])
def callback():
    """Handle OneDrive OAuth callback"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        logger.error(f"OneDrive OAuth error: {error}")
        return f"OneDrive authentication failed: {error}", 400
    
    if not code:
        return "No authorization code received", 400
    
    # Exchange code for token (use tenant ID if configured)
    token_url = f"https://login.microsoftonline.com/{ONEDRIVE_TENANT_ID}/oauth2/v2.0/token"
    token_data = {
        'client_id': ONEDRIVE_CLIENT_ID,
        'client_secret': ONEDRIVE_CLIENT_SECRET,
        'code': code,
        'redirect_uri': ONEDRIVE_REDIRECT_URI,
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
            'account_email': user_info.get('userPrincipalName', 'unknown'),
            'account_name': user_info.get('displayName', 'unknown')
        }
        
        save_token(token_storage)
        
        logger.info(f"OneDrive connected successfully for {token_storage['account_email']}")
        
        # Redirect back to patients page
        return redirect('/patients')
        
    except Exception as e:
        logger.error(f"Failed to exchange OneDrive code for token: {e}")
        return f"Failed to connect OneDrive: {str(e)}", 500

def get_user_info(access_token):
    """Get user information from Microsoft Graph API"""
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        return {}

@onedrive_bp.route('/disconnect', methods=['POST'])
def disconnect():
    """Disconnect OneDrive"""
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        logger.info("OneDrive disconnected")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Failed to disconnect OneDrive: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@onedrive_bp.route('/manual_token', methods=['POST'])
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
            'account_email': user_info.get('userPrincipalName', 'manual'),
            'account_name': user_info.get('displayName', 'Manual Token')
        }
        
        save_token(token_storage)
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Failed to save manual token: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@onedrive_bp.route('/upload', methods=['POST'])
def upload_file():
    """Upload a file to OneDrive"""
    token_data = load_token()
    
    if not token_data or not is_token_valid(token_data):
        return jsonify({'success': False, 'error': 'Not connected to OneDrive'}), 401
    
    try:
        # Get file from request
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        filename = file.filename
        
        # Upload to OneDrive
        access_token = token_data['access_token']
        upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{filename}:/content"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/octet-stream'
        }
        
        response = requests.put(upload_url, headers=headers, data=file.read())
        response.raise_for_status()
        
        result = response.json()
        
        logger.info(f"File uploaded to OneDrive: {filename}")
        
        return jsonify({
            'success': True,
            'file_id': result.get('id'),
            'web_url': result.get('webUrl'),
            'name': result.get('name')
        })
        
    except Exception as e:
        logger.error(f"Failed to upload to OneDrive: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@onedrive_bp.route('/setup', methods=['GET'])
def setup_page():
    """Render OneDrive setup page"""
    return render_template('onedrive_setup.html')
