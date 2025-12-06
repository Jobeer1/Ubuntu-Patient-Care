"""
Family Member Linking & Emergency Contact Discovery
Lightweight web scraper and relationship inference engine
Privacy-respecting with explicit consent tracking
"""

import os
import json
import logging
import sqlite3
import threading
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass
import hashlib

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from difflib import SequenceMatcher
    HAS_DIFFLIB = True
except ImportError:
    HAS_DIFFLIB = False

logger = logging.getLogger(__name__)

# =============================================
# Data Classes
# =============================================

@dataclass
class EmergencyContact:
    """Emergency contact information"""
    name: str
    phone: str
    email: Optional[str]
    relationship: str  # 'spouse', 'parent', 'child', 'sibling', 'other'
    address: Optional[str]
    verified: bool
    source: str  # 'manual', 'scraper', 'imported'
    consent_given: bool
    timestamp: str

@dataclass
class FamilyLinkingResult:
    """Result of family member search"""
    patient_id: int
    family_member_id: Optional[int]
    name: str
    phone: str
    relationship: str
    confidence: float
    sources: List[str]  # Where the link was found
    verification_status: str  # 'verified', 'pending', 'rejected'

# =============================================
# Emergency Contact Discovery Engine
# =============================================

class EmergencyContactDiscovery:
    """
    Discover emergency contacts and family members
    Uses multiple data sources with privacy consent
    """
    
    def __init__(self, db_path: str = './ris.db'):
        self.db_path = db_path
        self.available = HAS_REQUESTS and HAS_DIFFLIB
        self.session = requests.Session() if HAS_REQUESTS else None
        self.session.timeout = 5  # 5-second timeout for API calls
        self.lock = threading.RLock()
        
        # Rate limiting to be respectful
        self.request_delay = 0.5  # seconds between requests
        self.last_request_time = 0
    
    def discover_family_members(self, patient_data: Dict, 
                               search_sources: List[str] = None) -> List[FamilyLinkingResult]:
        """
        Discover family members using multiple data sources
        
        Args:
            patient_data: Patient information (name, phone, address)
            search_sources: List of sources to search
                - 'phone_directory': Local phone directory
                - 'social_media_hints': Name/location correlations
                - 'manual_contacts': Previously entered contacts
                - 'emergency_services': Public emergency contact databases
        
        Returns:
            List of potential family member matches
        """
        if search_sources is None:
            search_sources = ['phone_directory', 'manual_contacts']
        
        results = []
        
        for source in search_sources:
            if source == 'phone_directory':
                results.extend(self._search_phone_directory(patient_data))
            elif source == 'social_media_hints':
                results.extend(self._search_social_media(patient_data))
            elif source == 'manual_contacts':
                results.extend(self._search_manual_contacts(patient_data))
            elif source == 'emergency_services':
                results.extend(self._search_emergency_databases(patient_data))
        
        # Remove duplicates and sort by confidence
        results = self._deduplicate_results(results)
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        return results
    
    def _search_phone_directory(self, patient_data: Dict) -> List[FamilyLinkingResult]:
        """
        Search phone directory for contacts
        Uses local directory lookups (lightweight, privacy-respecting)
        """
        results = []
        
        try:
            # Extract names from patient data
            first_name = patient_data.get('first_name', '')
            last_name = patient_data.get('last_name', '')
            
            # Get all known emergency contacts from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT 
                    ec.name, ec.phone, ec.relationship, 
                    CASE WHEN p.id IS NOT NULL THEN p.id ELSE NULL END as patient_id
                FROM emergency_contacts ec
                LEFT JOIN patients p ON LOWER(p.first_name || ' ' || p.last_name) = LOWER(ec.name)
                WHERE ec.consent_given = 1
                AND (ec.relationship IS NOT NULL OR ec.phone LIKE ? OR ec.phone LIKE ?)
                LIMIT 50
            """, (f"%{last_name}%", f"%{first_name}%"))
            
            contacts = cursor.fetchall()
            conn.close()
            
            for name, phone, relationship, existing_patient_id in contacts:
                # Calculate name similarity
                patient_name = f"{first_name} {last_name}".lower()
                contact_name = name.lower()
                
                similarity = SequenceMatcher(None, patient_name, contact_name).ratio()
                
                if similarity > 0.4:  # Threshold for possible family match
                    results.append(FamilyLinkingResult(
                        patient_id=patient_data.get('id'),
                        family_member_id=existing_patient_id,
                        name=name,
                        phone=phone,
                        relationship=relationship or 'unknown',
                        confidence=round(similarity * 0.8, 3),  # Reduce confidence for directory match
                        sources=['phone_directory'],
                        verification_status='pending'
                    ))
        
        except Exception as e:
            logger.error(f"Error searching phone directory: {str(e)}")
        
        return results
    
    def _search_social_media(self, patient_data: Dict) -> List[FamilyLinkingResult]:
        """
        Search for social media hints (name, location correlations)
        Very lightweight - only correlates name/address patterns
        """
        results = []
        
        try:
            # This is a VERY lightweight implementation
            # In production, consider privacy-respecting APIs like:
            # - Gravatar API (with consent)
            # - Public business directories
            # - Emergency notification platforms (with permissions)
            
            first_name = patient_data.get('first_name', '')
            last_name = patient_data.get('last_name', '')
            city = patient_data.get('address', '').split(',')[-1].strip() if patient_data.get('address') else ''
            
            # Query database for users with same last name in same area
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # This is local-only, respecting privacy
            cursor.execute("""
                SELECT id, first_name, last_name 
                FROM patients 
                WHERE last_name = ? 
                AND address LIKE ?
                AND id != ?
                AND status = 'active'
                LIMIT 20
            """, (last_name, f"%{city}%" if city else "%", patient_data.get('id', 0)))
            
            potential_relatives = cursor.fetchall()
            conn.close()
            
            for rel_id, rel_first, rel_last in potential_relatives:
                # Infer relationship (simplified)
                # More sophisticated models could use age differences
                relationship = 'possible_relative'
                confidence = 0.5  # Conservative confidence for social correlation
                
                results.append(FamilyLinkingResult(
                    patient_id=patient_data.get('id'),
                    family_member_id=rel_id,
                    name=f"{rel_first} {rel_last}",
                    phone='',
                    relationship=relationship,
                    confidence=confidence,
                    sources=['location_correlation'],
                    verification_status='pending'
                ))
        
        except Exception as e:
            logger.error(f"Error searching social media hints: {str(e)}")
        
        return results
    
    def _search_manual_contacts(self, patient_data: Dict) -> List[FamilyLinkingResult]:
        """
        Search manually entered emergency contacts
        """
        results = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get emergency contacts for this patient
            cursor.execute("""
                SELECT ec.name, ec.phone, ec.relationship, ec.email
                FROM emergency_contacts ec
                WHERE ec.patient_id = ?
                AND ec.consent_given = 1
            """, (patient_data.get('id'),))
            
            contacts = cursor.fetchall()
            conn.close()
            
            for name, phone, relationship, email in contacts:
                # Try to find this contact as a patient in system
                potential_patient_id = self._find_patient_by_contact(name, phone)
                
                results.append(FamilyLinkingResult(
                    patient_id=patient_data.get('id'),
                    family_member_id=potential_patient_id,
                    name=name,
                    phone=phone,
                    relationship=relationship or 'emergency_contact',
                    confidence=0.8 if potential_patient_id else 0.3,
                    sources=['manual_entry'],
                    verification_status='verified' if potential_patient_id else 'pending'
                ))
        
        except Exception as e:
            logger.error(f"Error searching manual contacts: {str(e)}")
        
        return results
    
    def _search_emergency_databases(self, patient_data: Dict) -> List[FamilyLinkingResult]:
        """
        Search public emergency service databases (with consent)
        Example: Red Cross family linking, NGO emergency contact registries
        
        This is a STUB for disaster scenarios - 
        would connect to actual emergency services APIs
        """
        results = []
        
        # Placeholder for integration with:
        # - Red Cross family linking systems
        # - NGO emergency registries (with permissions)
        # - Government emergency contact databases
        # - Mobile carrier emergency contact services
        
        logger.info("Emergency database search would trigger here (requires API keys and permissions)")
        
        return results
    
    def _find_patient_by_contact(self, name: str, phone: str) -> Optional[int]:
        """Find patient ID by name and phone"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Normalize phone
            normalized_phone = ''.join(filter(str.isdigit, phone))
            
            # Search by name first
            cursor.execute("""
                SELECT id FROM patients 
                WHERE (first_name || ' ' || last_name) LIKE ?
                LIMIT 1
            """, (f"%{name}%",))
            
            result = cursor.fetchone()
            
            if result:
                conn.close()
                return result[0]
            
            # Search by phone
            if normalized_phone:
                cursor.execute("""
                    SELECT id FROM patients 
                    WHERE phone LIKE ?
                    LIMIT 1
                """, (f"%{normalized_phone[-7:]}%",))  # Last 7 digits
                
                result = cursor.fetchone()
                conn.close()
                return result[0] if result else None
            
            conn.close()
            return None
        
        except Exception as e:
            logger.error(f"Error finding patient by contact: {str(e)}")
            return None
    
    @staticmethod
    def _deduplicate_results(results: List[FamilyLinkingResult]) -> List[FamilyLinkingResult]:
        """Remove duplicate results"""
        seen = set()
        unique = []
        
        for result in results:
            key = (result.family_member_id, result.phone)
            if key not in seen:
                seen.add(key)
                unique.append(result)
        
        return unique
    
    def store_emergency_contact(self, patient_id: int, contact: EmergencyContact) -> bool:
        """Store emergency contact with consent tracking"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO emergency_contacts 
                (patient_id, name, phone, email, relationship, address, 
                 verified, source, consent_given, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                patient_id,
                contact.name,
                contact.phone,
                contact.email,
                contact.relationship,
                contact.address,
                contact.verified,
                contact.source,
                contact.consent_given,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            return True
        
        except Exception as e:
            logger.error(f"Error storing emergency contact: {str(e)}")
            return False
    
    def verify_family_link(self, patient_id: int, family_member_id: int, 
                          relationship: str) -> bool:
        """Verify and store family relationship"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO family_relationships 
                (patient_id, family_member_id, relationship, verified, created_at)
                VALUES (?, ?, ?, 1, ?)
            """, (patient_id, family_member_id, relationship, datetime.utcnow().isoformat()))
            
            conn.commit()
            conn.close()
            return True
        
        except Exception as e:
            logger.error(f"Error verifying family link: {str(e)}")
            return False

# =============================================
# QR Code Patient ID Generator
# =============================================

class QRCodePatientID:
    """
    Generate QR codes for patient identification
    Includes metadata for offline scanning
    """
    
    def __init__(self, db_path: str = './ris.db'):
        self.db_path = db_path
        try:
            import qrcode
            self.qrcode = qrcode
            self.available = True
        except ImportError:
            logger.warning("qrcode library not installed")
            self.available = False
    
    def generate_patient_qr(self, patient_id: int, include_metadata: bool = True) -> Optional[bytes]:
        """
        Generate QR code for patient
        
        Returns:
            QR code as PNG bytes or None if unavailable
        """
        if not self.available:
            return None
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, patient_id, first_name, last_name, date_of_birth
                FROM patients WHERE id = ?
            """, (patient_id,))
            
            patient = cursor.fetchone()
            conn.close()
            
            if not patient:
                return None
            
            # Create QR data
            if include_metadata:
                qr_data = json.dumps({
                    'patient_id': patient[1],
                    'name': f"{patient[2]} {patient[3]}",
                    'dob': patient[4],
                    'db_id': patient[0],
                    'version': '1.0'
                })
            else:
                qr_data = patient[1]  # Just patient ID
            
            # Generate QR code
            qr = self.qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to bytes
            import io
            byte_arr = io.BytesIO()
            img.save(byte_arr, format='PNG')
            return byte_arr.getvalue()
        
        except Exception as e:
            logger.error(f"Error generating QR code for patient {patient_id}: {str(e)}")
            return None
    
    def scan_and_retrieve_patient(self, qr_data: str) -> Optional[Dict]:
        """
        Retrieve patient data from QR code data
        Supports both JSON metadata and simple patient ID
        """
        try:
            # Try parsing as JSON
            try:
                data = json.loads(qr_data)
                patient_id = data.get('db_id') or data.get('patient_id')
            except:
                # Fall back to simple patient ID
                patient_id = qr_data
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM patients WHERE id = ? OR patient_id = ?
            """, (patient_id, patient_id))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                # Convert row to dictionary
                return dict(result)
            
            return None
        
        except Exception as e:
            logger.error(f"Error scanning QR code: {str(e)}")
            return None
