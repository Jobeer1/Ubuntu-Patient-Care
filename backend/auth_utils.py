from flask import request, jsonify, current_app
from functools import wraps
import jwt
import bcrypt
from datetime import datetime, timedelta
from .models import User

def generate_user_code():
    """Generate a random 10-digit code"""
    import random
    return str(random.randint(1000000000, 9999999999))

def hash_pin(pin):
    """Hash PIN with bcrypt"""
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt(rounds=12)).decode()

def verify_pin(pin, pin_hash):
    """Verify PIN against hash"""
    return bcrypt.checkpw(pin.encode(), pin_hash.encode())

def create_token(user_id, expires_in=86400):
    """Create JWT token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(seconds=expires_in),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['user_id']
    except:
        return None

def get_current_user():
    """Get current user from token"""
    token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return None
    return verify_token(token)

def require_auth(f):
    """Decorator to require JWT token authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Unauthorized - valid token required'}), 401
        
        current_user = User.query.get(user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        return f(current_user, *args, **kwargs)
    return decorated_function
