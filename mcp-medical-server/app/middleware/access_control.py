"""Middleware for access control and authentication"""
from typing import Optional, Callable, Any
from functools import wraps
from fastapi import HTTPException, status, Request
import jwt
from app.services.jwt_service import JWTService
from app.services.access_control import AccessControlService
from config.settings import Settings
from sqlalchemy.orm import Session

def get_token_from_request(request: Request) -> Optional[str]:
    """Extract JWT token from request"""
    # Try to get from Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]
    
    # Try to get from cookies
    token = request.cookies.get(Settings.JWT_COOKIE_NAME)
    if token:
        return token
    
    return None

def verify_mcp_token(token: str, db: Session) -> dict:
    """Verify JWT token for MCP communication"""
    try:
        payload = JWTService.verify_token(token)
        return payload
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

def check_patient_access_with_mcp(
    user_id: int,
    patient_id: str,
    token: str,
    db: Session
) -> bool:
    """Check patient access using MCP token"""
    try:
        payload = verify_mcp_token(token, db)
        if payload.get("user_id") != user_id:
            return False
        
        from app.models import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        return AccessControlService.can_access_patient(db, user, patient_id)
    except HTTPException:
        return False

def require_authentication(func: Callable) -> Callable:
    """Decorator to require authentication"""
    @wraps(func)
    async def wrapper(*args, request: Request = None, db: Session = None, **kwargs) -> Any:
        if not request:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Request context required"
            )
        
        token = get_token_from_request(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        try:
            payload = verify_mcp_token(token, db)
            request.state.user_id = payload.get("user_id")
            request.state.user_email = payload.get("email")
            request.state.user_role = payload.get("role")
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return await func(*args, request=request, db=db, **kwargs)
    
    return wrapper

def require_patient_access(func: Callable) -> Callable:
    """Decorator to require patient-level access"""
    @wraps(func)
    async def wrapper(
        *args,
        patient_id: str,
        request: Request = None,
        db: Session = None,
        **kwargs
    ) -> Any:
        if not request:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Request context required"
            )
        
        token = get_token_from_request(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        try:
            payload = verify_mcp_token(token, db)
            user_id = payload.get("user_id")
            
            from app.models import User
            from app.services.audit_service import AuditService
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            can_access = AccessControlService.can_access_patient(db, user, patient_id)
            if not can_access:
                ip_address = request.client.host if request.client else None
                AuditService.log_access_denied(
                    db=db,
                    user_id=user_id,
                    resource_type="patient",
                    resource_id=patient_id,
                    reason="Insufficient permissions",
                    ip_address=ip_address
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to patient data"
                )
            
            request.state.user_id = user_id
            request.state.user_email = payload.get("email")
            request.state.user_role = payload.get("role")
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}"
            )
        
        return await func(*args, patient_id=patient_id, request=request, db=db, **kwargs)
    
    return wrapper

def log_access_attempt(request: Request, success: bool = True, user_id: Optional[int] = None):
    """Log access attempt for audit trail"""
    try:
        from app.services.audit_service import AuditService
        from app.database import SessionLocal
        
        db = SessionLocal()
        ip_address = request.client.host if request.client else None
        
        if success:
            AuditService.log_event(
                db=db,
                user_id=user_id,
                event_type="access_attempt",
                details=f"Access to {request.url.path}",
                ip_address=ip_address,
                status="success"
            )
        else:
            AuditService.log_event(
                db=db,
                user_id=user_id,
                event_type="access_denied",
                details=f"Failed access to {request.url.path}",
                ip_address=ip_address,
                status="denied"
            )
        
        db.close()
    except Exception as e:
        # Silently fail audit logging to not break main request
        pass
