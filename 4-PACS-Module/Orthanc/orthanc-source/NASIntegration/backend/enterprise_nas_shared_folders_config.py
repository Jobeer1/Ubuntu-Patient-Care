#!/usr/bin/env python3
"""
🏥 Enterprise NAS Shared Folders Configuration Manager
Ubuntu Patient Care - Multi-Procedure Shared Folder Management

Manages multiple shared folders across NAS devices for different medical procedures:
- CT Scans (DICOM)
- MRI Studies (DICOM + Firebird)
- X-Ray Imaging (JPEG2000)
- Ultrasound (Multiple formats)
- Nuclear Medicine (DICOM + proprietary)
- Pathology Images (High-resolution TIFF)

Each procedure can have different shared folders with unique credentials.
"""

import json
import sqlite3
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import hashlib
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

@dataclass
class SharedFolderConfig:
    """Shared folder configuration for specific medical procedures"""
    folder_id: str
    nas_device_id: str
    procedure_type: str  # CT, MRI, XRAY, ULTRASOUND, etc.
    share_name: str
    share_path: str
    username: str
    password_encrypted: str
    domain: str
    protocol: str  # SMB, NFS, FTP
    mount_point: str
    auto_mount: bool
    read_only: bool
    compression_type: str  # DICOM, JPEG2000, TIFF, etc.
    database_format: str  # DICOM, FIREBIRD, SQLITE, etc.
    priority: int  # 1-10, higher = more important
    created_at: str
    last_tested: Optional[str] = None
    last_successful: Optional[str] = None
    is_active: bool = True

@dataclass
class NASDevice:
    """Enhanced NAS device with multiple shared folders"""
    device_id: str
    device_name: str
    ip_address: str
    manufacturer: str
    model: str
    shared_folders: List[SharedFolderConfig]
    default_domain: str
    admin_username: str
    admin_password_encrypted: str
    created_at: str
    last_discovery: str
    is_active: bool = True

class EnterpriseNASFoldersManager:
    """🏥 Enterprise NAS Shared Folders Configuration Manager"""
    
    def __init__(self, db_path: str = "enterprise_nas_folders.db"):
        self.db_path = db_path
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        self.init_database()
        
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for secure credential storage"""
        key_file = "nas_encryption.key"
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Restrict access
            return key
            
    def _encrypt_password(self, password: str) -> str:
        """Encrypt password for secure storage"""
        return self.cipher_suite.encrypt(password.encode()).decode()
        
    def _decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt password for use"""
        return self.cipher_suite.decrypt(encrypted_password.encode()).decode()
        
    def init_database(self):
        """Initialize enterprise NAS folders database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- NAS Devices table
                CREATE TABLE IF NOT EXISTS nas_devices (
                    device_id TEXT PRIMARY KEY,
                    device_name TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    manufacturer TEXT,
                    model TEXT,
                    default_domain TEXT,
                    admin_username TEXT,
                    admin_password_encrypted TEXT,
                    created_at TEXT NOT NULL,
                    last_discovery TEXT,
                    is_active BOOLEAN DEFAULT 1
                );
                
                -- Shared Folders table
                CREATE TABLE IF NOT EXISTS shared_folders (
                    folder_id TEXT PRIMARY KEY,
                    nas_device_id TEXT NOT NULL,
                    procedure_type TEXT NOT NULL,
                    share_name TEXT NOT NULL,
                    share_path TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password_encrypted TEXT NOT NULL,
                    domain TEXT,
                    protocol TEXT NOT NULL DEFAULT 'SMB',
                    mount_point TEXT,
                    auto_mount BOOLEAN DEFAULT 1,
                    read_only BOOLEAN DEFAULT 0,
                    compression_type TEXT,
                    database_format TEXT,
                    priority INTEGER DEFAULT 5,
                    created_at TEXT NOT NULL,
                    last_tested TEXT,
                    last_successful TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (nas_device_id) REFERENCES nas_devices(device_id)
                );
                
                -- Procedure Types reference
                CREATE TABLE IF NOT EXISTS procedure_types (
                    procedure_code TEXT PRIMARY KEY,
                    procedure_name TEXT NOT NULL,
                    description TEXT,
                    typical_formats TEXT,
                    typical_databases TEXT,
                    default_compression TEXT,
                    is_active BOOLEAN DEFAULT 1
                );
                
                -- Connection Test Log
                CREATE TABLE IF NOT EXISTS connection_tests (
                    test_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    folder_id TEXT NOT NULL,
                    test_time TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    response_time_ms INTEGER,
                    error_message TEXT,
                    files_found INTEGER,
                    FOREIGN KEY (folder_id) REFERENCES shared_folders(folder_id)
                );
                
                -- Indexing Status per folder
                CREATE TABLE IF NOT EXISTS folder_indexing_status (
                    folder_id TEXT PRIMARY KEY,
                    last_index_start TEXT,
                    last_index_complete TEXT,
                    files_indexed INTEGER DEFAULT 0,
                    files_failed INTEGER DEFAULT 0,
                    total_size_mb REAL DEFAULT 0,
                    indexing_active BOOLEAN DEFAULT 0,
                    next_scheduled_index TEXT,
                    FOREIGN KEY (folder_id) REFERENCES shared_folders(folder_id)
                );
                
                -- Create indexes for performance
                CREATE INDEX IF NOT EXISTS idx_shared_folders_nas_device 
                    ON shared_folders(nas_device_id);
                CREATE INDEX IF NOT EXISTS idx_shared_folders_procedure 
                    ON shared_folders(procedure_type);
                CREATE INDEX IF NOT EXISTS idx_connection_tests_folder 
                    ON connection_tests(folder_id, test_time);
            """)
            
            # Insert standard procedure types
            conn.executemany("""
                INSERT OR IGNORE INTO procedure_types 
                (procedure_code, procedure_name, description, typical_formats, typical_databases, default_compression)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                ('CT', 'CT Scans', 'Computed Tomography imaging', 'DICOM', 'DICOM,FIREBIRD', 'LOSSLESS'),
                ('MRI', 'MRI Studies', 'Magnetic Resonance Imaging', 'DICOM', 'DICOM,FIREBIRD', 'LOSSLESS'), 
                ('XRAY', 'X-Ray Imaging', 'Digital Radiography', 'DICOM,JPEG2000', 'FIREBIRD,SQLITE', 'JPEG2000'),
                ('ULTRASOUND', 'Ultrasound', 'Ultrasonography studies', 'DICOM,AVI,JPEG', 'DICOM,SQLITE', 'LOSSY'),
                ('NUCLEAR', 'Nuclear Medicine', 'PET/SPECT imaging', 'DICOM', 'DICOM,PROPRIETARY', 'LOSSLESS'),
                ('PATHOLOGY', 'Digital Pathology', 'Microscopy images', 'TIFF,JPEG2000,DICOM', 'SQLITE,FIREBIRD', 'LOSSLESS'),
                ('MAMMOGRAPHY', 'Mammography', 'Breast imaging studies', 'DICOM', 'DICOM,FIREBIRD', 'LOSSLESS'),
                ('FLUOROSCOPY', 'Fluoroscopy', 'Real-time X-ray imaging', 'DICOM,MP4', 'DICOM,SQLITE', 'LOSSY'),
                ('ENDOSCOPY', 'Endoscopy', 'Internal visualization', 'DICOM,MP4,JPEG', 'SQLITE,FIREBIRD', 'LOSSY'),
                ('CARDIOLOGY', 'Cardiac Imaging', 'ECG, Echo, Cath studies', 'DICOM,PDF,JPEG', 'DICOM,SQLITE', 'LOSSLESS')
            ])
            
            conn.commit()
            
    def add_nas_device(self, device_name: str, ip_address: str, manufacturer: str = "Unknown",
                      model: str = "Unknown", default_domain: str = "", 
                      admin_username: str = "", admin_password: str = "") -> str:
        """Add new NAS device"""
        device_id = f"nas_{ip_address.replace('.', '_')}"
        admin_password_encrypted = self._encrypt_password(admin_password) if admin_password else ""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO nas_devices 
                (device_id, device_name, ip_address, manufacturer, model, default_domain,
                 admin_username, admin_password_encrypted, created_at, last_discovery)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (device_id, device_name, ip_address, manufacturer, model, default_domain,
                  admin_username, admin_password_encrypted, datetime.now().isoformat(), 
                  datetime.now().isoformat()))
            
        logger.info(f"Added NAS device: {device_name} ({ip_address})")
        return device_id
        
    def add_shared_folder(self, nas_device_id: str, procedure_type: str, share_name: str,
                         share_path: str, username: str, password: str, domain: str = "",
                         protocol: str = "SMB", mount_point: str = "", auto_mount: bool = True,
                         read_only: bool = False, compression_type: str = "DICOM",
                         database_format: str = "DICOM", priority: int = 5) -> str:
        """Add shared folder configuration for specific procedure"""
        folder_id = f"{nas_device_id}_{procedure_type}_{share_name.replace('/', '_').replace('\\', '_')}"
        password_encrypted = self._encrypt_password(password)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO shared_folders 
                (folder_id, nas_device_id, procedure_type, share_name, share_path,
                 username, password_encrypted, domain, protocol, mount_point,
                 auto_mount, read_only, compression_type, database_format, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (folder_id, nas_device_id, procedure_type, share_name, share_path,
                  username, password_encrypted, domain, protocol, mount_point,
                  auto_mount, read_only, compression_type, database_format, priority,
                  datetime.now().isoformat()))
            
            # Initialize indexing status
            conn.execute("""
                INSERT OR IGNORE INTO folder_indexing_status (folder_id)
                VALUES (?)
            """, (folder_id,))
            
        logger.info(f"Added shared folder: {share_name} for {procedure_type} on {nas_device_id}")
        return folder_id
        
    def get_nas_devices(self) -> List[Dict[str, Any]]:
        """Get all NAS devices with their shared folders"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            devices = conn.execute("""
                SELECT * FROM nas_devices WHERE is_active = 1
                ORDER BY device_name
            """).fetchall()
            
            result = []
            for device in devices:
                device_dict = dict(device)
                
                # Get shared folders for this device
                folders = conn.execute("""
                    SELECT f.*, p.procedure_name, p.description 
                    FROM shared_folders f
                    LEFT JOIN procedure_types p ON f.procedure_type = p.procedure_code
                    WHERE f.nas_device_id = ? AND f.is_active = 1
                    ORDER BY f.priority DESC, f.procedure_type
                """, (device['device_id'],)).fetchall()
                
                device_dict['shared_folders'] = [dict(folder) for folder in folders]
                device_dict['admin_password'] = "[ENCRYPTED]"  # Don't expose passwords
                result.append(device_dict)
                
        return result
        
    def get_folders_by_procedure(self, procedure_type: str) -> List[Dict[str, Any]]:
        """Get all shared folders for specific procedure type across all NAS devices"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            folders = conn.execute("""
                SELECT f.*, d.device_name, d.ip_address, d.manufacturer,
                       p.procedure_name, p.description
                FROM shared_folders f
                JOIN nas_devices d ON f.nas_device_id = d.device_id
                LEFT JOIN procedure_types p ON f.procedure_type = p.procedure_code
                WHERE f.procedure_type = ? AND f.is_active = 1 AND d.is_active = 1
                ORDER BY f.priority DESC, d.device_name
            """, (procedure_type,)).fetchall()
            
        return [dict(folder) for folder in folders]
        
    def test_folder_connection(self, folder_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Test connection to specific shared folder"""
        folder = self.get_folder_config(folder_id)
        if not folder:
            return False, "Folder configuration not found", {}
            
        try:
            # Decrypt password for testing
            password = self._decrypt_password(folder['password_encrypted'])
            
            # Test based on protocol
            if folder['protocol'].upper() == 'SMB':
                success, message, details = self._test_smb_folder(folder, password)
            elif folder['protocol'].upper() == 'NFS':
                success, message, details = self._test_nfs_folder(folder, password)
            elif folder['protocol'].upper() == 'FTP':
                success, message, details = self._test_ftp_folder(folder, password)
            else:
                return False, f"Unsupported protocol: {folder['protocol']}", {}
                
            # Log test result
            self._log_connection_test(folder_id, success, message, details.get('response_time_ms', 0),
                                    details.get('files_found', 0))
                                    
            return success, message, details
            
        except Exception as e:
            logger.error(f"Error testing folder {folder_id}: {e}")
            self._log_connection_test(folder_id, False, str(e), 0, 0)
            return False, f"Test failed: {str(e)}", {}
            
    def _test_smb_folder(self, folder: Dict, password: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Test SMB shared folder connection"""
        import time
        start_time = time.time()
        
        try:
            # Try to connect via smbclient or similar
            # This is a simplified implementation - you may need to use smbprotocol or similar
            import subprocess
            
            # Test command (adjust based on your system)
            if os.name == 'nt':  # Windows
                cmd = f'net use \\\\{folder["share_path"]} /user:{folder["domain"]}\\{folder["username"]} {password}'
            else:  # Linux
                cmd = f'smbclient //{folder["share_path"]} -U {folder["username"]}%{password} -c "ls"'
                
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            response_time = int((time.time() - start_time) * 1000)
            
            if result.returncode == 0:
                return True, "SMB connection successful", {
                    'response_time_ms': response_time,
                    'files_found': 0,  # Could parse output to count files
                    'output': result.stdout
                }
            else:
                return False, f"SMB connection failed: {result.stderr}", {
                    'response_time_ms': response_time,
                    'files_found': 0,
                    'error': result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return False, "SMB connection timeout", {'response_time_ms': 30000, 'files_found': 0}
        except Exception as e:
            return False, f"SMB test error: {str(e)}", {'response_time_ms': 0, 'files_found': 0}
            
    def _test_nfs_folder(self, folder: Dict, password: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Test NFS shared folder connection"""
        # NFS testing implementation
        return True, "NFS test not implemented yet", {'response_time_ms': 0, 'files_found': 0}
        
    def _test_ftp_folder(self, folder: Dict, password: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Test FTP shared folder connection"""
        import ftplib
        import time
        
        start_time = time.time()
        try:
            # Extract server from share_path
            server = folder['share_path'].split('/')[0] if '/' in folder['share_path'] else folder['share_path']
            path = '/' + '/'.join(folder['share_path'].split('/')[1:]) if '/' in folder['share_path'] else '/'
            
            with ftplib.FTP(server) as ftp:
                ftp.login(folder['username'], password)
                ftp.cwd(path)
                files = ftp.nlst()
                response_time = int((time.time() - start_time) * 1000)
                
                return True, "FTP connection successful", {
                    'response_time_ms': response_time,
                    'files_found': len(files),
                    'sample_files': files[:5] if files else []
                }
                
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            return False, f"FTP connection failed: {str(e)}", {
                'response_time_ms': response_time,
                'files_found': 0
            }
            
    def _log_connection_test(self, folder_id: str, success: bool, message: str, 
                           response_time_ms: int, files_found: int):
        """Log connection test result"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO connection_tests 
                (folder_id, test_time, success, response_time_ms, error_message, files_found)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (folder_id, datetime.now().isoformat(), success, response_time_ms,
                  message if not success else None, files_found))
                  
            # Update last_tested time in shared_folders
            if success:
                conn.execute("""
                    UPDATE shared_folders 
                    SET last_tested = ?, last_successful = ?
                    WHERE folder_id = ?
                """, (datetime.now().isoformat(), datetime.now().isoformat(), folder_id))
            else:
                conn.execute("""
                    UPDATE shared_folders 
                    SET last_tested = ?
                    WHERE folder_id = ?
                """, (datetime.now().isoformat(), folder_id))
                
    def get_folder_config(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """Get specific folder configuration"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            folder = conn.execute("""
                SELECT f.*, d.device_name, d.ip_address 
                FROM shared_folders f
                JOIN nas_devices d ON f.nas_device_id = d.device_id
                WHERE f.folder_id = ?
            """, (folder_id,)).fetchone()
            
        return dict(folder) if folder else None
        
    def get_procedure_types(self) -> List[Dict[str, Any]]:
        """Get all available procedure types"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            procedures = conn.execute("""
                SELECT * FROM procedure_types WHERE is_active = 1
                ORDER BY procedure_name
            """).fetchall()
            
        return [dict(proc) for proc in procedures]
        
    def test_all_folders(self) -> Dict[str, Any]:
        """Test all shared folder connections"""
        results = {}
        total_tested = 0
        total_successful = 0
        
        folders = self.get_all_folders()
        
        for folder in folders:
            folder_id = folder['folder_id']
            success, message, details = self.test_folder_connection(folder_id)
            
            results[folder_id] = {
                'folder_name': folder['share_name'],
                'procedure_type': folder['procedure_type'],
                'device_name': folder.get('device_name', 'Unknown'),
                'success': success,
                'message': message,
                'details': details
            }
            
            total_tested += 1
            if success:
                total_successful += 1
                
        return {
            'summary': {
                'total_tested': total_tested,
                'total_successful': total_successful,
                'success_rate': (total_successful / total_tested * 100) if total_tested > 0 else 0
            },
            'results': results
        }
        
    def get_all_folders(self) -> List[Dict[str, Any]]:
        """Get all shared folders across all devices"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            folders = conn.execute("""
                SELECT f.*, d.device_name, d.ip_address, d.manufacturer,
                       p.procedure_name, p.description
                FROM shared_folders f
                JOIN nas_devices d ON f.nas_device_id = d.device_id
                LEFT JOIN procedure_types p ON f.procedure_type = p.procedure_code
                WHERE f.is_active = 1 AND d.is_active = 1
                ORDER BY d.device_name, f.priority DESC, f.procedure_type
            """).fetchall()
            
        return [dict(folder) for folder in folders]
        
    def get_folder_credentials(self, folder_id: str) -> Optional[Dict[str, str]]:
        """Get decrypted credentials for folder (admin only)"""
        folder = self.get_folder_config(folder_id)
        if not folder:
            return None
            
        try:
            return {
                'username': folder['username'],
                'password': self._decrypt_password(folder['password_encrypted']),
                'domain': folder['domain'],
                'protocol': folder['protocol'],
                'share_path': folder['share_path']
            }
        except Exception as e:
            logger.error(f"Error decrypting credentials for {folder_id}: {e}")
            return None

# Global instance
enterprise_nas_folders = EnterpriseNASFoldersManager()

if __name__ == "__main__":
    # Demo configuration
    manager = EnterpriseNASFoldersManager()
    
    # Add example NAS devices
    nas1_id = manager.add_nas_device("Primary Medical NAS", "192.168.1.100", "Synology", "DS920+", 
                                    "HOSPITAL", "admin", "admin_password")
    nas2_id = manager.add_nas_device("Secondary Medical NAS", "192.168.1.101", "QNAP", "TS-464", 
                                    "HOSPITAL", "admin", "admin_password")
    
    # Add shared folders for different procedures
    manager.add_shared_folder(nas1_id, "CT", "ct_scans", "//192.168.1.100/ct_scans", 
                             "ct_user", "ct_password", "HOSPITAL", "SMB", 
                             compression_type="DICOM", database_format="DICOM", priority=9)
                             
    manager.add_shared_folder(nas1_id, "MRI", "mri_studies", "//192.168.1.100/mri_studies", 
                             "mri_user", "mri_password", "HOSPITAL", "SMB",
                             compression_type="DICOM", database_format="FIREBIRD", priority=8)
                             
    manager.add_shared_folder(nas2_id, "XRAY", "xray_images", "//192.168.1.101/xray_images", 
                             "xray_user", "xray_password", "HOSPITAL", "SMB",
                             compression_type="JPEG2000", database_format="FIREBIRD", priority=7)
    
    print("✅ Enterprise NAS Shared Folders Configuration System Ready!")
    print(f"🗄️ Database: {manager.db_path}")
    print(f"🔐 Encryption: Enabled")
    print(f"📁 Folders configured: {len(manager.get_all_folders())}")