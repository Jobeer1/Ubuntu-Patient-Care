"""
Authentication decorators and utilities for the South African Medical Imaging System
"""

from functools import wraps
from flask import session, jsonify
import logging

logger = logging.getLogger(__name__)

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        if not session.get('is_admin', False):
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get current user from session"""
    if 'user_id' not in session:
        return None
    
    return {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'is_admin': session.get('is_admin', False)
    }

def is_authenticated():
    """Check if current user is authenticated"""
    return 'user_id' in session

def is_admin():
    """Check if current user is admin"""
    return session.get('is_admin', False)
