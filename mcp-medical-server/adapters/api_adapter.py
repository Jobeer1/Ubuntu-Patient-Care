"""
API Adapter - REST API Access

Retrieves credentials from REST APIs and management interfaces.
Supports various authentication methods and vendor APIs.
"""

import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json

from .base_adapter import (
    BaseAdapter,
    ConnectionError,
    AuthenticationError,
    RetrievalError,
    EphemeralAccountError
)

logger = logging.getLogger(__name__)


class APIAdapter(BaseAdapter):
    """
    REST API adapter for credential retrieval
    
    Retrieves secrets from:
    - Vendor management APIs (Synology, QNAP, NetApp)
    - Custom REST APIs
    - Cloud management interfaces
    
    Authentication:
    - API keys
    - Bearer tokens
    - Basic auth
    - OAuth2
    
    Example:
        adapter = APIAdapter(config={
            "timeout_seconds": 30,
            "verify_ssl": True
        })
        
        adapter.connect(
            target={
                "base_url": "https://nas.local:5001",
                "api_version": "v1"
            },
            credentials={
                "api_key": "your_api_key",
                # OR
                "username": "admin",
                "password": "secret"
            }
        )
        
        secret = adapter.retrieve(
            path="/api/v1/secrets/database",
            method="GET"
        )
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize API adapter"""
        super().__init__(config)
        
        self.timeout_seconds = self.config.get("timeout_seconds", 30)
        self.verify_ssl = self.config.get("verify_ssl", True)
        self.max_retries = self.config.get("max_retries", 3)
        
        self.session = None
        self.base_url = None
        
        logger.info("APIAdapter initialized")

    
    def connect(self, target: Dict[str, Any], credentials: Dict[str, Any]) -> bool:
        """Connect to API endpoint"""
        try:
            self.base_url = target.get("base_url")
            api_version = target.get("api_version", "")
            
            if not self.base_url:
                raise ConnectionError("base_url is required")
            
            # Create session
            self.session = requests.Session()
            self.session.verify = self.verify_ssl
            
            # Setup authentication
            api_key = credentials.get("api_key")
            token = credentials.get("token")
            username = credentials.get("username")
            password = credentials.get("password")
            
            if api_key:
                self.session.headers.update({"X-API-Key": api_key})
            elif token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
            elif username and password:
                self.session.auth = (username, password)
            else:
                raise AuthenticationError("No valid authentication provided")
            
            # Test connection
            health_endpoint = target.get("health_endpoint", "/health")
            try:
                response = self.session.get(
                    f"{self.base_url}{health_endpoint}",
                    timeout=self.timeout_seconds
                )
                # Accept 200, 401, 404 (endpoint might not exist)
                if response.status_code not in [200, 401, 404]:
                    raise ConnectionError(f"Health check failed: {response.status_code}")
            except requests.exceptions.RequestException:
                # Health endpoint might not exist, continue anyway
                pass
            
            self.connected = True
            self._log_operation("connect", {"base_url": self.base_url})
            return True
            
        except Exception as e:
            logger.error(f"API connection failed: {e}")
            raise ConnectionError(f"Failed to connect to API: {e}")
    
    def retrieve(self, path: str, **options) -> bytes:
        """Retrieve data from API"""
        if not self.connected:
            raise RetrievalError("Not connected")
        
        try:
            method = options.get("method", "GET").upper()
            headers = options.get("headers", {})
            params = options.get("params", {})
            data = options.get("data")
            json_data = options.get("json")
            
            url = f"{self.base_url}{path}"
            
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json_data,
                timeout=self.timeout_seconds
            )
            
            if response.status_code not in [200, 201]:
                raise RetrievalError(
                    f"API request failed: {response.status_code} - {response.text}"
                )
            
            content = response.content
            
            # Extract specific key if requested
            extract_key = options.get("extract_key")
            if extract_key and response.headers.get("content-type", "").startswith("application/json"):
                data = response.json()
                value = self._extract_key(data, extract_key)
                content = str(value).encode("utf-8")
            
            self._log_operation("retrieve", {
                "path": path,
                "method": method,
                "status": response.status_code,
                "size_bytes": len(content)
            })
            
            return content
            
        except Exception as e:
            logger.error(f"API retrieval failed: {e}")
            raise RetrievalError(f"Failed to retrieve from API: {e}")
    
    def create_ephemeral_account(self, ttl_seconds: int, **options) -> Dict[str, Any]:
        """Create ephemeral account via API"""
        if not self.connected:
            raise EphemeralAccountError("Not connected")
        
        try:
            import secrets
            import string
            
            # Generate credentials
            username_prefix = options.get("username_prefix", "temp_")
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            username = f"{username_prefix}{timestamp}"
            
            alphabet = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(alphabet) for _ in range(16))
            
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            
            # Call API to create account
            endpoint = options.get("create_endpoint", "/api/users")
            payload = {
                "username": username,
                "password": password,
                "expires_at": expires_at.isoformat(),
                "ttl_seconds": ttl_seconds
            }
            
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                timeout=self.timeout_seconds
            )
            
            if response.status_code not in [200, 201]:
                raise EphemeralAccountError(
                    f"Account creation failed: {response.status_code}"
                )
            
            result = response.json()
            
            self._log_operation("create_ephemeral", {
                "username": username,
                "ttl_seconds": ttl_seconds
            })
            
            return {
                "username": username,
                "password": password,
                "expires_ts": expires_at.isoformat() + "Z",
                "account_id": result.get("id", username)
            }
            
        except Exception as e:
            logger.error(f"Ephemeral account creation failed: {e}")
            raise EphemeralAccountError(f"Failed to create account: {e}")
    
    def cleanup(self):
        """Close API session"""
        try:
            if self.session:
                self.session.close()
                self.session = None
            
            self.connected = False
            self._log_operation("cleanup", {})
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def _extract_key(self, data: Any, key_path: str) -> Any:
        """Extract value from nested JSON using dot notation"""
        keys = key_path.split(".")
        current = data
        
        for key in keys:
            if isinstance(current, dict):
                current = current[key]
            else:
                raise KeyError(f"Cannot extract '{key}' from {type(current)}")
        
        return current
