"""User Service"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import bcrypt
from app.models import User
from datetime import datetime

class UserService:
    """Service for user management"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hashed password"""
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False
    
    @staticmethod
    def get_or_create_user(db: Session, email: str, full_name: str = None, role: str = "Patient") -> User:
        """Get existing user or create new one"""
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            return user
        
        user = User(
            email=email,
            full_name=full_name or email.split('@')[0],
            role=role,
            created_at=datetime.utcnow()
        )
        
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
        except IntegrityError:
            db.rollback()
            user = db.query(User).filter(User.email == email).first()
        
        return user
    
    @staticmethod
    def create_local_user(db: Session, email: str, password: str, full_name: str = None, role: str = "Patient") -> User:
        """Create a new local user with password"""
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError(f"User with email {email} already exists")
        
        hashed_password = UserService.hash_password(password)
        
        user = User(
            email=email,
            full_name=full_name or email.split('@')[0],
            password_hash=hashed_password,
            role=role,
            created_at=datetime.utcnow()
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        
        if not user.password_hash:
            return None
        
        if not UserService.verify_password(password, user.password_hash):
            return None
        
        return user
    
    @staticmethod
    def update_google_token(db: Session, user: User, access_token: str, refresh_token: Optional[str] = None) -> User:
        """Update user's Google OAuth token"""
        user.google_access_token = access_token
        if refresh_token:
            user.google_refresh_token = refresh_token
        user.google_token_updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def update_microsoft_token(db: Session, user: User, access_token: str, refresh_token: Optional[str] = None) -> User:
        """Update user's Microsoft OAuth token"""
        user.microsoft_access_token = access_token
        if refresh_token:
            user.microsoft_refresh_token = refresh_token
        user.microsoft_token_updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def update_last_login(db: Session, user: User) -> User:
        """Update user's last login timestamp"""
        user.last_login_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def update_user_role(db: Session, user: User, new_role: str) -> User:
        """Update user's role"""
        user.role = new_role
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        """Delete a user"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()
            return True
        return False
