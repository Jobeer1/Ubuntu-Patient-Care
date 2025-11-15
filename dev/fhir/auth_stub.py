"""
P1-FHIR-003: OAuth2 Authentication Stub for Development

Simple token-based auth for FHIR dev server testing.
DO NOT USE IN PRODUCTION - This is for development only!

Usage:
    python auth_stub.py
    
    Then use token in requests:
    curl -H "Authorization: Bearer dev-token-12345" http://localhost:8080/fhir/Patient
"""

from flask import Flask, request, jsonify
import secrets
import time
from datetime import datetime, timedelta

app = Flask(__name__)

# In-memory token store (dev only!)
TOKENS = {}
TOKEN_EXPIRY = 3600  # 1 hour

def generate_token():
    """Generate a random dev token"""
    return f"dev-token-{secrets.token_urlsafe(16)}"

def is_valid_token(token):
    """Check if token is valid and not expired"""
    if token not in TOKENS:
        return False
    
    expiry = TOKENS[token]['expires_at']
    return datetime.now() < expiry

@app.route('/auth/token', methods=['POST'])
def get_token():
    """
    Get an access token (dev stub)
    
    POST /auth/token
    {
        "username": "dev",
        "password": "dev"
    }
    
    Returns:
    {
        "access_token": "dev-token-...",
        "token_type": "Bearer",
        "expires_in": 3600
    }
    """
    data = request.get_json() or {}
    
    # Dev credentials (accept anything in dev mode)
    username = data.get('username', 'dev')
    password = data.get('password', 'dev')
    
    # Generate token
    token = generate_token()
    expires_at = datetime.now() + timedelta(seconds=TOKEN_EXPIRY)
    
    TOKENS[token] = {
        'username': username,
        'created_at': datetime.now(),
        'expires_at': expires_at
    }
    
    return jsonify({
        'access_token': token,
        'token_type': 'Bearer',
        'expires_in': TOKEN_EXPIRY,
        'scope': 'read write'
    })

@app.route('/auth/validate', methods=['POST'])
def validate_token():
    """
    Validate a token
    
    POST /auth/validate
    Authorization: Bearer <token>
    
    Returns:
    {
        "valid": true,
        "username": "dev",
        "expires_in": 3456
    }
    """
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return jsonify({'valid': False, 'error': 'Missing or invalid Authorization header'}), 401
    
    token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    if not is_valid_token(token):
        return jsonify({'valid': False, 'error': 'Invalid or expired token'}), 401
    
    token_data = TOKENS[token]
    expires_in = int((token_data['expires_at'] - datetime.now()).total_seconds())
    
    return jsonify({
        'valid': True,
        'username': token_data['username'],
        'expires_in': expires_in
    })

@app.route('/auth/revoke', methods=['POST'])
def revoke_token():
    """
    Revoke a token
    
    POST /auth/revoke
    Authorization: Bearer <token>
    """
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid Authorization header'}), 401
    
    token = auth_header[7:]
    
    if token in TOKENS:
        del TOKENS[token]
        return jsonify({'message': 'Token revoked'})
    
    return jsonify({'error': 'Token not found'}), 404

@app.route('/auth/tokens', methods=['GET'])
def list_tokens():
    """List all active tokens (dev only!)"""
    active_tokens = []
    now = datetime.now()
    
    for token, data in TOKENS.items():
        if data['expires_at'] > now:
            active_tokens.append({
                'token': token[:20] + '...',  # Truncate for display
                'username': data['username'],
                'created_at': data['created_at'].isoformat(),
                'expires_at': data['expires_at'].isoformat(),
                'expires_in': int((data['expires_at'] - now).total_seconds())
            })
    
    return jsonify({
        'active_tokens': len(active_tokens),
        'tokens': active_tokens
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'auth-stub',
        'active_tokens': len([t for t, d in TOKENS.items() if d['expires_at'] > datetime.now()])
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🔐 OAuth2 Auth Stub Server (DEV ONLY)")
    print("=" * 60)
    print("\nEndpoints:")
    print("  POST   /auth/token      - Get access token")
    print("  POST   /auth/validate   - Validate token")
    print("  POST   /auth/revoke     - Revoke token")
    print("  GET    /auth/tokens     - List active tokens")
    print("  GET    /health          - Health check")
    print("\nExample:")
    print('  curl -X POST http://localhost:5000/auth/token \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"username":"dev","password":"dev"}\'')
    print("\n⚠️  WARNING: This is for DEVELOPMENT ONLY!")
    print("    DO NOT use in production!")
    print("=" * 60)
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
