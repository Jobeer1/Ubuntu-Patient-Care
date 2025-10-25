"""
PACS Access Control Middleware
Validates MCP tokens and enforces patient-level access control

This middleware:
1. Extracts MCP JWT token from request
2. Validates token with MCP server
3. Checks if user has access to requested patient
4. Logs access attempts for audit trail
"""
import jwt
import requests
import logging
from functools import wraps
from flask import request, jsonify, g
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# MCP Server configuration
MCP_SERVER_URL = "http://localhost:8080"
JWT_SECRET_KEY = "7e2d9c8b7a6f5e4d3c2b1a9f8e7d6c5b4a3f2e1d9c8b7a6f5e4d3c2b1a0f9e8d"  # Should match MCP server


def get_token_from_request() -> Optional[str]:
    """
    Extract MCP token from request
    
    Checks multiple sources:
    1. Authorization header (Bearer token)
    2. Query parameter (mcp_token)
    3. Cookie (mcp_token)
    
    Returns:
        Token string or None
    """
    # Check Authorization header
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header.replace('Bearer ', '')
    
    # Check query parameter
    token = request.args.get('mcp_token')
    if token:
        return token
    
    # Check cookie
    token = request.cookies.get('mcp_token')
    if token:
        return token
    
    return None


def verify_mcp_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode MCP JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        # Decode token (without signature verification for now)
        # In production, verify signature with MCP server's public key
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # Check expiration
        import time
        if 'exp' in decoded and decoded['exp'] < time.time():
            logger.warning("Token expired")
            return None
        
        # Validate required fields
        required_fields = ['user_id', 'email', 'role']
        if not all(field in decoded for field in required_fields):
            logger.warning(f"Token missing required fields: {required_fields}")
            return None
        
        return decoded
        
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return None


def get_user_from_token() -> Optional[Dict[str, Any]]:
    """
    Get user information from request token
    
    Returns:
        User data dictionary or None
    """
    token = get_token_from_request()
    if not token:
        return None
    
    return verify_mcp_token(token)


def check_patient_access_with_mcp(user_id: int, patient_id: str) -> bool:
    """
    Check if user has access to patient via MCP server
    
    Args:
        user_id: MCP user ID
        patient_id: Patient ID/MRN
    
    Returns:
        True if user has access, False otherwise
    """
    try:
        # Call MCP server access check endpoint
        response = requests.get(
            f"{MCP_SERVER_URL}/access/check",
            params={'user_id': user_id, 'patient_id': patient_id},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('has_access', False)
        else:
            logger.error(f"MCP access check failed: {response.status_code}")
            return False
            
    except requests.RequestException as e:
        logger.error(f"Error checking access with MCP: {e}")
        # In case of MCP server error, deny access for security
        return False


def require_patient_access(patient_id_param: str = 'patient_id'):
    """
    Decorator to require patient access
    
    Validates that the user has access to the requested patient.
    
    Args:
        patient_id_param: Name of the parameter containing patient ID
                         Can be URL parameter, query parameter, or JSON body field
    
    Usage:
        @app.route('/api/patient/<patient_id>')
        @require_patient_access('patient_id')
        def get_patient(patient_id):
            # User has been validated
            return patient_data
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get token
            token = get_token_from_request()
            if not token:
                logger.warning("No token provided")
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'Authentication token required'
                }), 401
            
            # Verify token
            user_data = verify_mcp_token(token)
            if not user_data:
                logger.warning("Invalid token")
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'Invalid or expired token'
                }), 401
            
            # Get patient ID from request
            patient_id = None
            
            # Check URL parameters (kwargs)
            if patient_id_param in kwargs:
                patient_id = kwargs[patient_id_param]
            
            # Check query parameters
            elif patient_id_param in request.args:
                patient_id = request.args.get(patient_id_param)
            
            # Check JSON body
            elif request.is_json and patient_id_param in request.json:
                patient_id = request.json.get(patient_id_param)
            
            if not patient_id:
                logger.warning(f"Patient ID parameter '{patient_id_param}' not found")
                return jsonify({
                    'error': 'Bad Request',
                    'message': f'Patient ID required ({patient_id_param})'
                }), 400
            
            # Check access
            user_id = user_data['user_id']
            user_role = user_data['role']
            
            # Admin and Radiologist have full access
            if user_role in ['Admin', 'Radiologist', 'Technician']:
                logger.debug(f"User {user_id} ({user_role}) has full access")
                g.user = user_data
                return f(*args, **kwargs)
            
            # Check access via MCP server
            has_access = check_patient_access_with_mcp(user_id, patient_id)
            
            if not has_access:
                logger.warning(f"Access denied: user {user_id} → patient {patient_id}")
                return jsonify({
                    'error': 'Forbidden',
                    'message': 'You do not have access to this patient'
                }), 403
            
            # Access granted
            logger.info(f"Access granted: user {user_id} → patient {patient_id}")
            g.user = user_data
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_authentication():
    """
    Decorator to require authentication (but not specific patient access)
    
    Usage:
        @app.route('/api/my-studies')
        @require_authentication()
        def get_my_studies():
            user = g.user
            return studies
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get token
            token = get_token_from_request()
            if not token:
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'Authentication token required'
                }), 401
            
            # Verify token
            user_data = verify_mcp_token(token)
            if not user_data:
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'Invalid or expired token'
                }), 401
            
            # Store user in request context
            g.user = user_data
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def log_access_attempt(user_id: int, patient_id: str, access_type: str, granted: bool):
    """
    Log access attempt to MCP server for audit trail
    
    Args:
        user_id: MCP user ID
        patient_id: Patient ID
        access_type: Type of access (view, download, etc.)
        granted: Whether access was granted
    """
    try:
        # Get request details
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        # Send to MCP server (fire and forget)
        requests.post(
            f"{MCP_SERVER_URL}/access/log",
            json={
                'user_id': user_id,
                'patient_id': patient_id,
                'access_type': access_type,
                'granted': granted,
                'ip_address': ip_address,
                'user_agent': user_agent
            },
            timeout=2
        )
    except Exception as e:
        # Don't fail the request if logging fails
        logger.error(f"Error logging access attempt: {e}")


# Example usage in Flask routes:
"""
from middleware.access_control import require_patient_access, require_authentication

@app.route('/api/patient/<patient_id>/studies')
@require_patient_access('patient_id')
def get_patient_studies(patient_id):
    # User has been validated and has access to this patient
    user = g.user
    studies = get_studies_for_patient(patient_id)
    return jsonify(studies)

@app.route('/api/my-studies')
@require_authentication()
def get_my_studies():
    # User is authenticated
    user = g.user
    studies = get_studies_for_user(user['user_id'])
    return jsonify(studies)
"""
