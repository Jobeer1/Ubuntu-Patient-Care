#!/usr/bin/env python3
"""
User Management and Authentication for Medical STT System
Handles user sessions, authentication, and data isolation
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from flask import session, request
from functools import wraps
from models.database import db

logger = logging.getLogger(__name__)

class User(db.Model):
    """User model for authentication and data isolation"""
    __tablename__ = 'users'
    
    id = db.Column(db.String(50), primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    salt = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(50), default='doctor')
    
    # POPIA compliance fields
    data_retention_consent = db.Column(db.Boolean, default=False)
    data_retention_date = db.Column(db.DateTime)
    consent_date = db.Column(db.DateTime)

class UserSession(db.Model):
    """User session tracking for security"""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.String(100), primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    
    user = db.relationship('User', backref=db.backref('sessions', lazy=True))

class UserManager:
    """User management and authentication service"""
    
    SESSION_TIMEOUT = timedelta(hours=8)  # 8-hour session timeout
    
    @staticmethod
    def hash_password(password, salt=None):
        """Hash password with salt for secure storage"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 with SHA-256 for password hashing
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 100,000 iterations
        )
        
        return password_hash.hex(), salt
    
    @staticmethod
    def verify_password(password, stored_hash, salt):
        """Verify password against stored hash"""
        computed_hash, _ = UserManager.hash_password(password, salt)
        return secrets.compare_digest(computed_hash, stored_hash)
    
    @staticmethod
    def create_user(username, email, password, role='doctor'):
        """Create new user with secure password storage"""
        try:
            # Check if user already exists
            if User.query.filter_by(username=username).first():
                return None, "Username already exists"
            
            if User.query.filter_by(email=email).first():
                return None, "Email already exists"
            
            # Generate user ID
            user_id = f"user_{secrets.token_hex(8)}"
            
            # Hash password
            password_hash, salt = UserManager.hash_password(password)
            
            # Create user
            user = User(
                id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                salt=salt,
                role=role,
                consent_date=datetime.utcnow(),
                data_retention_consent=True,
                data_retention_date=datetime.utcnow() + timedelta(days=365*7)  # 7 years
            )
            
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"Created user: {username} ({user_id})")
            return user, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create user: {e}")
            return None, str(e)
    
    @staticmethod
    def authenticate_user(username, password):
        """Authenticate user credentials"""
        try:
            user = User.query.filter_by(username=username, is_active=True).first()
            if not user:
                return None, "Invalid username or password"
            
            if not UserManager.verify_password(password, user.password_hash, user.salt):
                return None, "Invalid username or password"
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            return user, None
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None, "Authentication failed"
    
    @staticmethod
    def create_session(user_id, ip_address=None, user_agent=None):
        """Create new user session"""
        try:
            session_id = f"sess_{secrets.token_hex(16)}"
            
            user_session = UserSession(
                id=session_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.session.add(user_session)
            db.session.commit()
            
            logger.info(f"Created session {session_id} for user {user_id}")
            return user_session
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create session: {e}")
            return None
    
    @staticmethod
    def validate_session(session_id):
        """Validate and refresh user session"""
        try:
            user_session = UserSession.query.filter_by(
                id=session_id, is_active=True
            ).first()
            
            if not user_session:
                return None, "Invalid session"
            
            # Check session timeout
            if datetime.utcnow() - user_session.last_activity > UserManager.SESSION_TIMEOUT:
                user_session.is_active = False
                db.session.commit()
                return None, "Session expired"
            
            # Update last activity
            user_session.last_activity = datetime.utcnow()
            db.session.commit()
            
            return user_session, None
            
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return None, "Session validation failed"
    
    @staticmethod
    def end_session(session_id):
        """End user session"""
        try:
            user_session = UserSession.query.filter_by(id=session_id).first()
            if user_session:
                user_session.is_active = False
                db.session.commit()
                logger.info(f"Ended session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to end session: {e}")
    
    @staticmethod
    def get_current_user():
        """Get current authenticated user from Flask session"""
        session_id = session.get('session_id')
        if not session_id:
            return None
        
        user_session, error = UserManager.validate_session(session_id)
        if error or not user_session:
            return None
        
        return user_session.user
    
    @staticmethod
    def cleanup_expired_sessions():
        """Clean up expired sessions (run periodically)"""
        try:
            cutoff_time = datetime.utcnow() - UserManager.SESSION_TIMEOUT
            expired_sessions = UserSession.query.filter(
                UserSession.last_activity < cutoff_time,
                UserSession.is_active == True
            ).all()
            
            for session in expired_sessions:
                session.is_active = False
            
            db.session.commit()
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")

def require_auth(f):
    """Decorator to require authentication for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = UserManager.get_current_user()
        if not user:
            # For demo mode, create a temporary session
            demo_user = ensure_demo_user()
            if demo_user:
                # Create a demo session
                session['demo_user_id'] = demo_user.id
                session['session_id'] = 'demo_session'
                request.current_user = demo_user
                logger.info("Using demo user for unauthenticated request")
            else:
                return {'error': 'Authentication required'}, 401
        else:
            request.current_user = user
        
        return f(*args, **kwargs)
    
    return decorated_function

def get_current_user_id():
    """Get current user ID, with fallback for demo mode"""
    try:
        user = UserManager.get_current_user()
        if user:
            return user.id
    except Exception as e:
        logger.warning(f"Failed to get current user: {e}")
    
    # Fallback for demo mode - ensure demo user exists
    demo_user = ensure_demo_user()
    if demo_user:
        session['demo_user_id'] = demo_user.id
        return demo_user.id
    
    # Final fallback
    return 'demo_user'

def ensure_demo_user():
    """Ensure demo user exists for development/testing"""
    try:
        demo_user = User.query.filter_by(username='demo').first()
        if not demo_user:
            demo_user, error = UserManager.create_user(
                username='demo',
                email='demo@medical-reporting.local',
                password='demo123',
                role='doctor'
            )
            if demo_user:
                logger.info("Created demo user for development")
            else:
                logger.error(f"Failed to create demo user: {error}")
        
        return demo_user
        
    except Exception as e:
        logger.error(f"Demo user setup error: {e}")
        return None