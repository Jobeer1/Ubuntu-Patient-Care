"""
NAS Device Discovery Service

Automatically discovers NAS devices, scans for shared folders, identifies database types,
and manages credentials for accessing different NAS shares.

Features:
- Network scanning for NAS devices
- Share enumeration on discovered devices
- Database type identification (DICOM, Orthanc, etc.)
- Credential management and validation
- Connection testing with credentials
"""

import os
import socket
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import subprocess
import json
import threading
from datetime import datetime

try:
    import keyring  # For secure credential storage
except ImportError:
    keyring = None

logger = logging.getLogger(__name__)


class DatabaseTypeDetector:
    """Identifies the type of database in a given path"""
    
    @staticmethod
    def detect_database_type(path: str) -> Dict[str, Any]:
        """
        Detect what type of databases are in a given path.
        
        Returns:
            {
                'has_dicom_files': bool,
                'has_sqlite_db': bool,
                'has_orthanc_index': bool,
                'db_files': [],
                'dicom_files': [],
                'type': 'DICOM_STORAGE' | 'DATABASE' | 'MIXED' | 'UNKNOWN'
            }
        """
        result = {
            'has_dicom_files': False,
            'has_sqlite_db': False,
            'has_orthanc_index': False,
            'db_files': [],
            'dicom_files': [],
            'type': 'UNKNOWN'
        }
        
        try:
            if not os.path.exists(path):
                logger.warning(f"Path does not exist: {path}")
                return result
            
            if not os.path.isdir(path):
                logger.warning(f"Path is not a directory: {path}")
                return result
            
            # Scan first level of directory
            items = []
            try:
                items = os.listdir(path)[:100]  # Limit scan to first 100 items
            except PermissionError:
                logger.warning(f"Permission denied reading directory: {path}")
                result['type'] = 'PERMISSION_DENIED'
                return result
            
            for item in items:
                item_path = os.path.join(path, item)
                
                # Check for database files
                if item.endswith('.db') or item.endswith('.sqlite') or item.endswith('.sqlite3'):
                    result['has_sqlite_db'] = True
                    result['db_files'].append({
                        'name': item,
                        'path': item_path,
                        'size': os.path.getsize(item_path) if os.path.exists(item_path) else 0
                    })
                    
                    # Check if it's an Orthanc index
                    if 'orthanc' in item.lower() or 'index' in item.lower():
                        result['has_orthanc_index'] = True
                
                # Check for DICOM files
                if item.upper().endswith(('.DCM', '.DICOM')):
                    result['has_dicom_files'] = True
                    result['dicom_files'].append(item)
                
                # Check for subdirectories that might contain DICOM
                if os.path.isdir(item_path) and item.upper() in ['DICOM', 'DICOM_FILES', 'IMAGES', 'SCANS']:
                    result['has_dicom_files'] = True
            
            # Determine type
            if result['has_sqlite_db'] and result['has_dicom_files']:
                result['type'] = 'MIXED'
            elif result['has_sqlite_db']:
                result['type'] = 'DATABASE'
            elif result['has_dicom_files']:
                result['type'] = 'DICOM_STORAGE'
            elif result['has_orthanc_index']:
                result['type'] = 'ORTHANC_INDEX'
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting database type for {path}: {e}")
            result['error'] = str(e)
            return result


class NASCredentialManager:
    """Manages NAS credentials securely"""
    
    def __init__(self):
        self.service_name = "ELC_Medical_System"
        self.creds_file = Path(__file__).parent.parent / "nas_credentials.json"
        self._load_credentials()
    
    def _load_credentials(self):
        """Load credentials from file"""
        self.credentials = {}
        if self.creds_file.exists():
            try:
                with open(self.creds_file, 'r') as f:
                    self.credentials = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load credentials file: {e}")
    
    def _save_credentials(self):
        """Save credentials to file (encrypted if possible)"""
        try:
            with open(self.creds_file, 'w') as f:
                json.dump(self.credentials, f, indent=2)
            # Set restrictive permissions
            os.chmod(self.creds_file, 0o600)
        except Exception as e:
            logger.error(f"Could not save credentials file: {e}")
    
    def store_credentials(self, nas_host: str, username: str, password: str) -> bool:
        """Store credentials for a NAS device"""
        try:
            key = f"{nas_host}:{username}"
            self.credentials[key] = {
                'host': nas_host,
                'username': username,
                'password': password,  # TODO: encrypt in production
                'added': datetime.now().isoformat()
            }
            self._save_credentials()
            logger.info(f"Stored credentials for {nas_host}")
            return True
        except Exception as e:
            logger.error(f"Error storing credentials: {e}")
            return False
    
    def get_credentials(self, nas_host: str) -> Optional[Dict[str, Any]]:
        """Get stored credentials for a NAS device"""
        for key, creds in self.credentials.items():
            if nas_host in key:
                return creds
        return None
    
    def remove_credentials(self, nas_host: str) -> bool:
        """Remove stored credentials"""
        keys_to_remove = [k for k in self.credentials.keys() if nas_host in k]
        if keys_to_remove:
            for key in keys_to_remove:
                del self.credentials[key]
            self._save_credentials()
            return True
        return False


class NASDeviceDiscovery:
    """Discovers NAS devices and shares on network"""
    
    def __init__(self):
        self.discovered_devices = {}
        self.credential_manager = NASCredentialManager()
        self.detector = DatabaseTypeDetector()
    
    def discover_devices_on_network(self, subnet: str = "155.235.81", timeout: int = 2) -> List[Dict[str, Any]]:
        """
        Scan network subnet for NAS devices
        
        Args:
            subnet: Network subnet to scan (e.g., "155.235.81")
            timeout: Timeout for each host check in seconds
        
        Returns:
            List of discovered devices
        """
        logger.info(f"Starting network scan of {subnet}.* subnet...")
        discovered = []
        
        def check_host(ip: str):
            try:
                # Try to resolve hostname
                hostname = socket.gethostbyaddr(ip)[0]
            except socket.herror:
                hostname = None
            
            # Try to connect to common NAS ports
            for port in [445, 139, 22, 8080]:  # SMB, SSH, web interface
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(timeout)
                    result = sock.connect_ex((ip, port))
                    sock.close()
                    
                    if result == 0:
                        logger.info(f"Found active host: {ip}:{port}")
                        discovered.append({
                            'ip': ip,
                            'hostname': hostname or ip,
                            'port': port,
                            'type': 'potential_nas',
                            'detected_at': datetime.now().isoformat()
                        })
                        break
                except Exception as e:
                    logger.debug(f"Error checking {ip}:{port}: {e}")
                    pass
        
        # Scan IP range
        threads = []
        for i in range(1, 256):
            ip = f"{subnet}.{i}"
            thread = threading.Thread(target=check_host, args=(ip,), daemon=True)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads with timeout
        for thread in threads:
            thread.join(timeout=timeout + 1)
        
        self.discovered_devices = {d['ip']: d for d in discovered}
        logger.info(f"Discovery complete. Found {len(discovered)} potential NAS devices")
        return discovered
    
    def enumerate_shares(self, nas_host: str, username: Optional[str] = None,
                        password: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Enumerate available shares on a NAS device
        
        Args:
            nas_host: IP or hostname of NAS
            username: Optional username for authentication
            password: Optional password for authentication
        
        Returns:
            List of available shares
        """
        logger.info(f"Enumerating shares on {nas_host}...")
        shares = []
        
        try:
            # Try using smbclient (Windows command)
            if os.name == 'nt':  # Windows
                cmd = f'net view \\\\{nas_host} /all'
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    lines = result.stdout.split('\n')
                    
                    for line in lines:
                        if '\\\\' in line or 'Disk' in line:
                            parts = line.split()
                            if parts:
                                share_name = parts[0].strip('\\')
                                if share_name and share_name != nas_host:
                                    shares.append({
                                        'name': share_name,
                                        'host': nas_host,
                                        'path': f"\\\\{nas_host}\\{share_name}",
                                        'type': 'share',
                                        'accessible': None  # Will test later
                                    })
                except subprocess.TimeoutExpired:
                    logger.warning(f"Timeout enumerating shares on {nas_host}")
            
            # Fallback: try to access common share names
            common_shares = ['DICOM_Storage', 'Images', 'Medical', 'PACS', 'Orthanc', 'shared', 'public']
            for share_name in common_shares:
                path = f"\\\\{nas_host}\\{share_name}"
                if self._test_share_access(path, username, password):
                    shares.append({
                        'name': share_name,
                        'host': nas_host,
                        'path': path,
                        'type': 'share',
                        'accessible': True
                    })
                    logger.info(f"Found accessible share: {path}")
            
        except Exception as e:
            logger.error(f"Error enumerating shares on {nas_host}: {e}")
        
        return shares
    
    def _test_share_access(self, share_path: str, username: Optional[str] = None,
                          password: Optional[str] = None) -> bool:
        """Test if a share is accessible"""
        try:
            if os.name == 'nt':  # Windows
                # Try to map network drive temporarily
                if username and password:
                    cmd = f'net use Z: {share_path} /user:{username} {password} /persistent:no'
                else:
                    cmd = f'net use Z: {share_path} /persistent:no'
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    # Drive mapped successfully
                    subprocess.run('net use Z: /delete /yes', capture_output=True, timeout=5)
                    return True
            
            # Fallback: try os.path.exists
            return os.path.exists(share_path)
            
        except Exception as e:
            logger.debug(f"Error testing share access for {share_path}: {e}")
            return False
    
    def scan_share_for_databases(self, share_path: str, username: Optional[str] = None,
                                password: Optional[str] = None,
                                max_depth: int = 3) -> List[Dict[str, Any]]:
        """
        Scan a share for database files and DICOM storage
        
        Args:
            share_path: Path to share (e.g., "\\\\192.168.1.100\\DICOM")
            username: Optional username
            password: Optional password
            max_depth: Maximum directory depth to scan
        
        Returns:
            List of found databases/DICOM directories
        """
        logger.info(f"Scanning share for databases: {share_path}")
        found_databases = []
        
        try:
            # Try to mount share if credentials provided
            if username and password:
                # Test access first
                if not self._test_share_access(share_path, username, password):
                    logger.warning(f"Cannot access share {share_path} with provided credentials")
                    return found_databases
            
            if not os.path.exists(share_path):
                logger.warning(f"Share path does not exist: {share_path}")
                return found_databases
            
            # Recursive scan with depth limit
            self._recursive_scan(share_path, found_databases, 0, max_depth)
            
            logger.info(f"Found {len(found_databases)} databases on {share_path}")
            return found_databases
            
        except Exception as e:
            logger.error(f"Error scanning share {share_path}: {e}")
            return found_databases
    
    def _recursive_scan(self, path: str, results: List[Dict], depth: int, max_depth: int):
        """Recursively scan directory for databases"""
        if depth >= max_depth:
            return
        
        try:
            items = os.listdir(path)
        except (PermissionError, OSError) as e:
            logger.debug(f"Cannot read directory {path}: {e}")
            return
        
        for item in items:
            try:
                item_path = os.path.join(path, item)
                
                if os.path.isdir(item_path):
                    # Check this directory for databases
                    db_info = self.detector.detect_database_type(item_path)
                    
                    if db_info['type'] != 'UNKNOWN':
                        results.append({
                            'path': item_path,
                            'name': item,
                            'depth': depth,
                            'database_type': db_info['type'],
                            'details': db_info,
                            'discovered_at': datetime.now().isoformat()
                        })
                        logger.info(f"Found database: {item_path} (type: {db_info['type']})")
                    
                    # Continue scanning deeper
                    self._recursive_scan(item_path, results, depth + 1, max_depth)
            
            except Exception as e:
                logger.debug(f"Error processing {item}: {e}")
                pass


class NASConnectionManager:
    """Manages NAS connections with credentials"""
    
    def __init__(self):
        self.discovery = NASDeviceDiscovery()
        self.credential_manager = self.discovery.credential_manager
        self.current_connections = {}
    
    def test_connection(self, nas_host: str, share_name: str,
                       username: Optional[str] = None,
                       password: Optional[str] = None) -> Tuple[bool, str]:
        """
        Test connection to a NAS share
        
        Returns:
            (success: bool, message: str)
        """
        try:
            share_path = f"\\\\{nas_host}\\{share_name}"
            
            if os.name == 'nt':  # Windows
                if username and password:
                    cmd = f'net use Z: {share_path} /user:{username} {password} /persistent:no'
                else:
                    cmd = f'net use Z: {share_path} /persistent:no'
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    # Connection successful, clean up
                    subprocess.run('net use Z: /delete /yes', capture_output=True, timeout=5)
                    message = f"Successfully connected to \\\\{nas_host}\\{share_name}"
                    logger.info(message)
                    return True, message
                else:
                    error = result.stderr.strip()
                    message = f"Failed to connect: {error}"
                    logger.warning(message)
                    return False, message
            else:
                # Try os.path.exists as fallback
                if os.path.exists(share_path):
                    message = f"Successfully accessed \\\\{nas_host}\\{share_name}"
                    logger.info(message)
                    return True, message
                else:
                    message = f"Cannot access \\\\{nas_host}\\{share_name}"
                    logger.warning(message)
                    return False, message
        
        except subprocess.TimeoutExpired:
            return False, "Connection attempt timed out"
        except Exception as e:
            return False, f"Error testing connection: {str(e)}"
    
    def save_connection(self, nas_host: str, share_name: str,
                       username: Optional[str] = None,
                       password: Optional[str] = None,
                       database_type: Optional[str] = None) -> bool:
        """Save a successful connection for later use"""
        try:
            connection_key = f"{nas_host}:{share_name}"
            
            self.current_connections[connection_key] = {
                'nas_host': nas_host,
                'share_name': share_name,
                'username': username,
                'database_type': database_type,
                'connected_at': datetime.now().isoformat()
            }
            
            # Store credentials if provided
            if username and password:
                self.credential_manager.store_credentials(nas_host, username, password)
            
            logger.info(f"Saved connection: {connection_key}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving connection: {e}")
            return False


# Global instance
nas_manager = NASConnectionManager()
