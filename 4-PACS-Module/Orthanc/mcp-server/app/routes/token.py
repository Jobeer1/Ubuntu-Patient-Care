"""Token management routes"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import JWTService, UserService

router = APIRouter(prefix="/token", tags=["token"])

class TokenValidateRequest(BaseModel):
    token: str
    resource: str = None

class TokenValidateResponse(BaseModel):
    valid: bool
    user_id: int = None
    email: str = None
    role: str = None
    message: str = None

@router.post("/validate", response_model=TokenValidateResponse)
async def validate_token(request: TokenValidateRequest, db: Session = Depends(get_db)):
    """Validate JWT token (used by reverse proxy)"""
    payload = JWTService.verify_token(request.token)
    
    if not payload:
        return TokenValidateResponse(
            valid=False,
            message="Invalid or expired token"
        )
    
    user_id = payload.get("user_id")
    user = UserService.get_user_by_id(db, user_id)
    
    if not user or not user.active:
        return TokenValidateResponse(
            valid=False,
            message="User not found or inactive"
        )
    
    return TokenValidateResponse(
        valid=True,
        user_id=user.id,
        email=user.email,
        role=user.role,
        message="Token is valid"
    )

@router.post("/refresh")
async def refresh_token(request: Request, db: Session = Depends(get_db)):
    """Refresh access token"""
    token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    payload = JWTService.verify_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("user_id")
    user = UserService.get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create new token
    token_data = {
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role
    }
    new_token = JWTService.create_access_token(token_data)
    
    return {
        "access_token": new_token,
        "token_type": "bearer"
    }
