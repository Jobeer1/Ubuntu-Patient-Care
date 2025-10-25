"""Authentication routes"""
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from config.settings import settings
from app.database import get_db
from app.services import JWTService, UserService, AuditService
from app.models import User
from typing import Optional
import secrets

router = APIRouter(prefix="/auth", tags=["authentication"])

# OAuth configuration
oauth = OAuth()

# Google OAuth with offline access for Drive
if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile https://www.googleapis.com/auth/drive.file',
            'access_type': 'offline',
            'prompt': 'consent'
        }
    )

# Microsoft OAuth with offline access for OneDrive
if settings.MICROSOFT_CLIENT_ID and settings.MICROSOFT_CLIENT_SECRET:
    oauth.register(
        name='microsoft',
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_secret=settings.MICROSOFT_CLIENT_SECRET,
        server_metadata_url=f'https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}/v2.0/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile offline_access Files.ReadWrite',
        }
    )

@router.get("/google")
async def login_google(request: Request):
    """Initiate Google SSO login"""
    # Check if SSO is enabled
    if not get_sso_status():
        return RedirectResponse(url="/?error=SSO is currently disabled by administrator")
    
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def auth_google_callback(request: Request, response: Response, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        email = user_info.get('email')
        name = user_info.get('name', email)
        
        # Get or create user
        user = UserService.get_or_create_user(db, email, name)
        
        # Store refresh token for Google Drive access
        refresh_token = token.get('refresh_token')
        if refresh_token:
            UserService.update_google_token(db, user.id, refresh_token)
        
        UserService.update_last_login(db, user.id)
        
        # Create JWT token
        token_data = {
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role
        }
        access_token = JWTService.create_access_token(token_data)
        
        # Log authentication
        AuditService.log_event(
            db=db,
            user_id=user.id,
            user_email=user.email,
            action="login_google",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            success=True
        )
        
        # Redirect to dashboard with modules based on role
        from app.services.rbac_service import RBACService
        modules = RBACService.get_accessible_modules(user)
        
        # Redirect to MCP server dashboard (not external RIS)
        # If admin, redirect to admin dashboard, otherwise to user dashboard
        if user.role == "Admin":
            redirect_url = "/admin"
        else:
            redirect_url = f"/dashboard?modules={','.join(modules)}"
        
        redirect_response = RedirectResponse(url=redirect_url)
        redirect_response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=settings.JWT_ACCESS_TOKEN_EXPIRES
        )
        
        return redirect_response
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")

@router.get("/microsoft")
async def login_microsoft(request: Request):
    """Initiate Microsoft SSO login"""
    # Check if SSO is enabled
    if not get_sso_status():
        return RedirectResponse(url="/?error=SSO is currently disabled by administrator")
    
    if not settings.MICROSOFT_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Microsoft OAuth not configured")
    
    redirect_uri = settings.MICROSOFT_REDIRECT_URI
    return await oauth.microsoft.authorize_redirect(request, redirect_uri)

@router.get("/microsoft/callback")
async def auth_microsoft_callback(request: Request, response: Response, db: Session = Depends(get_db)):
    """Handle Microsoft OAuth callback"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Log callback details
        logger.info(f"Microsoft callback received")
        logger.info(f"Query params: {dict(request.query_params)}")
        
        token = await oauth.microsoft.authorize_access_token(request)
        logger.info("Token received from Microsoft")
        
        user_info = token.get('userinfo')
        
        if not user_info:
            logger.error("No userinfo in token")
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        email = user_info.get('email') or user_info.get('preferred_username')
        name = user_info.get('name', email)
        
        logger.info(f"User authenticated: {email}")
        
        # Get or create user
        user = UserService.get_or_create_user(db, email, name)
        
        # Store refresh token for OneDrive access
        refresh_token = token.get('refresh_token')
        if refresh_token:
            UserService.update_microsoft_token(db, user.id, refresh_token)
        
        UserService.update_last_login(db, user.id)
        
        # Create JWT token
        token_data = {
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role
        }
        access_token = JWTService.create_access_token(token_data)
        
        # Log authentication
        AuditService.log_event(
            db=db,
            user_id=user.id,
            user_email=user.email,
            action="login_microsoft",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            success=True
        )
        
        # Redirect to dashboard with modules based on role
        from app.services.rbac_service import RBACService
        modules = RBACService.get_accessible_modules(user)
        
        # Redirect to MCP server dashboard (not external RIS)
        # If admin, redirect to admin dashboard, otherwise to user dashboard
        if user.role == "Admin":
            redirect_url = "/admin"
        else:
            redirect_url = f"/dashboard?modules={','.join(modules)}"
        
        logger.info(f"Redirecting user {user.email} (role: {user.role}) to: {redirect_url}")
        
        redirect_response = RedirectResponse(url=redirect_url)
        redirect_response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=settings.JWT_ACCESS_TOKEN_EXPIRES
        )
        
        return redirect_response
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Microsoft auth callback error: {str(e)}", exc_info=True)
        
        error_detail = str(e)
        if "redirect_uri" in error_detail.lower():
            error_detail = "REDIRECT_URI_MISMATCH: Make sure http://localhost:8080/auth/microsoft/callback is registered in Azure Portal"
        
        raise HTTPException(status_code=400, detail=f"Authentication failed: {error_detail}")

@router.post("/login")
async def login_local(request: Request, response: Response, db: Session = Depends(get_db)):
    """Local email/password login"""
    from pydantic import BaseModel
    import bcrypt
    
    class LoginRequest(BaseModel):
        email: str
        password: str
    
    try:
        body = await request.json()
        login_data = LoginRequest(**body)
        
        # Get user
        user = UserService.get_user_by_email(db, login_data.email)
        if not user or not user.password_hash:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Verify password
        if not bcrypt.checkpw(login_data.password.encode('utf-8'), user.password_hash.encode('utf-8')):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if not user.active:
            raise HTTPException(status_code=403, detail="Account is inactive")
        
        UserService.update_last_login(db, user.id)
        
        # Create JWT token
        token_data = {
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role
        }
        access_token = JWTService.create_access_token(token_data)
        
        # Log authentication
        AuditService.log_event(
            db=db,
            user_id=user.id,
            user_email=user.email,
            action="login_local",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            success=True
        )
        
        # Get accessible modules
        from app.services.rbac_service import RBACService
        modules = RBACService.get_accessible_modules(user)
        
        return {
            "success": True,
            "redirect_url": f"/dashboard?modules={','.join(modules)}",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Login failed: {str(e)}")

@router.post("/signup")
async def signup_local(request: Request, db: Session = Depends(get_db)):
    """Local email/password signup"""
    from pydantic import BaseModel
    import bcrypt
    
    class SignupRequest(BaseModel):
        email: str
        password: str
        name: str
        role: str = "Patient"
        patient_id: Optional[str] = None
    
    try:
        body = await request.json()
        signup_data = SignupRequest(**body)
        
        # Check if user exists
        existing_user = UserService.get_user_by_email(db, signup_data.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash password
        password_hash = bcrypt.hashpw(signup_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create user
        user = User(
            email=signup_data.email,
            password_hash=password_hash,
            name=signup_data.name,
            role=signup_data.role,
            patient_id=signup_data.patient_id,
            active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create default context
        from app.models import UserContext
        context = UserContext(
            user_id=user.id,
            language="en-ZA",
            dictation_model="whisper-large-v3"
        )
        db.add(context)
        db.commit()
        
        # Log registration
        AuditService.log_event(
            db=db,
            user_id=user.id,
            user_email=user.email,
            action="signup_local",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            success=True
        )
        
        return {
            "success": True,
            "message": "Account created successfully",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Signup failed: {str(e)}")

@router.get("/logout")
async def logout(response: Response):
    """Logout user"""
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie(key="access_token")
    return response


@router.get("/sso/pacs")
async def sso_redirect_pacs(request: Request):
    """Redirect to PACS with MCP JWT token for SSO handoff.

    Note: PACS must be updated to accept `mcp_token` query parameter and exchange it for a session.
    """
    token = request.cookies.get("access_token")
    if token:
        # Append token as query param; PACS must accept and exchange this for a session
        target = f"http://localhost:5000/?mcp_token={token}"
    else:
        # Not authenticated at MCP - send to admin with an error
        target = "/admin?error=not_authenticated"

    return RedirectResponse(url=target)

@router.get("/status")
async def auth_status(request: Request, db: Session = Depends(get_db)):
    """Check authentication status"""
    token = request.cookies.get("access_token")
    
    if not token:
        return {"authenticated": False}
    
    payload = JWTService.verify_token(token)
    if not payload:
        return {"authenticated": False}
    
    user = UserService.get_user_by_id(db, payload.get("user_id"))
    if not user:
        return {"authenticated": False}
    
    return {
        "authenticated": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role
        }
    }



# ============================================================================
# SSO Admin Control Endpoints
# ============================================================================

import json
from pathlib import Path

SSO_CONFIG_FILE = Path("sso_config.json")

def get_sso_status() -> bool:
    """Get current SSO enabled/disabled status"""
    try:
        if SSO_CONFIG_FILE.exists():
            with open(SSO_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('enabled', True)
        return True  # Default to enabled
    except Exception as e:
        print(f"Error reading SSO config: {e}")
        return True

def set_sso_status(enabled: bool) -> bool:
    """Set SSO enabled/disabled status"""
    try:
        config = {'enabled': enabled}
        with open(SSO_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"SSO status set to: {enabled}")
        return True
    except Exception as e:
        print(f"Error writing SSO config: {e}")
        return False


@router.get("/sso/status")
async def get_sso_config():
    """Get SSO configuration status"""
    try:
        enabled = get_sso_status()
        return {
            'enabled': enabled,
            'microsoft_configured': bool(settings.MICROSOFT_CLIENT_ID),
            'google_configured': bool(settings.GOOGLE_CLIENT_ID)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get SSO status: {str(e)}")


@router.post("/sso/toggle")
async def toggle_sso(request: Request, db: Session = Depends(get_db)):
    """Toggle SSO enabled/disabled (Admin only)"""
    try:
        # Check if user is authenticated
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Verify token and get user
        payload = JWTService.verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_email = payload.get("email")
        user = db.query(User).filter(User.email == user_email).first()
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Check if user is admin
        if user.role != "Admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get enabled status from request body
        body = await request.json()
        enabled = body.get('enabled', True)
        
        if set_sso_status(enabled):
            # Log the change
            AuditService.log_action(
                db=db,
                user_id=user.id,
                action=f"SSO {'enabled' if enabled else 'disabled'}",
                resource_type="system",
                resource_id="sso_config"
            )
            
            return {
                'success': True,
                'enabled': enabled,
                'message': f"SSO {'enabled' if enabled else 'disabled'} successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update SSO status")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle SSO: {str(e)}")
