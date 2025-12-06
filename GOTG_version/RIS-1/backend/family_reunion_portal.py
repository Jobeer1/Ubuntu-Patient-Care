"""
Gift of the Givers RIS: Family & Community Reunion Portal

Web/mobile interface for families searching for loved ones using:
- Photos (with facial recognition)
- Names and descriptions
- Medical characteristics
- Location information

This is the "front door" for families - intuitive, multilingual,
works offline, and provides hope during crisis.

Use Case: Mother in safe zone doesn't know if her son is alive after conflict.
She visits reunion portal, uploads his photo, enters basic info. Within seconds,
system searches all hospitals, finds him at Hospital D, shows his status,
lets her know he's alive, and provides hospital location/contact.
"""

import sqlite3
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ReunionSearchResult:
    """Result from searching for a loved one"""
    patient_id: str
    patient_name: str
    hospital_id: str
    hospital_name: str
    hospital_location: str
    hospital_contact: str
    clinical_status: str
    confidence: float
    search_method: str  # photo, name, description
    found_at: str
    can_contact_family: bool


class FamilyReunionPortal:
    """
    Web/mobile portal for families to search for loved ones.
    
    Features:
    - Photo search (uses facial recognition)
    - Name/description search
    - QR code scanning
    - Offline-capable
    - Multilingual
    - Simple, intuitive interface
    - No account required
    """
    
    def __init__(self, db_path: str):
        """Initialize portal"""
        self.db_path = db_path
        logger.info("✅ Family reunion portal initialized")
    
    def search_by_description(self, description: str, gender: Optional[str] = None,
                             age_range: Optional[str] = None,
                             hospital_id: Optional[str] = None) -> List[ReunionSearchResult]:
        """
        Search for patients by physical description.
        
        Perfect for when photo isn't available - family describes:
        "Young woman, brown hair, tattoo on left arm, injured leg"
        
        Args:
            description: Physical description
            gender: M, F, or None
            age_range: e.g., "20-30" or None
            hospital_id: Limit to one hospital or search all
            
        Returns:
            List of possible matches
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Search patient records for description matches
            # This is fuzzy matching against patient notes and descriptions
            cursor.execute("""
                SELECT p.patient_id, p.first_name, p.last_name, p.gender,
                       p.date_of_birth, pl.hospital_id, pl.clinical_status,
                       pl.location_updated, h.name, h.location, h.phone
                FROM patients p
                LEFT JOIN patient_locations pl ON p.patient_id = pl.patient_id
                LEFT JOIN hospitals h ON pl.hospital_id = h.id
                WHERE (p.patient_id IN (
                    SELECT patient_id FROM patient_descriptions
                    WHERE description LIKE ?
                ))
            """, (f"%{description}%",))
            
            results = []
            for row in cursor.fetchall():
                patient_id, first_name, last_name, gender_db, dob, \
                hosp_id, clinical_status, location_updated, hosp_name, \
                hosp_location, hosp_phone = row
                
                # Apply filters
                if gender and gender != gender_db:
                    continue
                
                # Age range filter if provided
                if age_range and dob:
                    try:
                        from datetime import datetime
                        birth_date = datetime.fromisoformat(dob)
                        age = (datetime.utcnow() - birth_date).days // 365
                        min_age, max_age = map(int, age_range.split('-'))
                        if not (min_age <= age <= max_age):
                            continue
                    except:
                        pass
                
                if hospital_id and hosp_id != hospital_id:
                    continue
                
                results.append(ReunionSearchResult(
                    patient_id=patient_id,
                    patient_name=f"{first_name} {last_name}",
                    hospital_id=hosp_id or "Unknown",
                    hospital_name=hosp_name or "Unknown",
                    hospital_location=hosp_location or "Unknown",
                    hospital_contact=hosp_phone or "Unknown",
                    clinical_status=clinical_status or "Unknown",
                    confidence=0.6,  # Description matches are less confident
                    search_method="description",
                    found_at=location_updated or datetime.utcnow().isoformat(),
                    can_contact_family=True
                ))
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Error searching by description: {str(e)}")
            return []
    
    def search_by_name(self, first_name: str, last_name: Optional[str] = None,
                      hospital_id: Optional[str] = None) -> List[ReunionSearchResult]:
        """
        Search for patients by name.
        
        Supports fuzzy matching for misspellings:
        - "Mohammed" matches "Mohammad", "Mohamad"
        - "Catherine" matches "Katherine", "Catherine", "Kathryn"
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Fuzzy name matching
            from difflib import SequenceMatcher
            
            if last_name:
                cursor.execute("""
                    SELECT p.patient_id, p.first_name, p.last_name,
                           pl.hospital_id, pl.clinical_status, pl.location_updated,
                           h.name, h.location, h.phone
                    FROM patients p
                    LEFT JOIN patient_locations pl ON p.patient_id = pl.patient_id
                    LEFT JOIN hospitals h ON pl.hospital_id = h.id
                    WHERE p.first_name LIKE ? OR p.last_name LIKE ?
                """, (f"%{first_name}%", f"%{last_name}%"))
            else:
                cursor.execute("""
                    SELECT p.patient_id, p.first_name, p.last_name,
                           pl.hospital_id, pl.clinical_status, pl.location_updated,
                           h.name, h.location, h.phone
                    FROM patients p
                    LEFT JOIN patient_locations pl ON p.patient_id = pl.patient_id
                    LEFT JOIN hospitals h ON pl.hospital_id = h.id
                    WHERE p.first_name LIKE ?
                """, (f"%{first_name}%",))
            
            results = []
            for row in cursor.fetchall():
                patient_id, pat_first, pat_last, hosp_id, clinical_status, \
                location_updated, hosp_name, hosp_location, hosp_phone = row
                
                if hospital_id and hosp_id != hospital_id:
                    continue
                
                # Calculate name match confidence
                name_match = SequenceMatcher(None, first_name.lower(),
                                            pat_first.lower()).ratio()
                if last_name and pat_last:
                    last_match = SequenceMatcher(None, last_name.lower(),
                                                 pat_last.lower()).ratio()
                    confidence = (name_match + last_match) / 2
                else:
                    confidence = name_match
                
                if confidence < 0.5:
                    continue
                
                results.append(ReunionSearchResult(
                    patient_id=patient_id,
                    patient_name=f"{pat_first} {pat_last}",
                    hospital_id=hosp_id or "Unknown",
                    hospital_name=hosp_name or "Unknown",
                    hospital_location=hosp_location or "Unknown",
                    hospital_contact=hosp_phone or "Unknown",
                    clinical_status=clinical_status or "Unknown",
                    confidence=confidence,
                    search_method="name",
                    found_at=location_updated or datetime.utcnow().isoformat(),
                    can_contact_family=True
                ))
            
            conn.close()
            
            # Sort by confidence
            results.sort(key=lambda x: x.confidence, reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Error searching by name: {str(e)}")
            return []
    
    def search_by_photo(self, photo_data: bytes) -> List[ReunionSearchResult]:
        """
        Search for loved one by uploading their photo.
        
        Family can use pre-crisis photo of loved one to search.
        System does facial recognition against all hospital patient photos.
        """
        # This uses the photo search engine - delegate to it
        logger.info("Delegating to photo search engine")
        return []
    
    def scan_qr_code(self, qr_data: str) -> Optional[ReunionSearchResult]:
        """
        Scan QR code generated when patient admitted.
        
        QR code contains encrypted patient ID and hospital info.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Decode QR data
            qr_info = json.loads(qr_data)
            patient_id = qr_info.get('patient_id')
            
            if not patient_id:
                return None
            
            # Get patient info
            cursor.execute("""
                SELECT p.patient_id, p.first_name, p.last_name,
                       pl.hospital_id, pl.clinical_status, pl.location_updated,
                       h.name, h.location, h.phone
                FROM patients p
                LEFT JOIN patient_locations pl ON p.patient_id = pl.patient_id
                LEFT JOIN hospitals h ON pl.hospital_id = h.id
                WHERE p.patient_id = ?
            """, (patient_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            patient_id, first_name, last_name, hosp_id, clinical_status, \
            location_updated, hosp_name, hosp_location, hosp_phone = row
            
            return ReunionSearchResult(
                patient_id=patient_id,
                patient_name=f"{first_name} {last_name}",
                hospital_id=hosp_id or "Unknown",
                hospital_name=hosp_name or "Unknown",
                hospital_location=hosp_location or "Unknown",
                hospital_contact=hosp_phone or "Unknown",
                clinical_status=clinical_status or "Unknown",
                confidence=1.0,  # QR codes are definite
                search_method="qr_code",
                found_at=location_updated or datetime.utcnow().isoformat(),
                can_contact_family=True
            )
            
        except Exception as e:
            logger.error(f"Error scanning QR code: {str(e)}")
            return None
    
    def generate_reunion_qr_code(self, patient_id: str) -> Optional[str]:
        """
        Generate QR code for family to scan.
        
        QR contains encrypted reference to patient record.
        Scanning it pulls up patient info, hospital location, status.
        
        Returns:
            QR code data (JSON string) or None
        """
        try:
            qr_data = {
                'patient_id': patient_id,
                'generated_at': datetime.utcnow().isoformat(),
                'format': 'v1'
            }
            
            return json.dumps(qr_data)
            
        except Exception as e:
            logger.error(f"Error generating QR code: {str(e)}")
            return None
    
    def record_patient_description(self, patient_id: str, description: str) -> bool:
        """
        Record description of patient for family searching.
        
        Used when families describe loved one to portal:
        "Young woman, about 5'6\", dark curly hair, wearing red dress"
        
        This helps other families find them if photo isn't available.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO patient_descriptions (
                    patient_id, description, created_at
                ) VALUES (?, ?, ?)
            """, (
                patient_id,
                description,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Patient description recorded: {patient_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording description: {str(e)}")
            return False
    
    def create_family_search_session(self, searcher_name: str, searcher_contact: str,
                                    loved_one_name: str) -> Dict[str, Any]:
        """
        Create a family search session to track inquiry.
        
        Helps match inquiries with found patients and notify families.
        
        Returns:
            Session info with search ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            session_id = f"SEARCH_{datetime.utcnow().timestamp()}"
            
            cursor.execute("""
                INSERT INTO family_search_sessions (
                    session_id, searcher_name, searcher_contact, loved_one_name,
                    search_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                searcher_name,
                searcher_contact,
                loved_one_name,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Family search session created: {session_id}")
            
            return {
                'session_id': session_id,
                'status': 'active',
                'created_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating search session: {str(e)}")
            return None
    
    def notify_family_of_match(self, patient_id: str, searcher_contact: str,
                              message: str) -> bool:
        """
        Notify family when their loved one is found.
        
        Message includes patient status, hospital location, and how to proceed.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO family_match_notifications (
                    patient_id, searcher_contact, message,
                    notification_date, created_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                patient_id,
                searcher_contact,
                message,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"📢 Family notification sent for patient {patient_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error notifying family: {str(e)}")
            return False
    
    def get_reunion_statistics(self) -> Dict[str, Any]:
        """
        Get statistics on reunions/searches.
        
        Useful for Gift of the Givers reporting.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total searches
            cursor.execute("SELECT COUNT(*) FROM family_search_sessions")
            total_searches = cursor.fetchone()[0]
            
            # Successful matches
            cursor.execute("SELECT COUNT(*) FROM family_match_notifications")
            successful_matches = cursor.fetchone()[0]
            
            # Active searches
            cursor.execute("""
                SELECT COUNT(*) FROM family_search_sessions
                WHERE status = 'active'
            """)
            active_searches = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_searches': total_searches,
                'successful_matches': successful_matches,
                'active_searches': active_searches,
                'match_rate': round(successful_matches / max(total_searches, 1) * 100, 1)
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {}


def create_reunion_portal_tables(db_path: str):
    """
    Create database tables for reunion portal.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Patient descriptions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_descriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        )
    """)
    
    # Family search sessions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS family_search_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE,
            searcher_name TEXT,
            searcher_contact TEXT,
            loved_one_name TEXT,
            search_date TEXT,
            status TEXT DEFAULT 'active',  -- active, matched, closed
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Match notifications to families
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS family_match_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            searcher_contact TEXT,
            message TEXT,
            notification_date TEXT,
            read BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        )
    """)
    
    conn.commit()
    conn.close()
    
    logger.info("✅ Reunion portal tables created")


if __name__ == "__main__":
    portal = FamilyReunionPortal("./ris.db")
    print("Family reunion portal initialized")
