"""
SDOH Chat - Authentication Utilities
PIN hashing, JWT tokens, code generation
"""

import jwt
import bcrypt
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict


class AuthUtils:
    """Authentication utilities"""
    
    SECRET_KEY = "sdoh-chat-secret-key-change-in-production"  # CHANGE IN PRODUCTION
    ALGORITHM = "HS256"
    PIN_ROUNDS = 12  # bcrypt rounds
    
    @staticmethod
    def generate_user_code() -> str:
        """Generate random 10-digit code"""
        return ''.join([str(random.randint(0, 9)) for _ in range(10)])
    
    @staticmethod
    def hash_pin(pin: str) -> str:
        """Hash PIN using bcrypt"""
        return bcrypt.hashpw(pin.encode(), bcrypt.gensalt(rounds=AuthUtils.PIN_ROUNDS)).decode()
    
    @staticmethod
    def verify_pin(pin: str, pin_hash: str) -> bool:
        """Verify PIN against hash"""
        try:
            return bcrypt.checkpw(pin.encode(), pin_hash.encode())
        except Exception:
            return False
    
    @staticmethod
    def create_token(user_id: str, alias: str, expires_in: int = 86400) -> str:
        """Create JWT token"""
        payload = {
            'user_id': user_id,
            'alias': alias,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, AuthUtils.SECRET_KEY, algorithm=AuthUtils.ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, AuthUtils.SECRET_KEY, algorithms=[AuthUtils.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def refresh_token(token: str, expires_in: int = 86400) -> Optional[str]:
        """Refresh expired token"""
        payload = AuthUtils.verify_token(token)
        if payload:
            return AuthUtils.create_token(payload['user_id'], payload['alias'], expires_in)
        return None


class PrivacyUtils:
    """Privacy controls"""
    
    @staticmethod
    def mask_user_code(user_id: str, code_visible: bool) -> Optional[str]:
        """Return code only if user allows visibility"""
        if code_visible:
            return user_id
        return None
    
    @staticmethod
    def format_user_for_response(user, show_code: bool = False) -> Dict:
        """Format user response based on privacy settings"""
        data = {
            'user_id': user.user_id if show_code else None,
            'alias': user.alias,
            'code_visible': user.code_visible
        }
        return {k: v for k, v in data.items() if v is not None}
    
    @staticmethod
    def format_message_response(message, include_code: bool = False) -> Dict:
        """Format message for response"""
        sender_data = {
            'sender_alias': message.sender.alias,
        }
        if include_code:
            sender_data['sender_id'] = message.sender.user_id
        
        return {
            'msg_id': message.msg_id,
            'sender_alias': sender_data['sender_alias'],
            'chat_id': message.chat_id,
            'content': message.content,
            'msg_type': message.msg_type,
            'created_at': message.created_at,
            **({k: v for k, v in sender_data.items() if k != 'sender_alias'} if include_code else {})
        }
