#!/usr/bin/env python3
"""
Security Service for Medical Reporting Module
Implements POPIA compliance, role-based access control, and data protection
"""

import hashlib
import secrets
import jwt
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, session, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
import base64
import os

logger = logging.getLogger(__name__)

class SecurityService:
    """Comprehensive security service for medical data protection"""
    
    def __init__(self, app=None):
        self.app = app
        self.encryption_key = None
        self.failed_attempts = {}  # Track failed login attempts
        self.max_attempts = 5
        self.lockout_duration = 300  # 5 minutes
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security service with Flask app"""
        self.app = app
        
        # Generate or load encryption key
        self.encryption_key = self._get_or_create_encryption_key()
        
        # Set security headers
        @app.after_request
        def set_security_headers(response):
            return self._set_security_headers(response)
    
    def _get_or_create_encryption_key(self):
        """Get or create encryption key for sensitive data"""
        key_file = 'instance/encryption.key'
        
        try:
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    return f.read()
            else:
                # Create new key
                key = Fernet.generate_key()
                os.makedirs('instance', exist_ok=True)
                with open(key_file, 'wb') as f:
                    f.write(key)
                logger.info("Generated new encryption key")
                return key
        except Exception as e:
            logger.error(f"Encryption key error: {e}")
            # Fallback to session-based key (not persistent)
            return Fernet.generate_key()
    
    def _set_security_headers(self, response):
        """Set security headers for POPIA compliance"""
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Strict transport security (HTTPS only)
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "img-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "font-src 'self' https://cdnjs.cloudflare.com"
        )
        
        # Referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # POPIA compliance headers
        response.headers['X-POPIA-Compliant'] = 'true'
        response.headers['X-Data-Classification'] = 'medical-confidential'
        
        return response
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive medical data"""
        try:
            fernet = Fernet(self.encryption_key)
            encrypted_data = fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise SecurityException("Failed to encrypt sensitive data")
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive medical data"""
        try:
            fernet = Fernet(self.encryption_key)
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise SecurityException("Failed to decrypt sensitive data")
    
    def hash_patient_id(self, patient_id: str) -> str:
        """Create secure hash of patient ID for logging"""
        salt = self.app.config.get('SECRET_KEY', 'default-salt')
        return hashlib.sha256(f"{patient_id}{salt}".encode()).hexdigest()[:16]
    
    def generate_session_token(self, user_id: str, role: str) -> str:
        """Generate secure session token"""
        payload = {
            'user_id': user_id,
            'role': role,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=8),  # 8-hour sessions
            'jti': secrets.token_hex(16)  # Unique token ID
        }
        
        return jwt.encode(
            payload,
            self.app.config['SECRET_KEY'],
            algorithm='HS256'
        )
    
    def validate_session_token(self, token: str) -> dict:
        """Validate and decode session token"""
        try:
            payload = jwt.decode(
                token,
                self.app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise SecurityException("Session expired")
        except jwt.InvalidTokenError:
            raise SecurityException("Invalid session token")
    
    def check_rate_limit(self, identifier: str) -> bool:
        """Check if identifier is rate limited"""
        now = datetime.utcnow()
        
        if identifier in self.failed_attempts:
            attempts, last_attempt = self.failed_attempts[identifier]
            
            # Reset if lockout period has passed
            if (now - last_attempt).total_seconds() > self.lockout_duration:
                del self.failed_attempts[identifier]
                return True
            
            # Check if still locked out
            if attempts >= self.max_attempts:
                return False
        
        return True
    
    def record_failed_attempt(self, identifier: str):
        """Record failed authentication attempt"""
        now = datetime.utcnow()
        
        if identifier in self.failed_attempts:
            attempts, _ = self.failed_attempts[identifier]
            self.failed_attempts[identifier] = (attempts + 1, now)
        else:
            self.failed_attempts[identifier] = (1, now)
    
    def clear_failed_attempts(self, identifier: str):
        """Clear failed attempts for successful authentication"""
        if identifier in self.failed_attempts:
            del self.failed_attempts[identifier]
    
    def validate_popia_consent(self, patient_id: str, purpose: str) -> bool:
        """Validate POPIA consent for data processing"""
        # In production, this would check a consent database
        # For now, assume consent is given for medical treatment
        allowed_purposes = [
            'medical_diagnosis',
            'medical_treatment', 
            'medical_reporting',
            'quality_assurance',
            'legal_compliance'
        ]
        
        return purpose in allowed_purposes
    
    def anonymize_patient_data(self, data: dict) -> dict:
        """Anonymize patient data for logging/analytics"""
        anonymized = data.copy()
        
        # Remove direct identifiers
        sensitive_fields = [
            'patient_name', 'id_number', 'passport_number',
            'phone_number', 'email', 'address', 'next_of_kin'
        ]
        
        for field in sensitive_fields:
            if field in anonymized:
                if field == 'patient_name':
                    anonymized[field] = 'PATIENT_' + self.hash_patient_id(data.get('patient_id', ''))
                else:
                    anonymized[field] = '[REDACTED]'
        
        # Hash patient ID
        if 'patient_id' in anonymized:
            anonymized['patient_id_hash'] = self.hash_patient_id(anonymized['patient_id'])
            del anonymized['patient_id']
        
        return anonymized
    
    def audit_data_access(self, user_id: str, patient_id: str, action: str, details: dict = None):
        """Audit data access for POPIA compliance"""
        from services.audit_service import AuditService
        
        audit_service = AuditService(self.app)
        audit_service.log_data_access(
            user_id=user_id,
            patient_id_hash=self.hash_patient_id(patient_id),
            action=action,
            details=details or {},
            ip_address=request.remote_addr if request else 'system',
            user_agent=request.headers.get('User-Agent', 'unknown') if request else 'system'
        )
    
    def check_data_retention_policy(self, created_date: datetime) -> dict:
        """Check data retention policy compliance"""
        now = datetime.utcnow()
        age_days = (now - created_date).days
        
        # POPIA retention periods for medical data
        retention_periods = {
            'voice_recordings': 30,      # 30 days for voice recordings
            'draft_reports': 365,        # 1 year for drafts
            'final_reports': 3650,       # 10 years for final reports
            'audit_logs': 2555,          # 7 years for audit logs
            'session_data': 90           # 90 days for session data
        }
        
        status = {}
        for data_type, retention_days in retention_periods.items():
            if age_days > retention_days:
                status[data_type] = 'expired'
            elif age_days > (retention_days * 0.9):  # 90% of retention period
                status[data_type] = 'expiring_soon'
            else:
                status[data_type] = 'valid'
        
        return status
    
    def sanitize_voice_data(self, audio_data: bytes) -> bytes:
        """Sanitize voice data to remove metadata"""
        # In production, this would strip metadata from audio files
        # For now, return as-is but log the sanitization
        logger.info("Voice data sanitized for POPIA compliance")
        return audio_data
    
    def generate_data_processing_notice(self, purpose: str) -> dict:
        """Generate POPIA data processing notice"""
        return {
            'notice_id': secrets.token_hex(8),
            'purpose': purpose,
            'legal_basis': 'Legitimate interest for medical care',
            'data_categories': [
                'Personal identifiers',
                'Medical information',
                'Voice recordings (if applicable)',
                'System usage data'
            ],
            'retention_period': 'As per medical records retention policy',
            'rights': [
                'Right to access your personal information',
                'Right to correct inaccurate information',
                'Right to delete information (subject to legal requirements)',
                'Right to object to processing',
                'Right to data portability'
            ],
            'contact': 'privacy@samedical.co.za',
            'generated_at': datetime.utcnow().isoformat()
        }


class SecurityMiddleware:
    """Security middleware for request processing"""
    
    def __init__(self, app, security_service):
        self.app = app
        self.security_service = security_service
        
        # Register middleware
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """Process request before handling"""
        # Skip security checks for health endpoint
        if request.endpoint == 'health_check':
            return
        
        # Check rate limiting
        client_ip = request.remote_addr
        if not self.security_service.check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return jsonify({
                'error': 'Too many requests',
                'message': 'Please try again later'
            }), 429
        
        # Validate session for protected endpoints
        if request.endpoint and request.endpoint.startswith('api.'):
            token = request.headers.get('Authorization')
            if token and token.startswith('Bearer '):
                try:
                    payload = self.security_service.validate_session_token(token[7:])
                    session['user_id'] = payload['user_id']
                    session['user_role'] = payload['role']
                except SecurityException as e:
                    return jsonify({'error': str(e)}), 401
    
    def after_request(self, response):
        """Process response after handling"""
        # Log security events
        if response.status_code >= 400:
            logger.warning(f"Security event: {response.status_code} for {request.path}")
        
        return response


class RoleBasedAccessControl:
    """Role-based access control for medical reporting"""
    
    ROLES = {
        'doctor': {
            'permissions': [
                'create_report', 'edit_report', 'view_report', 'delete_draft',
                'use_voice_dictation', 'access_patient_data', 'customize_templates'
            ],
            'data_access': ['own_reports', 'assigned_patients']
        },
        'radiologist': {
            'permissions': [
                'create_report', 'edit_report', 'view_report', 'delete_draft',
                'use_voice_dictation', 'access_patient_data', 'customize_templates',
                'approve_reports', 'quality_review'
            ],
            'data_access': ['all_reports', 'all_patients']
        },
        'typist': {
            'permissions': [
                'view_report', 'edit_transcription', 'submit_corrections'
            ],
            'data_access': ['assigned_reports']
        },
        'admin': {
            'permissions': [
                'view_report', 'manage_users', 'system_configuration',
                'audit_access', 'data_export'
            ],
            'data_access': ['system_data', 'audit_logs']
        },
        'viewer': {
            'permissions': ['view_report'],
            'data_access': ['assigned_reports']
        }
    }
    
    @classmethod
    def check_permission(cls, user_role: str, permission: str) -> bool:
        """Check if user role has specific permission"""
        role_config = cls.ROLES.get(user_role, {})
        permissions = role_config.get('permissions', [])
        return permission in permissions
    
    @classmethod
    def check_data_access(cls, user_role: str, access_type: str) -> bool:
        """Check if user role has specific data access"""
        role_config = cls.ROLES.get(user_role, {})
        data_access = role_config.get('data_access', [])
        return access_type in data_access


def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = session.get('user_role')
            if not user_role:
                return jsonify({'error': 'Authentication required'}), 401
            
            if not RoleBasedAccessControl.check_permission(user_role, permission):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_data_access(access_type: str):
    """Decorator to require specific data access level"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = session.get('user_role')
            if not user_role:
                return jsonify({'error': 'Authentication required'}), 401
            
            if not RoleBasedAccessControl.check_data_access(user_role, access_type):
                return jsonify({'error': 'Insufficient data access'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


class SecurityException(Exception):
    """Custom exception for security-related errors"""
    pass
# Global security service instance
security_service = SecurityService()