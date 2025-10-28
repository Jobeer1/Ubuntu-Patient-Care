"""JWT Token Service"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from config.settings import Settings

class JWTService:
    """Service for managing JWT tokens"""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
        
        to_encode.update({"exp": expire})
        
        try:
            encoded_jwt = jwt.encode(
                to_encode,
                Settings.JWT_SECRET_KEY,
                algorithm=Settings.JWT_ALGORITHM
            )
            return encoded_jwt
        except Exception as e:
            raise Exception(f"Failed to create token: {str(e)}")
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify a JWT token and return its payload"""
        try:
            payload = jwt.decode(
                token,
                Settings.JWT_SECRET_KEY,
                algorithms=[Settings.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
        except Exception as e:
            raise ValueError(f"Token verification failed: {str(e)}")
    
    @staticmethod
    def get_token_exp_time(token: str) -> Optional[datetime]:
        """Get expiration time of a token"""
        try:
            payload = jwt.decode(
                token,
                Settings.JWT_SECRET_KEY,
                algorithms=[Settings.JWT_ALGORITHM],
                options={"verify_exp": False}
            )
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp)
            return None
        except Exception as e:
            raise ValueError(f"Failed to get token expiration: {str(e)}")
    
    @staticmethod
    def is_token_expired(token: str) -> bool:
        """Check if a token is expired"""
        try:
            payload = jwt.decode(
                token,
                Settings.JWT_SECRET_KEY,
                algorithms=[Settings.JWT_ALGORITHM]
            )
            return False
        except jwt.ExpiredSignatureError:
            return True
        except Exception:
            return True
