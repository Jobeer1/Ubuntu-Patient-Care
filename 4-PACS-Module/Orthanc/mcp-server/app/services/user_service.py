"""User management service"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models import User, UserContext

class UserService:
    """User service for managing users"""
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def create_user(db: Session, email: str, name: str, role: str = "Technician") -> User:
        """Create new user"""
        user = User(
            email=email,
            name=name,
            role=role,
            active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create default context
        context = UserContext(
            user_id=user.id,
            language="en-ZA",
            dictation_model="whisper-large-v3"
        )
        db.add(context)
        db.commit()
        
        return user
    
    @staticmethod
    def update_last_login(db: Session, user_id: int):
        """Update user's last login timestamp"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.last_login = datetime.utcnow()
            db.commit()
    
    @staticmethod
    def get_or_create_user(db: Session, email: str, name: str) -> User:
        """Get existing user or create new one"""
        user = UserService.get_user_by_email(db, email)
        if not user:
            user = UserService.create_user(db, email, name)
        return user
    
    @staticmethod
    def update_google_token(db: Session, user_id: int, refresh_token: Optional[str]):
        """Update user's Google refresh token"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.google_refresh_token = refresh_token
            db.commit()
    
    @staticmethod
    def update_microsoft_token(db: Session, user_id: int, refresh_token: Optional[str]):
        """Update user's Microsoft refresh token"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.microsoft_refresh_token = refresh_token
            db.commit()
    
    @staticmethod
    def list_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """List all users"""
        return db.query(User).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_user_role(db: Session, user_id: int, role: str) -> Optional[User]:
        """Update user role"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.role = role
            db.commit()
            db.refresh(user)
        return user
    
    @staticmethod
    def delete_user(db: Session, user_id: int) -> Optional[User]:
        """Delete user"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            # Delete associated context
            db.query(UserContext).filter(UserContext.user_id == user_id).delete()
            db.delete(user)
            db.commit()
        return user
