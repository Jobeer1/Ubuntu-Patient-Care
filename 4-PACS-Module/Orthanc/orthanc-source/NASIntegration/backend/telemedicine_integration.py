#!/usr/bin/env python3
"""
Telemedicine Integration System for South African Healthcare
Enables remote consultation and diagnosis with secure video conferencing
"""

import sqlite3
import json
import uuid
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
from cryptography.fernet import Fernet
import base64
import os
from dataclasses import dataclass, asdict
from enum import Enum

class ConsultationType(Enum):
    EMERGENCY = "emergency"
    ROUTINE = "routine"
    SECOND_OPINION = "second_opinion"
    FOLLOW_UP = "follow_up"
    MULTIDISCIPLINARY = "multidisciplinary"

class ConsultationStatus(Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

class ParticipantRole(Enum):
    REQUESTING_DOCTOR = "requesting_doctor"
    CONSULTING_SPECIALIST = "consulting_specialist"
    PATIENT = "patient"
    OBSERVER = "observer"
    TECHNOLOGIST = "technologist"

@dataclass
class TelemedicineConsultation:
    consultation_id: str
    patient_id: str
    study_id: str
    consultation_type: ConsultationType
    status: ConsultationStatus
    scheduled_time: datetime
    duration_minutes: int
    requesting_doctor_id: str
    consulting_specialist_id: str
    hospital_id: str
    specialist_hospital_id: str
    title: str
    description: str
    clinical_question: str
    urgency_level: str  # 'low', 'medium', 'high', 'critical'
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

@dataclass
class ConsultationParticipant:
    participant_id: str
    consultation_id: str
    user_id: str
    username: str
    role: ParticipantRole
    hospital_id: str
    joined_at: Optional[datetime] = None
    left_at: Optional[datetime] = None
    connection_quality: str = "good"  # 'poor', 'fair', 'good', 'excellent'

class TelemedicineManager:
    """Manages telemedicine consultations and remote diagnosis"""
    
    def __init__(self, db_path: str = "telemedicine.db"):
        self.db_path = db_path
        self.init_database()
        self.encryption_key = self._get_or_create_encryption_key()
        
    def init_database(self):
        """Initialize the telemedicine database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Telemedicine consultations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS telemedicine_consultations (
                consultation_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                study_id TEXT NOT NULL,
                consultation_type TEXT NOT NULL,
                status TEXT NOT NULL,
                scheduled_time TIMESTAMP NOT NULL,
                duration_minutes INTEGER DEFAULT 30,
                requesting_doctor_id TEXT NOT NULL,
                consulting_specialist_id TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                specialist_hospital_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                clinical_question TEXT NOT NULL,
                urgency_level TEXT DEFAULT 'medium',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                ended_at TIMESTAMP,
                meeting_room_id TEXT,
                recording_url TEXT,
                consultation_notes TEXT,
                diagnosis TEXT,
                recommendations TEXT,
                follow_up_required BOOLEAN DEFAULT 0,
                follow_up_date TIMESTAMP
            )
        ''')
        
        # Consultation participants
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consultation_participants (
                participant_id TEXT PRIMARY KEY,
                consultation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                hospital_id TEXT,
                joined_at TIMESTAMP,
                left_at TIMESTAMP,
                connection_quality TEXT DEFAULT 'good',
                audio_enabled BOOLEAN DEFAULT 1,
                video_enabled BOOLEAN DEFAULT 1,
                screen_sharing BOOLEAN DEFAULT 0,
                FOREIGN KEY (consultation_id) REFERENCES telemedicine_consultations (consultation_id)
            )
        ''')
        
        # Consultation messages/chat
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consultation_messages (
                message_id TEXT PRIMARY KEY,
                consultation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                message TEXT NOT NULL,
                message_type TEXT DEFAULT 'text', -- 'text', 'image_reference', 'measurement', 'diagnosis'
                reference_data TEXT, -- JSON for image/measurement references
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (consultation_id) REFERENCES telemedicine_consultations (consultation_id)
            )
        ''')
        
        # Shared images/studies during consultation
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consultation_shared_images (
                share_id TEXT PRIMARY KEY,
                consultation_id TEXT NOT NULL,
                study_id TEXT NOT NULL,
                series_id TEXT,
                instance_id TEXT,
                shared_by_user_id TEXT NOT NULL,
                annotation_data TEXT, -- JSON of annotations
                measurement_data TEXT, -- JSON of measurements
                shared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (consultation_id) REFERENCES telemedicine_consultations (consultation_id)
            )
        ''')
        
        # Consultation recordings and documents
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consultation_recordings (
                recording_id TEXT PRIMARY KEY,
                consultation_id TEXT NOT NULL,
                recording_type TEXT NOT NULL, -- 'video', 'audio', 'screen', 'document'
                file_path TEXT NOT NULL,
                file_size INTEGER,
                duration_seconds INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                retention_until TIMESTAMP, -- Auto-delete date for privacy
                FOREIGN KEY (consultation_id) REFERENCES telemedicine_consultations (consultation_id)
            )
        ''')
        
        # Specialist availability
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS specialist_availability (
                availability_id TEXT PRIMARY KEY,
                specialist_id TEXT NOT NULL,
                specialty TEXT NOT NULL,
                hospital_id TEXT NOT NULL,
                day_of_week INTEGER NOT NULL, -- 0=Monday, 6=Sunday
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                timezone TEXT DEFAULT 'Africa/Johannesburg',
                is_active BOOLEAN DEFAULT 1,
                max_consultations_per_hour INTEGER DEFAULT 2,
                consultation_types TEXT, -- JSON array of supported types
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Emergency consultation queue
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emergency_consultation_queue (
                queue_id TEXT PRIMARY KEY,
                consultation_id TEXT NOT NULL,
                priority_score INTEGER NOT NULL, -- Higher = more urgent
                triage_notes TEXT,
                estimated_wait_minutes INTEGER,
                queue_position INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_at TIMESTAMP,
                FOREIGN KEY (consultation_id) REFERENCES telemedicine_consultations (consultation_id)
            )
        ''')
        
        # Consultation feedback and ratings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consultation_feedback (
                feedback_id TEXT PRIMARY KEY,
                consultation_id TEXT NOT NULL,
                reviewer_user_id TEXT NOT NULL,
                reviewer_role TEXT NOT NULL,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                technical_quality_rating INTEGER CHECK (technical_quality_rating >= 1 AND technical_quality_rating <= 5),
                clinical_value_rating INTEGER CHECK (clinical_value_rating >= 1 AND clinical_value_rating <= 5),
                feedback_text TEXT,
                would_recommend BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (consultation_id) REFERENCES telemedicine_consultations (consultation_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def _get_or_create_encryption_key(self) -> Fernet:
        """Get or create encryption key for secure telemedicine data"""
        key_file = "telemedicine_encryption.key"
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
                
        return Fernet(key)
        
    def schedule_consultation(self, consultation_data: Dict) -> str:
        """Schedule a new telemedicine consultation"""
        consultation_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO telemedicine_consultations (
                consultation_id, patient_id, study_id, consultation_type,
                status, scheduled_time, duration_minutes, requesting_doctor_id,
                consulting_specialist_id, hospital_id, specialist_hospital_id,
                title, description, clinical_question, urgency_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            consultation_id,
            consultation_data['patient_id'],
            consultation_data['study_id'],
            consultation_data['consultation_type'],
            ConsultationStatus.SCHEDULED.value,
            consultation_data['scheduled_time'],
            consultation_data.get('duration_minutes', 30),
            consultation_data['requesting_doctor_id'],
            consultation_data['consulting_specialist_id'],
            consultation_data['hospital_id'],
            consultation_data['specialist_hospital_id'],
            consultation_data['title'],
            consultation_data.get('description'),
            consultation_data['clinical_question'],
            consultation_data.get('urgency_level', 'medium')
        ))
        
        conn.commit()
        conn.close()
        
        # If emergency, add to priority queue
        if consultation_data.get('urgency_level') in ['high', 'critical']:
            self._add_to_emergency_queue(consultation_id, consultation_data.get('urgency_level'))
            
        # Send notifications
        self._send_consultation_notifications(consultation_id, 'scheduled')
        
        return consultation_id
        
    def start_consultation(self, consultation_id: str, meeting_room_id: str) -> bool:
        """Start a telemedicine consultation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE telemedicine_consultations 
            SET status = ?, started_at = CURRENT_TIMESTAMP, meeting_room_id = ?
            WHERE consultation_id = ?
        ''', (ConsultationStatus.IN_PROGRESS.value, meeting_room_id, consultation_id))
        
        conn.commit()
        conn.close()
        
        # Send notifications
        self._send_consultation_notifications(consultation_id, 'started')
        
        return True
        
    def end_consultation(self, consultation_id: str, consultation_notes: str = None,
                        diagnosis: str = None, recommendations: str = None,
                        follow_up_required: bool = False, follow_up_date: datetime = None) -> bool:
        """End a telemedicine consultation with notes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE telemedicine_consultations 
            SET status = ?, ended_at = CURRENT_TIMESTAMP, consultation_notes = ?,
                diagnosis = ?, recommendations = ?, follow_up_required = ?, follow_up_date = ?
            WHERE consultation_id = ?
        ''', (
            ConsultationStatus.COMPLETED.value, consultation_notes, diagnosis,
            recommendations, follow_up_required, follow_up_date, consultation_id
        ))
        
        conn.commit()
        conn.close()
        
        # Send completion notifications
        self._send_consultation_notifications(consultation_id, 'completed')
        
        return True
        
    def join_consultation(self, consultation_id: str, user_id: str, username: str,
                         role: str, hospital_id: str = None) -> str:
        """Add a participant to a consultation"""
        participant_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO consultation_participants (
                participant_id, consultation_id, user_id, username,
                role, hospital_id, joined_at
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (participant_id, consultation_id, user_id, username, role, hospital_id))
        
        conn.commit()
        conn.close()
        
        return participant_id
        
    def leave_consultation(self, consultation_id: str, user_id: str):
        """Remove a participant from a consultation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE consultation_participants 
            SET left_at = CURRENT_TIMESTAMP
            WHERE consultation_id = ? AND user_id = ?
        ''', (consultation_id, user_id))
        
        conn.commit()
        conn.close()
        
    def share_image_in_consultation(self, consultation_id: str, study_id: str,
                                  shared_by_user_id: str, series_id: str = None,
                                  instance_id: str = None, annotation_data: Dict = None,
                                  measurement_data: Dict = None) -> str:
        """Share an image/study during consultation"""
        share_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO consultation_shared_images (
                share_id, consultation_id, study_id, series_id, instance_id,
                shared_by_user_id, annotation_data, measurement_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            share_id, consultation_id, study_id, series_id, instance_id,
            shared_by_user_id,
            json.dumps(annotation_data) if annotation_data else None,
            json.dumps(measurement_data) if measurement_data else None
        ))
        
        conn.commit()
        conn.close()
        
        return share_id
        
    def send_consultation_message(self, consultation_id: str, user_id: str,
                                username: str, message: str, message_type: str = 'text',
                                reference_data: Dict = None) -> str:
        """Send a message during consultation"""
        message_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO consultation_messages (
                message_id, consultation_id, user_id, username,
                message, message_type, reference_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            message_id, consultation_id, user_id, username,
            message, message_type,
            json.dumps(reference_data) if reference_data else None
        ))
        
        conn.commit()
        conn.close()
        
        return message_id
        
    def find_available_specialists(self, specialty: str, consultation_type: str,
                                 preferred_time: datetime, duration_minutes: int = 30) -> List[Dict]:
        """Find available specialists for a consultation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get day of week and time
        day_of_week = preferred_time.weekday()
        consultation_time = preferred_time.time()
        
        cursor.execute('''
            SELECT sa.specialist_id, sa.specialty, sa.hospital_id,
                   sa.start_time, sa.end_time, sa.max_consultations_per_hour,
                   u.username, u.email, h.name as hospital_name
            FROM specialist_availability sa
            JOIN users u ON sa.specialist_id = u.user_id
            JOIN hospitals h ON sa.hospital_id = h.id
            WHERE sa.specialty = ? 
            AND sa.day_of_week = ?
            AND sa.start_time <= ?
            AND sa.end_time >= ?
            AND sa.is_active = 1
            AND (sa.consultation_types IS NULL OR sa.consultation_types LIKE ?)
        ''', (
            specialty, day_of_week, consultation_time, consultation_time,
            f'%{consultation_type}%'
        ))
        
        available_specialists = []
        for row in cursor.fetchall():
            # Check current bookings for this time slot
            cursor.execute('''
                SELECT COUNT(*) FROM telemedicine_consultations
                WHERE consulting_specialist_id = ?
                AND DATE(scheduled_time) = DATE(?)
                AND TIME(scheduled_time) BETWEEN TIME(?, '-30 minutes') AND TIME(?, '+30 minutes')
                AND status IN ('scheduled', 'in_progress')
            ''', (row[0], preferred_time, preferred_time, preferred_time))
            
            current_bookings = cursor.fetchone()[0]
            
            if current_bookings < row[5]:  # max_consultations_per_hour
                available_specialists.append({
                    'specialist_id': row[0],
                    'specialty': row[1],
                    'hospital_id': row[2],
                    'username': row[6],
                    'email': row[7],
                    'hospital_name': row[8],
                    'available_slots': row[5] - current_bookings
                })
                
        conn.close()
        return available_specialists
        
    def get_consultation_details(self, consultation_id: str) -> Dict:
        """Get complete consultation details"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get consultation info
        cursor.execute('SELECT * FROM telemedicine_consultations WHERE consultation_id = ?', 
                      (consultation_id,))
        consultation = cursor.fetchone()
        
        if not consultation:
            return None
            
        # Get participants
        cursor.execute('''
            SELECT * FROM consultation_participants 
            WHERE consultation_id = ?
            ORDER BY joined_at
        ''', (consultation_id,))
        participants = cursor.fetchall()
        
        # Get messages
        cursor.execute('''
            SELECT * FROM consultation_messages 
            WHERE consultation_id = ?
            ORDER BY timestamp
        ''', (consultation_id,))
        messages = cursor.fetchall()
        
        # Get shared images
        cursor.execute('''
            SELECT * FROM consultation_shared_images 
            WHERE consultation_id = ?
            ORDER BY shared_at
        ''', (consultation_id,))
        shared_images = cursor.fetchall()
        
        conn.close()
        
        return {
            'consultation': {
                'consultation_id': consultation[0],
                'patient_id': consultation[1],
                'study_id': consultation[2],
                'consultation_type': consultation[3],
                'status': consultation[4],
                'scheduled_time': consultation[5],
                'duration_minutes': consultation[6],
                'requesting_doctor_id': consultation[7],
                'consulting_specialist_id': consultation[8],
                'hospital_id': consultation[9],
                'specialist_hospital_id': consultation[10],
                'title': consultation[11],
                'description': consultation[12],
                'clinical_question': consultation[13],
                'urgency_level': consultation[14],
                'created_at': consultation[15],
                'started_at': consultation[16],
                'ended_at': consultation[17],
                'meeting_room_id': consultation[18],
                'consultation_notes': consultation[20],
                'diagnosis': consultation[21],
                'recommendations': consultation[22]
            },
            'participants': [
                {
                    'participant_id': p[0],
                    'user_id': p[2],
                    'username': p[3],
                    'role': p[4],
                    'hospital_id': p[5],
                    'joined_at': p[6],
                    'left_at': p[7],
                    'connection_quality': p[8]
                } for p in participants
            ],
            'messages': [
                {
                    'message_id': m[0],
                    'user_id': m[2],
                    'username': m[3],
                    'message': m[4],
                    'message_type': m[5],
                    'reference_data': json.loads(m[6]) if m[6] else None,
                    'timestamp': m[7]
                } for m in messages
            ],
            'shared_images': [
                {
                    'share_id': s[0],
                    'study_id': s[2],
                    'series_id': s[3],
                    'instance_id': s[4],
                    'shared_by_user_id': s[5],
                    'annotation_data': json.loads(s[6]) if s[6] else None,
                    'measurement_data': json.loads(s[7]) if s[7] else None,
                    'shared_at': s[8]
                } for s in shared_images
            ]
        }
        
    def _add_to_emergency_queue(self, consultation_id: str, urgency_level: str):
        """Add consultation to emergency queue"""
        priority_score = {'high': 80, 'critical': 100}.get(urgency_level, 50)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current queue position
        cursor.execute('''
            SELECT COUNT(*) FROM emergency_consultation_queue 
            WHERE priority_score >= ? AND assigned_at IS NULL
        ''', (priority_score,))
        queue_position = cursor.fetchone()[0] + 1
        
        cursor.execute('''
            INSERT INTO emergency_consultation_queue (
                queue_id, consultation_id, priority_score, queue_position,
                estimated_wait_minutes
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()), consultation_id, priority_score, 
            queue_position, queue_position * 15  # Estimate 15 min per consultation
        ))
        
        conn.commit()
        conn.close()
        
    def _send_consultation_notifications(self, consultation_id: str, event_type: str):
        """Send notifications for consultation events"""
        # Implementation would send emails, SMS, or push notifications
        # to relevant participants
        pass

# South African Healthcare Specialties
SA_MEDICAL_SPECIALTIES = [
    'radiology', 'cardiology', 'neurology', 'orthopedics', 'oncology',
    'pediatrics', 'emergency_medicine', 'internal_medicine', 'surgery',
    'psychiatry', 'dermatology', 'ophthalmology', 'ent', 'urology',
    'gynecology', 'anesthesiology', 'pathology', 'nuclear_medicine'
]

# South African Time Zones
SA_TIMEZONES = [
    'Africa/Johannesburg',  # SAST (UTC+2)
]

if __name__ == "__main__":
    # Example usage
    telemedicine = TelemedicineManager()
    
    # Schedule a consultation
    consultation_data = {
        'patient_id': 'patient_123',
        'study_id': 'study_456',
        'consultation_type': ConsultationType.SECOND_OPINION.value,
        'scheduled_time': datetime.now() + timedelta(hours=2),
        'requesting_doctor_id': 'dr_smith',
        'consulting_specialist_id': 'dr_jones',
        'hospital_id': 'hospital_1',
        'specialist_hospital_id': 'hospital_2',
        'title': 'Cardiac CT Second Opinion',
        'clinical_question': 'Please review cardiac CT for possible coronary artery disease',
        'urgency_level': 'medium'
    }
    
    consultation_id = telemedicine.schedule_consultation(consultation_data)
    print(f"Scheduled consultation: {consultation_id}")
    
    # Find available specialists
    specialists = telemedicine.find_available_specialists(
        'cardiology', 'second_opinion', datetime.now() + timedelta(hours=1)
    )
    print(f"Available specialists: {len(specialists)}")