#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - NAS Discovery System

Advanced NAS (Network Attached Storage) discovery for South African healthcare facilities.
Automatically discovers and configures NAS devices for DICOM storage.

Features:
- SMB/CIFS share discovery
- NFS share discovery  
- FTP server discovery
- Network drive mapping
- Automatic credential testing
- South African healthcare context
"""

import json
import sqlite3
import logging
import socket
import subprocess
import platform
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import re
import os

logger = logging.getLogger(__name__)

@dataclass
class NASDevice:
    """Network Attached Storage device"""
    id: str
    name: str
    ip_address: str
    hostname: str
    nas_type: str  # 'smb', 'nfs', 'ftp', 'sftp', 'webdav'
    manufacturer: str
    model: str
    shares: List[Dict]  # List of available shares
    ports: List[int]  # Open ports
    services: List[str]  # Detected services
    mac_address: Optional[str] = None
    via_arp: bool = False
    capacity_gb: Optional[int] = None
    free_space_gb: Optional[int] = None
    status: str = "discovered"  # discovered, configured, error
    credentials_tested: bool = False
    last_seen: str = ""
    created_at: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'NASDevice':
        """Create from dictionary"""
        return cls(**data)

class NASDiscoveryManager:
    """
    🏥 World-class NAS discovery for South African healthcare
    """
    
    def __init__(self, db_path: str = "nas_discovery.db"):
        self.db_path = db_path
        self.init_database()
        self.load_sa_nas_presets()
    
    def init_database(self):
        """Initialize NAS discovery database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS discovered_nas (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    hostname TEXT,
                    nas_type TEXT NOT NULL,
                    manufacturer TEXT,
                    model TEXT,
                    shares TEXT, -- JSON array of shares
                    ports TEXT, -- JSON array of ports
                    services TEXT, -- JSON array of services
                    capacity_gb INTEGER,
                    free_space_gb INTEGER,
                    status TEXT DEFAULT 'discovered',
                    credentials_tested BOOLEAN DEFAULT 0,
                    last_seen TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nas_credentials (
                    id TEXT PRIMARY KEY,
                    nas_id TEXT NOT NULL,
                    username TEXT,
                    password TEXT, -- Encrypted in production
                    domain TEXT,
                    share_path TEXT,
                    mount_point TEXT,
                    test_result TEXT,
                    tested_at TEXT,
                    FOREIGN KEY (nas_id) REFERENCES discovered_nas (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nas_scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_type TEXT NOT NULL,
                    ip_range TEXT,
                    devices_found INTEGER,
                    scan_duration_seconds REAL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ NAS discovery database initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing NAS discovery database: {e}")
            raise
    
    def load_sa_nas_presets(self):
        """Load South African NAS device presets"""
        self.sa_nas_presets = {
            "synology": {
                "ports": [5000, 5001, 445, 139, 22, 21],
                "services": ["DSM", "SMB", "SSH", "FTP"],
                "default_shares": ["homes", "photo", "video", "music", "documents"],
                "web_interface_ports": [5000, 5001],
                "identification": ["synology", "dsm", "diskstation"]
            },
            "qnap": {
                "ports": [8080, 443, 445, 139, 22, 21],
                "services": ["QTS", "SMB", "SSH", "FTP"],
                "default_shares": ["homes", "multimedia", "backup"],
                "web_interface_ports": [8080, 443],
                "identification": ["qnap", "qts", "turbonas"]
            },
            "netgear": {
                "ports": [80, 443, 445, 139, 21],
                "services": ["ReadyNAS", "SMB", "FTP"],
                "default_shares": ["backup", "media"],
                "web_interface_ports": [80, 443],
                "identification": ["netgear", "readynas"]
            },
            "buffalo": {
                "ports": [80, 445, 139, 21],
                "services": ["TeraStation", "SMB", "FTP"],
                "default_shares": ["share", "backup"],
                "web_interface_ports": [80],
                "identification": ["buffalo", "terastation", "linkstation"]
            },
            "western_digital": {
                "ports": [80, 445, 139, 22, 21],
                "services": ["MyCloud", "SMB", "SSH", "FTP"],
                "default_shares": ["Public", "TimeMachineBackup"],
                "web_interface_ports": [80],
                "identification": ["mycloud", "wdmycloud"]
            },
            "windows_server": {
                "ports": [445, 139, 135, 3389],
                "services": ["SMB", "RPC", "RDP"],
                "default_shares": ["C$", "ADMIN$", "IPC$"],
                "web_interface_ports": [],
                "identification": ["windows", "microsoft"]
            },
            "linux_samba": {
                "ports": [445, 139, 22],
                "services": ["SMB", "SSH"],
                "default_shares": ["public", "homes"],
                "web_interface_ports": [],
                "identification": ["samba", "linux"]
            }
        }
        
        # Common South African healthcare NAS configurations
        self.sa_healthcare_nas_configs = {
            "radiology_archive": {
                "typical_shares": ["DICOM", "Archive", "Backup", "Studies"],
                "capacity_range": "2TB-50TB",
                "raid_level": "RAID 5/6"
            },
            "pacs_storage": {
                "typical_shares": ["PACS", "Studies", "Reports", "Temp"],
                "capacity_range": "5TB-100TB",
                "raid_level": "RAID 6/10"
            },
            "backup_nas": {
                "typical_shares": ["Backup", "Archive", "DR"],
                "capacity_range": "10TB-200TB",
                "raid_level": "RAID 6"
            }
        }
    
    def discover_nas_devices(self, ip_range: str, scan_type: str = "comprehensive", 
                           max_threads: int = 50, max_hosts: Optional[int] = None) -> List[NASDevice]:
        """
        🔍 Discover NAS devices on the network
        
        Args:
            ip_range: IP range to scan (CIDR or range format)
            scan_type: 'quick', 'comprehensive', 'deep'
            max_threads: Maximum concurrent threads
        """
        start_time = time.time()
        logger.info(f"🔍 Starting NAS discovery scan on {ip_range}")
        
        try:
            # Parse IP range
            ips = self._parse_ip_range(ip_range)
            
            # Define ports to scan based on scan type
            if scan_type == "quick":
                ports = [445, 139, 22, 21, 80]  # Basic NAS ports
            elif scan_type == "comprehensive":
                ports = [445, 139, 22, 21, 80, 443, 5000, 5001, 8080, 2049, 111]  # Extended NAS ports
            else:  # deep
                ports = list(range(21, 23)) + list(range(80, 81)) + list(range(135, 140)) + \
                       list(range(443, 446)) + list(range(2049, 2051)) + \
                       list(range(5000, 5002)) + list(range(8080, 8081))
            
            discovered_devices = []

            # Respect max_hosts cap to avoid very large scans
            cap = max_hosts if max_hosts is not None else 100
            cap = max(1, min(cap, 1024))
            target_ips = ips[:cap]

            # Pre-scan ARP table to find devices that may be reachable even without ICMP
            arp_map = self._scan_arp_table()

            # Scan IPs concurrently
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                future_to_ip = {
                    executor.submit(self._scan_ip_for_nas, ip, ports): ip 
                    for ip in target_ips
                }

                for future in concurrent.futures.as_completed(future_to_ip):
                    ip = future_to_ip[future]
                    try:
                        nas_device = future.result()
                        if nas_device:
                            discovered_devices.append(nas_device)
                            logger.info(f"✅ Found NAS device: {nas_device.name} at {nas_device.ip_address}")
                        else:
                            # If no ports detected but ARP has this IP, include as ARP-known device
                            if ip in arp_map:
                                mac = arp_map[ip]
                                device_id = f"arp_{ip.replace('.', '_')}_{int(time.time())}"
                                arp_device = NASDevice(
                                    id=device_id,
                                    name=f"ARP Device {ip}",
                                    ip_address=ip,
                                    hostname=self._get_hostname(ip),
                                    nas_type='unknown',
                                    manufacturer='Unknown',
                                    model='Unknown',
                                    shares=[],
                                    ports=[],
                                    services=[],
                                    mac_address=mac,
                                    via_arp=True,
                                    last_seen=datetime.now().isoformat(),
                                    created_at=datetime.now().isoformat(),
                                    status='discovered'
                                )
                                discovered_devices.append(arp_device)
                                logger.info(f"⚠️ ARP-only device found: {ip} ({mac})")
                    except Exception as e:
                        logger.debug(f"Error scanning {ip}: {e}")
            
            # Save scan history
            scan_duration = time.time() - start_time
            self._save_scan_history(scan_type, ip_range, len(discovered_devices), scan_duration)
            
            # Save discovered devices
            for device in discovered_devices:
                self._save_discovered_nas(device)
            
            logger.info(f"✅ NAS discovery completed. Found {len(discovered_devices)} devices in {scan_duration:.1f}s")
            return discovered_devices
            
        except Exception as e:
            logger.error(f"❌ Error in NAS discovery: {e}")
            return []
    
    def _parse_ip_range(self, ip_range: str) -> List[str]:
        """Parse IP range into list of IPs"""
        ips: List[str] = []

        try:
            if '/' in ip_range:
                # CIDR notation
                network = ipaddress.IPv4Network(ip_range, strict=False)
                ips = [str(ip) for ip in network.hosts()]
            elif '-' in ip_range:
                # Range notation (simple single-octet range supported)
                start_ip, end_ip = ip_range.split('-')
                start_parts = start_ip.strip().split('.')
                end_parts = end_ip.strip().split('.')

                # if same first three octets, iterate last octet
                if start_parts[:3] == end_parts[:3]:
                    for i in range(int(start_parts[3]), int(end_parts[3]) + 1):
                        ips.append(f"{start_parts[0]}.{start_parts[1]}.{start_parts[2]}.{i}")
                else:
                    # Fallback: expand full networks using ipaddress (less efficient but safe)
                    start = ipaddress.IPv4Address(start_ip.strip())
                    end = ipaddress.IPv4Address(end_ip.strip())
                    cur = start
                    while cur <= end:
                        ips.append(str(cur))
                        cur = ipaddress.IPv4Address(int(cur) + 1)
            else:
                # Single IP
                ips = [ip_range.strip()]

        except Exception as e:
            logger.error(f"Error parsing IP range {ip_range}: {e}")

        return ips

    def _scan_arp_table(self) -> Dict[str, str]:
        """Return mapping ip -> mac from local ARP table."""
        arp_map: Dict[str, str] = {}
        try:
            system = platform.system().lower()
            if system == 'windows':
                res = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=3)
                out = res.stdout
                for line in out.splitlines():
                    m = re.match(r'\s*(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F-]{17})\s+\w+', line)
                    if m:
                        ip, mac = m.groups()
                        arp_map[ip] = mac.replace('-', ':').upper()
            else:
                # try /proc/net/arp first
                if os.path.exists('/proc/net/arp'):
                    with open('/proc/net/arp', 'r') as f:
                        lines = f.readlines()[1:]
                        for line in lines:
                            parts = line.split()
                            if len(parts) >= 4:
                                ip = parts[0]
                                mac = parts[3]
                                if mac != '00:00:00:00:00:00':
                                    arp_map[ip] = mac.upper()
                else:
                    # fallback to arp -a
                    res = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=3)
                    out = res.stdout
                    for line in out.splitlines():
                        m = re.search(r'(\d+\.\d+\.\d+\.\d+).*?([0-9a-fA-F:]{17})', line)
                        if m:
                            ip, mac = m.groups()
                            arp_map[ip] = mac.upper()
        except Exception as e:
            logger.debug(f"ARP scan failed: {e}")

        return arp_map
    
    def _scan_ip_for_nas(self, ip: str, ports: List[int]) -> Optional[NASDevice]:
        """Scan a single IP for NAS services"""
        try:
            open_ports = []
            services = []
            
            # Port scan
            for port in ports:
                if self._is_port_open(ip, port, timeout=2):
                    open_ports.append(port)
                    service = self._identify_service(ip, port)
                    if service:
                        services.append(service)
            
            if not open_ports:
                return None
            
            # Check if this looks like a NAS device
            if not self._is_likely_nas(open_ports, services):
                return None
            
            # Get hostname
            hostname = self._get_hostname(ip)
            
            # Identify NAS type and manufacturer
            nas_type, manufacturer, model = self._identify_nas_device(ip, open_ports, services, hostname)
            
            # Discover shares
            shares = self._discover_shares(ip, nas_type, open_ports)
            
            # Create NAS device object
            device_id = f"nas_{ip.replace('.', '_')}_{int(time.time())}"
            nas_device = NASDevice(
                id=device_id,
                name=f"{manufacturer} {model}" if manufacturer and model else f"NAS Device {ip}",
                ip_address=ip,
                hostname=hostname,
                nas_type=nas_type,
                manufacturer=manufacturer,
                model=model,
                shares=shares,
                ports=open_ports,
                services=services,
                last_seen=datetime.now().isoformat(),
                created_at=datetime.now().isoformat()
            )
            
            return nas_device
            
        except Exception as e:
            logger.debug(f"Error scanning {ip}: {e}")
            return None
    
    def _is_port_open(self, ip: str, port: int, timeout: int = 2) -> bool:
        """Check if a port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def _identify_service(self, ip: str, port: int) -> Optional[str]:
        """Identify service running on port"""
        service_map = {
            21: "FTP",
            22: "SSH",
            23: "Telnet",
            80: "HTTP",
            135: "RPC",
            139: "NetBIOS",
            443: "HTTPS",
            445: "SMB",
            2049: "NFS",
            5000: "UPnP/Synology",
            5001: "Synology HTTPS",
            8080: "HTTP Alt/QNAP"
        }
        
        service = service_map.get(port)
        
        # Try to get more specific service info for web ports
        if port in [80, 443, 5000, 5001, 8080]:
            try:
                protocol = "https" if port in [443, 5001] else "http"
                try:
                    import requests
                except Exception:
                    requests = None

                if requests:
                    response = requests.get(f"{protocol}://{ip}:{port}", timeout=3, verify=False)
                    # Check for NAS-specific headers or content
                    content = response.text.lower()
                    headers = str(response.headers).lower()

                    if "synology" in content or "dsm" in content:
                        return "Synology DSM"
                    elif "qnap" in content or "qts" in content:
                        return "QNAP QTS"
                    elif "netgear" in content or "readynas" in content:
                        return "Netgear ReadyNAS"
                    elif "buffalo" in content:
                        return "Buffalo NAS"
                    elif "mycloud" in content:
                        return "WD MyCloud"
            except Exception:
                # Network or parse error while probing web port; ignore and continue
                pass
        
        return service
    
    def _is_likely_nas(self, open_ports: List[int], services: List[str]) -> bool:
        """Determine if device is likely a NAS"""
        # Check for NAS-specific port combinations
        nas_indicators = [
            445 in open_ports,  # SMB
            2049 in open_ports,  # NFS
            (21 in open_ports and 22 in open_ports),  # FTP + SSH
            (80 in open_ports and 445 in open_ports),  # Web + SMB
            5000 in open_ports,  # Synology
            8080 in open_ports,  # QNAP
        ]
        
        # Check for NAS-specific services
        nas_services = ["Synology DSM", "QNAP QTS", "Netgear ReadyNAS", "Buffalo NAS", "WD MyCloud"]
        has_nas_service = any(service in services for service in nas_services)
        
        return any(nas_indicators) or has_nas_service
    
    def _get_hostname(self, ip: str) -> str:
        """Get hostname for IP address"""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except:
            return f"device-{ip.split('.')[-1]}"
    
    def _identify_nas_device(self, ip: str, open_ports: List[int], services: List[str], hostname: str) -> Tuple[str, str, str]:
        """Identify NAS device type, manufacturer, and model"""
        hostname_lower = hostname.lower()
        services_str = " ".join(services).lower()
        
        # Check each preset
        for nas_type, preset in self.sa_nas_presets.items():
            # Check identification keywords
            if any(keyword in hostname_lower or keyword in services_str 
                   for keyword in preset["identification"]):
                
                # Extract manufacturer and model from preset
                if nas_type == "synology":
                    return "smb", "Synology", "DiskStation"
                elif nas_type == "qnap":
                    return "smb", "QNAP", "TurboNAS"
                elif nas_type == "netgear":
                    return "smb", "Netgear", "ReadyNAS"
                elif nas_type == "buffalo":
                    return "smb", "Buffalo", "TeraStation"
                elif nas_type == "western_digital":
                    return "smb", "Western Digital", "MyCloud"
                elif nas_type == "windows_server":
                    return "smb", "Microsoft", "Windows Server"
                elif nas_type == "linux_samba":
                    return "smb", "Linux", "Samba Server"
        
        # Default identification based on ports
        if 445 in open_ports or 139 in open_ports:
            return "smb", "Unknown", "SMB Server"
        elif 2049 in open_ports:
            return "nfs", "Unknown", "NFS Server"
        elif 21 in open_ports:
            return "ftp", "Unknown", "FTP Server"
        else:
            return "unknown", "Unknown", "Network Storage"
    
    def _discover_shares(self, ip: str, nas_type: str, open_ports: List[int]) -> List[Dict]:
        """Discover available shares on NAS device"""
        shares = []
        
        try:
            if nas_type == "smb" and (445 in open_ports or 139 in open_ports):
                shares = self._discover_smb_shares(ip)
            elif nas_type == "nfs" and 2049 in open_ports:
                shares = self._discover_nfs_shares(ip)
            elif nas_type == "ftp" and 21 in open_ports:
                shares = self._discover_ftp_shares(ip)
                
        except Exception as e:
            logger.debug(f"Error discovering shares on {ip}: {e}")
        
        return shares
    
    def _discover_smb_shares(self, ip: str) -> List[Dict]:
        """Discover SMB shares"""
        shares = []
        
        try:
            if platform.system().lower() == 'windows':
                # Use net view command on Windows
                result = subprocess.run(['net', 'view', f'\\\\{ip}'], 
                                      capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'Disk' in line:
                            parts = line.split()
                            if parts:
                                share_name = parts[0]
                                shares.append({
                                    'name': share_name,
                                    'type': 'SMB',
                                    'path': f'\\\\{ip}\\{share_name}',
                                    'description': 'SMB Share'
                                })
            else:
                # Use smbclient on Linux/Mac (if available)
                try:
                    result = subprocess.run(['smbclient', '-L', ip, '-N'], 
                                          capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        for line in lines:
                            if 'Disk' in line:
                                parts = line.split()
                                if len(parts) >= 2:
                                    share_name = parts[0]
                                    shares.append({
                                        'name': share_name,
                                        'type': 'SMB',
                                        'path': f'//{ip}/{share_name}',
                                        'description': 'SMB Share'
                                    })
                except FileNotFoundError:
                    # smbclient not available
                    pass
                    
        except Exception as e:
            logger.debug(f"Error discovering SMB shares on {ip}: {e}")
        
        return shares
    
    def _discover_nfs_shares(self, ip: str) -> List[Dict]:
        """Discover NFS shares"""
        shares = []
        
        try:
            # Use showmount command (if available)
            result = subprocess.run(['showmount', '-e', ip], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')[1:]  # Skip header
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if parts:
                            export_path = parts[0]
                            shares.append({
                                'name': os.path.basename(export_path),
                                'type': 'NFS',
                                'path': f'{ip}:{export_path}',
                                'description': 'NFS Export'
                            })
                            
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # showmount not available or timeout
            pass
        except Exception as e:
            logger.debug(f"Error discovering NFS shares on {ip}: {e}")
        
        return shares
    
    def _discover_ftp_shares(self, ip: str) -> List[Dict]:
        """Discover FTP directories"""
        shares = []
        
        try:
            import ftplib
            
            ftp = ftplib.FTP()
            ftp.connect(ip, timeout=5)
            
            # Try anonymous login
            try:
                ftp.login()
                
                # List directories
                directories = []
                ftp.retrlines('LIST', directories.append)
                
                for item in directories:
                    if item.startswith('d'):  # Directory
                        parts = item.split()
                        if len(parts) >= 9:
                            dir_name = parts[-1]
                            shares.append({
                                'name': dir_name,
                                'type': 'FTP',
                                'path': f'ftp://{ip}/{dir_name}',
                                'description': 'FTP Directory'
                            })
                
                ftp.quit()
                
            except ftplib.error_perm:
                # Anonymous login failed
                shares.append({
                    'name': 'root',
                    'type': 'FTP',
                    'path': f'ftp://{ip}/',
                    'description': 'FTP Server (Auth Required)'
                })
                
        except Exception as e:
            logger.debug(f"Error discovering FTP shares on {ip}: {e}")
        
        return shares
    
    def _save_discovered_nas(self, nas_device: NASDevice):
        """Save discovered NAS device to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO discovered_nas (
                    id, name, ip_address, hostname, nas_type, manufacturer, model,
                    shares, ports, services, last_seen, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                nas_device.id, nas_device.name, nas_device.ip_address, nas_device.hostname,
                nas_device.nas_type, nas_device.manufacturer, nas_device.model,
                json.dumps(nas_device.shares), json.dumps(nas_device.ports),
                json.dumps(nas_device.services), nas_device.last_seen, nas_device.created_at
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving NAS device: {e}")
    
    def _save_scan_history(self, scan_type: str, ip_range: str, devices_found: int, duration: float):
        """Save scan history to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO nas_scan_history (
                    scan_type, ip_range, devices_found, scan_duration_seconds,
                    started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                scan_type, ip_range, devices_found, duration,
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving scan history: {e}")
    
    def get_discovered_nas_devices(self) -> List[NASDevice]:
        """Get all discovered NAS devices"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM discovered_nas ORDER BY last_seen DESC')
            rows = cursor.fetchall()
            
            conn.close()
            
            devices = []
            if rows:
                columns = [desc[0] for desc in cursor.description]
                for row in rows:
                    device_data = dict(zip(columns, row))
                    # Parse JSON fields
                    device_data['shares'] = json.loads(device_data['shares']) if device_data['shares'] else []
                    device_data['ports'] = json.loads(device_data['ports']) if device_data['ports'] else []
                    device_data['services'] = json.loads(device_data['services']) if device_data['services'] else []
                    
                    devices.append(NASDevice.from_dict(device_data))
            
            return devices
            
        except Exception as e:
            logger.error(f"Error getting discovered NAS devices: {e}")
            return []
    
    def test_nas_credentials(self, nas_id: str, username: str, password: str, 
                           domain: str = "", share_path: str = "") -> Tuple[bool, str]:
        """Test NAS credentials"""
        try:
            # Get NAS device
            nas_device = self.get_nas_device_by_id(nas_id)
            if not nas_device:
                return False, "NAS device not found"
            
            # Test based on NAS type
            if nas_device.nas_type == "smb":
                return self._test_smb_credentials(nas_device.ip_address, username, password, domain, share_path)
            elif nas_device.nas_type == "ftp":
                return self._test_ftp_credentials(nas_device.ip_address, username, password)
            else:
                return False, f"Credential testing not supported for {nas_device.nas_type}"
                
        except Exception as e:
            return False, f"Error testing credentials: {str(e)}"
    
    def _test_smb_credentials(self, ip: str, username: str, password: str, 
                            domain: str = "", share_path: str = "") -> Tuple[bool, str]:
        """Test SMB credentials"""
        try:
            # Try to connect using different methods based on OS
            if platform.system().lower() == 'windows':
                # Use net use command on Windows
                share = share_path or f"\\\\{ip}\\IPC$"
                cmd = ['net', 'use', share, password, f'/user:{domain}\\{username}' if domain else f'/user:{username}']
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    # Clean up connection
                    subprocess.run(['net', 'use', share, '/delete'], capture_output=True)
                    return True, "SMB credentials valid"
                else:
                    return False, f"SMB authentication failed: {result.stderr}"
            else:
                # Use smbclient on Linux/Mac
                try:
                    cmd = ['smbclient', f'//{ip}/IPC$', password, '-U', f'{domain}\\{username}' if domain else username, '-c', 'quit']
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        return True, "SMB credentials valid"
                    else:
                        return False, f"SMB authentication failed: {result.stderr}"
                except FileNotFoundError:
                    return False, "smbclient not available"
                    
        except Exception as e:
            return False, f"Error testing SMB credentials: {str(e)}"
    
    def _test_ftp_credentials(self, ip: str, username: str, password: str) -> Tuple[bool, str]:
        """Test FTP credentials"""
        try:
            import ftplib
            
            ftp = ftplib.FTP()
            ftp.connect(ip, timeout=5)
            ftp.login(username, password)
            ftp.quit()
            
            return True, "FTP credentials valid"
            
        except ftplib.error_perm as e:
            return False, f"FTP authentication failed: {str(e)}"
        except Exception as e:
            return False, f"Error testing FTP credentials: {str(e)}"
    
    def get_nas_device_by_id(self, nas_id: str) -> Optional[NASDevice]:
        """Get NAS device by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM discovered_nas WHERE id = ?', (nas_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                device_data = dict(zip(columns, row))
                # Parse JSON fields
                device_data['shares'] = json.loads(device_data['shares']) if device_data['shares'] else []
                device_data['ports'] = json.loads(device_data['ports']) if device_data['ports'] else []
                device_data['services'] = json.loads(device_data['services']) if device_data['services'] else []
                
                return NASDevice.from_dict(device_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting NAS device by ID: {e}")
            return None
    
    def get_network_suggestions(self) -> Dict:
        """Get network discovery suggestions for South African healthcare"""
        return {
            'common_ip_ranges': [
                '192.168.1.0/24',
                '192.168.0.0/24', 
                '10.0.0.0/24',
                '172.16.0.0/24',
                '192.168.10.0/24',  # Common in SA healthcare
                '10.1.0.0/24'       # Common in SA healthcare
            ],
            'scan_types': [
                {'value': 'quick', 'label': 'Quick Scan (5 ports)', 'duration': '1-2 minutes'},
                {'value': 'comprehensive', 'label': 'Comprehensive Scan (11 ports)', 'duration': '3-5 minutes'},
                {'value': 'deep', 'label': 'Deep Scan (20+ ports)', 'duration': '5-10 minutes'}
            ],
            'common_nas_brands': [
                'Synology', 'QNAP', 'Netgear ReadyNAS', 'Buffalo TeraStation',
                'Western Digital MyCloud', 'Windows Server', 'Linux Samba'
            ],
            'healthcare_tips': [
                'Start with your local network range (usually 192.168.x.x)',
                'NAS devices typically use ports 445 (SMB) and 80/443 (Web)',
                'Check with your IT department for network ranges',
                'Comprehensive scan is recommended for healthcare environments'
            ]
        }

# Create global instance
nas_discovery_manager = NASDiscoveryManager()

if __name__ == "__main__":
    # Example usage
    manager = NASDiscoveryManager()
    
    # Discover NAS devices
    devices = manager.discover_nas_devices("192.168.1.1-192.168.1.10", "comprehensive")
    
    print(f"Found {len(devices)} NAS devices:")
    for device in devices:
        print(f"  - {device.name} ({device.ip_address}) - {device.nas_type}")
        for share in device.shares:
            print(f"    Share: {share['name']} ({share['type']})")