"""
Authentication bridge for Medical Reporting Module
Integrates with SA Medical System authentication
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from config.integration_config import IntegrationConfig

logger = logging.getLogger(__name__)

class AuthenticationBridge:
    """Bridge to SA Medical System authentication"""
    
    def __init__(self):
        self.sa_config = IntegrationConfig.SA_MEDICAL_CONFIG
        self.base_url = self.sa_config['url']
        self.api_key = self.sa_config['api_key']
        self.timeout = self.sa_config['timeout']
        self.session_cache = {}  # Simple in-memory session cache
    
    def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Validate session token with SA Medical System"""
        try:
            headers = {
                'Authorization': f'Bearer {session_token}',
                'Content-Type': 'application/json'
            }
            
            if self.api_key:
                headers['X-API-Key'] = self.api_key
            
            response = requests.get(
                f"{self.base_url}{self.sa_config['auth_endpoint']}",
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                user_data = response.json()
                
                # Cache session for performance
                self.session_cache[session_token] = {
                    'user_data': user_data,
                    'cached_at': datetime.utcnow(),
                    'expires_at': datetime.utcnow() + timedelta(minutes=15)
                }
                
                logger.info(f"Session validated for user: {user_data.get('username', 'unknown')}")
                return user_data
            
            elif response.status_code == 401:
                logger.warning("Invalid session token provided")
                return None
            
            else:
                logger.error(f"Session validation failed with status: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to validate session: {e}")
            
            # Check cache for offline fallback
            cached_session = self.session_cache.get(session_token)
            if cached_session and cached_session['expires_at'] > datetime.utcnow():
                logger.info("Using cached session data (offline mode)")
                return cached_session['user_data']
            
            return None
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information from SA Medical System"""
        try:
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['X-API-Key'] = self.api_key
            
            response = requests.get(
                f"{self.base_url}{self.sa_config['user_endpoint']}/{user_id}",
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get user info: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get user info: {e}")
            return None
    
    def create_reporting_session(self, user_data: Dict[str, Any]) -> str:
        """Create a reporting module session"""
        import uuid
        session_id = str(uuid.uuid4())
        
        # Store session data
        self.session_cache[session_id] = {
            'user_data': user_data,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(hours=8),
            'is_reporting_session': True
        }
        
        logger.info(f"Created reporting session for user: {user_data.get('username', 'unknown')}")
        return session_id
    
    def get_session_user(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get user data from session"""
        cached_session = self.session_cache.get(session_id)
        if cached_session and cached_session['expires_at'] > datetime.utcnow():
            return cached_session['user_data']
        return None
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session"""
        if session_id in self.session_cache:
            del self.session_cache[session_id]
            logger.info("Session invalidated")
            return True
        return False
    
    def check_permissions(self, user_data: Dict[str, Any], permission: str) -> bool:
        """Check if user has specific permission"""
        user_permissions = user_data.get('permissions', [])
        user_roles = user_data.get('roles', [])
        
        # Check direct permissions
        if permission in user_permissions:
            return True
        
        # Check role-based permissions
        role_permissions = {
            'doctor': ['create_report', 'edit_report', 'voice_dictation', 'view_images'],
            'radiologist': ['create_report', 'edit_report', 'voice_dictation', 'view_images', 'finalize_report'],
            'typist': ['edit_report', 'view_reports'],
            'admin': ['*']  # All permissions
        }
        
        for role in user_roles:
            if role in role_permissions:
                if '*' in role_permissions[role] or permission in role_permissions[role]:
                    return True
        
        return False
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, session_data in self.session_cache.items()
            if session_data['expires_at'] <= current_time
        ]
        
        for session_id in expired_sessions:
            del self.session_cache[session_id]
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

# Global authentication bridge instance
auth_bridge = AuthenticationBridge()

def require_auth(permission: str = None):
    """Decorator to require authentication for routes"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            from flask import request, jsonify, session
            
            # Get session token from header or session
            token = request.headers.get('Authorization')
            if token and token.startswith('Bearer '):
                token = token[7:]  # Remove 'Bearer ' prefix
            else:
                token = session.get('session_token')
            
            if not token:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Validate session
            user_data = auth_bridge.validate_session(token)
            if not user_data:
                return jsonify({'error': 'Invalid session'}), 401
            
            # Check permissions if specified
            if permission and not auth_bridge.check_permissions(user_data, permission):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            # Add user data to request context
            request.current_user = user_data
            
            return f(*args, **kwargs)
        
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator