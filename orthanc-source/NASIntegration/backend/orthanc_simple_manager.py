"""
Simple Orthanc Management System for South African Healthcare
A practical, user-friendly approach to Orthanc PACS management
"""

import os
import json
import subprocess
import psutil
import requests
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SimpleOrthancManager:
    """Simple, practical Orthanc management for SA healthcare facilities"""
    
    def __init__(self, config_path: str = "orthanc_config.json"):
        self.config_path = config_path
        self.db_path = "orthanc_management.db"
        self.orthanc_process = None
        self.orthanc_url = "http://localhost:8042"
        self.orthanc_dicom_port = 4242
        self.init_database()
        
    def init_database(self):
        """Initialize simple database for management"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Simple tables for practical management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orthanc_status (
                id INTEGER PRIMARY KEY,
                status TEXT,
                started_at TEXT,
                last_check TEXT,
                studies_count INTEGER DEFAULT 0,
                storage_used_mb INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quick_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name TEXT,
                patient_id TEXT,
                study_date TEXT,
                study_description TEXT,
                share_token TEXT UNIQUE,
                created_by TEXT,
                created_at TEXT,
                expires_at TEXT,
                access_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referring_doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                phone TEXT,
                practice_name TEXT,
                hpcsa_number TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    # ===== SIMPLE SERVER MANAGEMENT =====
    
    def get_server_status(self) -> Dict[str, Any]:
        """Get simple server status - what admins actually need to know"""
        try:
            # Check if Orthanc process is running
            is_running = self.is_orthanc_running()
            
            if is_running:
                # Get basic stats from Orthanc API
                try:
                    response = requests.get(f"{self.orthanc_url}/system", timeout=5)
                    system_info = response.json()
                    
                    # Get studies count
                    studies_response = requests.get(f"{self.orthanc_url}/studies", timeout=5)
                    studies_count = len(studies_response.json())
                    
                    # Get storage info
                    storage_response = requests.get(f"{self.orthanc_url}/statistics", timeout=5)
                    storage_info = storage_response.json()
                    
                    return {
                        'status': 'running',
                        'version': system_info.get('Version', 'Unknown'),
                        'uptime': self.get_uptime(),
                        'studies_count': studies_count,
                        'storage_used_mb': storage_info.get('TotalDiskSizeMB', 0),
                        'web_url': self.orthanc_url,
                        'dicom_port': self.orthanc_dicom_port,
                        'last_check': datetime.now().isoformat()
                    }
                    
                except requests.RequestException:
                    return {
                        'status': 'process_running_but_not_responding',
                        'message': 'Orthanc process is running but not responding to web requests',
                        'last_check': datetime.now().isoformat()
                    }
            else:
                return {
                    'status': 'stopped',
                    'message': 'Orthanc is not running',
                    'last_check': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error checking server status: {e}")
            return {
                'status': 'error',
                'message': f'Error checking status: {str(e)}',
                'last_check': datetime.now().isoformat()
            }
    
    def is_orthanc_running(self) -> bool:
        """Check if Orthanc process is running"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'orthanc' in proc.info['name'].lower():
                    return True
                if proc.info['cmdline'] and any('orthanc' in cmd.lower() for cmd in proc.info['cmdline']):
                    return True
            return False
        except Exception:
            return False
    
    def start_orthanc(self) -> Dict[str, Any]:
        """Start Orthanc server with simple configuration"""
        try:
            if self.is_orthanc_running():
                return {'success': False, 'message': 'Orthanc is already running'}
            
            # Create basic configuration if it doesn't exist
            config = self.get_basic_config()
            
            # Write config to file
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Start Orthanc
            if os.name == 'nt':  # Windows
                self.orthanc_process = subprocess.Popen([
                    'Orthanc.exe', self.config_path
                ], creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:  # Linux
                self.orthanc_process = subprocess.Popen([
                    'orthanc', self.config_path
                ])
            
            # Wait a moment and check if it started
            import time
            time.sleep(3)
            
            if self.is_orthanc_running():
                self.update_status('running')
                return {
                    'success': True, 
                    'message': 'Orthanc started successfully',
                    'web_url': self.orthanc_url,
                    'dicom_port': self.orthanc_dicom_port
                }
            else:
                return {'success': False, 'message': 'Failed to start Orthanc'}
                
        except Exception as e:
            logger.error(f"Error starting Orthanc: {e}")
            return {'success': False, 'message': f'Error starting Orthanc: {str(e)}'}
    
    def stop_orthanc(self) -> Dict[str, Any]:
        """Stop Orthanc server"""
        try:
            # Try graceful shutdown via API first
            try:
                requests.post(f"{self.orthanc_url}/tools/shutdown", timeout=5)
                import time
                time.sleep(2)
            except:
                pass
            
            # Force kill if still running
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'orthanc' in proc.info['name'].lower():
                        proc.terminate()
                        proc.wait(timeout=5)
                    elif proc.info['cmdline'] and any('orthanc' in cmd.lower() for cmd in proc.info['cmdline']):
                        proc.terminate()
                        proc.wait(timeout=5)
                except:
                    continue
            
            self.update_status('stopped')
            return {'success': True, 'message': 'Orthanc stopped successfully'}
            
        except Exception as e:
            logger.error(f"Error stopping Orthanc: {e}")
            return {'success': False, 'message': f'Error stopping Orthanc: {str(e)}'}
    
    def restart_orthanc(self) -> Dict[str, Any]:
        """Restart Orthanc server"""
        stop_result = self.stop_orthanc()
        if stop_result['success']:
            import time
            time.sleep(2)
            return self.start_orthanc()
        return stop_result

    # ===== SIMPLE CONFIGURATION =====
    
    def get_basic_config(self) -> Dict[str, Any]:
        """Get basic Orthanc configuration suitable for SA healthcare"""
        return {
            "Name": "SA Healthcare PACS",
            "HttpPort": 8042,
            "DicomPort": 4242,
            "DicomAet": "ORTHANC",
            "DicomCheckCalledAet": False,
            "DicomCheckModalityHost": False,
            "RemoteAccessAllowed": True,
            "AuthenticationEnabled": False,  # Start simple, add security later
            "SslEnabled": False,
            "StorageDirectory": "./orthanc-storage",
            "IndexDirectory": "./orthanc-index",
            "StorageCompression": True,
            "MaximumStorageSize": 0,  # Unlimited
            "MaximumPatientCount": 0,  # Unlimited
            "LogLevel": "default",
            "LogFile": "./orthanc.log",
            "Plugins": [],
            "DicomModalities": {},
            "OrthancPeers": {},
            "HttpTimeout": 60,
            "DicomThreadsCount": 4,
            "StorageAccessOnFind": "Always",
            "SaveJobs": True,
            "OverwriteInstances": False,
            "MediaArchiveSize": 1,
            "StorageAccessOnFind": "Always",
            "MetricsEnabled": True
        }
    
    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update Orthanc configuration with simple validation"""
        try:
            # Load current config
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = self.get_basic_config()
            
            # Apply updates
            config.update(updates)
            
            # Write back
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            return {'success': True, 'message': 'Configuration updated successfully'}
            
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            return {'success': False, 'message': f'Error updating config: {str(e)}'}

    # ===== SIMPLE PATIENT SHARING =====
    
    def create_patient_share(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create simple patient sharing link"""
        try:
            import secrets
            share_token = secrets.token_urlsafe(32)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO quick_shares 
                (patient_name, patient_id, study_date, study_description, 
                 share_token, created_by, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient_data.get('patient_name', ''),
                patient_data.get('patient_id', ''),
                patient_data.get('study_date', ''),
                patient_data.get('study_description', ''),
                share_token,
                patient_data.get('created_by', 'admin'),
                datetime.now().isoformat(),
                (datetime.now() + timedelta(days=7)).isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            share_url = f"{self.orthanc_url}/share/{share_token}"
            
            return {
                'success': True,
                'share_token': share_token,
                'share_url': share_url,
                'expires_in_days': 7,
                'message': 'Patient share created successfully'
            }
            
        except Exception as e:
            logger.error(f"Error creating patient share: {e}")
            return {'success': False, 'message': f'Error creating share: {str(e)}'}
    
    def get_patient_shares(self) -> List[Dict[str, Any]]:
        """Get all patient shares"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM quick_shares 
                WHERE is_active = 1 
                ORDER BY created_at DESC
            ''')
            
            shares = []
            for row in cursor.fetchall():
                shares.append({
                    'id': row[0],
                    'patient_name': row[1],
                    'patient_id': row[2],
                    'study_date': row[3],
                    'study_description': row[4],
                    'share_token': row[5],
                    'created_by': row[6],
                    'created_at': row[7],
                    'expires_at': row[8],
                    'access_count': row[9],
                    'share_url': f"{self.orthanc_url}/share/{row[5]}"
                })
            
            conn.close()
            return shares
            
        except Exception as e:
            logger.error(f"Error getting patient shares: {e}")
            return []

    # ===== SIMPLE DOCTOR MANAGEMENT =====
    
    def add_referring_doctor(self, doctor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add referring doctor - simple registration"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO referring_doctors 
                (name, email, phone, practice_name, hpcsa_number, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                doctor_data.get('name', ''),
                doctor_data.get('email', ''),
                doctor_data.get('phone', ''),
                doctor_data.get('practice_name', ''),
                doctor_data.get('hpcsa_number', ''),
                datetime.now().isoformat()
            ))
            
            doctor_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'doctor_id': doctor_id,
                'message': 'Referring doctor added successfully'
            }
            
        except Exception as e:
            logger.error(f"Error adding doctor: {e}")
            return {'success': False, 'message': f'Error adding doctor: {str(e)}'}
    
    def get_referring_doctors(self) -> List[Dict[str, Any]]:
        """Get all referring doctors"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM referring_doctors WHERE is_active = 1')
            
            doctors = []
            for row in cursor.fetchall():
                doctors.append({
                    'id': row[0],
                    'name': row[1],
                    'email': row[2],
                    'phone': row[3],
                    'practice_name': row[4],
                    'hpcsa_number': row[5],
                    'created_at': row[7]
                })
            
            conn.close()
            return doctors
            
        except Exception as e:
            logger.error(f"Error getting doctors: {e}")
            return []

    # ===== UTILITY METHODS =====
    
    def update_status(self, status: str):
        """Update server status in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO orthanc_status 
                (id, status, started_at, last_check)
                VALUES (1, ?, ?, ?)
            ''', (status, datetime.now().isoformat(), datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating status: {e}")
    
    def get_uptime(self) -> str:
        """Get server uptime"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                if 'orthanc' in proc.info['name'].lower():
                    uptime_seconds = datetime.now().timestamp() - proc.info['create_time']
                    hours = int(uptime_seconds // 3600)
                    minutes = int((uptime_seconds % 3600) // 60)
                    return f"{hours}h {minutes}m"
            return "Unknown"
        except Exception:
            return "Unknown"
    
    def get_quick_stats(self) -> Dict[str, Any]:
        """Get quick stats for dashboard"""
        try:
            status = self.get_server_status()
            shares = self.get_patient_shares()
            doctors = self.get_referring_doctors()
            
            return {
                'server_status': status['status'],
                'studies_count': status.get('studies_count', 0),
                'storage_used_mb': status.get('storage_used_mb', 0),
                'active_shares': len([s for s in shares if datetime.fromisoformat(s['expires_at']) > datetime.now()]),
                'total_doctors': len(doctors),
                'uptime': status.get('uptime', 'Unknown')
            }
            
        except Exception as e:
            logger.error(f"Error getting quick stats: {e}")
            return {
                'server_status': 'error',
                'studies_count': 0,
                'storage_used_mb': 0,
                'active_shares': 0,
                'total_doctors': 0,
                'uptime': 'Unknown'
            }

# Global instance
orthanc_manager = SimpleOrthancManager()