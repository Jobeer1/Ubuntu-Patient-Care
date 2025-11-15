"""
Base Adapter Interface

Abstract base class that all credential retrieval adapters must implement.
Provides standardized interface for connecting to targets, retrieving secrets,
creating ephemeral accounts, and cleanup.

All adapters must inherit from BaseAdapter and implement the abstract methods.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class AdapterError(Exception):
    """Base exception for adapter errors"""
    pass


class ConnectionError(AdapterError):
    """Raised when connection to target fails"""
    pass


class AuthenticationError(AdapterError):
    """Raised when authentication fails"""
    pass


class RetrievalError(AdapterError):
    """Raised when secret retrieval fails"""
    pass


class EphemeralAccountError(AdapterError):
    """Raised when ephemeral account creation fails"""
    pass


class BaseAdapter(ABC):
    """
    Abstract base class for all credential retrieval adapters
    
    All adapters must implement:
    - connect(): Establish connection to target
    - retrieve(): Retrieve secret/file by path
    - create_ephemeral_account(): Create temporary account (optional)
    - cleanup(): Disconnect and cleanup resources
    
    Adapters should:
    - Log all operations (without exposing secrets)
    - Handle errors gracefully
    - Enforce timeouts
    - Clean up resources in cleanup()
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize adapter with configuration
        
        Args:
            config: Adapter-specific configuration dictionary
        """
        self.config = config or {}
        self.connected = False
        self.connection = None
        logger.info(f"{self.__class__.__name__} initialized")
    
    @abstractmethod
    def connect(self, target: Dict[str, Any], credentials: Dict[str, Any]) -> bool:
        """
        Connect to target device/service
        
        Args:
            target: Target connection details
                Examples:
                - SSH: {"host": "192.168.1.10", "port": 22}
                - SMB: {"host": "nas.local", "share": "config"}
                - API: {"url": "https://api.example.com", "endpoint": "/secrets"}
            
            credentials: Authentication credentials
                Examples:
                - SSH: {"username": "admin", "password": "...", "key_path": "..."}
                - SMB: {"username": "admin", "password": "...", "domain": "..."}
                - API: {"api_key": "...", "token": "..."}
        
        Returns:
            True if connection successful, False otherwise
        
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        
        Example:
            adapter = SSHAdapter()
            success = adapter.connect(
                target={"host": "192.168.1.10", "port": 22},
                credentials={"username": "admin", "password": "secret"}
            )
        """
        pass
    
    @abstractmethod
    def retrieve(self, path: str, **options) -> bytes:
        """
        Retrieve secret/file by path
        
        Args:
            path: Path to secret/file on target
                Examples:
                - SSH: "/etc/myapp/credentials.conf"
                - SMB: "config/database.ini"
                - API: "/v1/secrets/db-password"
                - Files: "/mnt/nas/app/config.json"
            
            **options: Adapter-specific options
                Examples:
                - parse_format: "json", "yaml", "ini"
                - encoding: "utf-8", "latin-1"
                - extract_key: "database.password"
        
        Returns:
            Secret content as bytes
        
        Raises:
            RetrievalError: If retrieval fails
            FileNotFoundError: If path doesn't exist
            PermissionError: If access denied
        
        Example:
            secret = adapter.retrieve(
                path="/etc/app/db.conf",
                parse_format="ini",
                extract_key="database.password"
            )
        """
        pass
    
    @abstractmethod
    def create_ephemeral_account(
        self, 
        ttl_seconds: int,
        **options
    ) -> Dict[str, Any]:
        """
        Create temporary account with TTL
        
        This is used when credentials are not known and need to be created
        on-demand. The account should be automatically deleted after TTL.
        
        Args:
            ttl_seconds: Time-to-live in seconds
            **options: Adapter-specific options
                Examples:
                - username_prefix: "temp_"
                - permissions: ["read", "write"]
                - groups: ["users", "operators"]
        
        Returns:
            Dictionary with account details:
            {
                "username": "temp_user_12345",
                "password": "random_secure_password",
                "expires_ts": "2025-11-07T15:30:00Z",
                "account_id": "unique_id"
            }
        
        Raises:
            EphemeralAccountError: If account creation fails
            NotImplementedError: If adapter doesn't support ephemeral accounts
        
        Example:
            account = adapter.create_ephemeral_account(
                ttl_seconds=3600,  # 1 hour
                username_prefix="emergency_",
                permissions=["read"]
            )
        """
        pass
    
    @abstractmethod
    def cleanup(self):
        """
        Disconnect and cleanup resources
        
        This method should:
        - Close connections
        - Release resources
        - Delete temporary files
        - Log cleanup actions
        
        Should be called in finally block or context manager __exit__.
        Must not raise exceptions (catch and log instead).
        
        Example:
            try:
                adapter.connect(...)
                secret = adapter.retrieve(...)
            finally:
                adapter.cleanup()
        """
        pass
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup"""
        self.cleanup()
        return False
    
    def _log_operation(self, operation: str, details: Dict[str, Any]):
        """
        Log adapter operation (without exposing secrets)
        
        Args:
            operation: Operation name (e.g., "connect", "retrieve")
            details: Operation details (secrets will be redacted)
        """
        # Redact sensitive fields
        safe_details = self._redact_secrets(details)
        logger.info(f"{self.__class__.__name__}.{operation}: {safe_details}")
    
    def _redact_secrets(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive fields from data
        
        Args:
            data: Dictionary that may contain secrets
        
        Returns:
            Dictionary with secrets redacted
        """
        sensitive_keys = [
            "password", "secret", "token", "api_key", "private_key",
            "credentials", "auth", "passphrase"
        ]
        
        redacted = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = self._redact_secrets(value)
            else:
                redacted[key] = value
        
        return redacted
    
    def _enforce_timeout(self, timeout_seconds: Optional[int] = None):
        """
        Enforce operation timeout
        
        Args:
            timeout_seconds: Timeout in seconds (uses config default if None)
        """
        timeout = timeout_seconds or self.config.get("timeout_seconds", 30)
        # TODO: Implement timeout enforcement (asyncio.wait_for or signal.alarm)
        return timeout


# Example adapter implementation (for reference)
class ExampleAdapter(BaseAdapter):
    """
    Example adapter implementation
    
    This is a reference implementation showing how to use BaseAdapter.
    Real adapters should follow this pattern.
    """
    
    def connect(self, target: Dict[str, Any], credentials: Dict[str, Any]) -> bool:
        """Connect to example target"""
        try:
            self._log_operation("connect", {"target": target})
            # Simulate connection
            self.connection = {"target": target, "authenticated": True}
            self.connected = True
            return True
        except Exception as e:
            raise ConnectionError(f"Connection failed: {e}")
    
    def retrieve(self, path: str, **options) -> bytes:
        """Retrieve from example target"""
        if not self.connected:
            raise RetrievalError("Not connected")
        
        try:
            self._log_operation("retrieve", {"path": path, "options": options})
            # Simulate retrieval
            return b"example_secret_data"
        except Exception as e:
            raise RetrievalError(f"Retrieval failed: {e}")
    
    def create_ephemeral_account(self, ttl_seconds: int, **options) -> Dict[str, Any]:
        """Create ephemeral account on example target"""
        if not self.connected:
            raise EphemeralAccountError("Not connected")
        
        try:
            self._log_operation("create_ephemeral", {"ttl": ttl_seconds})
            # Simulate account creation
            return {
                "username": "temp_user_12345",
                "password": "random_password",
                "expires_ts": "2025-11-07T15:30:00Z",
                "account_id": "example_123"
            }
        except Exception as e:
            raise EphemeralAccountError(f"Account creation failed: {e}")
    
    def cleanup(self):
        """Cleanup example adapter"""
        try:
            if self.connected:
                self._log_operation("cleanup", {})
                self.connection = None
                self.connected = False
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
