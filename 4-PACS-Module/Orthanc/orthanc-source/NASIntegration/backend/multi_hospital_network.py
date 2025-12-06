#!/usr/bin/env python3
"""
Multi-Hospital Network System for South African Healthcare
Enables distributed PACS across multiple healthcare facilities
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
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class MultiHospitalNetworkManager:
    """Manages distributed PACS network across multiple hospitals"""
    
    def __init__(self, db_path: str = "multi_hospital_network.db"):
        self.db_path = db_path
        self.init_database()
        self.encryption_key = self._get_or_create_encryption_key()
        
    def init_database(self):
        """Initialize the multi-hospital network database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Hospitals/Facilities table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hospitals (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL, -- 'public', 'private', 'clinic', 'specialist'
                province TEXT NOT NULL,
                city TEXT NOT NULL,
                address TEXT,
                contact_person TEXT,
                phone TEXT,
                email TEXT,
                api_endpoint TEXT NOT NULL,
                api_key TEXT NOT NULL,
                status TEXT DEFAULT 'active', -- 'active', 'inactive', 'maintenance'
                last_sync TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Network connections between hospitals
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hospital_connections (
                id TEXT PRIMARY KEY,
                hospital_a_id TEXT NOT NULL,
                hospital_b_id TEXT NOT NULL,
                connection_type TEXT NOT NULL, -- 'full', 'referral_only', 'emergency_only'
                permissions TEXT, -- JSON of specific permissions
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hospital_a_id) REFERENCES hospitals (id),
                FOREIGN KEY (hospital_b_id) REFERENCES hospitals (id)
            )
        ''')
        
        # Shared studies across hospitals
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shared_studies (
                id TEXT PRIMARY KEY,
                study_id TEXT NOT NULL,
                source_hospital_id TEXT NOT NULL,
                target_hospital_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                study_date TEXT,
                modality TEXT,
                description TEXT,
                sharing_reason TEXT, -- 'referral', 'consultation', 'emergency', 'second_opinion'
                shared_by_user_id TEXT,
                access_level TEXT DEFAULT 'read_only', -- 'read_only', 'full_access'
                expires_at TIMESTAMP,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_hospital_id) REFERENCES hospitals (id),
                FOREIGN KEY (target_hospital_id) REFERENCES hospitals (id)
            )
        ''')
        
        # Network sync logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_logs (
                id TEXT PRIMARY KEY,
                hospital_id TEXT NOT NULL,
                sync_type TEXT NOT NULL, -- 'full', 'incremental', 'emergency'
                status TEXT NOT NULL, -- 'success', 'failed', 'partial'
                records_synced INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                error_details TEXT,
                duration_seconds REAL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (hospital_id) REFERENCES hospitals (id)
            )
        ''')
        
        # Emergency access logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emergency_access_logs (
                id TEXT PRIMARY KEY,
                requesting_hospital_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                accessing_user_id TEXT NOT NULL,
                emergency_type TEXT NOT NULL, -- 'trauma', 'cardiac', 'stroke', 'general'
                justification TEXT NOT NULL,
                accessed_studies TEXT, -- JSON array of study IDs
                approved_by TEXT,
                access_duration_minutes INTEGER DEFAULT 60,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (requesting_hospital_id) REFERENCES hospitals (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def _get_or_create_encryption_key(self) -> Fernet:
        """Get or create encryption key for secure inter-hospital communication"""
        key_file = "network_encryption.key"
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
                
        return Fernet(key)
        
    def register_hospital(self, hospital_data: Dict) -> str:
        """Register a new hospital in the network"""
        hospital_id = str(uuid.uuid4())
        api_key = self._generate_api_key()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO hospitals (
                id, name, type, province, city, address, contact_person,
                phone, email, api_endpoint, api_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            hospital_id, hospital_data['name'], hospital_data['type'],
            hospital_data['province'], hospital_data['city'], hospital_data.get('address'),
            hospital_data.get('contact_person'), hospital_data.get('phone'),
            hospital_data.get('email'), hospital_data['api_endpoint'], api_key
        ))
        
        conn.commit()
        conn.close()
        
        return hospital_id
        
    def create_hospital_connection(self, hospital_a_id: str, hospital_b_id: str, 
                                 connection_type: str, permissions: Dict = None) -> str:
        """Create a connection between two hospitals"""
        connection_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO hospital_connections (
                id, hospital_a_id, hospital_b_id, connection_type, permissions
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            connection_id, hospital_a_id, hospital_b_id, connection_type,
            json.dumps(permissions) if permissions else None
        ))
        
        conn.commit()
        conn.close()
        
        return connection_id
        
    def share_study_with_hospital(self, study_id: str, source_hospital_id: str,
                                target_hospital_id: str, patient_id: str,
                                sharing_reason: str, shared_by_user_id: str,
                                expires_hours: int = 24) -> str:
        """Share a study with another hospital"""
        share_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO shared_studies (
                id, study_id, source_hospital_id, target_hospital_id,
                patient_id, sharing_reason, shared_by_user_id, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            share_id, study_id, source_hospital_id, target_hospital_id,
            patient_id, sharing_reason, shared_by_user_id, expires_at
        ))
        
        conn.commit()
        conn.close()
        
        # Notify target hospital
        self._notify_hospital_of_shared_study(target_hospital_id, share_id)
        
        return share_id
        
    def request_emergency_access(self, requesting_hospital_id: str, patient_id: str,
                               accessing_user_id: str, emergency_type: str,
                               justification: str) -> str:
        """Request emergency access to patient data across network"""
        access_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=1)  # 1 hour emergency access
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO emergency_access_logs (
                id, requesting_hospital_id, patient_id, accessing_user_id,
                emergency_type, justification, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            access_id, requesting_hospital_id, patient_id, accessing_user_id,
            emergency_type, justification, expires_at
        ))
        
        conn.commit()
        conn.close()
        
        # Auto-approve emergency access and find relevant studies
        self._process_emergency_access(access_id, patient_id)
        
        return access_id
        
    def sync_with_hospital(self, hospital_id: str, sync_type: str = 'incremental') -> Dict:
        """Synchronize data with a specific hospital"""
        sync_id = str(uuid.uuid4())
        started_at = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get hospital details
        cursor.execute('SELECT * FROM hospitals WHERE id = ?', (hospital_id,))
        hospital = cursor.fetchone()
        
        if not hospital:
            return {'error': 'Hospital not found'}
            
        try:
            # Perform sync based on type
            if sync_type == 'full':
                result = self._perform_full_sync(hospital)
            else:
                result = self._perform_incremental_sync(hospital)
                
            # Log successful sync
            cursor.execute('''
                INSERT INTO sync_logs (
                    id, hospital_id, sync_type, status, records_synced,
                    duration_seconds, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sync_id, hospital_id, sync_type, 'success',
                result.get('records_synced', 0),
                (datetime.now() - started_at).total_seconds(),
                started_at, datetime.now()
            ))
            
            # Update last sync time
            cursor.execute('''
                UPDATE hospitals SET last_sync = CURRENT_TIMESTAMP WHERE id = ?
            ''', (hospital_id,))
            
            conn.commit()
            return result
            
        except Exception as e:
            # Log failed sync
            cursor.execute('''
                INSERT INTO sync_logs (
                    id, hospital_id, sync_type, status, errors_count,
                    error_details, duration_seconds, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sync_id, hospital_id, sync_type, 'failed', 1,
                str(e), (datetime.now() - started_at).total_seconds(),
                started_at, datetime.now()
            ))
            conn.commit()
            return {'error': str(e)}
            
        finally:
            conn.close()
            
    def get_network_status(self) -> Dict:
        """Get overall network status and statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count hospitals by type and status
        cursor.execute('''
            SELECT type, status, COUNT(*) as count
            FROM hospitals
            GROUP BY type, status
        ''')
        hospital_stats = cursor.fetchall()
        
        # Count active connections
        cursor.execute('''
            SELECT COUNT(*) FROM hospital_connections WHERE status = 'active'
        ''')
        active_connections = cursor.fetchone()[0]
        
        # Count shared studies
        cursor.execute('''
            SELECT COUNT(*) FROM shared_studies WHERE status = 'active'
        ''')
        active_shares = cursor.fetchone()[0]
        
        # Recent sync status
        cursor.execute('''
            SELECT hospital_id, status, completed_at
            FROM sync_logs
            WHERE id IN (
                SELECT id FROM sync_logs s1
                WHERE completed_at = (
                    SELECT MAX(completed_at) FROM sync_logs s2
                    WHERE s2.hospital_id = s1.hospital_id
                )
            )
            ORDER BY completed_at DESC
        ''')
        recent_syncs = cursor.fetchall()
        
        conn.close()
        
        return {
            'hospital_stats': hospital_stats,
            'active_connections': active_connections,
            'active_shares': active_shares,
            'recent_syncs': recent_syncs,
            'network_health': self._calculate_network_health()
        }
        
    def _generate_api_key(self) -> str:
        """Generate a secure API key for hospital authentication"""
        return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
        
    def _notify_hospital_of_shared_study(self, hospital_id: str, share_id: str):
        """Notify a hospital about a newly shared study"""
        # Implementation would send notification via API or message queue
        pass
        
    def _process_emergency_access(self, access_id: str, patient_id: str):
        """Process emergency access request and find relevant studies"""
        # Implementation would search for patient studies across network
        # and grant temporary access
        pass
        
    def _perform_full_sync(self, hospital: Tuple) -> Dict:
        """Perform full synchronization with a hospital"""
        # Implementation would sync all data
        return {'records_synced': 0, 'type': 'full'}
        
    def _perform_incremental_sync(self, hospital: Tuple) -> Dict:
        """Perform incremental synchronization with a hospital"""
        # Implementation would sync only changes since last sync
        return {'records_synced': 0, 'type': 'incremental'}
        
    def _calculate_network_health(self) -> str:
        """Calculate overall network health score"""
        # Implementation would analyze sync success rates, connection status, etc.
        return 'healthy'

# South African Healthcare Network Configuration
SA_HEALTHCARE_PROVINCES = [
    'Eastern Cape', 'Free State', 'Gauteng', 'KwaZulu-Natal',
    'Limpopo', 'Mpumalanga', 'Northern Cape', 'North West', 'Western Cape'
]

SA_HOSPITAL_TYPES = [
    'public_hospital', 'private_hospital', 'district_hospital',
    'regional_hospital', 'tertiary_hospital', 'specialist_hospital',
    'clinic', 'community_health_centre', 'day_hospital'
]

SA_EMERGENCY_TYPES = [
    'trauma', 'cardiac', 'stroke', 'respiratory', 'neurological',
    'pediatric_emergency', 'obstetric_emergency', 'general_emergency'
]

if __name__ == "__main__":
    # Example usage
    network = MultiHospitalNetworkManager()
    
    # Register a hospital
    hospital_data = {
        'name': 'Groote Schuur Hospital',
        'type': 'tertiary_hospital',
        'province': 'Western Cape',
        'city': 'Cape Town',
        'api_endpoint': 'https://gsh.health.gov.za/api',
        'contact_person': 'Dr. Smith',
        'phone': '+27-21-404-9111',
        'email': 'admin@gsh.health.gov.za'
    }
    
    hospital_id = network.register_hospital(hospital_data)
    print(f"Registered hospital: {hospital_id}")
    
    # Get network status
    status = network.get_network_status()
    print(f"Network status: {status}")