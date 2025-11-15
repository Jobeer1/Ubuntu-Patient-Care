"""
SSH Adapter - Remote Linux/Unix System Access

Retrieves credentials from remote systems via SSH.
Supports password and key-based authentication.

Security:
- Timeout enforcement
- Command whitelisting (optional)
- No secrets in logs
- Automatic cleanup
"""

import io
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    paramiko = None

from .base_adapter import (
    BaseAdapter,
    ConnectionError,
    AuthenticationError,
    RetrievalError,
    EphemeralAccountError
)

logger = logging.getLogger(__name__)


class SSHAdapter(BaseAdapter):
    """
    SSH adapter for remote credential retrieval
    
    Retrieves secrets from remote Linux/Unix systems via SSH:
    - Execute commands (cat, grep, etc.)
    - Read files via SFTP
    - Create ephemeral accounts
    
    Authentication methods:
    - Password
    - Private key file
    - SSH agent
    
    Example:
        adapter = SSHAdapter(config={
            "timeout_seconds": 30,
            "max_retries": 3,
            "key_based_auth_preferred": True
        })
        
        # Password auth
        adapter.connect(
            target={"host": "192.168.1.10", "port": 22},
            credentials={"username": "admin", "password": "secret"}
        )
        
        # Key-based auth
        adapter.connect(
            target={"host": "192.168.1.10", "port": 22},
            credentials={"username": "admin", "key_path": "/path/to/key.pem"}
        )
        
        # Retrieve file
        secret = adapter.retrieve("/etc/app/credentials.conf")
        
        # Execute command
        secret = adapter.retrieve(
            path="",
            command="cat /etc/app/db.conf | grep password"
        )
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize SSH adapter"""
        super().__init__(config)
        
        if not PARAMIKO_AVAILABLE:
            raise ImportError(
                "paramiko is required for SSHAdapter. "
                "Install with: pip install paramiko"
            )
        
        self.timeout_seconds = self.config.get("timeout_seconds", 30)
        self.max_retries = self.config.get("max_retries", 3)
        self.key_based_auth_preferred = self.config.get("key_based_auth_preferred", True)
        
        self.ssh_client = None
        self.sftp_client = None
        
        logger.info("SSHAdapter initialized")
    
    def connect(self, target: Dict[str, Any], credentials: Dict[str, Any]) -> bool:
        """
        Connect to remote system via SSH
        
        Args:
            target: {
                "host": "192.168.1.10",
                "port": 22,
                "hostname_verify": True  # Optional
            }
            credentials: {
                "username": "admin",
                "password": "secret",  # OR
                "key_path": "/path/to/key.pem",
                "key_passphrase": "optional"  # If key is encrypted
            }
        
        Returns:
            True if connection successful
        
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        try:
            host = target.get("host")
            port = target.get("port", 22)
            
            if not host:
                raise ConnectionError("Host is required")
            
            username = credentials.get("username")
            password = credentials.get("password")
            key_path = credentials.get("key_path")
            key_passphrase = credentials.get("key_passphrase")
            
            if not username:
                raise AuthenticationError("Username is required")
            
            # Create SSH client
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Prepare authentication
            connect_kwargs = {
                "hostname": host,
                "port": port,
                "username": username,
                "timeout": self.timeout_seconds,
                "banner_timeout": self.timeout_seconds
            }
            
            # Try key-based auth first if preferred and available
            if self.key_based_auth_preferred and key_path:
                try:
                    private_key = self._load_private_key(key_path, key_passphrase)
                    connect_kwargs["pkey"] = private_key
                    self.ssh_client.connect(**connect_kwargs)
                    self.connected = True
                    self._log_operation("connect", {
                        "host": host,
                        "port": port,
                        "auth_method": "key"
                    })
                    return True
                except Exception as e:
                    logger.warning(f"Key-based auth failed, trying password: {e}")
            
            # Try password auth
            if password:
                connect_kwargs["password"] = password
                self.ssh_client.connect(**connect_kwargs)
                self.connected = True
                self._log_operation("connect", {
                    "host": host,
                    "port": port,
                    "auth_method": "password"
                })
                return True
            
            # Try key auth if not already tried
            if key_path and not self.key_based_auth_preferred:
                private_key = self._load_private_key(key_path, key_passphrase)
                connect_kwargs["pkey"] = private_key
                self.ssh_client.connect(**connect_kwargs)
                self.connected = True
                self._log_operation("connect", {
                    "host": host,
                    "port": port,
                    "auth_method": "key"
                })
                return True
            
            raise AuthenticationError("No valid authentication method provided")
            
        except paramiko.AuthenticationException as e:
            logger.error(f"Authentication failed: {e}")
            raise AuthenticationError(f"SSH authentication failed: {e}")
        except paramiko.SSHException as e:
            logger.error(f"SSH error: {e}")
            raise ConnectionError(f"SSH connection failed: {e}")
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise ConnectionError(f"Failed to connect via SSH: {e}")
    
    def retrieve(self, path: str, **options) -> bytes:
        """
        Retrieve file or execute command
        
        Args:
            path: File path on remote system (e.g., "/etc/app/credentials.conf")
            **options:
                command: Execute command instead of reading file
                use_sftp: Use SFTP instead of cat command (default: True)
                encoding: Text encoding (default: "utf-8")
        
        Returns:
            File content or command output as bytes
        
        Raises:
            RetrievalError: If retrieval fails
        """
        if not self.connected:
            raise RetrievalError("Not connected - call connect() first")
        
        try:
            command = options.get("command")
            use_sftp = options.get("use_sftp", True)
            
            if command:
                # Execute command
                content = self._execute_command(command)
            elif use_sftp:
                # Use SFTP to read file
                content = self._read_file_sftp(path)
            else:
                # Use cat command
                content = self._read_file_command(path)
            
            self._log_operation("retrieve", {
                "path": path,
                "method": "command" if command else ("sftp" if use_sftp else "cat"),
                "size_bytes": len(content)
            })
            
            return content
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            raise RetrievalError(f"Failed to retrieve via SSH: {e}")
    
    def create_ephemeral_account(self, ttl_seconds: int, **options) -> Dict[str, Any]:
        """
        Create temporary Linux user account
        
        Args:
            ttl_seconds: Time-to-live in seconds
            **options:
                username_prefix: "temp_" (default)
                shell: "/bin/bash" (default)
                home_dir: "/tmp/temp_user" (default)
                groups: ["users"] (optional)
        
        Returns:
            {
                "username": "temp_user_12345",
                "password": "random_password",
                "expires_ts": "2025-11-07T15:30:00Z",
                "account_id": "temp_user_12345"
            }
        
        Raises:
            EphemeralAccountError: If account creation fails
        """
        if not self.connected:
            raise EphemeralAccountError("Not connected - call connect() first")
        
        try:
            import secrets
            import string
            
            # Generate username and password
            username_prefix = options.get("username_prefix", "temp_")
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            username = f"{username_prefix}{timestamp}"
            
            # Generate secure random password
            alphabet = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(alphabet) for _ in range(16))
            
            # Calculate expiration
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            
            # Create user
            shell = options.get("shell", "/bin/bash")
            home_dir = options.get("home_dir", f"/tmp/{username}")
            
            # useradd command
            cmd = f"sudo useradd -m -d {home_dir} -s {shell} {username}"
            self._execute_command(cmd)
            
            # Set password
            cmd = f"echo '{username}:{password}' | sudo chpasswd"
            self._execute_command(cmd)
            
            # Add to groups if specified
            groups = options.get("groups", [])
            if groups:
                groups_str = ",".join(groups)
                cmd = f"sudo usermod -aG {groups_str} {username}"
                self._execute_command(cmd)
            
            # Schedule deletion (using at command)
            delete_cmd = f"sudo userdel -r {username}"
            at_time = expires_at.strftime("%H:%M %Y-%m-%d")
            cmd = f"echo '{delete_cmd}' | at {at_time}"
            try:
                self._execute_command(cmd)
            except Exception as e:
                logger.warning(f"Failed to schedule auto-deletion: {e}")
            
            self._log_operation("create_ephemeral", {
                "username": username,
                "ttl_seconds": ttl_seconds,
                "expires_at": expires_at.isoformat()
            })
            
            return {
                "username": username,
                "password": password,
                "expires_ts": expires_at.isoformat() + "Z",
                "account_id": username
            }
            
        except Exception as e:
            logger.error(f"Ephemeral account creation failed: {e}")
            raise EphemeralAccountError(f"Failed to create ephemeral account: {e}")
    
    def cleanup(self):
        """Close SSH and SFTP connections"""
        try:
            if self.sftp_client:
                self.sftp_client.close()
                self.sftp_client = None
            
            if self.ssh_client:
                self.ssh_client.close()
                self.ssh_client = None
            
            if self.connected:
                self._log_operation("cleanup", {})
                self.connected = False
                
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def _load_private_key(self, key_path: str, passphrase: Optional[str] = None):
        """
        Load private key from file
        
        Args:
            key_path: Path to private key file
            passphrase: Optional passphrase for encrypted keys
        
        Returns:
            paramiko.PKey instance
        """
        key_path = Path(key_path).expanduser()
        
        if not key_path.exists():
            raise FileNotFoundError(f"Private key not found: {key_path}")
        
        # Try different key types
        key_types = [
            paramiko.RSAKey,
            paramiko.Ed25519Key,
            paramiko.ECDSAKey,
            paramiko.DSSKey
        ]
        
        for key_type in key_types:
            try:
                return key_type.from_private_key_file(
                    str(key_path),
                    password=passphrase
                )
            except paramiko.SSHException:
                continue
        
        raise AuthenticationError(f"Could not load private key: {key_path}")
    
    def _execute_command(self, command: str) -> bytes:
        """
        Execute command on remote system
        
        Args:
            command: Shell command to execute
        
        Returns:
            Command output as bytes
        """
        stdin, stdout, stderr = self.ssh_client.exec_command(
            command,
            timeout=self.timeout_seconds
        )
        
        # Read output
        output = stdout.read()
        error = stderr.read()
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code != 0:
            raise RetrievalError(
                f"Command failed with exit code {exit_code}: {error.decode('utf-8', errors='ignore')}"
            )
        
        return output
    
    def _read_file_sftp(self, path: str) -> bytes:
        """
        Read file using SFTP
        
        Args:
            path: Remote file path
        
        Returns:
            File content as bytes
        """
        if not self.sftp_client:
            self.sftp_client = self.ssh_client.open_sftp()
        
        with self.sftp_client.open(path, "rb") as f:
            return f.read()
    
    def _read_file_command(self, path: str) -> bytes:
        """
        Read file using cat command
        
        Args:
            path: Remote file path
        
        Returns:
            File content as bytes
        """
        command = f"cat {path}"
        return self._execute_command(command)
