"""
Secure Link Sharing System for South African Healthcare
Provides cryptographically signed, time-limited links for sharing medical images and reports
with doctors, patients, and healthcare facilities across South Africa
"""

import secrets
import hashlib
import hmac
import json
import sqlite3
import qrcode
import io
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from urllib.parse import quote, unquote

logger = logging.getLogger(__name__)

class ShareType(Enum):
    """Types of content that can be shared"""
    SINGLE_IMAGE = "single_image"
    STUDY = "study"
    REPORT = "report"
    REPORT_WITH_IMAGES = "report_with_images"
    CONSULTATION_PACKAGE = "consultation_package"  # For referrals

class RecipientType(Enum):
    """Types of recipients in SA healthcare system"""
    DOCTOR = "doctor"
    SPECIALIST = "specialist"
    PATIENT = "patient"
    FAMILY_MEMBER = "family_member"
    MEDICAL_AID = "medical_aid"
    LEGAL_REPRESENTATIVE = "legal_representative"
    RESEARCH_INSTITUTION = "research_institution"
    REFERRING_FACILITY = "referring_facility"
    INSURANCE_ASSESSOR = "insurance_assessor"

class AccessLevel(Enum):
    """Access levels for shared content"""
    VIEW_ONLY = "view_only"
    VIEW_DOWNLOAD = "view_download"
    VIEW_ANNOTATE = "view_annotate"
    FULL_ACCESS = "full_access"

@dataclass
class SASecureShare:
    """Secure share record for South African healthcare"""
    id: str
    share_token: str
    content_type: ShareType
    content_ids: List[str]  # Image IDs, Study IDs, Report IDs
    sharer_id: str
    sharer_name: str
    sharer_facility: str
    recipient_type: RecipientType
    recipient_name: str
    recipient_email: Optional[str]
    recipient_phone: Optional[str]  # For SMS notifications
    access_level: AccessLevel
    expires_at: datetime
    created_at: datetime
    purpose: str  # Consultation, Second Opinion, Patient Access, etc.
    patient_name: str
    patient_id: str
    study_description: str
    requires_otp: bool = False
    max_access_count: int = 10
    access_count: int = 0
    is_active: bool = True
    province: str = ""
    medical_aid_scheme: Optional[str] = None
    reference_number: Optional[str] = None  # For medical aid claims
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now()

@dataclass
class ShareAccess:
    """Record of access to shared content"""
    id: str
    share_id: str
    accessed_at: datetime
    ip_address: str
    user_agent: str
    location: Optional[str] = None
    verification_method: Optional[str] = None  # OTP, email_link, etc.

class SASecureLinkManager:
    """Advanced secure link sharing for South African healthcare"""
    
    def __init__(self, db_path: str = "sa_secure_shares.db", secret_key: str = None):
        self.db_path = db_path
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.init_database()
    
    def init_database(self):
        """Initialize secure sharing database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Secure shares table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS secure_shares (
                id TEXT PRIMARY KEY,
                share_token TEXT UNIQUE NOT NULL,
                content_type TEXT NOT NULL,
                content_ids TEXT NOT NULL,  -- JSON array
                sharer_id TEXT NOT NULL,
                sharer_name TEXT NOT NULL,
                sharer_facility TEXT NOT NULL,
                recipient_type TEXT NOT NULL,
                recipient_name TEXT NOT NULL,
                recipient_email TEXT,
                recipient_phone TEXT,
                access_level TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                purpose TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                study_description TEXT,
                requires_otp BOOLEAN DEFAULT FALSE,
                max_access_count INTEGER DEFAULT 10,
                access_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                province TEXT,
                medical_aid_scheme TEXT,
                reference_number TEXT
            )
        ''')
        
        # Share access log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS share_access_log (
                id TEXT PRIMARY KEY,
                share_id TEXT NOT NULL,
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                location TEXT,
                verification_method TEXT,
                FOREIGN KEY (share_id) REFERENCES secure_shares (id)
            )
        ''')
        
        # OTP verification codes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS share_otp_codes (
                share_id TEXT NOT NULL,
                otp_code TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (share_id) REFERENCES secure_shares (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def generate_secure_token(self, content_ids: List[str], recipient_email: str, 
                            expires_at: datetime) -> str:
        """Generate cryptographically secure sharing token"""
        # Create payload
        payload = {
            'content_ids': content_ids,
            'recipient': recipient_email,
            'expires': expires_at.isoformat(),
            'random': secrets.token_urlsafe(16)
        }
        
        # Create signature
        payload_json = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            self.secret_key.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Combine payload and signature
        token_data = {
            'payload': payload,
            'signature': signature
        }
        
        # Base64 encode for URL safety
        token_json = json.dumps(token_data)
        token = base64.urlsafe_b64encode(token_json.encode()).decode()
        
        return token
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode sharing token"""
        try:
            # Decode token
            token_json = base64.urlsafe_b64decode(token.encode()).decode()
            token_data = json.loads(token_json)
            
            payload = token_data['payload']
            signature = token_data['signature']
            
            # Verify signature
            payload_json = json.dumps(payload, sort_keys=True)
            expected_signature = hmac.new(
                self.secret_key.encode(),
                payload_json.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return None
            
            # Check expiration
            expires_at = datetime.fromisoformat(payload['expires'])
            if datetime.now() > expires_at:
                return None
            
            return payload
            
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None
    
    def create_share(self, share: SASecureShare) -> str:
        """Create new secure share with South African healthcare context"""
        try:
            # Generate secure token
            share.share_token = self.generate_secure_token(
                share.content_ids,
                share.recipient_email or share.recipient_name,
                share.expires_at
            )
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO secure_shares (
                    id, share_token, content_type, content_ids, sharer_id, sharer_name,
                    sharer_facility, recipient_type, recipient_name, recipient_email,
                    recipient_phone, access_level, expires_at, purpose, patient_name,
                    patient_id, study_description, requires_otp, max_access_count,
                    province, medical_aid_scheme, reference_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                share.id, share.share_token, share.content_type.value,
                json.dumps(share.content_ids), share.sharer_id, share.sharer_name,
                share.sharer_facility, share.recipient_type.value, share.recipient_name,
                share.recipient_email, share.recipient_phone, share.access_level.value,
                share.expires_at.isoformat(), share.purpose, share.patient_name,
                share.patient_id, share.study_description, share.requires_otp,
                share.max_access_count, share.province, share.medical_aid_scheme,
                share.reference_number
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created secure share {share.id} for SA healthcare")
            return share.share_token
            
        except Exception as e:
            logger.error(f"Error creating secure share: {e}")
            return None
    
    def get_share_by_token(self, token: str) -> Optional[SASecureShare]:
        """Get share by token"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM secure_shares WHERE share_token = ? AND is_active = TRUE', (token,))
        row = cursor.fetchone()
        
        if row:
            share = SASecureShare(
                id=row[0], share_token=row[1], content_type=ShareType(row[2]),
                content_ids=json.loads(row[3]), sharer_id=row[4], sharer_name=row[5],
                sharer_facility=row[6], recipient_type=RecipientType(row[7]),
                recipient_name=row[8], recipient_email=row[9], recipient_phone=row[10],
                access_level=AccessLevel(row[11]), expires_at=datetime.fromisoformat(row[12]),
                created_at=datetime.fromisoformat(row[13]), purpose=row[14],
                patient_name=row[15], patient_id=row[16], study_description=row[17],
                requires_otp=row[18], max_access_count=row[19], access_count=row[20],
                is_active=row[21], province=row[22], medical_aid_scheme=row[23],
                reference_number=row[24]
            )
            
            conn.close()
            return share
        
        conn.close()
        return None
    
    def generate_qr_code(self, share_url: str) -> str:
        """Generate QR code for South African healthcare sharing"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(share_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for embedding
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def generate_otp(self, share_id: str) -> str:
        """Generate OTP for secure access"""
        otp = secrets.randbelow(900000) + 100000  # 6-digit OTP
        otp_str = str(otp)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Deactivate old OTPs
        cursor.execute('UPDATE share_otp_codes SET used = TRUE WHERE share_id = ?', (share_id,))
        
        # Create new OTP
        expires_at = datetime.now() + timedelta(minutes=15)
        cursor.execute('''
            INSERT INTO share_otp_codes (share_id, otp_code, expires_at)
            VALUES (?, ?, ?)
        ''', (share_id, otp_str, expires_at.isoformat()))
        
        conn.commit()
        conn.close()
        
        return otp_str
    
    def verify_otp(self, share_id: str, otp_code: str) -> bool:
        """Verify OTP for share access"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM share_otp_codes 
            WHERE share_id = ? AND otp_code = ? AND used = FALSE AND expires_at > ?
        ''', (share_id, otp_code, datetime.now().isoformat()))
        
        result = cursor.fetchone()
        
        if result:
            # Mark OTP as used
            cursor.execute('UPDATE share_otp_codes SET used = TRUE WHERE id = ?', (result[0],))
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    
    def log_access(self, share_id: str, ip_address: str, user_agent: str, 
                   verification_method: str = None):
        """Log access to shared content"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create access log entry
        access_id = secrets.token_urlsafe(16)
        cursor.execute('''
            INSERT INTO share_access_log (id, share_id, ip_address, user_agent, verification_method)
            VALUES (?, ?, ?, ?, ?)
        ''', (access_id, share_id, ip_address, user_agent, verification_method))
        
        # Increment access count
        cursor.execute('UPDATE secure_shares SET access_count = access_count + 1 WHERE id = ?', (share_id,))
        
        conn.commit()
        conn.close()
    
    def get_user_shares(self, user_id: str) -> List[SASecureShare]:
        """Get all shares created by user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM secure_shares 
            WHERE sharer_id = ? AND is_active = TRUE 
            ORDER BY created_at DESC
        ''', (user_id,))
        
        shares = []
        for row in cursor.fetchall():
            share = SASecureShare(
                id=row[0], share_token=row[1], content_type=ShareType(row[2]),
                content_ids=json.loads(row[3]), sharer_id=row[4], sharer_name=row[5],
                sharer_facility=row[6], recipient_type=RecipientType(row[7]),
                recipient_name=row[8], recipient_email=row[9], recipient_phone=row[10],
                access_level=AccessLevel(row[11]), expires_at=datetime.fromisoformat(row[12]),
                created_at=datetime.fromisoformat(row[13]), purpose=row[14],
                patient_name=row[15], patient_id=row[16], study_description=row[17],
                requires_otp=row[18], max_access_count=row[19], access_count=row[20],
                is_active=row[21], province=row[22], medical_aid_scheme=row[23],
                reference_number=row[24]
            )
            shares.append(share)
        
        conn.close()
        return shares
    
    def revoke_share(self, share_id: str, user_id: str) -> bool:
        """Revoke share access"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE secure_shares SET is_active = FALSE 
            WHERE id = ? AND sharer_id = ?
        ''', (share_id, user_id))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return rows_affected > 0
    
    def generate_share_url(self, base_url: str, share_token: str) -> str:
        """Generate complete share URL"""
        return f"{base_url}/shared/{share_token}"
    
    def create_medical_aid_package(self, patient_id: str, study_ids: List[str], 
                                 medical_aid_scheme: str, claim_number: str,
                                 sharer_id: str) -> Optional[str]:
        """Create special package for medical aid claims (South African specific)"""
        share = SASecureShare(
            id=secrets.token_urlsafe(16),
            share_token="",  # Will be generated
            content_type=ShareType.CONSULTATION_PACKAGE,
            content_ids=study_ids,
            sharer_id=sharer_id,
            sharer_name="Medical Aid Package",
            sharer_facility="Automated System",
            recipient_type=RecipientType.MEDICAL_AID,
            recipient_name=medical_aid_scheme,
            recipient_email=f"claims@{medical_aid_scheme.lower().replace(' ', '')}.co.za",
            access_level=AccessLevel.VIEW_DOWNLOAD,
            expires_at=datetime.now() + timedelta(days=30),
            created_at=datetime.now(),
            purpose="Medical Aid Claim",
            patient_name="Patient",
            patient_id=patient_id,
            study_description="Medical Aid Package",
            requires_otp=False,
            max_access_count=50,
            medical_aid_scheme=medical_aid_scheme,
            reference_number=claim_number
        )
        
        return self.create_share(share)

# Global instance
sa_link_manager = SASecureLinkManager()
