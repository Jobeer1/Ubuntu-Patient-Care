"""
Disaster Resilience Module for RIS-1
Offline-first operations, emergency broadcast, volunteer coordination
Tested for natural disasters, conflict zones, pandemics
"""

import os
import json
import sqlite3
import threading
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib
import queue

logger = logging.getLogger(__name__)

# =============================================
# Data Classes
# =============================================

@dataclass
class TriageRecord:
    """Emergency triage classification"""
    patient_id: int
    severity_level: str  # 'critical', 'urgent', 'moderate', 'minor', 'walking'
    chief_complaint: str
    vital_signs: Dict
    injuries: List[str]
    treatment_given: str
    assigned_to: Optional[str]  # Healthcare worker ID
    location_lat: Optional[float]
    location_lon: Optional[float]
    timestamp: str

@dataclass
class DisasterEvent:
    """Disaster event tracking"""
    event_id: str
    event_type: str  # 'earthquake', 'flood', 'conflict', 'pandemic', 'accident'
    location: str
    magnitude: str
    status: str  # 'active', 'contained', 'resolved'
    affected_facilities: List[str]
    affected_population: int
    created_at: str

@dataclass
class VolunteerTask:
    """Task assignment for volunteers"""
    task_id: str
    volunteer_id: str
    task_type: str  # 'triage', 'supply_distribution', 'casualty_evacuation', 'data_entry'
    patient_id: Optional[int]
    location: str
    status: str  # 'assigned', 'in_progress', 'completed', 'failed'
    priority: int
    created_at: str
    completed_at: Optional[str]

# =============================================
# Offline-First Triage Management
# =============================================

class TriageManager:
    """
    Offline-first triage management for mass casualty events
    Operates without network connectivity
    """
    
    def __init__(self, db_path: str = './ris.db'):
        self.db_path = db_path
        self.local_queue = queue.Queue()  # In-memory queue for pending operations
        self.sync_lock = threading.RLock()
    
    def create_triage_record(self, triage: TriageRecord) -> Tuple[bool, str]:
        """
        Create triage record (offline)
        
        Returns:
            (success, triage_id)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            triage_id = hashlib.sha256(
                f"{triage.patient_id}{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()[:16]
            
            cursor.execute("""
                INSERT INTO triage_records 
                (triage_id, patient_id, severity_level, chief_complaint, 
                 vital_signs, injuries, treatment_given, assigned_to, 
                 location_lat, location_lon, sync_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                triage_id,
                triage.patient_id,
                triage.severity_level,
                triage.chief_complaint,
                json.dumps(triage.vital_signs),
                json.dumps(triage.injuries),
                triage.treatment_given,
                triage.assigned_to,
                triage.location_lat,
                triage.location_lon,
                'pending',
                triage.timestamp
            ))
            
            # Queue for sync when online
            self.local_queue.put(('triage_record', triage_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Triage record created: {triage_id} (patient {triage.patient_id})")
            return True, triage_id
        
        except Exception as e:
            logger.error(f"Error creating triage record: {str(e)}")
            return False, str(e)
    
    def update_triage_status(self, triage_id: str, 
                            severity_level: str = None,
                            treatment_given: str = None,
                            assigned_to: str = None) -> bool:
        """Update triage record (offline)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if severity_level:
                updates.append("severity_level = ?")
                params.append(severity_level)
            
            if treatment_given:
                updates.append("treatment_given = ?")
                params.append(treatment_given)
            
            if assigned_to:
                updates.append("assigned_to = ?")
                params.append(assigned_to)
            
            if updates:
                updates.append("updated_at = ?")
                params.append(datetime.utcnow().isoformat())
                params.append(triage_id)
                
                cursor.execute(f"""
                    UPDATE triage_records 
                    SET {', '.join(updates)}
                    WHERE triage_id = ?
                """, params)
                
                conn.commit()
            
            conn.close()
            return True
        
        except Exception as e:
            logger.error(f"Error updating triage record: {str(e)}")
            return False
    
    def get_pending_syncs(self) -> Dict[str, List[str]]:
        """Get all pending sync operations"""
        pending = {'triage_records': [], 'patients': [], 'studies': []}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get pending triage records
            cursor.execute("""
                SELECT triage_id FROM triage_records 
                WHERE sync_status = 'pending'
            """)
            pending['triage_records'] = [row[0] for row in cursor.fetchall()]
            
            # Get pending patients
            cursor.execute("""
                SELECT id FROM patients 
                WHERE sync_status = 'pending'
            """)
            pending['patients'] = [str(row[0]) for row in cursor.fetchall()]
            
            conn.close()
        
        except Exception as e:
            logger.error(f"Error getting pending syncs: {str(e)}")
        
        return pending
    
    def sync_records(self, api_endpoint: str, auth_token: str = None) -> Dict:
        """
        Sync pending records when connectivity is available
        
        Returns:
            Sync status report
        """
        pending = self.get_pending_syncs()
        status = {
            'synced': 0,
            'failed': 0,
            'pending': sum(len(v) for v in pending.values())
        }
        
        if not HAS_REQUESTS or not pending['triage_records']:
            return status
        
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {auth_token}' if auth_token else None,
                'Content-Type': 'application/json'
            }
            
            # Sync triage records
            for triage_id in pending['triage_records']:
                try:
                    # Get record from local database
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT * FROM triage_records WHERE triage_id = ?
                    """, (triage_id,))
                    
                    record = dict(cursor.fetchone()) if cursor.fetchone() else None
                    conn.close()
                    
                    if not record:
                        continue
                    
                    # Send to server
                    response = requests.post(
                        f"{api_endpoint}/triage/sync",
                        json=record,
                        headers=headers,
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        # Mark as synced
                        conn = sqlite3.connect(self.db_path)
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE triage_records 
                            SET sync_status = 'synced'
                            WHERE triage_id = ?
                        """, (triage_id,))
                        conn.commit()
                        conn.close()
                        status['synced'] += 1
                    else:
                        status['failed'] += 1
                
                except Exception as e:
                    logger.error(f"Error syncing triage record {triage_id}: {str(e)}")
                    status['failed'] += 1
        
        except Exception as e:
            logger.error(f"Error during sync: {str(e)}")
        
        return status

# =============================================
# Disaster Event Management
# =============================================

class DisasterEventManager:
    """Manage disaster events and resource allocation"""
    
    def __init__(self, db_path: str = './ris.db'):
        self.db_path = db_path
    
    def register_disaster_event(self, event: DisasterEvent) -> bool:
        """Register a disaster event"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO disaster_events 
                (event_id, event_type, location, magnitude, status, 
                 affected_population, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.event_type,
                event.location,
                event.magnitude,
                event.status,
                event.affected_population,
                event.created_at
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Disaster event registered: {event.event_id} ({event.event_type})")
            return True
        
        except Exception as e:
            logger.error(f"Error registering disaster event: {str(e)}")
            return False
    
    def get_active_events(self) -> List[Dict]:
        """Get all active disaster events"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM disaster_events 
                WHERE status IN ('active', 'contained')
                ORDER BY created_at DESC
            """)
            
            events = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return events
        
        except Exception as e:
            logger.error(f"Error retrieving active events: {str(e)}")
            return []
    
    def get_affected_patients_by_event(self, event_id: str) -> List[Dict]:
        """Get patients affected by a specific event"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT p.*, COUNT(t.triage_id) as triage_count
                FROM patients p
                LEFT JOIN triage_records t ON p.id = t.patient_id
                JOIN disaster_events d ON d.event_id = ?
                WHERE p.created_at >= d.created_at
                GROUP BY p.id
                ORDER BY t.severity_level DESC
            """, (event_id,))
            
            patients = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return patients
        
        except Exception as e:
            logger.error(f"Error retrieving affected patients: {str(e)}")
            return []

# =============================================
# Volunteer Coordination
# =============================================

class VolunteerCoordinator:
    """Coordinate volunteers for disaster response"""
    
    def __init__(self, db_path: str = './ris.db'):
        self.db_path = db_path
    
    def assign_task(self, task: VolunteerTask) -> bool:
        """Assign task to volunteer"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO volunteer_tasks 
                (task_id, volunteer_id, task_type, patient_id, 
                 location, status, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id,
                task.volunteer_id,
                task.task_type,
                task.patient_id,
                task.location,
                task.status,
                task.priority,
                task.created_at
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Task assigned: {task.task_id} to volunteer {task.volunteer_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error assigning task: {str(e)}")
            return False
    
    def get_pending_tasks(self, volunteer_id: str = None) -> List[Dict]:
        """Get pending tasks (for all or specific volunteer)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if volunteer_id:
                cursor.execute("""
                    SELECT * FROM volunteer_tasks 
                    WHERE volunteer_id = ? AND status IN ('assigned', 'in_progress')
                    ORDER BY priority DESC, created_at ASC
                """, (volunteer_id,))
            else:
                cursor.execute("""
                    SELECT * FROM volunteer_tasks 
                    WHERE status IN ('assigned', 'in_progress')
                    ORDER BY priority DESC, created_at ASC
                """)
            
            tasks = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return tasks
        
        except Exception as e:
            logger.error(f"Error retrieving tasks: {str(e)}")
            return []
    
    def complete_task(self, task_id: str) -> bool:
        """Mark task as completed"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE volunteer_tasks 
                SET status = 'completed', completed_at = ?
                WHERE task_id = ?
            """, (datetime.utcnow().isoformat(), task_id))
            
            conn.commit()
            conn.close()
            
            return True
        
        except Exception as e:
            logger.error(f"Error completing task: {str(e)}")
            return False

# =============================================
# Emergency Broadcast System
# =============================================

class EmergencyBroadcaster:
    """
    Send emergency alerts and critical information
    Supports offline queuing with eventual sync
    """
    
    def __init__(self, db_path: str = './ris.db'):
        self.db_path = db_path
        self.broadcast_queue = queue.Queue()
    
    def broadcast_alert(self, title: str, message: str, 
                       severity: str = 'info',
                       recipient_type: str = 'all') -> bool:
        """
        Send broadcast alert (queued for delivery)
        
        Args:
            title: Alert title
            message: Alert message
            severity: 'critical', 'urgent', 'info'
            recipient_type: 'all', 'healthcare_workers', 'volunteers', 'patients'
        """
        try:
            alert = {
                'id': hashlib.sha256(f"{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16],
                'title': title,
                'message': message,
                'severity': severity,
                'recipient_type': recipient_type,
                'created_at': datetime.utcnow().isoformat(),
                'delivered': False
            }
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO emergency_alerts 
                (alert_id, title, message, severity, recipient_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                alert['id'],
                alert['title'],
                alert['message'],
                alert['severity'],
                alert['recipient_type'],
                alert['created_at']
            ))
            
            conn.commit()
            conn.close()
            
            # Queue for broadcast
            self.broadcast_queue.put(alert)
            
            logger.info(f"Alert queued: {alert['id']} (severity: {severity})")
            return True
        
        except Exception as e:
            logger.error(f"Error creating alert: {str(e)}")
            return False
    
    def get_pending_broadcasts(self) -> List[Dict]:
        """Get pending broadcasts"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM emergency_alerts 
                WHERE delivered = 0
                ORDER BY severity DESC, created_at DESC
            """)
            
            alerts = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return alerts
        
        except Exception as e:
            logger.error(f"Error retrieving pending broadcasts: {str(e)}")
            return []

# =============================================
# Data Backup & Redundancy
# =============================================

class DisasterDataBackup:
    """Automatic backup and redundancy for disaster scenarios"""
    
    def __init__(self, db_path: str = './ris.db', backup_dir: str = './backups'):
        self.db_path = db_path
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)
    
    def create_backup(self, include_metadata: bool = True) -> Tuple[bool, str]:
        """
        Create database backup
        
        Returns:
            (success, backup_path)
        """
        try:
            import shutil
            
            timestamp = datetime.utcnow().isoformat().replace(':', '-')
            backup_name = f"ris_backup_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Copy database file
            shutil.copy2(self.db_path, backup_path)
            
            if include_metadata:
                # Create metadata file
                metadata = {
                    'backup_time': datetime.utcnow().isoformat(),
                    'source_db': self.db_path,
                    'backup_file': backup_path,
                    'file_size': os.path.getsize(backup_path)
                }
                
                metadata_path = backup_path.replace('.db', '.metadata')
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            logger.info(f"Backup created: {backup_path}")
            return True, backup_path
        
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            return False, str(e)
    
    def get_backup_inventory(self) -> List[Dict]:
        """Get list of available backups"""
        try:
            backups = []
            
            for filename in os.listdir(self.backup_dir):
                if filename.endswith('.db'):
                    backup_path = os.path.join(self.backup_dir, filename)
                    metadata_path = backup_path.replace('.db', '.metadata')
                    
                    metadata = {}
                    if os.path.exists(metadata_path):
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                    
                    backups.append({
                        'filename': filename,
                        'path': backup_path,
                        'size': os.path.getsize(backup_path),
                        'created': os.path.getctime(backup_path),
                        'metadata': metadata
                    })
            
            return sorted(backups, key=lambda x: x['created'], reverse=True)
        
        except Exception as e:
            logger.error(f"Error getting backup inventory: {str(e)}")
            return []

# =============================================
# Import HAS_REQUESTS at module level
# =============================================

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
