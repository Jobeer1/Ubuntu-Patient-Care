"""
Orthanc Management API - Authentication Router
Login, logout, registration, and user management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from orthanc_management.api.auth import AuthManager, User
from orthanc_management.database.manager import DatabaseManager

logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Pydantic models for request/response
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=255)
    role: str = Field(default="doctor")
    hpcsa_number: Optional[str] = Field(None, max_length=20)
    practice_number: Optional[str] = Field(None, max_length=20)
    specialization: Optional[str] = Field(None, max_length=100)
    province: Optional[str] = Field(None, max_length=50)

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    hpcsa_number: Optional[str] = Field(None, max_length=20)
    practice_number: Optional[str] = Field(None, max_length=20)
    specialization: Optional[str] = Field(None, max_length=100)
    province: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    hpcsa_number: Optional[str]
    practice_number: Optional[str]
    specialization: Optional[str]
    province: Optional[str]
    last_login: Optional[str]
    created_at: Optional[str]

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class TokenRefresh(BaseModel):
    refresh_token: str

# Router instance
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Dependency to get database session
def get_db():
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

# Dependency to get auth manager
def get_auth_manager(db = Depends(get_db)):
    return AuthManager(db)

# Dependency to get current user
def get_current_user(token: str = Depends(oauth2_scheme), auth_manager: AuthManager = Depends(get_auth_manager)):
    return auth_manager.get_current_user_from_token(token)

# Dependency to get current active user
def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """
    Login with username/email and password
    Returns access and refresh tokens
    """
    try:
        # Authenticate user
        user = auth_manager.authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create tokens
        token_data = {"sub": user.id, "username": user.username, "role": user.role}
        access_token = auth_manager.create_access_token(token_data)
        refresh_token = auth_manager.create_refresh_token(token_data)
        
        logger.info(f"User logged in successfully: {user.username}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=auth_manager.access_token_expire_minutes * 60,
            user=UserResponse(**user.to_dict())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """
    Register a new user account
    """
    try:
        # Create user
        user = auth_manager.create_user(user_data.dict())
        
        logger.info(f"User registered successfully: {user.username}")
        
        return UserResponse(**user.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefresh,
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """
    Refresh access token using refresh token
    """
    try:
        # Verify refresh token
        payload = auth_manager.verify_token(token_data.refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        user = auth_manager.get_user_by_id(user_id)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new tokens
        token_payload = {"sub": user.id, "username": user.username, "role": user.role}
        access_token = auth_manager.create_access_token(token_payload)
        refresh_token = auth_manager.create_refresh_token(token_payload)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=auth_manager.access_token_expire_minutes * 60,
            user=UserResponse(**user.to_dict())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current user information
    """
    return UserResponse(**current_user.to_dict())


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """
    Update current user information
    """
    try:
        # Filter out None values
        update_data = {k: v for k, v in user_data.dict().items() if v is not None}
        
        # Update user
        updated_user = auth_manager.update_user(current_user.id, update_data)
        
        logger.info(f"User updated successfully: {updated_user.username}")
        
        return UserResponse(**updated_user.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User update failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User update failed"
        )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """
    Change current user password
    """
    try:
        # Verify current password
        if not auth_manager.verify_password(password_data.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )
        
        # Update password
        auth_manager.update_user(current_user.id, {"password": password_data.new_password})
        
        logger.info(f"Password changed successfully: {current_user.username}")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.post("/reset-password")
async def request_password_reset(
    reset_data: PasswordReset,
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """
    Request password reset (sends reset token)
    """
    try:
        # Generate reset token
        token = auth_manager.generate_password_reset_token(reset_data.email)
        
        # In production, send email with reset link
        # For demo, return the token (remove in production!)
        logger.info(f"Password reset requested for: {reset_data.email}")
        
        return {
            "message": "Password reset instructions sent to email",
            "reset_token": token  # Remove this in production!
        }
        
    except Exception as e:
        logger.error(f"Password reset request failed: {str(e)}")
        # Always return success to prevent email enumeration
        return {"message": "Password reset instructions sent to email"}


@router.post("/reset-password/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """
    Confirm password reset with token
    """
    try:
        # Reset password
        success = auth_manager.reset_password(reset_data.token, reset_data.new_password)
        
        if success:
            return {"message": "Password reset successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset failed"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset confirmation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """
    List all users (admin only)
    """
    try:
        # Check admin permission
        auth_manager.require_permission(current_user, "admin")
        
        # Get users from database
        from sqlalchemy import func
        users = auth_manager.db.query(User).offset(skip).limit(limit).all()
        
        return [UserResponse(**user.to_dict()) for user in users]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """
    Get user by ID (admin only or own profile)
    """
    try:
        # Check if user is accessing own profile or has admin permission
        if current_user.id != user_id:
            auth_manager.require_permission(current_user, "admin")
        
        user = auth_manager.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(**user.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """
    Update user by ID (admin only)
    """
    try:
        # Check admin permission
        auth_manager.require_permission(current_user, "admin")
        
        # Filter out None values
        update_data = {k: v for k, v in user_data.dict().items() if v is not None}
        
        # Update user
        updated_user = auth_manager.update_user(user_id, update_data)
        
        logger.info(f"User updated by admin: {updated_user.username}")
        
        return UserResponse(**updated_user.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.get("/roles")
async def get_roles(current_user: User = Depends(get_current_active_user)):
    """
    Get available user roles and permissions
    """
    auth_manager = AuthManager(None)  # Just for accessing roles definition
    return {
        "roles": auth_manager.roles,
        "current_user_role": current_user.role,
        "current_user_permissions": auth_manager.roles.get(current_user.role, {}).get("permissions", [])
    }
