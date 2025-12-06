"""
User Database Management for Orthanc NAS Integration
Handles user accounts, roles, authentication, and profile management
"""

import sqlite3
import hashlib
import secrets
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"  # Read-only access

@dataclass
class User:
    """User data class"""
    user_id: str
    username: str
    email: str
    role: str
    pin_hash: str = ""
    face_embedding: str = ""  # JSON string of face embedding vector
    phone_number: str = ""
    enabled_auth_methods: str = ""  # JSON array of enabled methods
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""
    last_login: str = ""
    login_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding sensitive data"""
        data = asdict(self)
        # Remove sensitive fields
        data.pop('pin_hash', None)
        data.pop('face_embedding', None)
        return data

class UserDatabase:
    """User database management class"""
    
    def __init__(self, db_path: str = "orthanc_users.db"):
        self.db_path = db_path
        self.logger = self._setup_logging()
        self._init_database()
        self._create_default_admin()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for user database operations"""
        logger = logging.getLogger('user_db')
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
        """Initialize the user database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                pin_hash TEXT NOT NULL,
                face_embedding TEXT,
                phone_number TEXT,
                enabled_auth_methods TEXT DEFAULT '["pin"]',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                login_count INTEGER DEFAULT 0
            )
        ''')
        
        # User sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Login attempts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                ip_address TEXT,
                user_agent TEXT,
                success BOOLEAN,
                failure_reason TEXT,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                theme TEXT DEFAULT 'light',
                language TEXT DEFAULT 'en',
                timezone TEXT DEFAULT 'UTC',
                notifications_enabled BOOLEAN DEFAULT TRUE,
                preferences_json TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _create_default_admin(self):
        """Create default admin user if none exists"""
        try:
            if not self.get_user_by_username('admin'):
                admin_user = User(
                    user_id=self._generate_user_id(),
                    username='admin',
                    email='admin@orthanc-nas.local',
                    role=UserRole.ADMIN.value,
                    pin_hash=self._hash_pin('admin123'),  # Default PIN
                    enabled_auth_methods='["pin"]',
                    created_at=datetime.now().isoformat()
                )
                
                if self.create_user(admin_user):
                    self.logger.info("Default admin user created (username: admin, pin: admin123)")
                    
        except Exception as e:
            self.logger.error(f"Failed to create default admin: {e}")
    
    def _generate_user_id(self) -> str:
        """Generate unique user ID"""
        return f"user_{secrets.token_hex(8)}"
    
    def _hash_pin(self, pin: str) -> str:
        """Hash PIN with salt"""
        salt = secrets.token_hex(16)
        pin_hash = hashlib.pbkdf2_hmac('sha256', pin.encode(), salt.encode(), 100000)
        return f"{salt}:{pin_hash.hex()}"
    
    def _verify_pin(self, pin: str, pin_hash: str) -> bool:
        """Verify PIN against hash"""
        try:
            salt, stored_hash = pin_hash.split(':')
            pin_hash_check = hashlib.pbkdf2_hmac('sha256', pin.encode(), salt.encode(), 100000)
            return pin_hash_check.hex() == stored_hash
        except Exception:
            return False
    
    def create_user(self, user: User) -> bool:
        """Create a new user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Set timestamps
            now = datetime.now().isoformat()
            user.created_at = now
            user.updated_at = now
            
            cursor.execute('''
                INSERT INTO users (
                    user_id, username, email, role, pin_hash, face_embedding,
                    phone_number, enabled_auth_methods, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user.user_id, user.username, user.email, user.role, user.pin_hash,
                user.face_embedding, user.phone_number, user.enabled_auth_methods,
                user.is_active, user.created_at, user.updated_at
            ))
            
            # Create default preferences
            cursor.execute('''
                INSERT INTO user_preferences (user_id) VALUES (?)
            ''', (user.user_id,))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"User created: {user.username} ({user.role})")
            return True
            
        except sqlite3.IntegrityError as e:
            self.logger.error(f"User creation failed - integrity error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"User creation failed: {e}")
            return False
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return User(*row)
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get user by ID {user_id}: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return User(*row)
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get user by username {username}: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return User(*row)
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get user by email {email}: {e}")
            return None
    
    def update_user(self, user: User) -> bool:
        """Update user information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            user.updated_at = datetime.now().isoformat()
            
            cursor.execute('''
                UPDATE users SET
                    username = ?, email = ?, role = ?, pin_hash = ?, face_embedding = ?,
                    phone_number = ?, enabled_auth_methods = ?, is_active = ?, updated_at = ?
                WHERE user_id = ?
            ''', (
                user.username, user.email, user.role, user.pin_hash, user.face_embedding,
                user.phone_number, user.enabled_auth_methods, user.is_active,
                user.updated_at, user.user_id
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"User updated: {user.username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update user {user.username}: {e}")
            return False
    
    def delete_user(self, user_id: str) -> bool:
        """Delete user (soft delete by deactivating)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET is_active = FALSE, updated_at = ?
                WHERE user_id = ?
            ''', (datetime.now().isoformat(), user_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"User deactivated: {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete user {user_id}: {e}")
            return False
    
    def list_users(self, include_inactive: bool = False) -> List[User]:
        """List all users"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if include_inactive:
                cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            else:
                cursor.execute('SELECT * FROM users WHERE is_active = TRUE ORDER BY created_at DESC')
            
            rows = cursor.fetchall()
            conn.close()
            
            return [User(*row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"Failed to list users: {e}")
            return []
    
    def authenticate_user(self, username: str, pin: str, ip_address: str = None, 
                         user_agent: str = None) -> Tuple[bool, Optional[User], str]:
        """Authenticate user with username and PIN"""
        try:
            user = self.get_user_by_username(username)
            
            if not user:
                self._log_login_attempt(username, ip_address, user_agent, False, "User not found")
                return False, None, "Invalid credentials"
            
            if not user.is_active:
                self._log_login_attempt(username, ip_address, user_agent, False, "User inactive")
                return False, None, "Account is inactive"
            
            if not self._verify_pin(pin, user.pin_hash):
                self._log_login_attempt(username, ip_address, user_agent, False, "Invalid PIN")
                return False, None, "Invalid credentials"
            
            # Update login statistics
            self._update_login_stats(user.user_id)
            
            # Log successful attempt
            self._log_login_attempt(username, ip_address, user_agent, True, "Success")
            
            return True, user, "Authentication successful"
            
        except Exception as e:
            self.logger.error(f"Authentication failed for {username}: {e}")
            return False, None, "Authentication error"
    
    def _update_login_stats(self, user_id: str):
        """Update user login statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET
                    last_login = ?,
                    login_count = login_count + 1
                WHERE user_id = ?
            ''', (datetime.now().isoformat(), user_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to update login stats for {user_id}: {e}")
    
    def _log_login_attempt(self, username: str, ip_address: str, user_agent: str, 
                          success: bool, failure_reason: str = None):
        """Log login attempt"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO login_attempts (username, ip_address, user_agent, success, failure_reason)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, ip_address, user_agent, success, failure_reason))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to log login attempt: {e}")
    
    def create_session(self, user_id: str, ip_address: str = None, 
                      user_agent: str = None, duration_hours: int = 8) -> str:
        """Create user session"""
        try:
            session_id = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=duration_hours)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Invalidate existing sessions for single-session enforcement
            cursor.execute('''
                UPDATE user_sessions SET is_active = FALSE
                WHERE user_id = ? AND is_active = TRUE
            ''', (user_id,))
            
            # Create new session
            cursor.execute('''
                INSERT INTO user_sessions (session_id, user_id, expires_at, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, user_id, expires_at.isoformat(), ip_address, user_agent))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Session created for user {user_id}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to create session for {user_id}: {e}")
            return ""
    
    def validate_session(self, session_id: str) -> Optional[User]:
        """Validate user session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.user_id, s.expires_at, u.*
                FROM user_sessions s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.session_id = ? AND s.is_active = TRUE
            ''', (session_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            user_id, expires_at = row[0], row[1]
            user_data = row[2:]
            
            # Check if session has expired
            if datetime.fromisoformat(expires_at) < datetime.now():
                self.invalidate_session(session_id)
                return None
            
            return User(*user_data)
            
        except Exception as e:
            self.logger.error(f"Failed to validate session {session_id}: {e}")
            return None
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate user session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_sessions SET is_active = FALSE
                WHERE session_id = ?
            ''', (session_id,))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to invalidate session {session_id}: {e}")
            return False
    
    def invalidate_user_sessions(self, user_id: str) -> bool:
        """Invalidate all sessions for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_sessions SET is_active = FALSE
                WHERE user_id = ?
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"All sessions invalidated for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to invalidate sessions for {user_id}: {e}")
            return False
    
    def update_user_pin(self, user_id: str, new_pin: str) -> bool:
        """Update user PIN"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            user.pin_hash = self._hash_pin(new_pin)
            return self.update_user(user)
            
        except Exception as e:
            self.logger.error(f"Failed to update PIN for {user_id}: {e}")
            return False
    
    def update_user_auth_methods(self, user_id: str, methods: List[str]) -> bool:
        """Update user's enabled authentication methods"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            user.enabled_auth_methods = json.dumps(methods)
            return self.update_user(user)
            
        except Exception as e:
            self.logger.error(f"Failed to update auth methods for {user_id}: {e}")
            return False
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT theme, language, timezone, notifications_enabled, preferences_json
                FROM user_preferences WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                preferences = {
                    'theme': row[0],
                    'language': row[1],
                    'timezone': row[2],
                    'notifications_enabled': bool(row[3]),
                    'custom': json.loads(row[4]) if row[4] else {}
                }
                return preferences
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Failed to get preferences for {user_id}: {e}")
            return {}
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_preferences SET
                    theme = ?, language = ?, timezone = ?, 
                    notifications_enabled = ?, preferences_json = ?
                WHERE user_id = ?
            ''', (
                preferences.get('theme', 'light'),
                preferences.get('language', 'en'),
                preferences.get('timezone', 'UTC'),
                preferences.get('notifications_enabled', True),
                json.dumps(preferences.get('custom', {})),
                user_id
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update preferences for {user_id}: {e}")
            return False
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total users
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = TRUE')
            total_users = cursor.fetchone()[0]
            
            # Users by role
            cursor.execute('''
                SELECT role, COUNT(*) FROM users WHERE is_active = TRUE GROUP BY role
            ''')
            users_by_role = dict(cursor.fetchall())
            
            # Recent logins (last 24 hours)
            cursor.execute('''
                SELECT COUNT(*) FROM login_attempts 
                WHERE success = TRUE AND attempted_at > datetime('now', '-24 hours')
            ''')
            recent_logins = cursor.fetchone()[0]
            
            # Failed login attempts (last 24 hours)
            cursor.execute('''
                SELECT COUNT(*) FROM login_attempts 
                WHERE success = FALSE AND attempted_at > datetime('now', '-24 hours')
            ''')
            failed_logins = cursor.fetchone()[0]
            
            # Active sessions
            cursor.execute('''
                SELECT COUNT(*) FROM user_sessions 
                WHERE is_active = TRUE AND expires_at > datetime('now')
            ''')
            active_sessions = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_users': total_users,
                'users_by_role': users_by_role,
                'recent_logins_24h': recent_logins,
                'failed_logins_24h': failed_logins,
                'active_sessions': active_sessions
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get user stats: {e}")
            return {}

# Global user database instance
user_db = UserDatabase()