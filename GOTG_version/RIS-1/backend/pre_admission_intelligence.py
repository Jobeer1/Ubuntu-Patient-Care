"""
Gift of the Givers RIS: Pre-Admission Patient Intelligence System

Aggregates everything known about a patient BEFORE they arrive at hospital:
- Medical history from previous visits
- Current medications
- Known allergies
- Family relationships and contacts
- Previous emergency contacts
- Emergency financial/insurance info
- Language preferences
- Disability accommodations needed

When clinician admits patient, they see COMPLETE context immediately,
enabling faster, safer treatment decisions.

Use Case: Unconscious patient brought in. Clinician matches face to photo.
System instantly pulls up:
- Previous injuries and chronic conditions
- Current medications
- Drug allergies (CRITICAL!)
- Known family members and their locations
- Previous treatment plans
- Emergency contacts
All visible in 5 seconds, enabling immediate informed care decisions.
"""

import sqlite3
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataCategory(Enum):
    """Categories of patient intelligence"""
    MEDICAL_HISTORY = "medical_history"
    MEDICATIONS = "medications"
    ALLERGIES = "allergies"
    FAMILY = "family"
    EMERGENCY_CONTACTS = "emergency_contacts"
    PREVIOUS_TREATMENTS = "previous_treatments"
    INSURANCE = "insurance"
    PREFERENCES = "preferences"
    DISABILITIES = "disabilities"


@dataclass
class PatientIntelligence:
    """Complete pre-admission patient context"""
    patient_id: str
    medical_history: List[str]
    current_medications: List[Dict]
    allergies: List[Dict]
    family_members: List[Dict]
    emergency_contacts: List[Dict]
    previous_treatments: List[Dict]
    disabilities_accommodations: List[str]
    language_preferences: List[str]
    insurance_info: Optional[Dict]
    completeness_score: float  # 0-1, how much info we have
    last_updated: str


class PreAdmissionIntelligence:
    """
    Pre-admission patient intelligence aggregator.
    
    Perfect for disaster medicine where time = life. Every second saved
    gathering patient history is a second available for treatment.
    """
    
    def __init__(self, db_path: str):
        """Initialize pre-admission system"""
        self.db_path = db_path
        logger.info("✅ Pre-admission intelligence system initialized")
    
    def record_medical_history(self, patient_id: str, condition: str,
                              diagnosis_date: str, notes: str = "") -> bool:
        """
        Record medical history for a patient.
        
        Examples:
        - "Hypertension" / "2015-03-10" / "Managed with lisinopril"
        - "Type 2 Diabetes" / "2010-06-15" / "Dietary controlled"
        - "Previous chest injury" / "2023-05-20" / "Right rib fractures, healed"
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO patient_medical_history (
                    patient_id, condition, diagnosis_date, notes, created_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                patient_id,
                condition,
                diagnosis_date,
                notes,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Medical history recorded: {patient_id} - {condition}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording medical history: {str(e)}")
            return False
    
    def record_medication(self, patient_id: str, medication_name: str,
                         dosage: str, frequency: str, indication: str,
                         notes: str = "") -> bool:
        """
        Record current medication for patient.
        
        CRITICAL: This helps clinicians avoid drug interactions!
        
        Examples:
        - "Lisinopril", "10mg", "Once daily", "Hypertension"
        - "Metformin", "500mg", "Three times daily", "Type 2 Diabetes"
        - "Aspirin", "100mg", "Once daily", "Cardiovascular prevention"
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO patient_medications (
                    patient_id, medication_name, dosage, frequency,
                    indication, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                patient_id,
                medication_name,
                dosage,
                frequency,
                indication,
                notes,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Medication recorded: {patient_id} - {medication_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording medication: {str(e)}")
            return False
    
    def record_allergy(self, patient_id: str, allergen: str, reaction: str,
                      severity: str = "moderate", onset_date: str = "") -> bool:
        """
        Record known allergies - CRITICAL for safe treatment!
        
        Severity levels: mild, moderate, severe, life_threatening
        
        Examples:
        - "Penicillin", "Rash and swelling", "moderate"
        - "Shellfish", "Anaphylaxis", "life_threatening"
        - "NSAIDs", "Severe GI bleeding", "severe"
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO patient_allergies (
                    patient_id, allergen, reaction, severity,
                    onset_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                patient_id,
                allergen,
                reaction,
                severity,
                onset_date or datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.warning(f"⚠️ ALLERGY recorded: {patient_id} - {allergen} ({severity})")
            return True
            
        except Exception as e:
            logger.error(f"Error recording allergy: {str(e)}")
            return False
    
    def link_family_member(self, patient_id: str, family_member_id: str,
                          relationship: str, emergency_priority: int = 0) -> bool:
        """
        Link family members for emergency notifications and context.
        
        Enables:
        1. Automatic family notification when patient found
        2. Quick lookup of family relationships
        3. Coordination when multiple family members injured
        
        Priority: 1 (highest) to 10 (lowest) - who to contact first
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO patient_family_links (
                    patient_id, family_member_id, relationship,
                    emergency_priority, created_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                patient_id,
                family_member_id,
                relationship,
                emergency_priority,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Family link recorded: {patient_id} - {relationship}")
            return True
            
        except Exception as e:
            logger.error(f"Error linking family: {str(e)}")
            return False
    
    def record_emergency_contact(self, patient_id: str, contact_name: str,
                                relationship: str, phone: str, email: str = "",
                                address: str = "", priority: int = 1) -> bool:
        """
        Record emergency contact for patient.
        
        Priority: 1 (call first), 2, 3, etc.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO emergency_contacts (
                    patient_id, contact_name, relationship, phone,
                    email, address, priority, consent, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                patient_id,
                contact_name,
                relationship,
                phone,
                email,
                address,
                priority,
                1,  # Assume consent given when recorded
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Emergency contact recorded: {patient_id} - {contact_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording emergency contact: {str(e)}")
            return False
    
    def record_previous_treatment(self, patient_id: str, treatment_date: str,
                                 hospital_name: str, treatment_type: str,
                                 outcome: str, notes: str = "") -> bool:
        """
        Record previous treatments to avoid duplicate or conflicting care.
        
        Examples:
        - "2023-06-15" / "Main Hospital" / "X-ray abdomen" / "No fractures" / "Negative findings"
        - "2024-02-10" / "Clinic A" / "Wound closure" / "Good healing" / "stitches removed on 2024-02-17"
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO patient_treatment_history (
                    patient_id, treatment_date, hospital_name, treatment_type,
                    outcome, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                patient_id,
                treatment_date,
                hospital_name,
                treatment_type,
                outcome,
                notes,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Treatment history recorded: {patient_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording treatment: {str(e)}")
            return False
    
    def record_disability_accommodation(self, patient_id: str, disability: str,
                                       accommodation_needed: str) -> bool:
        """
        Record disabilities and accommodations needed.
        
        CRITICAL for treating vulnerable patients!
        
        Examples:
        - "Deaf" / "Visual interpreter or written communication needed"
        - "Blindness" / "Verbal descriptions, guide required"
        - "Mobility limited" / "Wheelchair access, assistance needed"
        - "Intellectual disability" / "Simple language, family present for decisions"
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO patient_disabilities (
                    patient_id, disability, accommodation_needed, created_at
                ) VALUES (?, ?, ?, ?)
            """, (
                patient_id,
                disability,
                accommodation_needed,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.warning(f"ℹ️ Disability accommodation recorded: {patient_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording disability: {str(e)}")
            return False
    
    def record_language_preference(self, patient_id: str, language: str,
                                   fluency: str = "native") -> bool:
        """
        Record language preferences for communication.
        
        Fluency: native, fluent, intermediate, basic
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO patient_languages (
                    patient_id, language, fluency, created_at
                ) VALUES (?, ?, ?, ?)
            """, (
                patient_id,
                language,
                fluency,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Language recorded: {patient_id} - {language}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording language: {str(e)}")
            return False
    
    def get_patient_intelligence(self, patient_id: str) -> PatientIntelligence:
        """
        Get complete patient intelligence for admission/triage.
        
        This is what clinician sees when patient is identified.
        Everything they need to know, in 5 seconds.
        
        Returns:
            Complete patient context
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Medical history
            cursor.execute("""
                SELECT condition, diagnosis_date, notes
                FROM patient_medical_history
                WHERE patient_id = ?
                ORDER BY diagnosis_date DESC
            """, (patient_id,))
            medical_history = [
                f"{row[0]} (diagnosed {row[1]})" + (f": {row[2]}" if row[2] else "")
                for row in cursor.fetchall()
            ]
            
            # Current medications
            cursor.execute("""
                SELECT medication_name, dosage, frequency, indication
                FROM patient_medications
                WHERE patient_id = ?
                ORDER BY created_at DESC
            """, (patient_id,))
            medications = [
                {
                    'name': row[0],
                    'dosage': row[1],
                    'frequency': row[2],
                    'indication': row[3]
                }
                for row in cursor.fetchall()
            ]
            
            # Allergies - CRITICAL
            cursor.execute("""
                SELECT allergen, reaction, severity, onset_date
                FROM patient_allergies
                WHERE patient_id = ?
                ORDER BY severity DESC, onset_date DESC
            """, (patient_id,))
            allergies = [
                {
                    'allergen': row[0],
                    'reaction': row[1],
                    'severity': row[2],
                    'date': row[3]
                }
                for row in cursor.fetchall()
            ]
            
            # Family members
            cursor.execute("""
                SELECT family_member_id, relationship, emergency_priority
                FROM patient_family_links
                WHERE patient_id = ?
                ORDER BY emergency_priority ASC
            """, (patient_id,))
            family_members = [
                {
                    'patient_id': row[0],
                    'relationship': row[1],
                    'priority': row[2]
                }
                for row in cursor.fetchall()
            ]
            
            # Emergency contacts
            cursor.execute("""
                SELECT contact_name, relationship, phone, email, priority
                FROM emergency_contacts
                WHERE patient_id = ?
                ORDER BY priority ASC
            """, (patient_id,))
            emergency_contacts = [
                {
                    'name': row[0],
                    'relationship': row[1],
                    'phone': row[2],
                    'email': row[3],
                    'priority': row[4]
                }
                for row in cursor.fetchall()
            ]
            
            # Previous treatments
            cursor.execute("""
                SELECT treatment_date, hospital_name, treatment_type, outcome
                FROM patient_treatment_history
                WHERE patient_id = ?
                ORDER BY treatment_date DESC
            """, (patient_id,))
            previous_treatments = [
                {
                    'date': row[0],
                    'hospital': row[1],
                    'type': row[2],
                    'outcome': row[3]
                }
                for row in cursor.fetchall()
            ]
            
            # Disabilities
            cursor.execute("""
                SELECT disability, accommodation_needed
                FROM patient_disabilities
                WHERE patient_id = ?
            """, (patient_id,))
            disabilities = [
                f"{row[0]}: {row[1]}"
                for row in cursor.fetchall()
            ]
            
            # Languages
            cursor.execute("""
                SELECT language, fluency
                FROM patient_languages
                WHERE patient_id = ?
            """, (patient_id,))
            languages = [
                f"{row[0]} ({row[1]})"
                for row in cursor.fetchall()
            ]
            
            conn.close()
            
            # Calculate completeness score
            total_fields = 8  # categories we track
            filled_fields = sum([
                1 if medical_history else 0,
                1 if medications else 0,
                1 if allergies else 0,
                1 if family_members else 0,
                1 if emergency_contacts else 0,
                1 if previous_treatments else 0,
                1 if disabilities else 0,
                1 if languages else 0,
            ])
            completeness = filled_fields / total_fields
            
            return PatientIntelligence(
                patient_id=patient_id,
                medical_history=medical_history,
                current_medications=medications,
                allergies=allergies,
                family_members=family_members,
                emergency_contacts=emergency_contacts,
                previous_treatments=previous_treatments,
                disabilities_accommodations=disabilities,
                language_preferences=languages,
                insurance_info=None,  # Optional field
                completeness_score=completeness,
                last_updated=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error getting patient intelligence: {str(e)}")
            return None
    
    def get_critical_alerts(self, patient_id: str) -> Dict[str, List[str]]:
        """
        Get CRITICAL alerts that clinician must see FIRST.
        
        Includes:
        - Life-threatening allergies
        - Severe medical conditions
        - Disability accommodations for safety
        
        Returns:
            Dict with alert categories and messages
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            alerts = {
                'allergies': [],
                'medical_conditions': [],
                'disabilities': [],
                'medications': []
            }
            
            # Life-threatening allergies
            cursor.execute("""
                SELECT allergen, reaction
                FROM patient_allergies
                WHERE patient_id = ? AND severity IN ('severe', 'life_threatening')
            """, (patient_id,))
            for row in cursor.fetchall():
                alerts['allergies'].append(f"⚠️ ALERT: ALLERGIC TO {row[0]} - {row[1]}")
            
            # Critical medical conditions
            critical_conditions = ['cardiac', 'seizure', 'stroke', 'trauma', 'pregnancy']
            for condition in critical_conditions:
                cursor.execute("""
                    SELECT condition FROM patient_medical_history
                    WHERE patient_id = ? AND condition LIKE ?
                """, (patient_id, f"%{condition}%"))
                for row in cursor.fetchall():
                    alerts['medical_conditions'].append(f"⚠️ HISTORY: {row[0]}")
            
            # Safety accommodations
            cursor.execute("""
                SELECT disability, accommodation_needed
                FROM patient_disabilities
                WHERE patient_id = ?
            """, (patient_id,))
            for row in cursor.fetchall():
                alerts['disabilities'].append(f"ℹ️ ACCOMMODATION: {row[0]} - {row[1]}")
            
            conn.close()
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting critical alerts: {str(e)}")
            return {'allergies': [], 'medical_conditions': [], 'disabilities': [], 'medications': []}


def create_pre_admission_tables(db_path: str):
    """
    Create database tables for pre-admission intelligence.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Medical history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_medical_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            condition TEXT NOT NULL,
            diagnosis_date TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        )
    """)
    
    # Current medications
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            medication_name TEXT NOT NULL,
            dosage TEXT,
            frequency TEXT,
            indication TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        )
    """)
    
    # Allergies - CRITICAL
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_allergies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            allergen TEXT NOT NULL,
            reaction TEXT,
            severity TEXT,  -- mild, moderate, severe, life_threatening
            onset_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_allergies_patient_id ON patient_allergies(patient_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_allergies_severity ON patient_allergies(severity)
    """)
    
    # Family links
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_family_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            family_member_id TEXT NOT NULL,
            relationship TEXT,
            emergency_priority INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        )
    """)
    
    # Treatment history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_treatment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            treatment_date TEXT,
            hospital_name TEXT,
            treatment_type TEXT,
            outcome TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        )
    """)
    
    # Disabilities
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_disabilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            disability TEXT,
            accommodation_needed TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        )
    """)
    
    # Languages
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_languages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            language TEXT,
            fluency TEXT,  -- native, fluent, intermediate, basic
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        )
    """)
    
    conn.commit()
    conn.close()
    
    logger.info("✅ Pre-admission intelligence tables created")


if __name__ == "__main__":
    system = PreAdmissionIntelligence("./ris.db")
    print("Pre-admission intelligence system initialized")
