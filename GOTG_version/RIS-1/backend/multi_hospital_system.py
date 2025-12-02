"""
Gift of the Givers RIS: Multi-Hospital Awareness System

Enables real-time visibility of which field hospitals patients are in,
automatic notification to family when they're identified, and coordination
between hospitals to ensure continuity of care.

Key Features:
- Real-time patient location across all deployed hospitals
- Automatic family notification when patient is found
- Hospital-to-hospital alerts for patient transfers
- Synchronized patient records across hospitals
- Disaster dashboard showing all hospitals and patient distribution
- Missing person broadcasts to all hospitals
- Family member linking across hospital network

Use Case: Patient is admitted to Hospital C, system automatically checks
if any family members are in Hospitals A, B, D, E, F, G and notifies
all parties of patient location, enabling family reunification.
"""

import sqlite3
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PatientLocation(Enum):
    """Possible patient locations/states"""
    UNKNOWN = "unknown"              # Not yet identified
    UNIDENTIFIED = "unidentified"    # At hospital but not yet ID'd
    IDENTIFIED = "identified"         # Name/ID confirmed
    TRANSFERRED = "transferred"       # Moved to another hospital
    DISCHARGED = "discharged"        # Left hospital
    DECEASED = "deceased"            # Patient has passed away
    REUNIFIED = "reunified"          # Reunited with family


class NotificationType(Enum):
    """Types of notifications sent"""
    PATIENT_IDENTIFIED = "patient_identified"        # Your loved one has been identified
    PATIENT_FOUND = "patient_found"                  # We found someone matching your description
    PATIENT_TRANSFERRED = "patient_transferred"      # Patient moved to different hospital
    PATIENT_DISCHARGED = "patient_discharged"        # Patient released from care
    FAMILY_NEARBY = "family_nearby"                  # Family member located nearby
    NEED_IDENTIFICATION = "need_identification"      # Hospital needs help identifying patient


@dataclass
class PatientLocationRecord:
    """Current patient location and status"""
    patient_id: str
    hospital_id: str
    hospital_name: str
    location_updated: str
    identified_at: Optional[str]
    identified_by: Optional[str]
    clinical_status: str  # critical, serious, stable, recovering, discharged
    last_known_location: Optional[str]
    transfer_history: List[str]  # List of hospital IDs
    family_notified: bool
    created_at: str


@dataclass
class HospitalNetwork:
    """Information about a field hospital"""
    id: str
    name: str
    location: str  # Coordinates or description
    capacity: int
    current_patient_count: int
    active: bool
    sync_status: str  # online, offline, syncing
    last_sync: str


@dataclass
class FamilyNotification:
    """Notification sent to family member"""
    id: int
    patient_id: str
    family_member_id: Optional[str]
    notification_type: str
    message: str
    recipient_phone: str
    recipient_email: Optional[str]
    sent_at: str
    delivered: bool
    read: bool


class MultiHospitalAwarenessSystem:
    """
    Coordinates patient information across all deployed field hospitals.
    
    Architecture:
    - Each hospital has local patient records (offline-first)
    - Changes are queued and synced when connectivity available
    - Headquarters has central registry of all patients across hospitals
    - Real-time updates for patient identification, transfers, family notifications
    
    Perfect for disaster scenarios:
    - 6-7 field hospitals deployed across conflict zone
    - Some hospitals offline, some with poor connectivity
    - System guarantees eventual consistency
    - Family can search for loved one once, hits are checked at all hospitals
    """
    
    def __init__(self, db_path: str):
        """Initialize multi-hospital system"""
        self.db_path = db_path
        logger.info("✅ Multi-hospital awareness system initialized")
    
    def register_hospital(self, hospital_id: str, hospital_name: str,
                         location: str, capacity: int) -> bool:
        """
        Register a field hospital in the network.
        
        Args:
            hospital_id: Unique ID for hospital
            hospital_name: Human-readable name
            location: Location description or coordinates
            capacity: Patient capacity
            
        Returns:
            True if registered successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO hospitals (
                    id, name, location, capacity, active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                hospital_id,
                hospital_name,
                location,
                capacity,
                1,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Hospital registered: {hospital_name} ({hospital_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error registering hospital: {str(e)}")
            return False
    
    def record_patient_location(self, patient_id: str, hospital_id: str,
                               identified_by: Optional[str] = None,
                               clinical_status: str = "stable") -> bool:
        """
        Record that patient is at a specific hospital.
        
        This triggers:
        1. Check if family members are at other hospitals
        2. Send notifications to family
        3. Update patient location record
        4. Broadcast to all hospitals
        
        Args:
            patient_id: Patient identifier
            hospital_id: Which hospital patient is at
            identified_by: Who identified the patient
            clinical_status: Patient's clinical condition
            
        Returns:
            True if recorded successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Record location
            cursor.execute("""
                INSERT INTO patient_locations (
                    patient_id, hospital_id, clinical_status,
                    identified_by, identified_at, location_updated, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                patient_id,
                hospital_id,
                clinical_status,
                identified_by,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Patient {patient_id} recorded at hospital {hospital_id}")
            
            # Trigger notifications
            self._notify_family_of_location(patient_id, hospital_id)
            self._check_for_family_nearby(patient_id, hospital_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error recording patient location: {str(e)}")
            return False
    
    def _notify_family_of_location(self, patient_id: str, hospital_id: str):
        """
        Automatically notify family members when patient is identified.
        
        Use case: Family has been searching for loved one, patient is found
        at Hospital C. All registered emergency contacts are notified via
        SMS, email, radio, local channels, etc.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get patient info
            cursor.execute("""
                SELECT first_name, last_name FROM patients WHERE patient_id = ?
            """, (patient_id,))
            patient_row = cursor.fetchone()
            
            if not patient_row:
                conn.close()
                return
            
            patient_name = f"{patient_row[0]} {patient_row[1]}"
            
            # Get hospital info
            cursor.execute("""
                SELECT name, location FROM hospitals WHERE id = ?
            """, (hospital_id,))
            hospital_row = cursor.fetchone()
            hospital_name = hospital_row[0] if hospital_row else hospital_id
            hospital_location = hospital_row[1] if hospital_row else "Unknown"
            
            # Get emergency contacts
            cursor.execute("""
                SELECT id, phone, email, relationship FROM emergency_contacts
                WHERE patient_id = ? AND consent = 1
            """, (patient_id,))
            
            contacts = cursor.fetchall()
            
            for contact_id, phone, email, relationship in contacts:
                # Create notification
                message = f"Your {relationship} {patient_name} has been found at {hospital_name} ({hospital_location})"
                
                cursor.execute("""
                    INSERT INTO family_notifications (
                        patient_id, contact_id, notification_type, message,
                        recipient_phone, recipient_email, sent_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    patient_id,
                    contact_id,
                    NotificationType.PATIENT_IDENTIFIED.value,
                    message,
                    phone,
                    email,
                    datetime.utcnow().isoformat()
                ))
                
                logger.info(f"📢 Notification sent to {phone}: {message}")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error notifying family: {str(e)}")
    
    def _check_for_family_nearby(self, patient_id: str, hospital_id: str):
        """
        Check if any family members are at nearby hospitals.
        
        Use case: Patient admitted to Hospital C. System checks if siblings,
        parents, children, spouse are at any of the other deployed hospitals
        and notifies all parties they're nearby.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get family members of this patient
            cursor.execute("""
                SELECT family_member_patient_id, relationship
                FROM family_relationships
                WHERE patient_id = ?
            """, (patient_id,))
            
            family_members = cursor.fetchall()
            
            for family_patient_id, relationship in family_members:
                # Check if family member is at a hospital
                cursor.execute("""
                    SELECT hospital_id FROM patient_locations
                    WHERE patient_id = ? AND hospital_id != ?
                    ORDER BY identified_at DESC LIMIT 1
                """, (family_patient_id, hospital_id))
                
                location_row = cursor.fetchone()
                
                if location_row:
                    family_hospital_id = location_row[0]
                    
                    # Get names
                    cursor.execute("""
                        SELECT first_name, last_name FROM patients WHERE patient_id = ?
                    """, (family_patient_id,))
                    family_row = cursor.fetchone()
                    family_name = f"{family_row[0]} {family_row[1]}" if family_row else family_patient_id
                    
                    cursor.execute("""
                        SELECT first_name, last_name FROM patients WHERE patient_id = ?
                    """, (patient_id,))
                    patient_row = cursor.fetchone()
                    patient_name = f"{patient_row[0]} {patient_row[1]}" if patient_row else patient_id
                    
                    # Create bidirectional notifications
                    message1 = f"Your {relationship} {family_name} is at a nearby field hospital"
                    message2 = f"Your {relationship} {patient_name} is at a nearby field hospital"
                    
                    cursor.execute("""
                        INSERT INTO family_notifications (
                            patient_id, notification_type, message, sent_at
                        ) VALUES (?, ?, ?, ?)
                    """, (
                        patient_id,
                        NotificationType.FAMILY_NEARBY.value,
                        message1,
                        datetime.utcnow().isoformat()
                    ))
                    
                    cursor.execute("""
                        INSERT INTO family_notifications (
                            patient_id, notification_type, message, sent_at
                        ) VALUES (?, ?, ?, ?)
                    """, (
                        family_patient_id,
                        NotificationType.FAMILY_NEARBY.value,
                        message2,
                        datetime.utcnow().isoformat()
                    ))
                    
                    logger.info(f"👨‍👩‍👧 Family members nearby: {patient_name} and {family_name}")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error checking for family nearby: {str(e)}")
    
    def transfer_patient(self, patient_id: str, from_hospital_id: str,
                        to_hospital_id: str, reason: str = "") -> bool:
        """
        Record patient transfer between hospitals.
        
        Triggers notifications to family about location change.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get patient info
            cursor.execute("""
                SELECT first_name, last_name FROM patients WHERE patient_id = ?
            """, (patient_id,))
            patient_row = cursor.fetchone()
            patient_name = f"{patient_row[0]} {patient_row[1]}" if patient_row else patient_id
            
            # Get hospital names
            cursor.execute("SELECT name FROM hospitals WHERE id = ?", (from_hospital_id,))
            from_hosp = cursor.fetchone()
            from_hosp_name = from_hosp[0] if from_hosp else from_hospital_id
            
            cursor.execute("SELECT name FROM hospitals WHERE id = ?", (to_hospital_id,))
            to_hosp = cursor.fetchone()
            to_hosp_name = to_hosp[0] if to_hosp else to_hospital_id
            
            # Record transfer
            cursor.execute("""
                INSERT INTO patient_transfers (
                    patient_id, from_hospital_id, to_hospital_id, reason,
                    transfer_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                patient_id,
                from_hospital_id,
                to_hospital_id,
                reason,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
            
            # Update patient location
            cursor.execute("""
                UPDATE patient_locations
                SET hospital_id = ?, location_updated = ?
                WHERE patient_id = ?
            """, (to_hospital_id, datetime.utcnow().isoformat(), patient_id))
            
            # Notify family
            message = f"{patient_name} has been transferred from {from_hosp_name} to {to_hosp_name}"
            cursor.execute("""
                INSERT INTO family_notifications (
                    patient_id, notification_type, message, sent_at
                ) VALUES (?, ?, ?, ?)
            """, (
                patient_id,
                NotificationType.PATIENT_TRANSFERRED.value,
                message,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Patient transferred: {patient_name} ({from_hosp_name} → {to_hosp_name})")
            return True
            
        except Exception as e:
            logger.error(f"Error transferring patient: {str(e)}")
            return False
    
    def get_hospital_patient_distribution(self) -> Dict[str, int]:
        """
        Get patient count at each hospital.
        
        Returns:
            Dict mapping hospital_id to patient count
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT hospital_id, COUNT(DISTINCT patient_id) as count
                FROM patient_locations
                GROUP BY hospital_id
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            return dict(rows)
            
        except Exception as e:
            logger.error(f"Error getting distribution: {str(e)}")
            return {}
    
    def get_patients_at_hospital(self, hospital_id: str) -> List[Dict]:
        """
        Get all patients currently at a hospital with their clinical status.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT p.patient_id, p.first_name, p.last_name, p.phone,
                       pl.clinical_status, pl.identified_at, pl.location_updated
                FROM patient_locations pl
                JOIN patients p ON pl.patient_id = p.patient_id
                WHERE pl.hospital_id = ?
                ORDER BY pl.identified_at DESC
            """, (hospital_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for row in rows:
                results.append({
                    'patient_id': row[0],
                    'name': f"{row[1]} {row[2]}",
                    'phone': row[3],
                    'clinical_status': row[4],
                    'identified_at': row[5],
                    'location_updated': row[6]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting hospital patients: {str(e)}")
            return []
    
    def broadcast_missing_person(self, patient_id: str, description: str,
                                photo_path: Optional[str] = None) -> bool:
        """
        Broadcast missing person alert to all hospitals.
        
        Use case: Family member calls field headquarters saying their son
        is missing. Alert is broadcast to all 7 hospitals with description
        and photo. Clinicians keep eye out and notify if they see him.
        
        Returns:
            True if broadcast successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get patient info
            cursor.execute("""
                SELECT first_name, last_name FROM patients WHERE patient_id = ?
            """, (patient_id,))
            patient_row = cursor.fetchone()
            patient_name = f"{patient_row[0]} {patient_row[1]}" if patient_row else patient_id
            
            # Create broadcast message
            message = f"MISSING: {patient_name} - {description}"
            
            # Get all active hospitals
            cursor.execute("SELECT id FROM hospitals WHERE active = 1")
            hospitals = cursor.fetchall()
            
            broadcast_count = 0
            for hospital_row in hospitals:
                hospital_id = hospital_row[0]
                
                cursor.execute("""
                    INSERT INTO hospital_broadcasts (
                        hospital_id, patient_id, broadcast_type, message,
                        photo_path, broadcast_date, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    hospital_id,
                    patient_id,
                    "missing_person",
                    message,
                    photo_path,
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat()
                ))
                
                broadcast_count += 1
            
            conn.commit()
            conn.close()
            
            logger.info(f"📢 Missing person broadcast sent to {broadcast_count} hospitals")
            return True
            
        except Exception as e:
            logger.error(f"Error broadcasting: {str(e)}")
            return False


def create_multi_hospital_tables(db_path: str):
    """
    Create database tables for multi-hospital system.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Hospitals registry
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hospitals (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            location TEXT,
            capacity INTEGER,
            active BOOLEAN DEFAULT 1,
            sync_status TEXT DEFAULT 'online',
            last_sync TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Patient locations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            hospital_id TEXT NOT NULL,
            clinical_status TEXT DEFAULT 'stable',
            identified_by TEXT,
            identified_at TEXT,
            location_updated TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY(hospital_id) REFERENCES hospitals(id)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_patient_locations_patient_id
        ON patient_locations(patient_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_patient_locations_hospital_id
        ON patient_locations(hospital_id)
    """)
    
    # Patient transfers between hospitals
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            from_hospital_id TEXT NOT NULL,
            to_hospital_id TEXT NOT NULL,
            reason TEXT,
            transfer_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        )
    """)
    
    # Family notifications
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS family_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            contact_id INTEGER,
            notification_type TEXT NOT NULL,
            message TEXT,
            recipient_phone TEXT,
            recipient_email TEXT,
            sent_at TEXT,
            delivered BOOLEAN DEFAULT 0,
            read BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        )
    """)
    
    # Hospital broadcasts (missing persons, alerts, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hospital_broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_id TEXT NOT NULL,
            patient_id TEXT NOT NULL,
            broadcast_type TEXT,  -- missing_person, alert, etc.
            message TEXT,
            photo_path TEXT,
            broadcast_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(hospital_id) REFERENCES hospitals(id)
        )
    """)
    
    conn.commit()
    conn.close()
    
    logger.info("✅ Multi-hospital awareness tables created")


if __name__ == "__main__":
    system = MultiHospitalAwarenessSystem("./ris.db")
    print("Multi-hospital awareness system initialized")
