"""
Advanced User and Group Management System for South African Healthcare
Provides Active Directory-like functionality with local healthcare context
"""

import sqlite3
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import bcrypt
import logging
from dataclasses import dataclass, asdict
from enum import Enum

# South African healthcare-specific imports
import re

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """Healthcare roles specific to South African medical practice"""
    ADMIN = "admin"
    RADIOLOGIST = "radiologist"
    SPECIALIST = "specialist"  # Cardiologist, Orthopaedic, etc.
    GP = "gp"  # General Practitioner
    REGISTRAR = "registrar"  # Medical specialist in training
    MEDICAL_OFFICER = "medical_officer"
    NURSING_SISTER = "nursing_sister"
    PROFESSIONAL_NURSE = "professional_nurse"
    TYPIST = "typist"
    RADIOGRAPHER = "radiographer"
    THEATRE_NURSE = "theatre_nurse"
    PATIENT = "patient"
    STUDENT = "student"  # Medical students
    INTERN = "intern"  # Medical interns
    COMMUNITY_SERVICE = "community_service"  # Community service doctors
    LOCUM = "locum"  # Locum tenens
    BIOMEDICAL_ENGINEER = "biomedical_engineer"

class Province(Enum):
    """South African provinces for healthcare administration"""
    GAUTENG = "gauteng"
    WESTERN_CAPE = "western_cape"
    KWAZULU_NATAL = "kwazulu_natal"
    EASTERN_CAPE = "eastern_cape"
    LIMPOPO = "limpopo"
    MPUMALANGA = "mpumalanga"
    NORTH_WEST = "north_west"
    FREE_STATE = "free_state"
    NORTHERN_CAPE = "northern_cape"

class FacilityType(Enum):
    """Healthcare facility types in South Africa"""
    ACADEMIC_HOSPITAL = "academic_hospital"  # Groote Schuur, Charlotte Maxeke
    TERTIARY_HOSPITAL = "tertiary_hospital"
    REGIONAL_HOSPITAL = "regional_hospital"
    DISTRICT_HOSPITAL = "district_hospital"
    COMMUNITY_HEALTH_CENTRE = "community_health_centre"
    PRIVATE_HOSPITAL = "private_hospital"
    PRIVATE_PRACTICE = "private_practice"
    MOBILE_CLINIC = "mobile_clinic"
    CLINIC = "clinic"

@dataclass
class SAHealthcareUser:
    """User model tailored for South African healthcare system"""
    id: str
    username: str
    hashed_password: str
    email: str
    role: UserRole
    practice_number: Optional[str] = None  # HPCSA practice number
    facility_name: str = ""
    facility_type: FacilityType = FacilityType.CLINIC
    province: Province = Province.GAUTENG
    department: str = ""
    specialization: str = ""
    language_preference: str = "english"  # english, afrikaans, zulu, xhosa, sotho
    two_factor_enabled: bool = False
    face_recognition_enabled: bool = False
    created_at: datetime = None
    last_login: Optional[datetime] = None
    is_active: bool = True
    session_token: Optional[str] = None
    permissions: List[str] = None
    groups: List[str] = None
    medical_aid_schemes: List[str] = None  # Discovery, Momentum, etc.
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.permissions is None:
            self.permissions = []
        if self.groups is None:
            self.groups = []
        if self.medical_aid_schemes is None:
            self.medical_aid_schemes = []

@dataclass
class SAHealthcareGroup:
    """Group model for South African healthcare organizations"""
    id: str
    name: str
    description: str
    facility_name: str
    province: Province
    group_type: str  # department, ward, practice_group, etc.
    permissions: List[str]
    created_at: datetime = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class SAUserGroupManager:
    """Advanced user and group management for South African healthcare"""
    
    def __init__(self, db_path: str = "sa_healthcare_users.db"):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Initialize database with South African healthcare schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table with SA healthcare fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL,
                practice_number TEXT,
                facility_name TEXT NOT NULL,
                facility_type TEXT NOT NULL,
                province TEXT NOT NULL,
                department TEXT,
                specialization TEXT,
                language_preference TEXT DEFAULT 'english',
                two_factor_enabled BOOLEAN DEFAULT FALSE,
                face_recognition_enabled BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                session_token TEXT,
                medical_aid_schemes TEXT  -- JSON array
            )
        ''')
        
        # Groups table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                facility_name TEXT NOT NULL,
                province TEXT NOT NULL,
                group_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # User permissions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_permissions (
                user_id TEXT,
                permission TEXT,
                granted_by TEXT,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                PRIMARY KEY (user_id, permission)
            )
        ''')
        
        # Group permissions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_permissions (
                group_id TEXT,
                permission TEXT,
                granted_by TEXT,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups (id),
                PRIMARY KEY (group_id, permission)
            )
        ''')
        
        # User group memberships
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_groups (
                user_id TEXT,
                group_id TEXT,
                added_by TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (group_id) REFERENCES groups (id),
                PRIMARY KEY (user_id, group_id)
            )
        ''')
        
        # Audit log for South African compliance
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                action TEXT NOT NULL,
                resource TEXT,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                province TEXT,
                facility_name TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Create default admin user if none exists
        self._create_default_admin()
        
    def _create_default_admin(self):
        """Create default admin user for South African system"""
        if not self.get_user_by_username("admin"):
            admin_user = SAHealthcareUser(
                id=secrets.token_urlsafe(16),
                username="admin",
                hashed_password=self._hash_password("admin123"),
                email="admin@hospital.co.za",
                role=UserRole.ADMIN,
                facility_name="System Administration",
                facility_type=FacilityType.ACADEMIC_HOSPITAL,
                province=Province.GAUTENG,
                department="IT Department",
                language_preference="english"
            )
            admin_user.permissions = self._get_all_permissions()
            self.create_user(admin_user, created_by="system")
            logger.info("Default admin user created for SA healthcare system")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt for security"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def _validate_practice_number(self, practice_number: str, role: UserRole) -> bool:
        """Validate HPCSA practice numbers for South African healthcare professionals"""
        if not practice_number and role in [UserRole.RADIOLOGIST, UserRole.SPECIALIST, UserRole.GP]:
            return False
        
        if practice_number:
            # HPCSA numbers typically follow format: MP followed by 6-7 digits
            if not re.match(r'^MP\d{6,7}$', practice_number):
                return False
        
        return True
    
    def _get_all_permissions(self) -> List[str]:
        """Get all available permissions in the system"""
        return [
            "users.read", "users.create", "users.update", "users.delete",
            "groups.read", "groups.create", "groups.update", "groups.delete",
            "images.read", "images.upload", "images.share", "images.delete",
            "reports.read", "reports.create", "reports.update", "reports.delete",
            "reports.dictate", "reports.review", "reports.approve",
            "nas.configure", "nas.view_status",
            "devices.read", "devices.configure", "devices.test",
            "system.admin", "system.audit",
            "patients.read", "patients.create", "patients.update",
            "studies.read", "studies.assign", "studies.report",
            "dicom.view", "dicom.measure", "dicom.annotate",
            "billing.read", "billing.process"  # For medical aid integration
        ]
    
    def get_default_permissions(self, role: UserRole) -> List[str]:
        """Get default permissions based on South African healthcare role"""
        base_permissions = ["images.read", "studies.read", "dicom.view"]
        
        role_permissions = {
            UserRole.ADMIN: self._get_all_permissions(),
            UserRole.RADIOLOGIST: [
                *base_permissions,
                "reports.read", "reports.create", "reports.update", "reports.approve",
                "reports.dictate", "dicom.measure", "dicom.annotate",
                "studies.assign", "studies.report", "images.share"
            ],
            UserRole.SPECIALIST: [
                *base_permissions,
                "reports.read", "reports.create", "reports.update",
                "patients.read", "patients.update", "dicom.measure",
                "images.share", "studies.assign"
            ],
            UserRole.GP: [
                *base_permissions,
                "reports.read", "patients.read", "patients.create",
                "patients.update", "images.share"
            ],
            UserRole.REGISTRAR: [
                *base_permissions,
                "reports.read", "reports.create", "dicom.measure",
                "patients.read", "studies.assign"
            ],
            UserRole.MEDICAL_OFFICER: [
                *base_permissions,
                "reports.read", "patients.read", "patients.update"
            ],
            UserRole.NURSING_SISTER: [
                *base_permissions,
                "patients.read", "patients.update"
            ],
            UserRole.TYPIST: [
                "reports.read", "reports.update", "reports.review"
            ],
            UserRole.RADIOGRAPHER: [
                *base_permissions,
                "images.upload", "devices.read", "patients.read"
            ],
            UserRole.PATIENT: [
                "images.read"  # Only their own images
            ],
            UserRole.STUDENT: [
                "images.read", "dicom.view"  # Limited access for learning
            ]
        }
        
        return role_permissions.get(role, base_permissions)
    
    def create_user(self, user: SAHealthcareUser, created_by: str) -> bool:
        """Create new healthcare user with validation"""
        try:
            # Validate practice number for medical professionals
            if not self._validate_practice_number(user.practice_number, user.role):
                raise ValueError("Invalid HPCSA practice number for role")
            
            # Validate email format
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', user.email):
                raise ValueError("Invalid email format")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert user
            cursor.execute('''
                INSERT INTO users (
                    id, username, hashed_password, email, role, practice_number,
                    facility_name, facility_type, province, department, specialization,
                    language_preference, two_factor_enabled, face_recognition_enabled,
                    medical_aid_schemes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user.id, user.username, user.hashed_password, user.email, user.role.value,
                user.practice_number, user.facility_name, user.facility_type.value,
                user.province.value, user.department, user.specialization,
                user.language_preference, user.two_factor_enabled, user.face_recognition_enabled,
                json.dumps(user.medical_aid_schemes)
            ))
            
            # Add default permissions based on role
            default_permissions = self.get_default_permissions(user.role)
            for permission in default_permissions:
                cursor.execute('''
                    INSERT INTO user_permissions (user_id, permission, granted_by)
                    VALUES (?, ?, ?)
                ''', (user.id, permission, created_by))
            
            # Log creation
            self._log_audit(cursor, created_by, "USER_CREATED", f"user:{user.id}",
                          f"Created user {user.username} with role {user.role.value}",
                          user.province.value, user.facility_name)
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created SA healthcare user: {user.username}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    def get_user_by_username(self, username: str) -> Optional[SAHealthcareUser]:
        """Get user by username"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ? AND is_active = TRUE', (username,))
        row = cursor.fetchone()
        
        if row:
            # Get permissions
            cursor.execute('SELECT permission FROM user_permissions WHERE user_id = ?', (row[0],))
            permissions = [p[0] for p in cursor.fetchall()]
            
            # Get groups
            cursor.execute('''
                SELECT g.name FROM groups g
                JOIN user_groups ug ON g.id = ug.group_id
                WHERE ug.user_id = ? AND g.is_active = TRUE
            ''', (row[0],))
            groups = [g[0] for g in cursor.fetchall()]
            
            medical_aid_schemes = json.loads(row[18]) if row[18] else []
            
            user = SAHealthcareUser(
                id=row[0], username=row[1], hashed_password=row[2], email=row[3],
                role=UserRole(row[4]), practice_number=row[5], facility_name=row[6],
                facility_type=FacilityType(row[7]), province=Province(row[8]),
                department=row[9], specialization=row[10], language_preference=row[11],
                two_factor_enabled=row[12], face_recognition_enabled=row[13],
                created_at=datetime.fromisoformat(row[14]) if row[14] else None,
                last_login=datetime.fromisoformat(row[15]) if row[15] else None,
                is_active=row[16], session_token=row[17],
                permissions=permissions, groups=groups, medical_aid_schemes=medical_aid_schemes
            )
            
            conn.close()
            return user
        
        conn.close()
        return None
    
    def authenticate_user(self, username: str, password: str, ip_address: str = None) -> Optional[SAHealthcareUser]:
        """Authenticate user with South African compliance logging"""
        user = self.get_user_by_username(username)
        if user and self._verify_password(password, user.hashed_password):
            # Generate new session token
            session_token = secrets.token_urlsafe(32)
            
            # Update last login and session token
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP, session_token = ?
                WHERE id = ?
            ''', (session_token, user.id))
            
            # Log successful login
            self._log_audit(cursor, user.id, "LOGIN_SUCCESS", "authentication",
                          f"Successful login from {ip_address}", user.province.value, user.facility_name,
                          ip_address)
            
            conn.commit()
            conn.close()
            
            user.session_token = session_token
            user.last_login = datetime.now()
            
            return user
        else:
            # Log failed login attempt
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            self._log_audit(cursor, username, "LOGIN_FAILED", "authentication",
                          f"Failed login attempt from {ip_address}", ip_address=ip_address)
            conn.commit()
            conn.close()
            
        return None
    
    def _log_audit(self, cursor, user_id: str, action: str, resource: str, details: str,
                   province: str = None, facility_name: str = None, ip_address: str = None,
                   user_agent: str = None):
        """Log audit events for South African compliance"""
        cursor.execute('''
            INSERT INTO audit_log (user_id, action, resource, details, ip_address, user_agent, province, facility_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, action, resource, details, ip_address, user_agent, province, facility_name))
    
    def create_group(self, group: SAHealthcareGroup, created_by: str) -> bool:
        """Create healthcare group/department"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO groups (id, name, description, facility_name, province, group_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (group.id, group.name, group.description, group.facility_name,
                  group.province.value, group.group_type))
            
            # Add group permissions
            for permission in group.permissions:
                cursor.execute('''
                    INSERT INTO group_permissions (group_id, permission, granted_by)
                    VALUES (?, ?, ?)
                ''', (group.id, permission, created_by))
            
            self._log_audit(cursor, created_by, "GROUP_CREATED", f"group:{group.id}",
                          f"Created group {group.name}", group.province.value, group.facility_name)
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error creating group: {e}")
            return False
    
    def get_user_effective_permissions(self, user_id: str) -> List[str]:
        """Get all effective permissions for user (direct + group permissions)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Direct permissions
        cursor.execute('SELECT permission FROM user_permissions WHERE user_id = ?', (user_id,))
        direct_permissions = {p[0] for p in cursor.fetchall()}
        
        # Group permissions
        cursor.execute('''
            SELECT gp.permission FROM group_permissions gp
            JOIN user_groups ug ON gp.group_id = ug.group_id
            JOIN groups g ON ug.group_id = g.id
            WHERE ug.user_id = ? AND g.is_active = TRUE
        ''', (user_id,))
        group_permissions = {p[0] for p in cursor.fetchall()}
        
        conn.close()
        return list(direct_permissions | group_permissions)
    
    def has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specific permission"""
        effective_permissions = self.get_user_effective_permissions(user_id)
        return permission in effective_permissions or "system.admin" in effective_permissions

# Global instance
sa_user_manager = SAUserGroupManager()
