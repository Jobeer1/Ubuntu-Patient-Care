"""
NAS Connector Module for Orthanc Integration
Handles SMB/CIFS and NFS connections to Network Attached Storage
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import shutil

import uuid
import hashlib

try:
    from smbprotocol.connection import Connection
    from smbprotocol.session import Session
    from smbprotocol.tree import TreeConnect
    from smbprotocol.open import Open, CreateDisposition, CreateOptions, FileAttributes
    SMB_AVAILABLE = True
except ImportError:
    SMB_AVAILABLE = False
    print("Warning: smbprotocol not available. Install with: pip install smbprotocol")

class NASConnectionError(Exception):
    """Custom exception for NAS connection issues"""
    pass

class NASConnector:
    """Main NAS connector class supporting SMB/CIFS and NFS"""
    
    def __init__(self, config_path: str = "nas_config.json"):
        self.config_path = config_path
        self.config = {}
        self.connection = None
        self.session = None
        self.tree = None
        self.is_connected = False
        self.last_error = None
        self.connection_lock = threading.Lock()
        self.logger = self._setup_logging()
        
        # Load configuration
        self.load_config()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for NAS operations"""
        logger = logging.getLogger('nas_connector')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def load_config(self) -> Dict[str, Any]:
        """Load NAS configuration from file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            else:
                # Default configuration
                self.config = {
                    "enabled": False,
                    "type": "smb",  # smb, nfs, local
                    "host": "",
                    "port": 445,
                    "share": "",
                    "username": "",
                    "password": "",
                    "domain": "",
                    "path": "/dicom",
                    "timeout": 30,
                    "retry_attempts": 3,
                    "retry_delay": 5,
                    "auto_reconnect": True,
                    "connection_pool_size": 5
                }
                self.save_config()
            
            return self.config
        except Exception as e:
            self.logger.error(f"Failed to load NAS config: {e}")
            return {}
    
    def save_config(self) -> bool:
        """Save NAS configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save NAS config: {e}")
            return False
    
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Update NAS configuration"""
        try:
            # Validate required fields
            required_fields = ['type', 'host', 'share', 'username', 'password']
            for field in required_fields:
                if field not in new_config:
                    raise ValueError(f"Missing required field: {field}")
            
            # Update configuration
            self.config.update(new_config)
            
            # Save to file
            if self.save_config():
                self.logger.info("NAS configuration updated successfully")
                
                # Reconnect if currently connected
                if self.is_connected:
                    self.disconnect()
                    self.connect()
                
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to update NAS config: {e}")
            self.last_error = str(e)
            return False
    
    def connect(self) -> bool:
        """Connect to NAS"""
        if not self.config.get('enabled', False):
            self.logger.info("NAS connection disabled in configuration")
            return False
        
        with self.connection_lock:
            try:
                nas_type = self.config.get('type', 'smb').lower()
                
                if nas_type == 'smb':
                    return self._connect_smb()
                elif nas_type == 'nfs':
                    return self._connect_nfs()
                elif nas_type == 'local':
                    return self._connect_local()
                else:
                    raise NASConnectionError(f"Unsupported NAS type: {nas_type}")
                    
            except Exception as e:
                self.logger.error(f"Failed to connect to NAS: {e}")
                self.last_error = str(e)
                self.is_connected = False
                return False
    
    def _connect_smb(self) -> bool:
        """Connect to SMB/CIFS share"""
        if not SMB_AVAILABLE:
            raise NASConnectionError("SMB support not available. Install smbprotocol package.")
        
        try:
            host = self.config['host']
            port = self.config.get('port', 445)
            username = self.config['username']
            password = self.config['password']
            domain = self.config.get('domain', '')
            share = self.config['share']
            
            # Create connection
            self.connection = Connection(uuid.uuid4(), host, port)
            self.connection.connect()
            
            # Create session
            self.session = Session(self.connection, username, password, domain)
            self.session.connect()
            
            # Connect to tree (share)
            self.tree = TreeConnect(self.session, f"\\\\{host}\\{share}")
            self.tree.connect()
            
            self.is_connected = True
            self.last_error = None
            self.logger.info(f"Successfully connected to SMB share: //{host}/{share}")
            return True
            
        except Exception as e:
            self.logger.error(f"SMB connection failed: {e}")
            self.last_error = str(e)
            self._cleanup_connection()
            return False
    
    def _connect_nfs(self) -> bool:
        """Connect to NFS share (placeholder for future implementation)"""
        # TODO: Implement NFS support using nfs-utils or similar
        self.logger.warning("NFS support not yet implemented")
        return False
    
    def _connect_local(self) -> bool:
        """Connect to local filesystem (for testing)"""
        try:
            local_path = self.config.get('path', '/tmp/orthanc_nas')
            
            # Create directory if it doesn't exist
            os.makedirs(local_path, exist_ok=True)
            
            # Test write access
            test_file = os.path.join(local_path, '.orthanc_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
            self.is_connected = True
            self.last_error = None
            self.logger.info(f"Successfully connected to local path: {local_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Local connection failed: {e}")
            self.last_error = str(e)
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from NAS"""
        with self.connection_lock:
            try:
                self._cleanup_connection()
                self.is_connected = False
                self.logger.info("Disconnected from NAS")
                return True
            except Exception as e:
                self.logger.error(f"Error during disconnect: {e}")
                return False
    
    def _cleanup_connection(self):
        """Clean up connection objects"""
        try:
            if self.tree:
                self.tree.disconnect()
                self.tree = None
            if self.session:
                self.session.disconnect()
                self.session = None
            if self.connection:
                self.connection.disconnect()
                self.connection = None
        except Exception as e:
            self.logger.warning(f"Error during connection cleanup: {e}")
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test NAS connection"""
        try:
            if self.connect():
                # Try to list root directory
                files = self.list_files("/")
                self.disconnect()
                return True, f"Connection successful. Found {len(files)} items in root directory."
            else:
                return False, self.last_error or "Connection failed"
        except Exception as e:
            return False, str(e)
    
    def list_files(self, path: str = "/") -> List[Dict[str, Any]]:
        """List files and directories in NAS path"""
        if not self.is_connected:
            if not self.connect():
                raise NASConnectionError("Not connected to NAS")
        
        try:
            nas_type = self.config.get('type', 'smb').lower()
            
            if nas_type == 'smb':
                return self._list_files_smb(path)
            elif nas_type == 'local':
                return self._list_files_local(path)
            else:
                raise NASConnectionError(f"List files not implemented for {nas_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to list files in {path}: {e}")
            raise NASConnectionError(f"Failed to list files: {e}")
    
    def _list_files_smb(self, path: str) -> List[Dict[str, Any]]:
        """List files in SMB share"""
        files = []
        try:
            # Normalize path
            smb_path = path.replace('/', '\\').lstrip('\\')
            if smb_path and not smb_path.endswith('\\'):
                smb_path += '\\*'
            else:
                smb_path += '*'
            
            # Query directory
            file_info = self.tree.query_directory(smb_path)
            
            for info in file_info:
                if info.file_name in ['.', '..']:
                    continue
                
                files.append({
                    'name': info.file_name,
                    'path': f"{path.rstrip('/')}/{info.file_name}",
                    'is_directory': bool(info.file_attributes & FileAttributes.FILE_ATTRIBUTE_DIRECTORY),
                    'size': info.end_of_file,
                    'modified': info.last_write_time.isoformat() if info.last_write_time else None,
                    'created': info.creation_time.isoformat() if info.creation_time else None
                })
            
            return files
            
        except Exception as e:
            self.logger.error(f"SMB list files failed: {e}")
            raise
    
    def _list_files_local(self, path: str) -> List[Dict[str, Any]]:
        """List files in local filesystem"""
        files = []
        try:
            base_path = self.config.get('path', '/tmp/orthanc_nas')
            full_path = os.path.join(base_path, path.lstrip('/'))
            
            if not os.path.exists(full_path):
                return files
            
            for item in os.listdir(full_path):
                item_path = os.path.join(full_path, item)
                stat = os.stat(item_path)
                
                files.append({
                    'name': item,
                    'path': f"{path.rstrip('/')}/{item}",
                    'is_directory': os.path.isdir(item_path),
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
            
            return files
            
        except Exception as e:
            self.logger.error(f"Local list files failed: {e}")
            raise
    
    def read_file(self, path: str) -> bytes:
        """Read file from NAS"""
        if not self.is_connected:
            if not self.connect():
                raise NASConnectionError("Not connected to NAS")
        
        try:
            nas_type = self.config.get('type', 'smb').lower()
            
            if nas_type == 'smb':
                return self._read_file_smb(path)
            elif nas_type == 'local':
                return self._read_file_local(path)
            else:
                raise NASConnectionError(f"Read file not implemented for {nas_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to read file {path}: {e}")
            raise NASConnectionError(f"Failed to read file: {e}")
    
    def _read_file_smb(self, path: str) -> bytes:
        """Read file from SMB share"""
        try:
            smb_path = path.replace('/', '\\').lstrip('\\')
            
            file_obj = Open(self.tree, smb_path)
            file_obj.open(CreateDisposition.FILE_OPEN, CreateOptions.FILE_NON_DIRECTORY_FILE)
            
            data = file_obj.read()
            file_obj.close()
            
            return data
            
        except Exception as e:
            self.logger.error(f"SMB read file failed: {e}")
            raise
    
    def _read_file_local(self, path: str) -> bytes:
        """Read file from local filesystem"""
        try:
            base_path = self.config.get('path', '/tmp/orthanc_nas')
            full_path = os.path.join(base_path, path.lstrip('/'))
            
            with open(full_path, 'rb') as f:
                return f.read()
                
        except Exception as e:
            self.logger.error(f"Local read file failed: {e}")
            raise
    
    def write_file(self, path: str, data: bytes) -> bool:
        """Write file to NAS"""
        if not self.is_connected:
            if not self.connect():
                raise NASConnectionError("Not connected to NAS")
        
        try:
            nas_type = self.config.get('type', 'smb').lower()
            
            if nas_type == 'smb':
                return self._write_file_smb(path, data)
            elif nas_type == 'local':
                return self._write_file_local(path, data)
            else:
                raise NASConnectionError(f"Write file not implemented for {nas_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to write file {path}: {e}")
            raise NASConnectionError(f"Failed to write file: {e}")
    
    def _write_file_smb(self, path: str, data: bytes) -> bool:
        """Write file to SMB share"""
        try:
            smb_path = path.replace('/', '\\').lstrip('\\')
            
            # Create directories if needed
            dir_path = '\\'.join(smb_path.split('\\')[:-1])
            if dir_path:
                self._create_directory_smb(dir_path)
            
            file_obj = Open(self.tree, smb_path)
            file_obj.open(CreateDisposition.FILE_OVERWRITE_IF, CreateOptions.FILE_NON_DIRECTORY_FILE)
            
            file_obj.write(data)
            file_obj.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"SMB write file failed: {e}")
            raise
    
    def _write_file_local(self, path: str, data: bytes) -> bool:
        """Write file to local filesystem"""
        try:
            base_path = self.config.get('path', '/tmp/orthanc_nas')
            full_path = os.path.join(base_path, path.lstrip('/'))
            
            # Create directories if needed
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'wb') as f:
                f.write(data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Local write file failed: {e}")
            raise
    
    def _create_directory_smb(self, path: str):
        """Create directory in SMB share"""
        try:
            parts = path.split('\\')
            current_path = ""
            
            for part in parts:
                if not part:
                    continue
                
                current_path = f"{current_path}\\{part}" if current_path else part
                
                try:
                    dir_obj = Open(self.tree, current_path)
                    dir_obj.open(CreateDisposition.FILE_CREATE, 
                               CreateOptions.FILE_DIRECTORY_FILE)
                    dir_obj.close()
                except Exception:
                    # Directory might already exist, ignore error
                    pass
                    
        except Exception as e:
            self.logger.warning(f"Failed to create directory {path}: {e}")
    
    def delete_file(self, path: str) -> bool:
        """Delete file from NAS"""
        if not self.is_connected:
            if not self.connect():
                raise NASConnectionError("Not connected to NAS")
        
        try:
            nas_type = self.config.get('type', 'smb').lower()
            
            if nas_type == 'smb':
                return self._delete_file_smb(path)
            elif nas_type == 'local':
                return self._delete_file_local(path)
            else:
                raise NASConnectionError(f"Delete file not implemented for {nas_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to delete file {path}: {e}")
            raise NASConnectionError(f"Failed to delete file: {e}")
    
    def _delete_file_smb(self, path: str) -> bool:
        """Delete file from SMB share"""
        try:
            smb_path = path.replace('/', '\\').lstrip('\\')
            
            file_obj = Open(self.tree, smb_path)
            file_obj.open(CreateDisposition.FILE_OPEN, CreateOptions.FILE_NON_DIRECTORY_FILE)
            file_obj.delete()
            file_obj.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"SMB delete file failed: {e}")
            raise
    
    def _delete_file_local(self, path: str) -> bool:
        """Delete file from local filesystem"""
        try:
            base_path = self.config.get('path', '/tmp/orthanc_nas')
            full_path = os.path.join(base_path, path.lstrip('/'))
            
            os.remove(full_path)
            return True
            
        except Exception as e:
            self.logger.error(f"Local delete file failed: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get NAS connection status and statistics"""
        try:
            status = {
                'connected': self.is_connected,
                'config': {
                    'enabled': self.config.get('enabled', False),
                    'type': self.config.get('type', 'unknown'),
                    'host': self.config.get('host', ''),
                    'share': self.config.get('share', ''),
                    'path': self.config.get('path', '/')
                },
                'last_error': self.last_error,
                'last_check': datetime.now().isoformat()
            }
            
            if self.is_connected:
                try:
                    # Get basic statistics
                    files = self.list_files("/")
                    status['stats'] = {
                        'total_items': len(files),
                        'directories': len([f for f in files if f['is_directory']]),
                        'files': len([f for f in files if not f['is_directory']])
                    }
                except Exception as e:
                    status['stats_error'] = str(e)
            
            return status
            
        except Exception as e:
            return {
                'connected': False,
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }
    
    def get_space_info(self) -> Dict[str, Any]:
        """Get NAS space information"""
        try:
            if self.config.get('type') == 'local':
                base_path = self.config.get('path', '/tmp/orthanc_nas')
                stat = shutil.disk_usage(base_path)
                
                return {
                    'total_bytes': stat.total,
                    'used_bytes': stat.total - stat.free,
                    'free_bytes': stat.free,
                    'total_gb': round(stat.total / (1024**3), 2),
                    'used_gb': round((stat.total - stat.free) / (1024**3), 2),
                    'free_gb': round(stat.free / (1024**3), 2),
                    'usage_percent': round(((stat.total - stat.free) / stat.total) * 100, 1)
                }
            else:
                # For SMB/NFS, this would require additional implementation
                return {
                    'error': 'Space information not available for this NAS type'
                }
                
        except Exception as e:
            return {
                'error': f'Failed to get space information: {e}'
            }

# Global NAS connector instance
nas_connector = NASConnector()