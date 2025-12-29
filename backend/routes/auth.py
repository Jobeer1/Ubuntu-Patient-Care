from flask import Blueprint, request, jsonify
from datetime import datetime
from ..extensions import db
from ..models import User
from ..auth_utils import generate_user_code, hash_pin, verify_pin, create_token, get_current_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register new user"""
    # ensure_db_initialized() is handled by app startup
    user_code = generate_user_code()
    return jsonify({
        'status': 'success',
        'user_id': user_code,
        'needs_alias': True
    }), 201

@auth_bp.route('/set-alias', methods=['POST'])
def set_alias():
    """Set user alias"""
    data = request.json
    user_code = data.get('user_id')
    alias = data.get('alias', '').strip()
    
    if not alias or len(alias) < 3 or len(alias) > 50:
        return jsonify({'error': 'Alias must be 3-50 characters'}), 400
    
    if User.query.filter_by(alias=alias).first():
        return jsonify({'error': 'Alias already taken'}), 400
    
    # Check if user exists, if not create placeholder with NULL pin_hash
    try:
        user = User.query.get(user_code)
        if not user:
            # Create new user with nullable pin_hash
            user = User(user_id=user_code, alias=alias, pin_hash=None)
            db.session.add(user)
        else:
            # Update existing user
            user.alias = alias
        
        db.session.commit()
        return jsonify({'status': 'success', 'alias': alias}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in set_alias: {str(e)}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@auth_bp.route('/set-pin', methods=['POST'])
def set_pin():
    """Set user PIN"""
    data = request.json
    user_code = data.get('user_id')
    pin = data.get('pin', '')
    
    if not pin or len(pin) < 4 or len(pin) > 8 or not pin.isdigit():
        return jsonify({'error': 'PIN must be 4-8 digits'}), 400
    
    user = User.query.get(user_code)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.pin_hash = hash_pin(pin)
    db.session.commit()
    
    return jsonify({'status': 'success'}), 200

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    data = request.json
    user_code = data.get('user_id', '')
    pin = data.get('pin', '')
    
    user = User.query.get(user_code)
    if not user or not verify_pin(pin, user.pin_hash):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    token = create_token(user_code)
    return jsonify({
        'status': 'success',
        'token': token,
        'alias': user.alias,
        'user_id': user_code
    }), 200

@auth_bp.route('/profile', methods=['GET'])
def profile():
    """Get user profile"""
    user_id = get_current_user()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user_id': user.user_id,
        'alias': user.alias,
        'code_visible': user.code_visible,
        'created_at': user.created_at.isoformat()
    }), 200
