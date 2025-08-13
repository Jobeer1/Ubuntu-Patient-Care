#!/usr/bin/env python3
"""
Fallback Device Management for when full module is not available
Provides basic device management functionality
"""

import json
import sqlite3
import logging
import socket
import subprocess
import platform
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

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
    status: str = "active"
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

class DeviceManagerFallback:
    """Fallback device manager with basic functionality"""
    
    def __init__(self, db_path: str = "medical_devices.db"):
        self.db_path = db_path
        self.init_database()
        
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
            
            conn.commit()
            conn.close()
            logger.info("✅ Device database initialized (fallback)")
            
        except Exception as e:
            logger.error(f"❌ Error initializing device database: {e}")
            
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
    
    def generate_device_id(self, name: str) -> str:
        """Generate unique device ID"""
        base_id = name.upper().replace(" ", "_").replace("-", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{base_id}_{timestamp}"
    
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
        
        try:
            import time
            start_time = time.time()
            
            # Simple ping test
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((device.ip_address, device.port))
            sock.close()
            
            response_time = int((time.time() - start_time) * 1000)
            
            if result == 0:
                return True, "Connection successful", response_time
            else:
                return False, f"Cannot connect to {device.ip_address}:{device.port}", response_time
                
        except Exception as e:
            return False, f"Connection test failed: {str(e)}", 0
    
    def get_equipment_presets(self, modality_type: str) -> Dict:
        """Get equipment presets for modality type"""
        presets = {
            "ultrasound": {
                "GE Healthcare": {"Vivid E95": {"port": 104, "ae_title": "GE_VIVID"}},
                "Philips": {"EPIQ Elite": {"port": 104, "ae_title": "PHILIPS_EPIQ"}},
                "Mindray": {"Resona 7": {"port": 104, "ae_title": "MINDRAY_R7"}}
            },
            "xray": {
                "Siemens": {"Ysio Max": {"port": 104, "ae_title": "SIEMENS_YSIO"}},
                "GE Healthcare": {"Definium 8000": {"port": 104, "ae_title": "GE_DEF8000"}}
            },
            "ct": {
                "Siemens": {"SOMATOM go.Top": {"port": 104, "ae_title": "SIEMENS_CT"}},
                "GE Healthcare": {"Revolution CT": {"port": 104, "ae_title": "GE_REV_CT"}}
            }
        }
        return presets.get(modality_type.lower(), {})
    
    def get_departments(self, language: str = "en") -> List[str]:
        """Get department list"""
        return [
            "Radiology", "Emergency", "Theatre", "ICU", "Cardiology",
            "Orthopedics", "Neurology", "Oncology", "Pediatrics"
        ]
    
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
            
            conn.close()
            
            return {
                'total_devices': total_devices,
                'status_counts': status_counts,
                'modality_counts': modality_counts,
                'department_counts': {},
                'recent_connectivity_tests': 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting device statistics: {e}")
            return {}
    
    def get_connectivity_history(self, device_id: str, limit: int = 50) -> List[Dict]:
        """Get connectivity test history for device"""
        return []  # Fallback returns empty history
    
    # Network discovery methods
    def scan_arp_table(self) -> List[Dict]:
        """Scan ARP table to find network devices with enhanced medical device detection"""
        try:
            devices = []
            
            if platform.system().lower() == 'windows':
                result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        match = re.match(r'\s*(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F-]{17})\s+(\w+)', line)
                        if match:
                            ip, mac, arp_type = match.groups()
                            
                            # Enhanced device information
                            device_info = {
                                'ip_address': ip,
                                'mac_address': mac.upper().replace('-', ':'),
                                'hostname': self._get_hostname(ip),
                                'arp_type': arp_type,
                                'source': 'arp_table',
                                'manufacturer': self._get_manufacturer_from_mac(mac),
                                'device_type': 'unknown',
                                'likely_medical_device': False,
                                'dicom_capable': False,
                                'connectivity_tests': {},
                                'confidence_score': 0
                            }
                            
                            # Perform enhanced medical device detection
                            self._enhance_device_detection(device_info)
                            
                            devices.append(device_info)
            
            # Sort by confidence score (most likely medical devices first)
            devices.sort(key=lambda x: x['confidence_score'], reverse=True)
            
            return devices
            
        except Exception as e:
            logger.error(f"❌ Error scanning ARP table: {e}")
            return []
    
    def network_discovery_scan(self, ip_range: str, ports: List[int] = None, max_threads: int = 50) -> List[Dict]:
        """Perform enhanced network discovery scan with medical device detection"""
        if ports is None:
            ports = [104, 11112, 8042, 80, 443, 22, 23, 443, 8080]
        
        try:
            devices = []
            
            # Parse IP range
            if '/' in ip_range:
                # CIDR notation
                import ipaddress
                network = ipaddress.IPv4Network(ip_range, strict=False)
                ips = [str(ip) for ip in network.hosts()]
            elif '-' in ip_range:
                # Range notation like 192.168.1.1-192.168.1.100
                start_ip, end_ip = ip_range.split('-')
                start_parts = start_ip.strip().split('.')
                end_parts = end_ip.strip().split('.')
                
                ips = []
                for i in range(int(start_parts[3]), int(end_parts[3]) + 1):
                    ips.append(f"{start_parts[0]}.{start_parts[1]}.{start_parts[2]}.{i}")
            else:
                # Single IP
                ips = [ip_range]
            
            # Scan each IP with enhanced detection
            for ip in ips[:50]:  # Limit to 50 IPs for performance
                device_info = self._enhanced_scan_single_ip(ip, ports)
                if device_info:
                    devices.append(device_info)
            
            # Sort by confidence score (most likely medical devices first)
            devices.sort(key=lambda x: x['confidence_score'], reverse=True)
            
            return devices
            
        except Exception as e:
            logger.error(f"❌ Error in network discovery scan: {e}")
            return []
    
    def _scan_single_ip(self, ip: str, ports: List[int]) -> Optional[Dict]:
        """Scan a single IP address"""
        try:
            open_ports = []
            
            for port in ports:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((ip, port))
                sock.close()
                
                if result == 0:
                    open_ports.append(port)
            
            if open_ports:
                return {
                    'ip_address': ip,
                    'hostname': f'device-{ip.split(".")[-1]}',
                    'open_ports': open_ports,
                    'likely_medical_device': 104 in open_ports or 11112 in open_ports,
                    'dicom_capable': 104 in open_ports,
                    'source': 'network_scan'
                }
            
            return None
            
        except Exception as e:
            return None
    
    def _get_hostname(self, ip: str) -> str:
        """Get hostname for IP address"""
        try:
            import socket
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except:
            return f'device-{ip.split(".")[-1]}'
    
    def _get_manufacturer_from_mac(self, mac: str) -> str:
        """Get manufacturer from MAC address OUI"""
        mac_oui_database = {
            '00:50:C2': 'IEEE Registration Authority',
            '00:0C:29': 'VMware',
            '08:00:20': 'Sun Microsystems',
            '00:A0:C9': 'Intel',
            '00:1B:21': 'Intel',
            '00:15:5D': 'Microsoft',
            '00:03:FF': 'Microsoft',
            '00:50:56': 'VMware',
            '00:0F:4B': 'Inventec',
            '00:1C:42': 'Parallels',
            # Medical device manufacturers
            '00:50:C2:7A': 'GE Healthcare',
            '00:A0:C9:14': 'Intel (Medical)',
            '00:1B:21:3C': 'Philips Healthcare',
            '00:0C:29:6B': 'Siemens Healthcare',
            '00:15:5D:FF': 'Mindray',
            '00:03:FF:12': 'Hologic',
            '00:50:56:C0': 'Canon Medical',
            '00:0F:4B:90': 'Fujifilm Medical',
        }
        
        mac_prefix = mac[:8].upper()
        return mac_oui_database.get(mac_prefix, 'Unknown')
    
    def _enhance_device_detection(self, device_info: Dict):
        """Enhance device detection with medical device identification"""
        ip = device_info['ip_address']
        mac = device_info['mac_address']
        hostname = device_info['hostname']
        manufacturer = device_info['manufacturer']
        
        confidence_score = 0
        
        # Test DICOM port (104)
        dicom_test = self._test_port(ip, 104, timeout=2)
        device_info['connectivity_tests']['dicom_104'] = dicom_test
        if dicom_test['success']:
            confidence_score += 50
            device_info['dicom_capable'] = True
            device_info['device_type'] = 'dicom_device'
        
        # Test common medical device ports
        medical_ports = {
            11112: 'PACS_Server',
            8042: 'Orthanc_Server',
            80: 'Web_Interface',
            443: 'HTTPS_Interface',
            22: 'SSH',
            23: 'Telnet'
        }
        
        for port, service in medical_ports.items():
            test_result = self._test_port(ip, port, timeout=1)
            device_info['connectivity_tests'][f'port_{port}'] = test_result
            if test_result['success']:
                if port in [11112, 8042]:  # Medical-specific ports
                    confidence_score += 30
                elif port in [80, 443]:  # Web interfaces
                    confidence_score += 10
        
        # Check hostname for medical device indicators
        medical_keywords = [
            'dicom', 'pacs', 'xray', 'ct', 'mri', 'ultrasound', 'mammo',
            'ge-', 'philips', 'siemens', 'mindray', 'hologic', 'canon',
            'medical', 'radiology', 'imaging', 'scanner'
        ]
        
        hostname_lower = hostname.lower()
        for keyword in medical_keywords:
            if keyword in hostname_lower:
                confidence_score += 20
                device_info['device_type'] = 'medical_device'
                break
        
        # Check manufacturer
        medical_manufacturers = [
            'GE Healthcare', 'Philips Healthcare', 'Siemens Healthcare',
            'Mindray', 'Hologic', 'Canon Medical', 'Fujifilm Medical'
        ]
        
        if manufacturer in medical_manufacturers:
            confidence_score += 40
            device_info['device_type'] = 'medical_device'
        
        # Ping test
        ping_test = self._test_ping(ip)
        device_info['connectivity_tests']['ping'] = ping_test
        if ping_test['success']:
            confidence_score += 5
        
        device_info['confidence_score'] = min(confidence_score, 100)
        device_info['likely_medical_device'] = confidence_score >= 30
    
    def _enhanced_scan_single_ip(self, ip: str, ports: List[int]) -> Optional[Dict]:
        """Enhanced scan of a single IP address with medical device detection"""
        try:
            device_info = {
                'ip_address': ip,
                'hostname': self._get_hostname(ip),
                'source': 'network_scan',
                'manufacturer': 'Unknown',
                'device_type': 'unknown',
                'likely_medical_device': False,
                'dicom_capable': False,
                'connectivity_tests': {},
                'confidence_score': 0,
                'open_ports': []
            }
            
            # Test all ports
            for port in ports:
                test_result = self._test_port(ip, port, timeout=2)
                if test_result['success']:
                    device_info['open_ports'].append(port)
                    device_info['connectivity_tests'][f'port_{port}'] = test_result
            
            # Only return devices that respond to at least one port
            if device_info['open_ports']:
                # Enhance detection
                self._enhance_network_device_detection(device_info)
                return device_info
            
            return None
            
        except Exception as e:
            return None
    
    def _enhance_network_device_detection(self, device_info: Dict):
        """Enhance network device detection"""
        open_ports = device_info['open_ports']
        hostname = device_info['hostname']
        
        confidence_score = 0
        
        # DICOM port detection
        if 104 in open_ports:
            confidence_score += 50
            device_info['dicom_capable'] = True
            device_info['device_type'] = 'dicom_device'
        
        # Medical-specific ports
        if 11112 in open_ports:  # PACS server
            confidence_score += 40
            device_info['device_type'] = 'pacs_server'
        
        if 8042 in open_ports:  # Orthanc
            confidence_score += 35
            device_info['device_type'] = 'orthanc_server'
        
        # Web interface ports
        if 80 in open_ports or 443 in open_ports:
            confidence_score += 10
        
        # Check hostname for medical indicators
        medical_keywords = [
            'dicom', 'pacs', 'xray', 'ct', 'mri', 'ultrasound', 'mammo',
            'ge-', 'philips', 'siemens', 'mindray', 'hologic', 'canon',
            'medical', 'radiology', 'imaging', 'scanner'
        ]
        
        hostname_lower = hostname.lower()
        for keyword in medical_keywords:
            if keyword in hostname_lower:
                confidence_score += 25
                device_info['device_type'] = 'medical_device'
                break
        
        device_info['confidence_score'] = min(confidence_score, 100)
        device_info['likely_medical_device'] = confidence_score >= 25
    
    def _test_port(self, ip: str, port: int, timeout: int = 3) -> Dict:
        """Test connectivity to a specific port"""
        try:
            import time
            start_time = time.time()
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            
            response_time = int((time.time() - start_time) * 1000)
            
            return {
                'success': result == 0,
                'response_time_ms': response_time,
                'port': port,
                'status': 'open' if result == 0 else 'closed',
                'error': None if result == 0 else f'Connection failed (code: {result})'
            }
            
        except Exception as e:
            return {
                'success': False,
                'response_time_ms': 0,
                'port': port,
                'status': 'error',
                'error': str(e)
            }
    
    def _test_ping(self, ip: str) -> Dict:
        """Test basic ping connectivity"""
        try:
            import time
            start_time = time.time()
            
            # Try to connect to port 80 as a basic connectivity test
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, 80))
            sock.close()
            
            response_time = int((time.time() - start_time) * 1000)
            
            return {
                'success': result == 0,
                'response_time_ms': response_time,
                'status': 'reachable' if result == 0 else 'unreachable',
                'error': None if result == 0 else 'Host unreachable'
            }
            
        except Exception as e:
            return {
                'success': False,
                'response_time_ms': 0,
                'status': 'error',
                'error': str(e)
            }
    
    def get_network_discovery_suggestions(self) -> Dict:
        """Get network discovery suggestions"""
        return {
            'common_ip_ranges': [
                '192.168.1.0/24',
                '192.168.0.0/24',
                '10.0.0.0/24',
                '172.16.0.0/24'
            ],
            'common_ports': [104, 11112, 8042, 80, 443],
            'tips': [
                'Start with your local network range',
                'Port 104 is the standard DICOM port',
                'Port 11112 is used by some PACS systems',
                'Port 8042 is used by Orthanc servers'
            ]
        }
    
    def test_dicom_connectivity(self, ip: str, port: int = 104, ae_title: str = "TEST_AE") -> Dict:
        """Test DICOM connectivity with C-ECHO"""
        try:
            # First test basic port connectivity
            port_test = self._test_port(ip, port, timeout=5)
            
            if not port_test['success']:
                return {
                    'success': False,
                    'test_type': 'dicom_echo',
                    'error': f'Cannot connect to port {port}',
                    'port_test': port_test,
                    'dicom_test': None
                }
            
            # For now, return successful port test as DICOM test
            # In a full implementation, this would use pynetdicom for C-ECHO
            return {
                'success': True,
                'test_type': 'dicom_echo',
                'message': f'DICOM port {port} is accessible',
                'port_test': port_test,
                'dicom_test': {
                    'ae_title': ae_title,
                    'status': 'port_accessible',
                    'note': 'Full DICOM C-ECHO requires pynetdicom library'
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'test_type': 'dicom_echo',
                'error': str(e),
                'port_test': None,
                'dicom_test': None
            }
    
    def create_device_from_discovery(self, discovered_device: Dict, additional_info: Dict) -> Tuple[bool, str, Optional[MedicalDevice]]:
        """Create device from discovered network device"""
        try:
            # Use discovered device information to pre-fill data
            manufacturer = discovered_device.get('manufacturer', 'Unknown')
            if manufacturer == 'Unknown' and discovered_device.get('hostname'):
                # Try to guess manufacturer from hostname
                hostname_lower = discovered_device['hostname'].lower()
                if 'ge' in hostname_lower:
                    manufacturer = 'GE Healthcare'
                elif 'philips' in hostname_lower:
                    manufacturer = 'Philips Healthcare'
                elif 'siemens' in hostname_lower:
                    manufacturer = 'Siemens Healthcare'
                elif 'mindray' in hostname_lower:
                    manufacturer = 'Mindray'
            
            # Suggest modality type based on device type
            suggested_modality = 'other'
            if discovered_device.get('device_type') == 'dicom_device':
                suggested_modality = 'ultrasound'  # Default for DICOM devices
            
            device_data = {
                'name': additional_info.get('name', f"{manufacturer}_{discovered_device['ip_address'].replace('.', '_')}"),
                'modality_type': additional_info.get('modality_type', suggested_modality),
                'manufacturer': additional_info.get('manufacturer', manufacturer),
                'model': additional_info.get('model', discovered_device.get('hostname', 'Unknown')),
                'ae_title': additional_info.get('ae_title', f"DEV_{discovered_device['ip_address'].replace('.', '_')}"),
                'ip_address': discovered_device['ip_address'],
                'port': additional_info.get('port', 104 if discovered_device.get('dicom_capable') else 80),
                'department': additional_info.get('department', 'Radiology'),
                'location': additional_info.get('location', 'Main Hospital'),
                'notes': f"Auto-discovered from {discovered_device.get('source', 'network scan')}. Confidence: {discovered_device.get('confidence_score', 0)}%"
            }
            
            return self.add_device(device_data)
            
        except Exception as e:
            logger.error(f"❌ Error creating device from discovery: {e}")
            return False, f"Error creating device: {str(e)}", None

# Create global instance
device_manager = DeviceManagerFallback()