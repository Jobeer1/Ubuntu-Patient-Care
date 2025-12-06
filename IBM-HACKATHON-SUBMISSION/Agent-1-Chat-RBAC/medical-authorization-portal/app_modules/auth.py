"""
Authentication Module
====================
OAuth flows, login/logout, session management
Google & Microsoft authentication, user role detection
"""

from flask import session, redirect, url_for, request
from app_modules.config import (
    GoogleOAuthConfig, MicrosoftOAuthConfig, 
    EmailDomainRoleMapping, ThemeConfig, SecurityConfig
)
from app_modules.database import db
from app_modules.utils import (
    hash_password, verify_password, generate_unique_id,
    detect_role_from_email, validate_email, log_info, 
    log_error, get_current_datetime
)

# ============================================================================
# OAUTH CONFIGURATION
# ============================================================================

class OAuthProvider:
    """Base class for OAuth providers"""
    
    def __init__(self, provider_name, client_id, client_secret, redirect_uri):
        self.provider_name = provider_name
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
    
    def get_authorization_url(self):
        """Get authorization URL - override in subclass"""
        raise NotImplementedError
    
    def exchange_code_for_token(self, code):
        """Exchange authorization code for token - override in subclass"""
        raise NotImplementedError
    
    def get_user_info(self, access_token):
        """Get user info from provider - override in subclass"""
        raise NotImplementedError


class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth implementation"""
    
    def __init__(self):
        super().__init__(
            'google',
            GoogleOAuthConfig.CLIENT_ID,
            GoogleOAuthConfig.CLIENT_SECRET,
            GoogleOAuthConfig.REDIRECT_URI
        )
    
    def get_authorization_url(self, state):
        """Get Google authorization URL"""
        scope = ' '.join([
            'openid',
            'profile',
            'email'
        ])
        
        return (
            f"{GoogleOAuthConfig.AUTH_URL}?"
            f"client_id={self.client_id}&"
            f"redirect_uri={self.redirect_uri}&"
            f"scope={scope}&"
            f"response_type=code&"
            f"state={state}"
        )
    
    def exchange_code_for_token(self, code):
        """Exchange code for token"""
        import requests
        
        try:
            response = requests.post(
                GoogleOAuthConfig.TOKEN_URL,
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'code': code,
                    'grant_type': 'authorization_code',
                    'redirect_uri': self.redirect_uri
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                log_error(f"Google token exchange failed: {response.text}")
                return None
        except Exception as e:
            log_error("Google token exchange error", e)
            return None
    
    def get_user_info(self, access_token):
        """Get user info from Google"""
        import requests
        
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                GoogleOAuthConfig.USERINFO_URL,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                log_error(f"Google userinfo failed: {response.text}")
                return None
        except Exception as e:
            log_error("Google userinfo error", e)
            return None


class MicrosoftOAuthProvider(OAuthProvider):
    """Microsoft OAuth implementation"""
    
    def __init__(self):
        super().__init__(
            'microsoft',
            MicrosoftOAuthConfig.CLIENT_ID,
            MicrosoftOAuthConfig.CLIENT_SECRET,
            MicrosoftOAuthConfig.REDIRECT_URI
        )
    
    def get_authorization_url(self, state):
        """Get Microsoft authorization URL"""
        scope = ' '.join([
            'openid',
            'profile',
            'email'
        ])
        
        return (
            f"{MicrosoftOAuthConfig.AUTH_URL}?"
            f"client_id={self.client_id}&"
            f"redirect_uri={self.redirect_uri}&"
            f"scope={scope}&"
            f"response_type=code&"
            f"state={state}"
        )
    
    def exchange_code_for_token(self, code):
        """Exchange code for token"""
        import requests
        
        try:
            response = requests.post(
                MicrosoftOAuthConfig.TOKEN_URL,
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'code': code,
                    'grant_type': 'authorization_code',
                    'redirect_uri': self.redirect_uri,
                    'scope': 'openid profile email'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                log_error(f"Microsoft token exchange failed: {response.text}")
                return None
        except Exception as e:
            log_error("Microsoft token exchange error", e)
            return None
    
    def get_user_info(self, access_token):
        """Get user info from Microsoft"""
        import requests
        
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                MicrosoftOAuthConfig.USERINFO_URL,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                log_error(f"Microsoft userinfo failed: {response.text}")
                return None
        except Exception as e:
            log_error("Microsoft userinfo error", e)
            return None


# ============================================================================
# AUTHENTICATION MANAGER
# ============================================================================

class AuthenticationManager:
    """Manage user authentication and sessions"""
    
    @staticmethod
    def create_or_update_oauth_user(provider, user_info):
        """Create or update user from OAuth provider"""
        
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0])
        
        if not email or not validate_email(email):
            log_error(f"Invalid email from {provider}: {email}")
            return None
        
        # Check if user exists
        existing_user = db.users.get_user_by_email(email)
        
        if existing_user:
            # Update last login
            db.users.update_last_login(existing_user['id'])
            log_info(f"OAuth login for existing user: {email} ({provider})")
            return existing_user
        
        else:
            # Create new user
            user_id = generate_unique_id()
            role = detect_role_from_email(email)
            
            new_user = {
                'id': user_id,
                'username': email.split('@')[0],
                'email': email,
                'name': name,
                'password_hash': None,  # OAuth users don't have password
                'role': role,
                'provider': provider,
                'profile_picture': user_info.get('picture'),
                'last_login': get_current_datetime()
            }
            
            db.users.create_user(new_user)
            log_info(f"New OAuth user created: {email} as {role} ({provider})")
            return new_user
    
    @staticmethod
    def local_login(email, password):
        """Local login with email and password"""
        
        if not validate_email(email):
            log_error(f"Invalid email attempt: {email}")
            return None
        
        user = db.users.get_user_by_email(email)
        
        if not user:
            log_error(f"Login failed - user not found: {email}")
            return None
        
        if not user.get('password_hash'):
            log_error(f"Local login attempted for OAuth user: {email}")
            return None
        
        if not verify_password(password, user['password_hash']):
            log_error(f"Login failed - invalid password: {email}")
            return None
        
        # Update last login
        db.users.update_last_login(user['id'])
        log_info(f"Local login successful: {email}")
        return user
    
    @staticmethod
    def register_local_user(email, password, name):
        """Register new local user"""
        
        # Validate email
        if not validate_email(email):
            return None, "Invalid email format"
        
        # Check if email already exists
        if db.users.get_user_by_email(email):
            return None, "Email already registered"
        
        # Check password strength
        if len(password) < SecurityConfig.PASSWORD_MIN_LENGTH:
            return None, f"Password must be at least {SecurityConfig.PASSWORD_MIN_LENGTH} characters"
        
        # Create user
        user_id = generate_unique_id()
        role = detect_role_from_email(email)
        
        new_user = {
            'id': user_id,
            'username': email.split('@')[0],
            'email': email,
            'name': name,
            'password_hash': hash_password(password),
            'role': role,
            'provider': 'local'
        }
        
        db.users.create_user(new_user)
        log_info(f"New local user registered: {email} as {role}")
        return new_user, "Registration successful"
    
    @staticmethod
    def set_session(user):
        """Set user session"""
        session['user_id'] = user['id']
        session['email'] = user['email']
        session['name'] = user['name']
        session['role'] = user['role']
        session.permanent = True
        log_info(f"Session created for user: {user['email']}")
    
    @staticmethod
    def clear_session():
        """Clear user session"""
        email = session.get('email', 'unknown')
        session.clear()
        log_info(f"Session cleared for user: {email}")
    
    @staticmethod
    def is_authenticated():
        """Check if user is authenticated"""
        return 'user_id' in session
    
    @staticmethod
    def get_current_user():
        """Get current authenticated user"""
        if not AuthenticationManager.is_authenticated():
            return None
        
        user = db.users.get_user_by_id(session['user_id'])
        return user
    
    @staticmethod
    def get_current_user_email():
        """Get current user email"""
        return session.get('email')
    
    @staticmethod
    def get_current_user_role():
        """Get current user role"""
        return session.get('role', 'patient')
    
    @staticmethod
    def change_password(user_id, old_password, new_password):
        """Change user password"""
        
        user = db.users.get_user_by_id(user_id)
        
        if not user:
            return False, "User not found"
        
        if not user.get('password_hash'):
            return False, "User is OAuth-only and cannot change password"
        
        if not verify_password(old_password, user['password_hash']):
            return False, "Incorrect current password"
        
        if len(new_password) < SecurityConfig.PASSWORD_MIN_LENGTH:
            return False, f"Password must be at least {SecurityConfig.PASSWORD_MIN_LENGTH} characters"
        
        if old_password == new_password:
            return False, "New password must be different from current password"
        
        # Update password
        db.users.update_user(user_id, {
            'password_hash': hash_password(new_password)
        })
        
        log_info(f"Password changed for user: {user['email']}")
        return True, "Password changed successfully"
    
    @staticmethod
    def reset_password(email, new_password):
        """Reset user password (admin function)"""
        
        user = db.users.get_user_by_email(email)
        
        if not user:
            return False, "User not found"
        
        if len(new_password) < SecurityConfig.PASSWORD_MIN_LENGTH:
            return False, f"Password must be at least {SecurityConfig.PASSWORD_MIN_LENGTH} characters"
        
        # Update password
        db.users.update_user(user['id'], {
            'password_hash': hash_password(new_password)
        })
        
        log_info(f"Password reset for user: {email}")
        return True, "Password reset successfully"


# ============================================================================
# SESSION UTILITIES
# ============================================================================

def get_oauth_provider(provider_name):
    """Get OAuth provider instance"""
    if provider_name == 'google':
        return GoogleOAuthProvider()
    elif provider_name == 'microsoft':
        return MicrosoftOAuthProvider()
    else:
        return None

def generate_oauth_state():
    """Generate OAuth state for CSRF protection"""
    return generate_unique_id()

def verify_oauth_state(state, stored_state):
    """Verify OAuth state matches"""
    return state == stored_state
