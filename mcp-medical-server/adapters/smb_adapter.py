"""
SMB Adapter - Windows Shares and NAS Access

Retrieves credentials from SMB/CIFS shares (Windows, NAS devices).
Supports SMB2/SMB3 protocols with authentication.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

try:
    from smbprotocol.connection import Connection
    from smbprotocol.session import Session
    from smbprotocol.tree import TreeConnect
    from smbprotocol.open import Open, CreateDisposition, FileAttributes
    from smbprotocol.file_info import FileStandardInformation
    SMB_AVAILABLE = True
except ImportError:
    SMB_AVAILABLE = False

from .base_adapter import (
    BaseAdapter,
    ConnectionError,
    AuthenticationError,
    RetrievalError,
    EphemeralAccountError
)

logger = logging.getLogger(__name__)


class SMBAdapter(BaseAdapter):
    """
    SMB/CIFS adapter for network share access
    
    Retrieves secrets from:
    - Windows file shares
    - NAS devices (Synology, QNAP, etc.)
    - Samba shares
    
    Authentication:
    - Username/password
    - Domain authentication
    - NTLMv2
    
    Example:
        adapter = SMBAdapter(config={"timeout_seconds": 30})
        
        adapter.connect(
            target={
                "host": "nas.local",
                "share": "config",
                "port": 445
            },
            credentials={
                "username": "admin",
                "password": "secret",
                "domain": "WORKGROUP"  # Optional
            }
        )
        
        secret = adapter.retrieve("app/database.conf")
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize SMB adapter"""
        super().__init__(config)
        
        if not SMB_AVAILABLE:
            raise ImportError(
                "smbprotocol is required for SMBAdapter. "
                "Install with: pip install smbprotocol"
            )
        
        self.timeout_seconds = self.config.get("timeout_seconds", 30)
        self.protocol_version = self.config.get("protocol_version", "SMB3")
        
        self.connection = None
        self.session = None
        self.tree = None
        self.host = None
        self.share = None
        
        logger.info("SMBAdapter initialized")

    
    def connect(self, target: Dict[str, Any], credentials: Dict[str, Any]) -> bool:
        """Connect to SMB share"""
        try:
            self.host = target.get("host")
            self.share = target.get("share")
            port = target.get("port", 445)
            
            if not self.host or not self.share:
                raise ConnectionError("Host and share are required")
            
            username = credentials.get("username")
            password = credentials.get("password")
            domain = credentials.get("domain", "")
            
            if not username or not password:
                raise AuthenticationError("Username and password required")
            
            # Create connection
            self.connection = Connection(
                uuid.uuid4(),
                self.host,
                port
            )
            self.connection.connect()
            
            # Create session
            self.session = Session(
                self.connection,
                username,
                password,
                domain_name=domain
            )
            self.session.connect()
            
            # Connect to share
            tree_path = f"\\\\{self.host}\\{self.share}"
            self.tree = TreeConnect(self.session, tree_path)
            self.tree.connect()
            
            self.connected = True
            self._log_operation("connect", {
                "host": self.host,
                "share": self.share,
                "port": port
            })
            return True
            
        except Exception as e:
            logger.error(f"SMB connection failed: {e}")
            raise ConnectionError(f"Failed to connect to SMB share: {e}")
    
    def retrieve(self, path: str, **options) -> bytes:
        """Retrieve file from SMB share"""
        if not self.connected:
            raise RetrievalError("Not connected")
        
        try:
            # Open file
            file_open = Open(self.tree, path)
            file_open.create(
                CreateDisposition.FILE_OPEN,
                FileAttributes.FILE_ATTRIBUTE_NORMAL
            )
            
            # Get file size
            info = FileStandardInformation()
            info.unpack(file_open.query_info(info))
            file_size = info['end_of_file'].get_value()
            
            # Read file
            content = file_open.read(0, file_size)
            file_open.close()
            
            self._log_operation("retrieve", {
                "path": path,
                "size_bytes": len(content)
            })
            
            return content
            
        except Exception as e:
            logger.error(f"SMB retrieval failed: {e}")
            raise RetrievalError(f"Failed to retrieve from SMB: {e}")
    
    def create_ephemeral_account(self, ttl_seconds: int, **options) -> Dict[str, Any]:
        """Not supported for SMB adapter"""
        raise NotImplementedError(
            "SMBAdapter does not support ephemeral account creation"
        )
    
    def cleanup(self):
        """Close SMB connections"""
        try:
            if self.tree:
                self.tree.disconnect()
            if self.session:
                self.session.disconnect()
            if self.connection:
                self.connection.disconnect()
            
            self.connected = False
            self._log_operation("cleanup", {})
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
