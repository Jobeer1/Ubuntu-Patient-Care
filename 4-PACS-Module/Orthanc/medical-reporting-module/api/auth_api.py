#!/usr/bin/env python3
"""
Authentication API for Medical STT System
Handles user authentication, session management, and POPIA compliance
"""

import logging
from flask import Blueprint, request, jsonify, session
from core.user_manager import UserManager, require_auth, get_current_user_id
from core.popia_compliance import POPIACompliance
from models.database import db

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register_user():
    """Register new user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        role = data.get('role', 'doctor')
        
        # Validation
        if not username or len(username) < 3:
            return jsonify({"error": "Username must be at least 3 characters"}), 400
        
        if not email or '@' not in email:
            return jsonify({"error": "Valid email address required"}), 400
        
        if not password or len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        
        # Create user
        user, error = UserManager.create_user(username, email, password, role)
        if not user:
            return jsonify({"error": error}), 400
        
        logger.info(f"User registered: {username}")
        
        return jsonify({
            "success": True,
            "message": "User registered successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({"error": "Registration failed"}), 500

@auth_bp.route("/login", methods=["POST"])
def login_user():
    """Authenticate user and create session"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400
        
        # Authenticate user
        user, error = UserManager.authenticate_user(username, password)
        if not user:
            return jsonify({"error": error}), 401
        
        # Create session
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        user_session = UserManager.create_session(user.id, ip_address, user_agent)
        if not user_session:
            return jsonify({"error": "Failed to create session"}), 500
        
        # Store session in Flask session
        session['session_id'] = user_session.id
        session['user_id'] = user.id
        
        logger.info(f"User logged in: {username}")
        
        return jsonify({
            "success": True,
            "message": "Login successful",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            },
            "session": {
                "id": user_session.id,
                "created_at": user_session.created_at.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"error": "Login failed"}), 500

@auth_bp.route("/logout", methods=["POST"])
@require_auth
def logout_user():
    """End user session"""
    try:
        session_id = session.get('session_id')
        if session_id:
            UserManager.end_session(session_id)
        
        # Clear Flask session
        session.clear()
        
        logger.info("User logged out")
        
        return jsonify({
            "success": True,
            "message": "Logout successful"
        })
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"error": "Logout failed"}), 500

@auth_bp.route("/profile", methods=["GET"])
@require_auth
def get_user_profile():
    """Get current user profile"""
    try:
        user = UserManager.get_current_user()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get consent status
        consent_status = POPIACompliance.get_consent_status(user.id)
        
        return jsonify({
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None
            },
            "consent": consent_status
        })
        
    except Exception as e:
        logger.error(f"Profile error: {e}")
        return jsonify({"error": "Failed to get profile"}), 500

@auth_bp.route("/profile", methods=["PUT"])
@require_auth
def update_user_profile():
    """Update user profile"""
    try:
        user = UserManager.get_current_user()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Update allowed fields
        if 'email' in data:
            new_email = data['email'].strip()
            if '@' not in new_email:
                return jsonify({"error": "Valid email required"}), 400
            user.email = new_email
        
        # Update password if provided
        if 'password' in data:
            new_password = data['password']
            if len(new_password) < 6:
                return jsonify({"error": "Password must be at least 6 characters"}), 400
            
            password_hash, salt = UserManager.hash_password(new_password)
            user.password_hash = password_hash
            user.salt = salt
        
        db.session.commit()
        
        logger.info(f"Profile updated for user: {user.username}")
        
        return jsonify({
            "success": True,
            "message": "Profile updated successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Profile update error: {e}")
        return jsonify({"error": "Failed to update profile"}), 500

@auth_bp.route("/consent", methods=["POST"])
@require_auth
def update_consent():
    """Update user consent for data processing"""
    try:
        user_id = get_current_user_id()
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        consent_granted = data.get('consent_granted', False)
        retention_years = data.get('retention_years', 7)
        
        success = POPIACompliance.update_user_consent(user_id, consent_granted, retention_years)
        if not success:
            return jsonify({"error": "Failed to update consent"}), 500
        
        return jsonify({
            "success": True,
            "message": "Consent updated successfully",
            "consent": POPIACompliance.get_consent_status(user_id)
        })
        
    except Exception as e:
        logger.error(f"Consent update error: {e}")
        return jsonify({"error": "Failed to update consent"}), 500

@auth_bp.route("/data-export", methods=["GET"])
@require_auth
def export_user_data():
    """Export user data for POPIA compliance"""
    try:
        user_id = get_current_user_id()
        format_type = request.args.get('format', 'json').lower()
        
        if format_type not in ['json', 'csv']:
            return jsonify({"error": "Format must be 'json' or 'csv'"}), 400
        
        exported_data = POPIACompliance.export_user_data(user_id, format_type)
        if not exported_data:
            return jsonify({"error": "Failed to export data"}), 500
        
        # Set appropriate content type
        if format_type == 'json':
            return jsonify({
                "success": True,
                "data": exported_data,
                "format": format_type
            })
        else:
            from flask import Response
            return Response(
                exported_data,
                mimetype='text/csv',
                headers={"Content-disposition": f"attachment; filename=user_data_{user_id}.csv"}
            )
        
    except Exception as e:
        logger.error(f"Data export error: {e}")
        return jsonify({"error": "Failed to export data"}), 500

@auth_bp.route("/data-summary", methods=["GET"])
@require_auth
def get_data_summary():
    """Get summary of user's stored data"""
    try:
        user_id = get_current_user_id()
        summary = POPIACompliance.get_user_data_summary(user_id)
        
        if not summary:
            return jsonify({"error": "Failed to get data summary"}), 500
        
        return jsonify({
            "success": True,
            "summary": summary
        })
        
    except Exception as e:
        logger.error(f"Data summary error: {e}")
        return jsonify({"error": "Failed to get data summary"}), 500

@auth_bp.route("/delete-data", methods=["DELETE"])
@require_auth
def delete_user_data():
    """Delete user data categories"""
    try:
        user_id = get_current_user_id()
        data = request.get_json() or {}
        
        categories = data.get('categories', [
            'training_sessions', 'voice_shortcuts', 'shortcut_usage',
            'training_progress', 'sessions', 'audio_files'
        ])
        
        deleted_items = POPIACompliance.delete_user_data(user_id, categories)
        if deleted_items is None:
            return jsonify({"error": "Failed to delete data"}), 500
        
        return jsonify({
            "success": True,
            "message": "Data deleted successfully",
            "deleted_items": deleted_items
        })
        
    except Exception as e:
        logger.error(f"Data deletion error: {e}")
        return jsonify({"error": "Failed to delete data"}), 500

@auth_bp.route("/anonymize", methods=["POST"])
@require_auth
def anonymize_user_data():
    """Anonymize user data while preserving research value"""
    try:
        user_id = get_current_user_id()
        
        success = POPIACompliance.anonymize_user_data(user_id)
        if not success:
            return jsonify({"error": "Failed to anonymize data"}), 500
        
        # End current session since user is now anonymized
        session_id = session.get('session_id')
        if session_id:
            UserManager.end_session(session_id)
        session.clear()
        
        return jsonify({
            "success": True,
            "message": "Data anonymized successfully. You have been logged out."
        })
        
    except Exception as e:
        logger.error(f"Data anonymization error: {e}")
        return jsonify({"error": "Failed to anonymize data"}), 500

@auth_bp.route("/session/validate", methods=["GET"])
def validate_session():
    """Validate current session"""
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({"valid": False, "error": "No session"}), 401
        
        user_session, error = UserManager.validate_session(session_id)
        if error or not user_session:
            session.clear()
            return jsonify({"valid": False, "error": error}), 401
        
        return jsonify({
            "valid": True,
            "session": {
                "id": user_session.id,
                "user_id": user_session.user_id,
                "last_activity": user_session.last_activity.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return jsonify({"valid": False, "error": "Validation failed"}), 500

# Demo mode endpoints (for development/testing)
@auth_bp.route("/demo/login", methods=["POST"])
def demo_login():
    """Demo login for development/testing"""
    try:
        from core.user_manager import ensure_demo_user
        
        demo_user = ensure_demo_user()
        if not demo_user:
            return jsonify({"error": "Demo user not available"}), 500
        
        # Create demo session
        session['demo_user_id'] = demo_user.id
        session['user_id'] = demo_user.id
        
        return jsonify({
            "success": True,
            "message": "Demo login successful",
            "user": {
                "id": demo_user.id,
                "username": demo_user.username,
                "role": demo_user.role
            },
            "demo_mode": True
        })
        
    except Exception as e:
        logger.error(f"Demo login error: {e}")
        return jsonify({"error": "Demo login failed"}), 500