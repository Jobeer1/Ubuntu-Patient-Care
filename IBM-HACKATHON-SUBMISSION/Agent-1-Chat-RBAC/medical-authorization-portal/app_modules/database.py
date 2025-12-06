"""
Database Module - SQLite Operations & Schema Management
======================================================
Handles all database initialization, queries, and schema management
Abstracted layer for easy migration to other databases
"""

import sqlite3
import uuid
from datetime import datetime
from contextlib import contextmanager
from app_modules.config import DatabaseConfig, SecurityConfig

# ============================================================================
# DATABASE CONNECTION MANAGEMENT
# ============================================================================

class DatabaseConnection:
    """Manage SQLite database connections"""
    
    def __init__(self, db_file=DatabaseConfig.DATABASE_FILE):
        self.db_file = db_file
        self.timeout = DatabaseConfig.TIMEOUT
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_file, timeout=self.timeout)
        conn.row_factory = sqlite3.Row  # Access columns by name
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query, params=None):
        """Execute SELECT query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
    
    def execute_single(self, query, params=None):
        """Execute SELECT query and return single result"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchone()
    
    def execute_update(self, query, params=None):
        """Execute INSERT/UPDATE/DELETE query"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.rowcount

# ============================================================================
# DATABASE SCHEMA INITIALIZATION
# ============================================================================

class DatabaseSchema:
    """Initialize and manage database schema"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def init_db(self):
        """Initialize all database tables"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT DEFAULT 'patient',
                phone TEXT,
                date_of_birth TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )''')
            
            # Chat history table
            cursor.execute('''CREATE TABLE IF NOT EXISTS chat_history (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )''')
            
            # Authorizations table
            cursor.execute('''CREATE TABLE IF NOT EXISTS authorizations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                patient_id TEXT,
                procedure TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                ai_confidence FLOAT,
                ai_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )''')
            
            # Appointments table
            cursor.execute('''CREATE TABLE IF NOT EXISTS appointments (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                specialty TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT DEFAULT 'scheduled',
                doctor_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(doctor_id) REFERENCES users(id)
            )''')
            
            # Audit log table
            cursor.execute('''CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )''')
            
            conn.commit()

# ============================================================================
# USER OPERATIONS
# ============================================================================

class UserOperations:
    """User-related database operations"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create_user(self, username, email, password_hash, role='patient'):
        """Create new user"""
        user_id = str(uuid.uuid4())
        query = '''INSERT INTO users (id, username, email, password_hash, role)
                   VALUES (?, ?, ?, ?, ?)'''
        self.db.execute_update(query, (user_id, username, email, password_hash, role))
        return user_id
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        query = 'SELECT * FROM users WHERE id = ?'
        result = self.db.execute_single(query, (user_id,))
        return self._row_to_dict(result) if result else None
    
    def get_user_by_email(self, email):
        """Get user by email"""
        query = 'SELECT * FROM users WHERE email = ?'
        result = self.db.execute_single(query, (email,))
        return self._row_to_dict(result) if result else None
    
    def get_user_by_username(self, username):
        """Get user by username"""
        query = 'SELECT * FROM users WHERE username = ?'
        result = self.db.execute_single(query, (username,))
        return self._row_to_dict(result) if result else None
    
    def update_user(self, user_id, **kwargs):
        """Update user fields"""
        allowed_fields = ['email', 'phone', 'date_of_birth', 'role', 'is_active']
        fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not fields:
            return 0
        
        set_clause = ', '.join([f'{k} = ?' for k in fields.keys()])
        values = list(fields.values()) + [user_id]
        query = f'UPDATE users SET {set_clause} WHERE id = ?'
        return self.db.execute_update(query, values)
    
    def update_last_login(self, user_id):
        """Update user's last login timestamp"""
        query = 'UPDATE users SET last_login = ? WHERE id = ?'
        return self.db.execute_update(query, (datetime.now(), user_id))
    
    def _row_to_dict(self, row):
        """Convert sqlite3.Row to dictionary"""
        return dict(row) if row else None

# ============================================================================
# CHAT OPERATIONS
# ============================================================================

class ChatOperations:
    """Chat history database operations"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def save_chat(self, user_id, message, response, context=None):
        """Save chat message and response"""
        chat_id = str(uuid.uuid4())
        query = '''INSERT INTO chat_history (id, user_id, message, response, context)
                   VALUES (?, ?, ?, ?, ?)'''
        self.db.execute_update(query, (chat_id, user_id, message, response, context))
        return chat_id
    
    def get_chat_history(self, user_id, limit=50):
        """Get user's chat history"""
        query = '''SELECT * FROM chat_history 
                   WHERE user_id = ? 
                   ORDER BY created_at DESC 
                   LIMIT ?'''
        results = self.db.execute_query(query, (user_id, limit))
        return [dict(row) for row in results]

# ============================================================================
# AUTHORIZATION OPERATIONS
# ============================================================================

class AuthorizationOperations:
    """Authorization/Pre-auth database operations"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create_authorization(self, user_id, procedure, patient_id=None, status='pending'):
        """Create new authorization request"""
        auth_id = str(uuid.uuid4())
        query = '''INSERT INTO authorizations (id, user_id, patient_id, procedure, status)
                   VALUES (?, ?, ?, ?, ?)'''
        self.db.execute_update(query, (auth_id, user_id, patient_id, procedure, status))
        return auth_id
    
    def get_authorization(self, auth_id):
        """Get authorization by ID"""
        query = 'SELECT * FROM authorizations WHERE id = ?'
        result = self.db.execute_single(query, (auth_id,))
        return dict(result) if result else None
    
    def get_user_authorizations(self, user_id, limit=10):
        """Get user's authorizations"""
        query = '''SELECT * FROM authorizations 
                   WHERE user_id = ? 
                   ORDER BY created_at DESC 
                   LIMIT ?'''
        results = self.db.execute_query(query, (user_id, limit))
        return [dict(row) for row in results]
    
    def update_authorization(self, auth_id, status=None, ai_confidence=None, ai_notes=None):
        """Update authorization status"""
        updates = []
        values = []
        
        if status is not None:
            updates.append('status = ?')
            values.append(status)
        if ai_confidence is not None:
            updates.append('ai_confidence = ?')
            values.append(ai_confidence)
        if ai_notes is not None:
            updates.append('ai_notes = ?')
            values.append(ai_notes)
        
        if not updates:
            return 0
        
        updates.append('updated_at = ?')
        values.append(datetime.now())
        values.append(auth_id)
        
        query = f"UPDATE authorizations SET {', '.join(updates)} WHERE id = ?"
        return self.db.execute_update(query, values)

# ============================================================================
# APPOINTMENT OPERATIONS
# ============================================================================

class AppointmentOperations:
    """Appointment database operations"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def create_appointment(self, user_id, specialty, date, time, reason):
        """Create new appointment"""
        apt_id = str(uuid.uuid4())
        query = '''INSERT INTO appointments (id, user_id, specialty, date, time, reason)
                   VALUES (?, ?, ?, ?, ?, ?)'''
        self.db.execute_update(query, (apt_id, user_id, specialty, date, time, reason))
        return apt_id
    
    def get_user_appointments(self, user_id, limit=10):
        """Get user's appointments"""
        query = '''SELECT * FROM appointments 
                   WHERE user_id = ? 
                   ORDER BY date DESC 
                   LIMIT ?'''
        results = self.db.execute_query(query, (user_id, limit))
        return [dict(row) for row in results]
    
    def get_appointment(self, apt_id):
        """Get appointment by ID"""
        query = 'SELECT * FROM appointments WHERE id = ?'
        result = self.db.execute_single(query, (apt_id,))
        return dict(result) if result else None
    
    def update_appointment_status(self, apt_id, status):
        """Update appointment status"""
        query = 'UPDATE appointments SET status = ?, updated_at = ? WHERE id = ?'
        return self.db.execute_update(query, (status, datetime.now(), apt_id))

# ============================================================================
# AUDIT LOG OPERATIONS
# ============================================================================

class AuditLogOperations:
    """Audit logging database operations"""
    
    def __init__(self):
        self.db = DatabaseConnection()
    
    def log_action(self, user_id, action, resource_type=None, resource_id=None, details=None):
        """Log user action for audit trail"""
        log_id = str(uuid.uuid4())
        query = '''INSERT INTO audit_log (id, user_id, action, resource_type, resource_id, details)
                   VALUES (?, ?, ?, ?, ?, ?)'''
        self.db.execute_update(query, (log_id, user_id, action, resource_type, resource_id, details))
        return log_id

# ============================================================================
# DATABASE FACTORY
# ============================================================================

class Database:
    """Factory class for all database operations"""
    
    def __init__(self):
        self.users = UserOperations()
        self.chat = ChatOperations()
        self.authorizations = AuthorizationOperations()
        self.appointments = AppointmentOperations()
        self.audit = AuditLogOperations()
        self.schema = DatabaseSchema()
    
    def initialize(self):
        """Initialize database schema"""
        self.schema.init_db()

# Create singleton instance
db = Database()
db.initialize()
