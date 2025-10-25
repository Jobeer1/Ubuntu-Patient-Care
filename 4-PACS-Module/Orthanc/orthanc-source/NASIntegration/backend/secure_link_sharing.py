"""
Secure Link Sharing System for South African Medical Imaging
Time-limited, encrypted sharing of medical images and reports
"""

import os
import json
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import sqlite3
import logging
from dataclasses import dataclass, asdict
import base64
import qrcode
import io
from urllib.parse import urlencode
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("Warning: cryptography not available. Install with: pip install cryptography")

from .south_african_localization import sa_localization

@dataclass
class SecureLink:
    """Secure link data structure"""
    link_id: str
    resource_type: str  # 'image', 'study', 'report'
    resource_id: str
    created_by: str
    recipient_email: Optional[str]
    recipient_name: Optional[str]
    access_token: str
    encryption_key: str
    expires_at: str
    max_views: int
    current_views: int
    requires_password: bool
    password_hash: Optional[str]
    requires_identity_verification: bool
    allowed_ip_addresses: Optional[str]  # JSON array
    is_active: bool
    created_at: str
    last_accessed: Optional[str]
    access_log: str  # JSON array of access attempts
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        data = asdict(self)
        if not include_sensitive:
            # Remove sensitive information from API responses
            data.pop('encryption_key', None)
            data.pop('password_hash', None)
            data.pop('access_token', None)
        return data

@dataclass
class LinkAccess:
    """Link access attempt record"""
    access_id: str
    link_id: str
    ip_address: str
    user_agent: str
    success: bool
    failure_reason: Optional[str]
    accessed_at: str

class SecureLinkSharing:
    """Advanced secure link sharing system for medical content"""
    
    def __init__(self, db_path: str = "secure_links.db", base_url: str = "https://localhost:5000"):
        self.db_path = db_path
        self.base_url = base_url.rstrip('/')
        self.logger = self._setup_logging()
        self.encryption_key = self._get_or_create_master_key()
        self.fernet = Fernet(self.encryption_key) if CRYPTO_AVAILABLE else None
        self._init_database()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for secure link sharing"""
        logger = logging.getLogger('secure_links')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _init_database(self):
        """Initialize secure links database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Secure links table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS secure_links (
                link_id TEXT PRIMARY KEY,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                created_by TEXT NOT NULL,
                recipient_email TEXT,
                recipient_name TEXT,
                access_token TEXT UNIQUE NOT NULL,
                encryption_key TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                max_views INTEGER DEFAULT -1,
                current_views INTEGER DEFAULT 0,
                requires_password BOOLEAN DEFAULT FALSE,
                password_hash TEXT,
                requires_identity_verification BOOLEAN DEFAULT FALSE,
                allowed_ip_addresses TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP,
                access_log TEXT DEFAULT '[]'
            )
        ''')
        
        # Link access attempts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS link_access_attempts (
                access_id TEXT PRIMARY KEY,
                link_id TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                success BOOLEAN NOT NULL,
                failure_reason TEXT,
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (link_id) REFERENCES secure_links (link_id)
            )
        ''')
        
        # Shared content metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shared_content_metadata (
                content_id TEXT PRIMARY KEY,
                link_id TEXT NOT NULL,
                content_type TEXT NOT NULL,
                encrypted_content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (link_id) REFERENCES secure_links (link_id)
            )
        ''')
        
        # System settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sharing_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Initialize default settings
        default_settings = {
            'max_link_duration_hours': '168',  # 7 days
            'default_max_views': '10',
            'require_https': 'true',
            'enable_email_notifications': 'true',
            'enable_qr_codes': 'true',
            'enable_password_protection': 'true',
            'enable_ip_restrictions': 'true',
            'smtp_server': '',
            'smtp_port': '587',
            'smtp_username': '',
            'smtp_password': '',
            'from_email': 'noreply@orthanc-nas.local'
        }
        
        for key, value in default_settings.items():
            cursor.execute('''
                INSERT OR IGNORE INTO sharing_settings (setting_key, setting_value)
                VALUES (?, ?)
            ''', (key, value))
        
        conn.commit()
        conn.close()
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key"""
        key_file = "master_key.key"
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key() if CRYPTO_AVAILABLE else b'dummy_key_for_testing'
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def create_secure_link(self, resource_type: str, resource_id: str, created_by: str,
                          recipient_email: str = None, recipient_name: str = None,
                          expires_hours: int = 24, max_views: int = -1,
                          requires_password: bool = False, password: str = None,
                          requires_identity_verification: bool = False,
                          allowed_ip_addresses: List[str] = None) -> Optional[SecureLink]:
        """Create a new secure sharing link"""
        
        try:
            # Generate unique identifiers
            link_id = f"link_{secrets.token_hex(16)}"
            access_token = secrets.token_urlsafe(32)
            
            # Generate encryption key for this link
            link_encryption_key = Fernet.generate_key() if CRYPTO_AVAILABLE else b'dummy_key'
            
            # Calculate expiration
            expires_at = datetime.now() + timedelta(hours=expires_hours)
            
            # Hash password if provided
            password_hash = None
            if requires_password and password:
                password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), 
                                                  access_token.encode(), 100000).hex()
            
            # Create secure link object
            secure_link = SecureLink(
                link_id=link_id,
                resource_type=resource_type,
                resource_id=resource_id,
                created_by=created_by,
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                access_token=access_token,
                encryption_key=base64.b64encode(link_encryption_key).decode(),
                expires_at=expires_at.isoformat(),
                max_views=max_views,
                current_views=0,
                requires_password=requires_password,
                password_hash=password_hash,
                requires_identity_verification=requires_identity_verification,
                allowed_ip_addresses=json.dumps(allowed_ip_addresses) if allowed_ip_addresses else None,
                is_active=True,
                created_at=datetime.now().isoformat(),
                last_accessed=None,
                access_log='[]'
            )
            
            # Save to database
            if self._save_secure_link(secure_link):
                self.logger.info(f"Secure link created: {link_id} for {resource_type} {resource_id}")
                return secure_link
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create secure link: {e}")
            return None
    
    def _save_secure_link(self, link: SecureLink) -> bool:
        """Save secure link to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO secure_links (
                    link_id, resource_type, resource_id, created_by, recipient_email,
                    recipient_name, access_token, encryption_key, expires_at, max_views,
                    current_views, requires_password, password_hash, requires_identity_verification,
                    allowed_ip_addresses, is_active, created_at, last_accessed, access_log
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                link.link_id, link.resource_type, link.resource_id, link.created_by,
                link.recipient_email, link.recipient_name, link.access_token,
                link.encryption_key, link.expires_at, link.max_views, link.current_views,
                link.requires_password, link.password_hash, link.requires_identity_verification,
                link.allowed_ip_addresses, link.is_active, link.created_at,
                link.last_accessed, link.access_log
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save secure link: {e}")
            return False
    
    def validate_and_access_link(self, access_token: str, password: str = None,
                                ip_address: str = None, user_agent: str = None) -> Tuple[bool, Optional[SecureLink], str]:
        """Validate access token and return link if valid"""
        
        access_id = f"access_{secrets.token_hex(8)}"
        
        try:
            # Get link by access token
            link = self._get_link_by_token(access_token)
            
            if not link:
                self._log_access_attempt(access_id, None, ip_address, user_agent, False, "Invalid token")
                return False, None, "Invalid or expired link"
            
            # Check if link is active
            if not link.is_active:
                self._log_access_attempt(access_id, link.link_id, ip_address, user_agent, False, "Link deactivated")
                return False, None, "Link has been deactivated"
            
            # Check expiration
            if datetime.fromisoformat(link.expires_at) < datetime.now():
                self._deactivate_link(link.link_id)
                self._log_access_attempt(access_id, link.link_id, ip_address, user_agent, False, "Link expired")
                return False, None, "Link has expired"
            
            # Check view limit
            if link.max_views > 0 and link.current_views >= link.max_views:
                self._log_access_attempt(access_id, link.link_id, ip_address, user_agent, False, "View limit exceeded")
                return False, None, "Link has reached maximum view limit"
            
            # Check IP restrictions
            if link.allowed_ip_addresses and ip_address:
                allowed_ips = json.loads(link.allowed_ip_addresses)
                if ip_address not in allowed_ips:
                    self._log_access_attempt(access_id, link.link_id, ip_address, user_agent, False, "IP not allowed")
                    return False, None, "Access denied from this IP address"
            
            # Check password if required
            if link.requires_password:
                if not password:
                    self._log_access_attempt(access_id, link.link_id, ip_address, user_agent, False, "Password required")
                    return False, None, "Password required"
                
                # Verify password
                password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), 
                                                  access_token.encode(), 100000).hex()
                if password_hash != link.password_hash:
                    self._log_access_attempt(access_id, link.link_id, ip_address, user_agent, False, "Invalid password")
                    return False, None, "Invalid password"
            
            # Update access statistics
            self._update_link_access(link.link_id)
            self._log_access_attempt(access_id, link.link_id, ip_address, user_agent, True, None)
            
            return True, link, "Access granted"
            
        except Exception as e:
            self.logger.error(f"Link validation failed: {e}")
            self._log_access_attempt(access_id, None, ip_address, user_agent, False, f"System error: {str(e)}")
            return False, None, "System error"
    
    def _get_link_by_token(self, access_token: str) -> Optional[SecureLink]:
        """Get secure link by access token"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM secure_links WHERE access_token = ?', (access_token,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return SecureLink(
                    link_id=row[0], resource_type=row[1], resource_id=row[2],
                    created_by=row[3], recipient_email=row[4], recipient_name=row[5],
                    access_token=row[6], encryption_key=row[7], expires_at=row[8],
                    max_views=row[9], current_views=row[10], requires_password=bool(row[11]),
                    password_hash=row[12], requires_identity_verification=bool(row[13]),
                    allowed_ip_addresses=row[14], is_active=bool(row[15]),
                    created_at=row[16], last_accessed=row[17], access_log=row[18]
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get link by token: {e}")
            return None
    
    def _update_link_access(self, link_id: str):
        """Update link access statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE secure_links 
                SET current_views = current_views + 1, last_accessed = ?
                WHERE link_id = ?
            ''', (datetime.now().isoformat(), link_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to update link access: {e}")
    
    def _deactivate_link(self, link_id: str):
        """Deactivate a secure link"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('UPDATE secure_links SET is_active = FALSE WHERE link_id = ?', (link_id,))
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to deactivate link: {e}")
    
    def _log_access_attempt(self, access_id: str, link_id: str, ip_address: str,
                           user_agent: str, success: bool, failure_reason: str = None):
        """Log link access attempt"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO link_access_attempts (
                    access_id, link_id, ip_address, user_agent, success, failure_reason
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (access_id, link_id, ip_address, user_agent, success, failure_reason))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to log access attempt: {e}")
    
    def generate_share_url(self, link: SecureLink) -> str:
        """Generate the full sharing URL"""
        return f"{self.base_url}/share/{link.access_token}"
    
    def generate_qr_code(self, link: SecureLink) -> str:
        """Generate QR code for sharing link"""
        try:
            share_url = self.generate_share_url(link)
            
            # Create QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(share_url)
            qr.make(fit=True)
            
            # Convert to base64 image
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{qr_code_base64}"
            
        except Exception as e:
            self.logger.error(f"Failed to generate QR code: {e}")
            return ""
    
    def send_email_notification(self, link: SecureLink, custom_message: str = None) -> bool:
        """Send email notification with secure link"""
        if not link.recipient_email:
            return False
        
        try:
            # Get SMTP settings
            settings = self._get_smtp_settings()
            if not settings['smtp_server']:
                self.logger.warning("SMTP not configured, cannot send email")
                return False
            
            # Create email content
            subject = f"Secure Medical Image Share - {link.resource_type.title()}"
            
            # Generate email body
            share_url = self.generate_share_url(link)
            recipient_name = link.recipient_name or "Colleague"
            
            body = f"""
Dear {recipient_name},

You have been securely shared a medical {link.resource_type} via Orthanc NAS.

Access Link: {share_url}

Security Information:
- This link expires on: {datetime.fromisoformat(link.expires_at).strftime('%d/%m/%Y at %H:%M')}
- Maximum views allowed: {'Unlimited' if link.max_views == -1 else link.max_views}
- Password required: {'Yes' if link.requires_password else 'No'}

{custom_message or ''}

IMPORTANT SECURITY NOTICE:
This link contains protected health information (PHI). Please:
- Do not share this link with unauthorized individuals
- Access only from secure networks
- Delete this email after accessing the content
- Report any suspicious activity

This system complies with South African POPIA regulations and international healthcare privacy standards.

Best regards,
Orthanc NAS Medical Imaging System
"""
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = settings['from_email']
            msg['To'] = link.recipient_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(settings['smtp_server'], int(settings['smtp_port'])) as server:
                if settings['smtp_username']:
                    server.starttls()
                    server.login(settings['smtp_username'], settings['smtp_password'])
                
                server.send_message(msg)
            
            self.logger.info(f"Email notification sent for link {link.link_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
            return False
    
    def _get_smtp_settings(self) -> Dict[str, str]:
        """Get SMTP configuration settings"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            smtp_keys = ['smtp_server', 'smtp_port', 'smtp_username', 'smtp_password', 'from_email']
            settings = {}
            
            for key in smtp_keys:
                cursor.execute('SELECT setting_value FROM sharing_settings WHERE setting_key = ?', (key,))
                result = cursor.fetchone()
                settings[key] = result[0] if result else ''
            
            conn.close()
            return settings
            
        except Exception as e:
            self.logger.error(f"Failed to get SMTP settings: {e}")
            return {}
    
    def get_user_links(self, user_id: str, active_only: bool = True) -> List[SecureLink]:
        """Get all links created by a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = 'SELECT * FROM secure_links WHERE created_by = ?'
            params = [user_id]
            
            if active_only:
                query += ' AND is_active = TRUE'
            
            query += ' ORDER BY created_at DESC'
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            links = []
            for row in rows:
                links.append(SecureLink(
                    link_id=row[0], resource_type=row[1], resource_id=row[2],
                    created_by=row[3], recipient_email=row[4], recipient_name=row[5],
                    access_token=row[6], encryption_key=row[7], expires_at=row[8],
                    max_views=row[9], current_views=row[10], requires_password=bool(row[11]),
                    password_hash=row[12], requires_identity_verification=bool(row[13]),
                    allowed_ip_addresses=row[14], is_active=bool(row[15]),
                    created_at=row[16], last_accessed=row[17], access_log=row[18]
                ))
            
            return links
            
        except Exception as e:
            self.logger.error(f"Failed to get user links: {e}")
            return []
    
    def revoke_link(self, link_id: str, user_id: str) -> bool:
        """Revoke a secure link"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if user owns the link
            cursor.execute('SELECT created_by FROM secure_links WHERE link_id = ?', (link_id,))
            result = cursor.fetchone()
            
            if not result or result[0] != user_id:
                return False
            
            # Deactivate the link
            cursor.execute('UPDATE secure_links SET is_active = FALSE WHERE link_id = ?', (link_id,))
            conn.commit()
            conn.close()
            
            self.logger.info(f"Link revoked: {link_id} by user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to revoke link: {e}")
            return False
    
    def get_sharing_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get sharing statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            where_clause = "WHERE created_by = ?" if user_id else ""
            params = [user_id] if user_id else []
            
            # Total links
            cursor.execute(f'SELECT COUNT(*) FROM secure_links {where_clause}', params)
            total_links = cursor.fetchone()[0]
            
            # Active links
            cursor.execute(f'SELECT COUNT(*) FROM secure_links {where_clause} {"AND" if where_clause else "WHERE"} is_active = TRUE', params)
            active_links = cursor.fetchone()[0]
            
            # Recent links (last 7 days)
            cursor.execute(f'''
                SELECT COUNT(*) FROM secure_links 
                {where_clause} {"AND" if where_clause else "WHERE"} 
                created_at > datetime('now', '-7 days')
            ''', params)
            recent_links = cursor.fetchone()[0]
            
            # Total views
            cursor.execute(f'SELECT SUM(current_views) FROM secure_links {where_clause}', params)
            total_views = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'total_links': total_links,
                'active_links': active_links,
                'recent_links_7d': recent_links,
                'total_views': total_views
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get sharing stats: {e}")
            return {}

# Global secure link sharing instance
secure_link_sharing = SecureLinkSharing()