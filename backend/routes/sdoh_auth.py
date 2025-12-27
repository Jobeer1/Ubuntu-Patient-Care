"""
SDOH Chat - Authentication Routes
Register, login, alias management
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from RIS-1.SDOH-chat.backend.models import User, Status
from RIS-1.SDOH-chat.backend.schemas import (
    UserRegisterRequest, UserRegisterResponse,
    SetAliasRequest, SetPinRequest,
    LoginRequest, LoginResponse,
    ErrorResponse
)
from RIS-1.SDOH-chat.backend.utils.auth_utils import AuthUtils, PrivacyUtils

router = APIRouter(prefix="/api/sdoh/auth", tags=["auth"])


@router.post("/register", response_model=UserRegisterResponse)
async def register(req: UserRegisterRequest, db: Session = Depends()):
    """
    Register new user (server-side code generation, privacy-first)
    
    Returns: 10-digit code (user must set alias and PIN next)
    """
    try:
        # Generate unique 10-digit code
        while True:
            user_code = AuthUtils.generate_user_code()
            existing = db.query(User).filter(User.user_id == user_code).first()
            if not existing:
                break
        
        # Create user (alias and pin_hash not set yet)
        user = User(
            user_id=user_code,
            alias=f"User{user_code[:4]}",  # Temporary alias
            pin_hash=""  # Empty until PIN is set
        )
        db.add(user)
        db.commit()
        
        return UserRegisterResponse(
            user_id=user_code,
            needs_alias=True
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/set-alias")
async def set_alias(req: SetAliasRequest, db: Session = Depends()):
    """
    Set user's unique alias (visible in chats)
    
    Alias must be:
    - 3-50 characters
    - Alphanumeric + underscore/dash
    - Globally unique
    """
    try:
        user = db.query(User).filter(User.user_id == req.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if alias is already taken
        existing_alias = db.query(User).filter(User.alias == req.alias).first()
        if existing_alias:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Alias already taken"
            )
        
        user.alias = req.alias
        db.commit()
        
        return {"status": "ok", "alias": req.alias}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/set-pin")
async def set_pin(req: SetPinRequest, db: Session = Depends()):
    """
    Set user's PIN (password)
    
    PIN must be:
    - 4-8 digits
    - Numeric only
    """
    try:
        user = db.query(User).filter(User.user_id == req.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.pin_hash = AuthUtils.hash_pin(req.pin)
        db.commit()
        
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: Session = Depends()):
    """
    Login with 10-digit code + PIN
    
    Returns JWT token (24-hour expiry)
    """
    try:
        user = db.query(User).filter(User.user_id == req.user_id).first()
        if not user or not user.pin_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid code or PIN"
            )
        
        # Verify PIN
        if not AuthUtils.verify_pin(req.pin, user.pin_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid code or PIN"
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        
        # Create or update status
        status_rec = db.query(Status).filter(Status.user_id == req.user_id).first()
        if not status_rec:
            status_rec = Status(user_id=req.user_id, status="available")
            db.add(status_rec)
        else:
            status_rec.status = "available"
        
        db.commit()
        
        # Create token
        token = AuthUtils.create_token(user.user_id, user.alias)
        
        return LoginResponse(
            token=token,
            alias=user.alias,
            user_id=user.user_id,
            expires_in=86400
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/logout")
async def logout(token: str, db: Session = Depends()):
    """
    Logout - set status to offline
    """
    try:
        payload = AuthUtils.verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        status_rec = db.query(Status).filter(Status.user_id == payload['user_id']).first()
        if status_rec:
            status_rec.status = "offline"
            db.commit()
        
        return {"status": "logged_out"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/profile")
async def get_profile(token: str, db: Session = Depends()):
    """
    Get current user profile
    """
    try:
        payload = AuthUtils.verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user = db.query(User).filter(User.user_id == payload['user_id']).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "user_id": user.user_id,  # Show only to themselves
            "alias": user.alias,
            "code_visible": user.code_visible,
            "created_at": user.created_at,
            "last_login": user.last_login
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/toggle-code-visibility")
async def toggle_code_visibility(token: str, db: Session = Depends()):
    """
    Toggle whether 10-digit code is visible in user profile
    Privacy control - user-owned
    """
    try:
        payload = AuthUtils.verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user = db.query(User).filter(User.user_id == payload['user_id']).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.code_visible = not user.code_visible
        db.commit()
        
        return {
            "status": "ok",
            "code_visible": user.code_visible
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
