"""
Orthanc Management API - Authentication Manager
JWT token management, user authentication, and role-based access control
"""

import jwt
import bcrypt
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from orthanc_management.database.base import Base

logger = logging.getLogger(__name__)

# User model for authentication
class User(Base):
    """User model for authentication system"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="doctor")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # South African specific fields
    hpcsa_number = Column(String(20), unique=True, nullable=True)
    practice_number = Column(String(20), nullable=True)
    specialization = Column(String(100), nullable=True)
    province = Column(String(50), nullable=True)
    
    # Security fields
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert user to dictionary (excluding sensitive data)"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "hpcsa_number": self.hpcsa_number,
            "practice_number": self.practice_number,
            "specialization": self.specialization,
            "province": self.province,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AuthManager:
    """Authentication and authorization manager"""
    
    def __init__(self, db_session: Session, secret_key: str = "your-secret-key"):
        self.db = db_session
        self.secret_key = secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
        self.max_failed_attempts = 5
        self.lockout_duration_minutes = 15
        
        # Valid roles and permissions
        self.roles = {
            "admin": {
                "permissions": ["read", "write", "delete", "admin"],
                "description": "System administrator"
            },
            "doctor": {
                "permissions": ["read", "write"],
                "description": "Medical doctor"
            },
            "radiologist": {
                "permissions": ["read", "write", "diagnose"],
                "description": "Radiologist"
            },
            "technician": {
                "permissions": ["read"],
                "description": "Medical technician"
            },
            "viewer": {
                "permissions": ["read"],
                "description": "View-only access"
            }
        }
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        try:
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        except Exception as e:
            logger.error(f"Password hashing failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password processing failed"
            )
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification failed: {str(e)}")
            return False
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create JWT access token"""
        try:
            to_encode = data.copy()
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
            to_encode.update({"exp": expire, "type": "access"})
            
            token = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return token
        except Exception as e:
            logger.error(f"Token creation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token generation failed"
            )
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        try:
            to_encode = data.copy()
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
            to_encode.update({"exp": expire, "type": "refresh"})
            
            token = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return token
        except Exception as e:
            logger.error(f"Refresh token creation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token generation failed"
            )
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username/email and password"""
        try:
            # Find user by username or email
            user = self.db.query(User).filter(
                (User.username == username) | (User.email == username)
            ).first()
            
            if not user:
                logger.warning(f"Authentication failed: User not found - {username}")
                return None
            
            # Check if account is locked
            if user.locked_until and user.locked_until > datetime.utcnow():
                logger.warning(f"Authentication failed: Account locked - {username}")
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail=f"Account locked until {user.locked_until.strftime('%Y-%m-%d %H:%M:%S')} UTC"
                )
            
            # Verify password
            if not self.verify_password(password, user.password_hash):
                # Increment failed attempts
                user.failed_login_attempts += 1
                
                # Lock account if max attempts reached
                if user.failed_login_attempts >= self.max_failed_attempts:
                    user.locked_until = datetime.utcnow() + timedelta(minutes=self.lockout_duration_minutes)
                    logger.warning(f"Account locked due to failed attempts: {username}")
                
                self.db.commit()
                logger.warning(f"Authentication failed: Invalid password - {username}")
                return None
            
            # Check if user is active
            if not user.is_active:
                logger.warning(f"Authentication failed: Inactive account - {username}")
                return None
            
            # Reset failed attempts and update last login
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"User authenticated successfully: {username}")
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication failed"
            )
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            return self.db.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logger.error(f"Failed to get user by ID: {str(e)}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            return self.db.query(User).filter(User.username == username).first()
        except Exception as e:
            logger.error(f"Failed to get user by username: {str(e)}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            return self.db.query(User).filter(User.email == email).first()
        except Exception as e:
            logger.error(f"Failed to get user by email: {str(e)}")
            return None
    
    def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create new user"""
        try:
            # Validate required fields
            required_fields = ["username", "email", "password", "full_name"]
            for field in required_fields:
                if field not in user_data:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Missing required field: {field}"
                    )
            
            # Check if username already exists
            if self.get_user_by_username(user_data["username"]):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username already exists"
                )
            
            # Check if email already exists
            if self.get_user_by_email(user_data["email"]):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already exists"
                )
            
            # Validate role
            role = user_data.get("role", "doctor")
            if role not in self.roles:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role: {role}"
                )
            
            # Generate user ID
            import uuid
            user_id = str(uuid.uuid4())
            
            # Create user
            user = User(
                id=user_id,
                username=user_data["username"],
                email=user_data["email"],
                password_hash=self.hash_password(user_data["password"]),
                full_name=user_data["full_name"],
                role=role,
                hpcsa_number=user_data.get("hpcsa_number"),
                practice_number=user_data.get("practice_number"),
                specialization=user_data.get("specialization"),
                province=user_data.get("province"),
                is_active=user_data.get("is_active", True),
                is_verified=user_data.get("is_verified", False)
            )
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"User created successfully: {user.username}")
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User creation failed: {str(e)}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed"
            )
    
    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> User:
        """Update user information"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Update allowed fields
            allowed_fields = [
                "full_name", "email", "role", "hpcsa_number", 
                "practice_number", "specialization", "province",
                "is_active", "is_verified"
            ]
            
            for field, value in update_data.items():
                if field in allowed_fields:
                    if field == "role" and value not in self.roles:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid role: {value}"
                        )
                    setattr(user, field, value)
                elif field == "password":
                    user.password_hash = self.hash_password(value)
            
            user.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"User updated successfully: {user.username}")
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User update failed: {str(e)}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User update failed"
            )
    
    def has_permission(self, user: User, permission: str) -> bool:
        """Check if user has specific permission"""
        if not user or not user.is_active:
            return False
        
        user_permissions = self.roles.get(user.role, {}).get("permissions", [])
        return permission in user_permissions
    
    def require_permission(self, user: User, permission: str):
        """Require specific permission or raise exception"""
        if not self.has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
    
    def get_current_user_from_token(self, token: str) -> User:
        """Get current user from JWT token"""
        try:
            payload = self.verify_token(token)
            user_id = payload.get("sub")
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            user = self.get_user_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Inactive user"
                )
            
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token validation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed"
            )
    
    def generate_password_reset_token(self, email: str) -> str:
        """Generate password reset token"""
        try:
            user = self.get_user_by_email(email)
            if not user:
                # Don't reveal if email exists
                return "token-generated"
            
            # Generate reset token
            import secrets
            reset_token = secrets.token_urlsafe(32)
            
            # Set token and expiration
            user.password_reset_token = reset_token
            user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
            
            self.db.commit()
            
            logger.info(f"Password reset token generated for: {email}")
            return reset_token
            
        except Exception as e:
            logger.error(f"Password reset token generation failed: {str(e)}")
            self.db.rollback()
            return "token-generated"  # Don't reveal errors
    
    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using reset token"""
        try:
            user = self.db.query(User).filter(
                User.password_reset_token == token,
                User.password_reset_expires > datetime.utcnow()
            ).first()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired reset token"
                )
            
            # Update password and clear reset token
            user.password_hash = self.hash_password(new_password)
            user.password_reset_token = None
            user.password_reset_expires = None
            user.failed_login_attempts = 0
            user.locked_until = None
            user.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Password reset successfully for user: {user.username}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Password reset failed: {str(e)}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password reset failed"
            )
