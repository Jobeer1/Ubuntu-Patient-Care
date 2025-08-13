#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - Device/Modality Management

Easy device management system for South African healthcare facilities.
Supports adding imaging machines (ultrasound, X-ray, CT, MRI, etc.) with
South African context and terminology.

Features:
- Step-by-step device addition wizard
- South African equipment presets
- DICOM connectivity testing
- Multi-language support (English, Afrikaans, isiZulu)
- Integration with common SA medical equipment
"""

import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import socket
import threading
import time
import subprocess
import platform
import ipaddress
import re
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

# DICOM networking
try:
    from pynetdicom import AE, evt, build_context
    from pynetdicom.sop_class import Verification
    DICOM_AVAILABLE = True
except ImportError:
    DICOM_AVAILABLE = False
    logging.warning("pynetdicom not available - DICOM connectivity testing disabled")

logger = logging.getLogger(__name__)

@dataclass
class MedicalDevice:
    """Medical imaging device/modality"""
    id: str
    name: str
    modality_type: str
    manufacturer: str
    model: str
    ae_title: str
    ip_address: str
    port: int
    department: str
    location: str
    serial_number: str = ""
    installation_date: str = ""
    last_service_date: str = ""
    status: str = "active"  # active, inactive, maintenance
    notes: str = ""
    created_date: str = ""
    updated_date: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MedicalDevice':
        """Create from dictionary"""
        return cls(**data)

class DeviceManager:
    """
    🏥 World-class device management for South African healthcare
    """
    
    def __init__(self, db_path: str = "medical_devices.db"):
        self.db_path = db_path
        self.init_database()
        self.load_sa_presets()
    
    def init_database(self):
        """Initialize device database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS medical_devices (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    modality_type TEXT NOT NULL,
                    manufacturer TEXT NOT NULL,
                    model TEXT NOT NULL,
                    ae_title TEXT NOT NULL UNIQUE,
                    ip_address TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    department TEXT NOT NULL,
                    location TEXT NOT NULL,
                    serial_number TEXT,
                    installation_date TEXT,
                    last_service_date TEXT,
                    status TEXT DEFAULT 'active',
                    notes TEXT,
                    created_date TEXT NOT NULL,
                    updated_date TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS device_connectivity_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    test_date TEXT NOT NULL,
                    test_type TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    response_time_ms INTEGER,
                    error_message TEXT,
                    FOREIGN KEY (device_id) REFERENCES medical_devices (id)
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_device_modality ON medical_devices(modality_type)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_device_department ON medical_devices(department)
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Device database initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing device database: {e}")
            raise
    
    def load_sa_presets(self):
        """Load South African medical equipment presets"""
        self.sa_equipment_presets = {
            "ultrasound": {
                "GE Healthcare": {
                    "Vivid E95": {"port": 104, "ae_title": "GE_VIVID"},
                    "Vivid S70": {"port": 104, "ae_title": "GE_VIVID_S70"},
                    "Logiq E10": {"port": 104, "ae_title": "GE_LOGIQ"}
                },
                "Philips": {
                    "EPIQ Elite": {"port": 104, "ae_title": "PHILIPS_EPIQ"},
                    "Affiniti 70": {"port": 104, "ae_title": "PHILIPS_AFF"},
                    "ClearVue 850": {"port": 104, "ae_title": "PHILIPS_CV"}
                },
                "Mindray": {
                    "Resona 7": {"port": 104, "ae_title": "MINDRAY_R7"},
                    "DC-8": {"port": 104, "ae_title": "MINDRAY_DC8"}
                },
                "Samsung": {
                    "RS85": {"port": 104, "ae_title": "SAMSUNG_RS85"},
                    "HS70A": {"port": 104, "ae_title": "SAMSUNG_HS70"}
                }
            },
            "xray": {
                "Siemens": {
                    "Ysio Max": {"port": 104, "ae_title": "SIEMENS_YSIO"},
                    "Multix Impact": {"port": 104, "ae_title": "SIEMENS_MX"}
                },
                "GE Healthcare": {
                    "Definium 8000": {"port": 104, "ae_title": "GE_DEF8000"},
                    "AMX 4+": {"port": 104, "ae_title": "GE_AMX4"}
                },
                "Philips": {
                    "DigitalDiagnost C90": {"port": 104, "ae_title": "PHILIPS_DD"},
                    "MobileDiagnost wDR": {"port": 104, "ae_title": "PHILIPS_MD"}
                }
            },
            "ct": {
                "Siemens": {
                    "SOMATOM go.Top": {"port": 104, "ae_title": "SIEMENS_CT"},
                    "SOMATOM Definition": {"port": 104, "ae_title": "SIEMENS_DEF"}
                },
                "GE Healthcare": {
                    "Revolution CT": {"port": 104, "ae_title": "GE_REV_CT"},
                    "Optima CT660": {"port": 104, "ae_title": "GE_OPT660"}
                },
                "Philips": {
                    "Ingenuity CT": {"port": 104, "ae_title": "PHILIPS_ING"},
                    "Brilliance CT": {"port": 104, "ae_title": "PHILIPS_BRI"}
                }
            },
            "mri": {
                "Siemens": {
                    "MAGNETOM Vida": {"port": 104, "ae_title": "SIEMENS_VIDA"},
                    "MAGNETOM Aera": {"port": 104, "ae_title": "SIEMENS_AERA"}
                },
                "GE Healthcare": {
                    "SIGNA Premier": {"port": 104, "ae_title": "GE_SIGNA"},
                    "Optima MR450w": {"port": 104, "ae_title": "GE_OPT450"}
                },
                "Philips": {
                    "Ingenia": {"port": 104, "ae_title": "PHILIPS_ING_MR"},
                    "Achieva": {"port": 104, "ae_title": "PHILIPS_ACH"}
                }
            },
            "mammography": {
                "Hologic": {
                    "Selenia Dimensions": {"port": 104, "ae_title": "HOLOGIC_SEL"},
                    "3Dimensions": {"port": 104, "ae_title": "HOLOGIC_3D"}
                },
                "GE Healthcare": {
                    "Senographe Pristina": {"port": 104, "ae_title": "GE_PRISTINA"},
                    "Essential": {"port": 104, "ae_title": "GE_ESSENTIAL"}
                }
            },
            "bone_density": {
                "Hologic": {
                    "Horizon DXA": {"port": 104, "ae_title": "HOLOGIC_DXA"},
                    "Discovery": {"port": 104, "ae_title": "HOLOGIC_DISC"}
                },
                "GE Healthcare": {
                    "Lunar Prodigy": {"port": 104, "ae_title": "GE_LUNAR"},
                    "iDXA": {"port": 104, "ae_title": "GE_IDXA"}
                }
            }
        }
        
        # South African hospital departments (in multiple languages)
        self.sa_departments = {
            "en": [
                "Radiology", "Emergency", "Theatre", "ICU", "Cardiology",
                "Orthopedics", "Neurology", "Oncology", "Pediatrics",
                "Obstetrics & Gynecology", "Urology", "Gastroenterology"
            ],
            "af": [
                "Radiologie", "Noodgeval", "Teater", "ICU", "Kardiologie",
                "Ortopedies", "Neurologie", "Onkologie", "Pediatrie",
                "Obstetrie & Ginekologie", "Urologie", "Gastroenterologie"
            ],
            "zu": [
                "I-Radiology", "Isimo", "I-Theatre", "ICU", "I-Cardiology",
                "I-Orthopedics", "I-Neurology", "I-Oncology", "Izingane",
                "Ukuzala & Abesifazane", "I-Urology", "I-Gastroenterology"
            ]
        }
    
    def get_equipment_presets(self, modality_type: str) -> Dict:
        """Get equipment presets for modality type"""
        return self.sa_equipment_presets.get(modality_type.lower(), {})
    
    def get_departments(self, language: str = "en") -> List[str]:
        """Get department list in specified language"""
        return self.sa_departments.get(language, self.sa_departments["en"])
    
    def generate_device_id(self, name: str) -> str:
        """Generate unique device ID"""
        base_id = name.upper().replace(" ", "_").replace("-", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{base_id}_{timestamp}"
    
    def add_device(self, device_data: Dict) -> Tuple[bool, str, Optional[MedicalDevice]]:
        """Add new medical device"""
        try:
            # Generate ID if not provided
            if 'id' not in device_data or not device_data['id']:
                device_data['id'] = self.generate_device_id(device_data['name'])
            
            # Set timestamps
            now = datetime.now().isoformat()
            device_data['created_date'] = now
            device_data['updated_date'] = now
            
            # Create device object
            device = MedicalDevice.from_dict(device_data)
            
            # Validate required fields
            required_fields = ['name', 'modality_type', 'manufacturer', 'model', 
                             'ae_title', 'ip_address', 'port', 'department', 'location']
            
            for field in required_fields:
                if not getattr(device, field):
                    return False, f"Missing required field: {field}", None
            
            # Validate IP address format
            try:
                socket.inet_aton(device.ip_address)
            except socket.error:
                return False, "Invalid IP address format", None
            
            # Validate port range
            if not (1 <= device.port <= 65535):
                return False, "Port must be between 1 and 65535", None
            
            # Check for duplicate AE Title
            if self.get_device_by_ae_title(device.ae_title):
                return False, f"AE Title '{device.ae_title}' already exists", None
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO medical_devices 
                (id, name, modality_type, manufacturer, model, ae_title, ip_address, port,
                 department, location, serial_number, installation_date, last_service_date,
                 status, notes, created_date, updated_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                device.id, device.name, device.modality_type, device.manufacturer,
                device.model, device.ae_title, device.ip_address, device.port,
                device.department, device.location, device.serial_number,
                device.installation_date, device.last_service_date, device.status,
                device.notes, device.created_date, device.updated_date
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Added device: {device.name} ({device.ae_title})")
            return True, "Device added successfully", device
            
        except Exception as e:
            logger.error(f"❌ Error adding device: {e}")
            return False, f"Error adding device: {str(e)}", None
    
    def get_device_by_id(self, device_id: str) -> Optional[MedicalDevice]:
        """Get device by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM medical_devices WHERE id = ?', (device_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                device_data = dict(zip(columns, row))
                return MedicalDevice.from_dict(device_data)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting device by ID: {e}")
            return None
    
    def get_device_by_ae_title(self, ae_title: str) -> Optional[MedicalDevice]:
        """Get device by AE Title"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM medical_devices WHERE ae_title = ?', (ae_title,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                device_data = dict(zip(columns, row))
                return MedicalDevice.from_dict(device_data)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting device by AE Title: {e}")
            return None
    
    def get_all_devices(self, status: str = None, modality_type: str = None, 
                       department: str = None) -> List[MedicalDevice]:
        """Get all devices with optional filters"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = 'SELECT * FROM medical_devices WHERE 1=1'
            params = []
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            if modality_type:
                query += ' AND modality_type = ?'
                params.append(modality_type)
            
            if department:
                query += ' AND department = ?'
                params.append(department)
            
            query += ' ORDER BY name'
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            conn.close()
            
            devices = []
            if rows:
                columns = [desc[0] for desc in cursor.description]
                for row in rows:
                    device_data = dict(zip(columns, row))
                    devices.append(MedicalDevice.from_dict(device_data))
            
            return devices
            
        except Exception as e:
            logger.error(f"❌ Error getting devices: {e}")
            return []
    
    def update_device(self, device_id: str, updates: Dict) -> Tuple[bool, str]:
        """Update device information"""
        try:
            # Get existing device
            device = self.get_device_by_id(device_id)
            if not device:
                return False, "Device not found"
            
            # Update timestamp
            updates['updated_date'] = datetime.now().isoformat()
            
            # Build update query
            set_clauses = []
            params = []
            
            for field, value in updates.items():
                if hasattr(device, field):
                    set_clauses.append(f"{field} = ?")
                    params.append(value)
            
            if not set_clauses:
                return False, "No valid fields to update"
            
            params.append(device_id)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = f"UPDATE medical_devices SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(query, params)
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Updated device: {device_id}")
            return True, "Device updated successfully"
            
        except Exception as e:
            logger.error(f"❌ Error updating device: {e}")
            return False, f"Error updating device: {str(e)}"
    
    def delete_device(self, device_id: str) -> Tuple[bool, str]:
        """Delete device"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if device exists
            cursor.execute('SELECT name FROM medical_devices WHERE id = ?', (device_id,))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return False, "Device not found"
            
            device_name = row[0]
            
            # Delete device
            cursor.execute('DELETE FROM medical_devices WHERE id = ?', (device_id,))
            
            # Delete connectivity test history
            cursor.execute('DELETE FROM device_connectivity_tests WHERE device_id = ?', (device_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Deleted device: {device_name} ({device_id})")
            return True, f"Device '{device_name}' deleted successfully"
            
        except Exception as e:
            logger.error(f"❌ Error deleting device: {e}")
            return False, f"Error deleting device: {str(e)}"
    
    def test_connectivity(self, device_id: str, test_type: str = "ping") -> Tuple[bool, str, int]:
        """Test device connectivity"""
        device = self.get_device_by_id(device_id)
        if not device:
            return False, "Device not found", 0
        
        start_time = time.time()
        success = False
        error_message = ""
        
        try:
            if test_type == "ping":
                success, error_message = self._test_ping(device.ip_address)
            elif test_type == "dicom_echo" and DICOM_AVAILABLE:
                success, error_message = self._test_dicom_echo(device)
            else:
                return False, f"Unsupported test type: {test_type}", 0
            
        except Exception as e:
            error_message = str(e)
        
        response_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        
        # Record test result
        self._record_connectivity_test(device_id, test_type, success, response_time, error_message)
        
        return success, error_message, response_time
    
    def _test_ping(self, ip_address: str) -> Tuple[bool, str]:
        """Test basic network connectivity"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((ip_address, 80))  # Try port 80 first
            sock.close()
            
            if result == 0:
                return True, "Network connectivity successful"
            else:
                return False, f"Cannot reach {ip_address}"
                
        except Exception as e:
            return False, f"Network test failed: {str(e)}"
    
    def _test_dicom_echo(self, device: MedicalDevice) -> Tuple[bool, str]:
        """Test DICOM C-ECHO connectivity"""
        if not DICOM_AVAILABLE:
            return False, "DICOM testing not available (pynetdicom not installed)"
        
        try:
            # Create Application Entity
            ae = AE()
            ae.add_requested_context(Verification)
            
            # Associate with peer AE
            assoc = ae.associate(device.ip_address, device.port, ae_title=device.ae_title)
            
            if assoc.is_established:
                # Send C-ECHO request
                status = assoc.send_c_echo()
                
                # Release association
                assoc.release()
                
                if status:
                    return True, "DICOM C-ECHO successful"
                else:
                    return False, "DICOM C-ECHO failed"
            else:
                return False, f"Failed to establish DICOM association with {device.ae_title}"
                
        except Exception as e:
            return False, f"DICOM test failed: {str(e)}"
    
    def _record_connectivity_test(self, device_id: str, test_type: str, success: bool, 
                                response_time: int, error_message: str):
        """Record connectivity test result"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO device_connectivity_tests 
                (device_id, test_date, test_type, success, response_time_ms, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (device_id, datetime.now().isoformat(), test_type, success, 
                  response_time, error_message))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error recording connectivity test: {e}")
    
    def get_connectivity_history(self, device_id: str, limit: int = 50) -> List[Dict]:
        """Get connectivity test history for device"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT test_date, test_type, success, response_time_ms, error_message
                FROM device_connectivity_tests 
                WHERE device_id = ?
                ORDER BY test_date DESC
                LIMIT ?
            ''', (device_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            history = []
            if rows:
                columns = ['test_date', 'test_type', 'success', 'response_time_ms', 'error_message']
                for row in rows:
                    history.append(dict(zip(columns, row)))
            
            return history
            
        except Exception as e:
            logger.error(f"❌ Error getting connectivity history: {e}")
            return []
    
    def get_device_statistics(self) -> Dict:
        """Get device statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total devices
            cursor.execute('SELECT COUNT(*) FROM medical_devices')
            total_devices = cursor.fetchone()[0]
            
            # Devices by status
            cursor.execute('SELECT status, COUNT(*) FROM medical_devices GROUP BY status')
            status_counts = dict(cursor.fetchall())
            
            # Devices by modality
            cursor.execute('SELECT modality_type, COUNT(*) FROM medical_devices GROUP BY modality_type')
            modality_counts = dict(cursor.fetchall())
            
            # Devices by department
            cursor.execute('SELECT department, COUNT(*) FROM medical_devices GROUP BY department')
            department_counts = dict(cursor.fetchall())
            
            # Recent connectivity tests
            cursor.execute('''
                SELECT COUNT(*) FROM device_connectivity_tests 
                WHERE test_date > datetime('now', '-24 hours')
            ''')
            recent_tests = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_devices': total_devices,
                'status_counts': status_counts,
                'modality_counts': modality_counts,
                'department_counts': department_counts,
                'recent_connectivity_tests': recent_tests
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting device statistics: {e}")
            return {}

    # ============================================================================
    # 🌐 NETWORK DISCOVERY FUNCTIONS - EXTREMELY EASY DEVICE ADDITION
    # ============================================================================

    def scan_arp_table(self) -> List[Dict]:
        """
        🔍 Scan ARP table to find all devices on the network
        This makes it EXTREMELY easy to discover medical devices!
        """
        try:
            logger.info("🔍 Scanning ARP table for network devices...")
            devices = []
            
            # Get ARP table based on operating system
            if platform.system().lower() == 'windows':
                devices = self._scan_arp_windows()
            else:
                devices = self._scan_arp_unix()
            
            # Enhance device information
            enhanced_devices = []
            for device in devices:
                enhanced = self._enhance_device_info(device)
                enhanced_devices.append(enhanced)
            
            logger.info(f"✅ Found {len(enhanced_devices)} devices in ARP table")
            return enhanced_devices
            
        except Exception as e:
            logger.error(f"❌ Error scanning ARP table: {e}")
            return []

    def _scan_arp_windows(self) -> List[Dict]:
        """Scan ARP table on Windows"""
        devices = []
        try:
            # Run arp -a command
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    # Parse ARP entry: IP address, MAC address, type
                    match = re.match(r'\s*(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F-]{17})\s+(\w+)', line)
                    if match:
                        ip, mac, arp_type = match.groups()
                        devices.append({
                            'ip_address': ip,
                            'mac_address': mac.upper().replace('-', ':'),
                            'arp_type': arp_type,
                            'source': 'arp_table'
                        })
            
        except Exception as e:
            logger.error(f"❌ Error scanning Windows ARP table: {e}")
        
        return devices

    def _scan_arp_unix(self) -> List[Dict]:
        """Scan ARP table on Unix/Linux"""
        devices = []
        try:
            # Try different ARP commands
            commands = [
                ['arp', '-a'],
                ['ip', 'neigh', 'show'],
                ['cat', '/proc/net/arp']
            ]
            
            for cmd in commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        devices = self._parse_unix_arp_output(result.stdout)
                        if devices:
                            break
                except:
                    continue
            
        except Exception as e:
            logger.error(f"❌ Error scanning Unix ARP table: {e}")
        
        return devices

    def _parse_unix_arp_output(self, output: str) -> List[Dict]:
        """Parse Unix ARP command output"""
        devices = []
        lines = output.split('\n')
        
        for line in lines:
            # Parse different ARP output formats
            # Format 1: hostname (ip) at mac [ether] on interface
            match1 = re.search(r'(\d+\.\d+\.\d+\.\d+).*?([0-9a-fA-F:]{17})', line)
            # Format 2: ip dev interface lladdr mac
            match2 = re.search(r'(\d+\.\d+\.\d+\.\d+).*?lladdr\s+([0-9a-fA-F:]{17})', line)
            # Format 3: /proc/net/arp format
            match3 = re.match(r'(\d+\.\d+\.\d+\.\d+)\s+\w+\s+\w+\s+([0-9a-fA-F:]{17})', line)
            
            match = match1 or match2 or match3
            if match:
                ip, mac = match.groups()
                devices.append({
                    'ip_address': ip,
                    'mac_address': mac.upper(),
                    'arp_type': 'dynamic',
                    'source': 'arp_table'
                })
        
        return devices

    def network_discovery_scan(self, ip_range: str, ports: List[int] = None, 
                             max_threads: int = 50) -> List[Dict]:
        """
        🌐 Perform network discovery scan on IP range
        This makes it EXTREMELY easy to find medical devices!
        
        Args:
            ip_range: IP range to scan (e.g., "192.168.1.0/24" or "192.168.1.1-192.168.1.254")
            ports: List of ports to check (default: common DICOM ports)
            max_threads: Maximum concurrent threads
        """
        try:
            if ports is None:
                ports = [104, 11112, 2762, 2761, 4242, 8042, 80, 443, 22, 23]  # Common DICOM and service ports
            
            logger.info(f"🌐 Starting network discovery scan on {ip_range}")
            
            # Parse IP range
            ip_list = self._parse_ip_range(ip_range)
            logger.info(f"📡 Scanning {len(ip_list)} IP addresses with {len(ports)} ports each")
            
            discovered_devices = []
            
            # Use ThreadPoolExecutor for concurrent scanning
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                # Submit all scan tasks
                future_to_ip = {}
                for ip in ip_list:
                    future = executor.submit(self._scan_single_ip, ip, ports)
                    future_to_ip[future] = ip
                
                # Collect results
                completed = 0
                for future in concurrent.futures.as_completed(future_to_ip):
                    ip = future_to_ip[future]
                    try:
                        result = future.result(timeout=30)
                        if result:
                            discovered_devices.append(result)
                        
                        completed += 1
                        if completed % 50 == 0:  # Progress update every 50 IPs
                            logger.info(f"📊 Scanned {completed}/{len(ip_list)} IPs, found {len(discovered_devices)} devices")
                            
                    except Exception as e:
                        logger.debug(f"❌ Error scanning {ip}: {e}")
            
            # Enhance discovered devices with additional information
            enhanced_devices = []
            for device in discovered_devices:
                enhanced = self._enhance_device_info(device)
                enhanced_devices.append(enhanced)
            
            logger.info(f"✅ Network discovery completed: {len(enhanced_devices)} devices found")
            return enhanced_devices
            
        except Exception as e:
            logger.error(f"❌ Error in network discovery scan: {e}")
            return []

    def _parse_ip_range(self, ip_range: str) -> List[str]:
        """Parse IP range string into list of IP addresses"""
        ip_list = []
        
        try:
            if '/' in ip_range:
                # CIDR notation (e.g., 192.168.1.0/24)
                network = ipaddress.IPv4Network(ip_range, strict=False)
                ip_list = [str(ip) for ip in network.hosts()]
                
            elif '-' in ip_range:
                # Range notation (e.g., 192.168.1.1-192.168.1.254)
                start_ip, end_ip = ip_range.split('-')
                start = ipaddress.IPv4Address(start_ip.strip())
                end = ipaddress.IPv4Address(end_ip.strip())
                
                current = start
                while current <= end:
                    ip_list.append(str(current))
                    current += 1
                    
            else:
                # Single IP
                ip_list = [ip_range]
                
        except Exception as e:
            logger.error(f"❌ Error parsing IP range {ip_range}: {e}")
            
        return ip_list

    def _scan_single_ip(self, ip: str, ports: List[int]) -> Optional[Dict]:
        """Scan a single IP address for open ports"""
        try:
            # First, check if IP is reachable with ping
            if not self._ping_ip(ip):
                return None
            
            open_ports = []
            device_info = {
                'ip_address': ip,
                'open_ports': [],
                'services': {},
                'source': 'network_scan',
                'reachable': True
            }
            
            # Scan each port
            for port in ports:
                if self._check_port(ip, port):
                    open_ports.append(port)
                    
                    # Try to identify service
                    service_info = self._identify_service(ip, port)
                    if service_info:
                        device_info['services'][port] = service_info
            
            if open_ports:
                device_info['open_ports'] = open_ports
                return device_info
            
            return None
            
        except Exception as e:
            logger.debug(f"❌ Error scanning {ip}: {e}")
            return None

    def _ping_ip(self, ip: str, timeout: int = 2) -> bool:
        """Ping an IP address to check if it's reachable"""
        try:
            if platform.system().lower() == 'windows':
                cmd = ['ping', '-n', '1', '-w', str(timeout * 1000), ip]
            else:
                cmd = ['ping', '-c', '1', '-W', str(timeout), ip]
            
            result = subprocess.run(cmd, capture_output=True, timeout=timeout + 2)
            return result.returncode == 0
            
        except:
            return False

    def _check_port(self, ip: str, port: int, timeout: int = 3) -> bool:
        """Check if a port is open on an IP address"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False

    def _identify_service(self, ip: str, port: int) -> Optional[Dict]:
        """Try to identify the service running on a port"""
        try:
            service_info = {'port': port, 'service': 'unknown'}
            
            # Common service identification
            if port == 104:
                service_info['service'] = 'DICOM'
                service_info['description'] = 'DICOM C-STORE/C-FIND'
            elif port == 11112:
                service_info['service'] = 'DICOM'
                service_info['description'] = 'DICOM Alternative Port'
            elif port == 8042:
                service_info['service'] = 'Orthanc'
                service_info['description'] = 'Orthanc PACS Server'
            elif port == 80:
                service_info['service'] = 'HTTP'
                service_info['description'] = 'Web Server'
            elif port == 443:
                service_info['service'] = 'HTTPS'
                service_info['description'] = 'Secure Web Server'
            elif port == 22:
                service_info['service'] = 'SSH'
                service_info['description'] = 'Secure Shell'
            elif port == 23:
                service_info['service'] = 'Telnet'
                service_info['description'] = 'Telnet'
            
            # Try to get banner/service info
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((ip, port))
                
                if port == 80:
                    # Try HTTP request
                    sock.send(b'GET / HTTP/1.0\r\n\r\n')
                    response = sock.recv(1024).decode('utf-8', errors='ignore')
                    if 'server:' in response.lower():
                        server_line = [line for line in response.split('\n') if 'server:' in line.lower()]
                        if server_line:
                            service_info['banner'] = server_line[0].strip()
                
                sock.close()
                
            except:
                pass
            
            return service_info
            
        except Exception as e:
            logger.debug(f"❌ Error identifying service on {ip}:{port}: {e}")
            return None

    def _enhance_device_info(self, device: Dict) -> Dict:
        """Enhance device information with additional details"""
        try:
            enhanced = device.copy()
            
            # Try to get hostname
            try:
                hostname = socket.gethostbyaddr(device['ip_address'])[0]
                enhanced['hostname'] = hostname
                
                # Try to guess device type from hostname
                hostname_lower = hostname.lower()
                if any(keyword in hostname_lower for keyword in ['ge', 'philips', 'siemens', 'mindray', 'samsung']):
                    enhanced['likely_medical_device'] = True
                    enhanced['suspected_manufacturer'] = self._guess_manufacturer_from_hostname(hostname_lower)
                
            except:
                enhanced['hostname'] = None
            
            # Analyze MAC address for manufacturer (if available)
            if 'mac_address' in device and device['mac_address']:
                manufacturer = self._get_manufacturer_from_mac(device['mac_address'])
                if manufacturer:
                    enhanced['mac_manufacturer'] = manufacturer
                    if any(med_vendor in manufacturer.lower() for med_vendor in 
                          ['ge', 'philips', 'siemens', 'mindray', 'samsung', 'hologic']):
                        enhanced['likely_medical_device'] = True
            
            # Analyze open ports for medical device indicators
            if 'open_ports' in device:
                medical_ports = [104, 11112, 2762, 2761]
                if any(port in device['open_ports'] for port in medical_ports):
                    enhanced['likely_medical_device'] = True
                    enhanced['dicom_capable'] = True
            
            # Add timestamp
            enhanced['discovered_at'] = datetime.now().isoformat()
            
            return enhanced
            
        except Exception as e:
            logger.debug(f"❌ Error enhancing device info: {e}")
            return device

    def _guess_manufacturer_from_hostname(self, hostname: str) -> str:
        """Guess manufacturer from hostname"""
        manufacturers = {
            'ge': 'GE Healthcare',
            'philips': 'Philips',
            'siemens': 'Siemens',
            'mindray': 'Mindray',
            'samsung': 'Samsung',
            'hologic': 'Hologic',
            'canon': 'Canon Medical',
            'toshiba': 'Canon Medical (Toshiba)',
            'hitachi': 'Hitachi'
        }
        
        for key, manufacturer in manufacturers.items():
            if key in hostname:
                return manufacturer
        
        return 'Unknown'

    def _get_manufacturer_from_mac(self, mac_address: str) -> Optional[str]:
        """Get manufacturer from MAC address OUI"""
        # This is a simplified version - in production, you'd use a full OUI database
        oui_map = {
            '00:50:C2': 'GE Healthcare',
            '00:0C:29': 'VMware (Virtual)',
            '08:00:27': 'VirtualBox (Virtual)',
            '00:1B:21': 'Intel',
            '00:E0:4C': 'Realtek',
            '00:90:27': 'Intel',
            # Add more OUIs as needed
        }
        
        if len(mac_address) >= 8:
            oui = mac_address[:8].upper()
            return oui_map.get(oui)
        
        return None

    def create_device_from_discovery(self, discovered_device: Dict, additional_info: Dict = None) -> Tuple[bool, str, Optional[MedicalDevice]]:
        """
        🎯 Create a medical device from discovered network device
        This makes adding devices EXTREMELY easy!
        """
        try:
            # Start with discovered device info
            device_data = {
                'ip_address': discovered_device['ip_address'],
                'port': 104,  # Default DICOM port
                'status': 'active'
            }
            
            # Add additional info if provided
            if additional_info:
                device_data.update(additional_info)
            
            # Try to auto-fill information based on discovery
            if discovered_device.get('hostname'):
                if not device_data.get('name'):
                    device_data['name'] = discovered_device['hostname']
            
            if discovered_device.get('suspected_manufacturer'):
                if not device_data.get('manufacturer'):
                    device_data['manufacturer'] = discovered_device['suspected_manufacturer']
            
            if discovered_device.get('mac_manufacturer'):
                if not device_data.get('manufacturer'):
                    device_data['manufacturer'] = discovered_device['mac_manufacturer']
            
            # Set defaults for required fields if not provided
            required_defaults = {
                'name': f"Device_{discovered_device['ip_address'].replace('.', '_')}",
                'modality_type': 'other',
                'manufacturer': discovered_device.get('mac_manufacturer', 'Unknown'),
                'model': 'Unknown',
                'ae_title': f"DEVICE_{discovered_device['ip_address'].replace('.', '_')}",
                'department': 'Radiology',
                'location': 'Main Hospital'
            }
            
            for field, default_value in required_defaults.items():
                if not device_data.get(field):
                    device_data[field] = default_value
            
            # Use preferred DICOM port if available
            if 'open_ports' in discovered_device:
                dicom_ports = [104, 11112, 2762, 2761]
                for port in dicom_ports:
                    if port in discovered_device['open_ports']:
                        device_data['port'] = port
                        break
            
            # Add discovery metadata
            device_data['notes'] = f"Auto-discovered from network scan. " \
                                 f"Discovery method: {discovered_device.get('source', 'unknown')}. " \
                                 f"Discovered at: {discovered_device.get('discovered_at', 'unknown')}"
            
            # Add the device
            return self.add_device(device_data)
            
        except Exception as e:
            logger.error(f"❌ Error creating device from discovery: {e}")
            return False, f"Error creating device: {str(e)}", None

    def get_network_discovery_suggestions(self) -> Dict:
        """Get network discovery suggestions for the admin"""
        try:
            # Get current network information
            suggestions = {
                'suggested_ranges': [],
                'current_network': None,
                'common_ranges': [
                    '192.168.1.0/24',
                    '192.168.0.0/24',
                    '10.0.0.0/24',
                    '172.16.0.0/24'
                ]
            }
            
            # Try to detect current network
            try:
                # Get local IP address
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.connect(("8.8.8.8", 80))
                local_ip = sock.getsockname()[0]
                sock.close()
                
                # Calculate network range
                ip_parts = local_ip.split('.')
                network_base = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
                suggestions['current_network'] = network_base
                suggestions['suggested_ranges'].insert(0, network_base)
                
            except:
                pass
            
            return suggestions
            
        except Exception as e:
            logger.error(f"❌ Error getting network discovery suggestions: {e}")
            return {}

# Global device manager instance
device_manager = DeviceManager()