"""
Two-Factor Authentication Module for Orthanc NAS Integration
Provides configurable 2FA options for administrators and users
"""

import pyotp
import qrcode
import io
import base64
import json
import sqlite3
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from flask import session, jsonify

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') or session.get('role') != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated_function

class TwoFactorMethod(Enum):
    TOTP = "totp"  # Time-based One-Time Password (Google Authenticator, Authy)
    SMS = "sms"    # SMS-based codes
    EMAIL = "email"  # Email-based codes
    BACKUP_CODES = "backup_codes"  # Static backup codes

@dataclass
class TwoFactorConfig:
    """Configuration for 2FA settings"""
    enabled: bool = False
    required_for_admin: bool = True
    required_for_users: bool = False
    allowed_methods: list = None
    totp_issuer: str = "Orthanc NAS"
    code_validity_seconds: int = 300  # 5 minutes
    backup_codes_count: int = 10
    max_failed_attempts: int = 3
    lockout_duration_minutes: int = 15

    def __post_init__(self):
        if self.allowed_methods is None:
            self.allowed_methods = [TwoFactorMethod.TOTP.value, TwoFactorMethod.BACKUP_CODES.value]

class TwoFactorAuth:
    """Main 2FA authentication handler"""
    
    def __init__(self, db_path: str = "orthanc_2fa.db"):
        self.db_path = db_path
        self.config = TwoFactorConfig()
        self._init_database()
    
    def _init_database(self):
        """Initialize the 2FA database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 2FA user settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_2fa (
                user_id TEXT PRIMARY KEY,
                totp_secret TEXT,
                backup_codes TEXT,  -- JSON array of hashed backup codes
                phone_number TEXT,
                email TEXT,
                enabled_methods TEXT,  -- JSON array of enabled methods
                is_setup_complete BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2FA attempts tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                method TEXT,
                success BOOLEAN,
                ip_address TEXT,
                user_agent TEXT,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_2fa (user_id)
            )
        ''')
        
        # 2FA configuration table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_2fa_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def update_config(self, config_dict: Dict[str, Any]) -> bool:
        """Update 2FA system configuration"""
        try:
            # Validate configuration
            for key, value in config_dict.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            config_json = json.dumps(config_dict)
            cursor.execute('''
                INSERT OR REPLACE INTO system_2fa_config (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', ('main_config', config_json, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating 2FA config: {e}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """Get current 2FA configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM system_2fa_config WHERE key = ?', ('main_config',))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        
        # Return default config
        return {
            'enabled': self.config.enabled,
            'required_for_admin': self.config.required_for_admin,
            'required_for_users': self.config.required_for_users,
            'allowed_methods': self.config.allowed_methods,
            'totp_issuer': self.config.totp_issuer,
            'code_validity_seconds': self.config.code_validity_seconds,
            'backup_codes_count': self.config.backup_codes_count,
            'max_failed_attempts': self.config.max_failed_attempts,
            'lockout_duration_minutes': self.config.lockout_duration_minutes
        }
    
    def setup_totp_for_user(self, user_id: str) -> Dict[str, str]:
        """Setup TOTP for a user and return QR code data"""
        # Generate a new secret
        secret = pyotp.random_base32()
        
        # Create TOTP instance
        totp = pyotp.TOTP(secret)
        
        # Generate provisioning URI for QR code
        provisioning_uri = totp.provisioning_uri(
            name=user_id,
            issuer_name=self.config.totp_issuer
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        # Convert QR code to base64 image
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # Store secret in database (temporarily, until user confirms setup)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_2fa (user_id, totp_secret, is_setup_complete)
            VALUES (?, ?, FALSE)
        ''', (user_id, secret))
        
        conn.commit()
        conn.close()
        
        return {
            'secret': secret,
            'qr_code': f"data:image/png;base64,{qr_code_base64}",
            'manual_entry_key': secret,
            'provisioning_uri': provisioning_uri
        }
    
    def verify_totp_setup(self, user_id: str, code: str) -> bool:
        """Verify TOTP code during initial setup"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT totp_secret FROM user_2fa WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
        
        secret = result[0]
        totp = pyotp.TOTP(secret)
        
        if totp.verify(code, valid_window=2):  # Allow 2 time windows for clock skew
            # Mark setup as complete and enable TOTP method
            enabled_methods = [TwoFactorMethod.TOTP.value]
            cursor.execute('''
                UPDATE user_2fa 
                SET is_setup_complete = TRUE, enabled_methods = ?, updated_at = ?
                WHERE user_id = ?
            ''', (json.dumps(enabled_methods), datetime.now().isoformat(), user_id))
            
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    
    def generate_backup_codes(self, user_id: str) -> list:
        """Generate backup codes for a user"""
        codes = []
        hashed_codes = []
        
        for _ in range(self.config.backup_codes_count):
            # Generate 8-digit backup code
            code = ''.join([str(secrets.randbelow(10)) for _ in range(8)])
            codes.append(code)
            
            # Hash the code for storage
            hashed_code = hashlib.sha256(code.encode()).hexdigest()
            hashed_codes.append(hashed_code)
        
        # Store hashed codes in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE user_2fa 
            SET backup_codes = ?, updated_at = ?
            WHERE user_id = ?
        ''', (json.dumps(hashed_codes), datetime.now().isoformat(), user_id))
        
        conn.commit()
        conn.close()
        
        return codes
    
    def verify_backup_code(self, user_id: str, code: str) -> bool:
        """Verify and consume a backup code"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT backup_codes FROM user_2fa WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            conn.close()
            return False
        
        hashed_codes = json.loads(result[0])
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        
        if code_hash in hashed_codes:
            # Remove the used code
            hashed_codes.remove(code_hash)
            
            cursor.execute('''
                UPDATE user_2fa 
                SET backup_codes = ?, updated_at = ?
                WHERE user_id = ?
            ''', (json.dumps(hashed_codes), datetime.now().isoformat(), user_id))
            
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    
    def verify_2fa_code(self, user_id: str, code: str, method: str, 
                       ip_address: str = None, user_agent: str = None) -> Tuple[bool, str]:
        """Verify a 2FA code for authentication"""
        
        # Check if user is locked out
        if self._is_user_locked_out(user_id):
            return False, "Account temporarily locked due to too many failed attempts"
        
        success = False
        error_message = "Invalid code"
        
        try:
            if method == TwoFactorMethod.TOTP.value:
                success = self._verify_totp_code(user_id, code)
            elif method == TwoFactorMethod.BACKUP_CODES.value:
                success = self.verify_backup_code(user_id, code)
            elif method == TwoFactorMethod.SMS.value:
                success = self._verify_sms_code(user_id, code)
            elif method == TwoFactorMethod.EMAIL.value:
                success = self._verify_email_code(user_id, code)
            else:
                error_message = "Unsupported 2FA method"
        
        except Exception as e:
            error_message = f"Verification error: {str(e)}"
        
        # Log the attempt
        self._log_auth_attempt(user_id, method, success, ip_address, user_agent)
        
        if success:
            return True, "Code verified successfully"
        else:
            return False, error_message
    
    def _verify_totp_code(self, user_id: str, code: str) -> bool:
        """Verify TOTP code"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT totp_secret FROM user_2fa WHERE user_id = ? AND is_setup_complete = TRUE', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False
        
        secret = result[0]
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=2)
    
    def _verify_sms_code(self, user_id: str, code: str) -> bool:
        """Verify SMS code (placeholder - implement with SMS service)"""
        # TODO: Implement SMS verification with service like Twilio
        # For now, return False as SMS is not implemented
        return False
    
    def _verify_email_code(self, user_id: str, code: str) -> bool:
        """Verify email code (placeholder - implement with email service)"""
        # TODO: Implement email verification
        # For now, return False as email is not implemented
        return False
    
    def _is_user_locked_out(self, user_id: str) -> bool:
        """Check if user is locked out due to failed attempts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check failed attempts in the last lockout duration
        lockout_start = datetime.now() - timedelta(minutes=self.config.lockout_duration_minutes)
        
        cursor.execute('''
            SELECT COUNT(*) FROM auth_attempts 
            WHERE user_id = ? AND success = FALSE AND attempted_at > ?
        ''', (user_id, lockout_start.isoformat()))
        
        failed_count = cursor.fetchone()[0]
        conn.close()
        
        return failed_count >= self.config.max_failed_attempts
    
    def _log_auth_attempt(self, user_id: str, method: str, success: bool, 
                         ip_address: str = None, user_agent: str = None):
        """Log authentication attempt"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO auth_attempts (user_id, method, success, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, method, success, ip_address, user_agent))
        
        conn.commit()
        conn.close()
    
    def get_user_2fa_status(self, user_id: str) -> Dict[str, Any]:
        """Get 2FA status for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT totp_secret, backup_codes, enabled_methods, is_setup_complete
            FROM user_2fa WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return {
                'setup_complete': False,
                'enabled_methods': [],
                'has_backup_codes': False,
                'backup_codes_remaining': 0
            }
        
        totp_secret, backup_codes, enabled_methods, is_setup_complete = result
        enabled_methods = json.loads(enabled_methods) if enabled_methods else []
        backup_codes = json.loads(backup_codes) if backup_codes else []
        
        return {
            'setup_complete': bool(is_setup_complete),
            'enabled_methods': enabled_methods,
            'has_backup_codes': len(backup_codes) > 0,
            'backup_codes_remaining': len(backup_codes)
        }
    
    def disable_2fa_for_user(self, user_id: str) -> bool:
        """Disable 2FA for a user (admin function)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM user_2fa WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error disabling 2FA for user {user_id}: {e}")
            return False
    
    def get_2fa_stats(self) -> Dict[str, Any]:
        """Get 2FA usage statistics for admin dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total users with 2FA enabled
        cursor.execute('SELECT COUNT(*) FROM user_2fa WHERE is_setup_complete = TRUE')
        users_with_2fa = cursor.fetchone()[0]
        
        # Recent authentication attempts
        cursor.execute('''
            SELECT COUNT(*) FROM auth_attempts 
            WHERE attempted_at > datetime('now', '-24 hours')
        ''')
        recent_attempts = cursor.fetchone()[0]
        
        # Failed attempts in last 24 hours
        cursor.execute('''
            SELECT COUNT(*) FROM auth_attempts 
            WHERE attempted_at > datetime('now', '-24 hours') AND success = FALSE
        ''')
        recent_failures = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'users_with_2fa_enabled': users_with_2fa,
            'recent_auth_attempts_24h': recent_attempts,
            'recent_failed_attempts_24h': recent_failures,
            'system_2fa_enabled': self.config.enabled,
            'admin_2fa_required': self.config.required_for_admin,
            'user_2fa_required': self.config.required_for_users
        }