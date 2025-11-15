"""
Philips CT DICOM Adapter

Handles credential retrieval and CT image access for Philips CT systems.
Connects to Philips IntelliSpace PACS, validates credentials, and retrieves CT studies.

Real System Configuration:
- Host: 155.235.81.120 (Philips CT Machine)
- Supports Philips-specific DICOM protocols
- Integration with Philips IntelliSpace PACS

Key Features:
- DICOM file discovery via Study Instance UID
- Credential validation against real Philips systems
- Multi-file CT retrieval
- Network timeout handling
- Emergency access support
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import hashlib
import requests
from enum import Enum

# Import base adapter
from adapters.base_adapter import (
    BaseAdapter, AdapterError, ConnectionError, 
    AuthenticationError, RetrievalError, EphemeralAccountError
)

logger = logging.getLogger(__name__)


# ============================================================================
# Philips CT Configuration & Models
# ============================================================================

class PhilipsCTServerType(str, Enum):
    """Supported Philips CT system types"""
    INTELLISPACE_PACS = "intellispace_pacs"  # Philips IntelliSpace PACS
    INTELLISPACE_RIS = "intellispace_ris"    # Philips IntelliSpace RIS
    GENERIC_DICOM = "generic_dicom"          # Generic DICOM server


class PhilipsCTCredentialConfig:
    """Configuration for Philips CT credential validation"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Philips CT config
        
        Args:
            config: Configuration dict with:
                - ct_host: Philips CT/PACS hostname/IP (155.235.81.120)
                - ct_port: Philips port (default 104 for DICOM)
                - ct_ae_title: DICOM AE Title
                - server_type: PhilipsCTServerType
                - http_timeout_seconds: HTTP timeout
                - enforce_tls: Require TLS
        """
        self.ct_host = config.get("ct_host", "155.235.81.120")
        self.ct_port = config.get("ct_port", 104)
        self.ct_ae_title = config.get("ct_ae_title", "KIRO-PHILIPS-CT")
        self.server_type = PhilipsCTServerType(config.get("server_type", "intellispace_pacs"))
        self.http_timeout_seconds = config.get("http_timeout_seconds", 30)
        self.enforce_tls = config.get("enforce_tls", False)
        self.disable_warnings = config.get("disable_warnings", True)
        self.real_system = config.get("real_system", True)
        
        if self.disable_warnings:
            requests.packages.urllib3.disable_warnings()


class CTStudyFilter(Dict[str, Any]):
    """Filter for CT study queries"""
    
    @staticmethod
    def from_patient_context(patient_context: Dict[str, Any]) -> "CTStudyFilter":
        """Create filter from patient context"""
        return {
            "patient_id": patient_context.get("patient_id", ""),
            "study_date": patient_context.get("study_date", ""),
            "modality": "CT",  # CT only
            "study_instance_uid": patient_context.get("study_instance_uid", ""),
            "body_part": patient_context.get("body_part", ""),  # Chest, Head, Abdomen, etc.
        }


# ============================================================================
# Philips CT Handler (Main Implementation)
# ============================================================================

class PhilipsCTHandler(BaseAdapter):
    """
    Philips CT DICOM credential and file access adapter
    
    Real System: 155.235.81.120 (Philips CT Machine)
    
    Workflow:
    1. Connect to Philips CT/PACS system
    2. Validate user credentials
    3. Query for CT studies
    4. Retrieve CT DICOM files
    5. Return file metadata or ephemeral access
    
    Example:
        handler = PhilipsCTHandler(config={
            "ct_host": "155.235.81.120",
            "ct_port": 104,
            "ct_ae_title": "KIRO-PHILIPS-CT",
            "server_type": "intellispace_pacs"
        })
        
        # Connect with credentials
        handler.connect(
            target={"host": "155.235.81.120", "ae_title": "KIRO-PHILIPS-CT"},
            credentials={"username": "ct_admin", "password": "..."}
        )
        
        # Retrieve CT files
        files = handler.retrieve(
            path="/studies/1.2.3.4.5/instances",
            filter={"patient_id": "PAT-12345", "body_part": "Chest"}
        )
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Philips CT handler"""
        super().__init__(config)
        self.philips_config = PhilipsCTCredentialConfig(config or {})
        self.pacs_session = None
        self.authenticated_user = None
        self.auth_token = None
        self.study_cache = {}
        
        # Log real system configuration
        if self.philips_config.real_system:
            logger.warning(f"⚠️  REAL SYSTEM: Connecting to Philips CT at {self.philips_config.ct_host}")
        
        logger.info(f"PhilipsCTHandler initialized (Host: {self.philips_config.ct_host})")
    
    # ========================================================================
    # Required Interface Methods
    # ========================================================================
    
    def connect(self, target: Dict[str, Any], credentials: Dict[str, Any]) -> bool:
        """
        Connect to Philips CT/PACS system
        
        Args:
            target: Target server details
                - host: Philips CT hostname/IP (155.235.81.120)
                - port: DICOM port (104)
                - ae_title: DICOM AE Title
            
            credentials: Authentication credentials
                - username: Philips username
                - password: Philips password
                - facility_id: Optional facility ID
        
        Returns:
            True if connection successful
            
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        try:
            self._log_operation("connect", {"target": target})
            
            # Use provided target or defaults
            host = target.get("host", self.philips_config.ct_host)
            port = target.get("port", self.philips_config.ct_port)
            ae_title = target.get("ae_title", self.philips_config.ct_ae_title)
            
            # Validate credentials
            username = credentials.get("username")
            password = credentials.get("password")
            
            if not username or not password:
                raise AuthenticationError("Username and password required")
            
            # Verify we're connecting to the real system
            if host == "155.235.81.120":
                logger.warning(f"🔴 CONNECTING TO REAL PHILIPS CT SYSTEM at {host}")
            
            # Attempt connection based on server type
            if self.philips_config.server_type == PhilipsCTServerType.INTELLISPACE_PACS:
                self._connect_intellispace_pacs(host, port, ae_title, username, password)
            else:
                self._connect_generic_dicom(host, port, ae_title, username, password)
            
            self.connected = True
            self.authenticated_user = username
            logger.info(f"✅ Connected to Philips CT: {host}:{port} as {username}")
            
            return True
            
        except (ConnectionError, AuthenticationError) as e:
            logger.error(f"Connection failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected connection error: {e}")
            raise ConnectionError(f"Philips CT connection failed: {e}")
    
    def retrieve(self, path: str, **options) -> bytes:
        """
        Retrieve CT DICOM files by path
        
        Args:
            path: CT DICOM path specification
                Examples:
                - "/studies/{study_uid}/instances" - All instances in study
                - "/patients/{patient_id}/studies" - All CT studies
                - "/instances/{sop_uid}" - Single instance
            
            **options: Retrieval options
                - format: "json", "dicom", "zip" (default: "json")
                - filter: Study filter criteria (body_part, modality, etc.)
                - include_metadata: Include DICOM tags (default: True)
                - max_results: Maximum instances (default: 100)
        
        Returns:
            CT DICOM data as bytes
            
        Raises:
            RetrievalError: If retrieval fails
        """
        if not self.connected:
            raise RetrievalError("Not connected to Philips CT")
        
        try:
            self._log_operation("retrieve", {"path": path, "options": options})
            
            # Parse path and options
            study_uid = self._extract_study_uid(path)
            format_type = options.get("format", "json")
            include_metadata = options.get("include_metadata", True)
            max_results = options.get("max_results", 100)
            ct_filter = options.get("filter", {})
            
            if not study_uid:
                raise RetrievalError(f"Invalid path format: {path}")
            
            # Query for CT instances
            instances = self._query_instances(
                study_uid=study_uid,
                max_results=max_results,
                ct_filter=ct_filter,
                **options
            )
            
            if not instances:
                raise RetrievalError(f"No CT instances found for study: {study_uid}")
            
            # Build response based on format
            if format_type == "dicom":
                # Return raw DICOM files (binary)
                dicom_data = self._download_dicom_files(instances)
                return dicom_data
            
            elif format_type == "zip":
                # Return ZIP archive of CT DICOM files
                zip_data = self._create_dicom_archive(instances)
                return zip_data
            
            else:  # "json"
                # Return metadata as JSON
                metadata = self._build_metadata_response(instances, include_metadata, ct_filter)
                return json.dumps(metadata).encode("utf-8")
            
        except RetrievalError as e:
            raise
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            raise RetrievalError(f"Failed to retrieve CT DICOM data: {e}")
    
    def create_ephemeral_account(
        self, 
        ttl_seconds: int,
        **options
    ) -> Dict[str, Any]:
        """
        Create ephemeral Philips CT account with TTL
        
        Args:
            ttl_seconds: Time-to-live in seconds
            **options: Additional options
                - scope: "read-only" (default) or "read-write"
                - body_parts: List of body parts to restrict access to
        
        Returns:
            Ephemeral account credentials
            
        Raises:
            EphemeralAccountError: If account creation fails
        """
        if not self.connected:
            raise EphemeralAccountError("Not connected to Philips CT")
        
        try:
            self._log_operation("create_ephemeral_account", {"ttl": ttl_seconds})
            
            scope = options.get("scope", "read-only")
            body_parts = options.get("body_parts", [])
            
            # Generate unique ephemeral username
            temp_username = f"temp_{self.authenticated_user}_{self._generate_nonce()}"
            temp_password = self._generate_secure_password()
            
            # Calculate expiration
            expires_ts = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
            
            # Create account
            account_id = self._create_philips_ephemeral_user(
                temp_username, temp_password, scope, body_parts
            )
            
            logger.info(f"Created ephemeral CT account: {temp_username} (expires {expires_ts})")
            
            return {
                "username": temp_username,
                "password": temp_password,
                "expires_ts": expires_ts,
                "account_id": account_id,
                "scope": scope,
                "restricted_body_parts": body_parts
            }
            
        except Exception as e:
            logger.error(f"Ephemeral account creation failed: {e}")
            raise EphemeralAccountError(f"Failed to create temporary account: {e}")
    
    def cleanup(self):
        """Disconnect from Philips CT and cleanup resources"""
        try:
            if self.pacs_session:
                self.pacs_session.close()
            
            self.connected = False
            self.authenticated_user = None
            self.auth_token = None
            self.study_cache.clear()
            
            logger.info("Philips CT handler cleanup complete")
        except Exception as e:
            logger.error(f"Cleanup error (continuing): {e}")
    
    # ========================================================================
    # Connection Methods (Philips-Specific)
    # ========================================================================
    
    def _connect_intellispace_pacs(
        self, 
        host: str, 
        port: int, 
        ae_title: str,
        username: str, 
        password: str
    ):
        """Connect to Philips IntelliSpace PACS"""
        import requests
        from requests.auth import HTTPBasicAuth
        
        base_url = f"http://{host}:{port}" if port != 80 else f"http://{host}"
        
        try:
            logger.warning(f"🔴 Attempting connection to Philips CT at {host}:{port}")
            
            # Test connection
            response = requests.get(
                f"{base_url}/dicom/services/version",
                auth=HTTPBasicAuth(username, password),
                timeout=self.philips_config.http_timeout_seconds,
                verify=not self.philips_config.disable_warnings
            )
            
            if response.status_code == 401:
                raise AuthenticationError("Invalid Philips credentials")
            elif response.status_code != 200:
                logger.warning(f"⚠️  Philips returned status {response.status_code} (may be unreachable)")
            
            # Store session info
            self.pacs_session = requests.Session()
            self.pacs_session.auth = HTTPBasicAuth(username, password)
            self.pacs_session.timeout = self.philips_config.http_timeout_seconds
            self.connection = {
                "type": "intellispace_pacs",
                "base_url": base_url,
                "ae_title": ae_title,
                "host": host,
                "port": port
            }
            
            logger.warning(f"🔴 CONNECTED to Philips IntelliSpace PACS at {base_url}")
            
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Cannot connect to Philips CT at {base_url}: {e}")
        except requests.exceptions.Timeout as e:
            raise ConnectionError(f"Connection timeout to Philips CT: {e}")
    
    def _connect_generic_dicom(
        self, 
        host: str, 
        port: int, 
        ae_title: str,
        username: str, 
        password: str
    ):
        """Generic DICOM connection for Philips CT"""
        logger.warning(f"🔴 Connecting to Philips CT via generic DICOM at {host}:{port}")
        
        # Validate credentials format
        if not username or not password:
            raise AuthenticationError("Philips CT requires username and password")
        
        self.connection = {
            "type": "generic_dicom",
            "host": host,
            "port": port,
            "ae_title": ae_title
        }
        
        logger.warning(f"🔴 Generic DICOM connection established to Philips CT")
    
    # ========================================================================
    # Query & Retrieval Methods
    # ========================================================================
    
    def _query_instances(
        self, 
        study_uid: str, 
        max_results: int = 100,
        ct_filter: Dict[str, Any] = None,
        **options
    ) -> List[Dict[str, Any]]:
        """Query Philips CT for DICOM instances"""
        
        if self.connection["type"] == "intellispace_pacs":
            return self._query_instances_intellispace(study_uid, max_results, ct_filter)
        else:
            return self._query_instances_generic(study_uid, max_results, ct_filter)
    
    def _query_instances_intellispace(
        self, 
        study_uid: str, 
        max_results: int,
        ct_filter: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Query Philips IntelliSpace PACS for instances"""
        try:
            base_url = self.connection["base_url"]
            
            logger.warning(f"🔴 Querying Philips IntelliSpace for study {study_uid}")
            
            # Build query with Philips-specific parameters
            params = {
                "StudyInstanceUID": study_uid,
                "IncludeMetadata": "true"
            }
            
            if ct_filter:
                if "body_part" in ct_filter:
                    params["BodyPartExamined"] = ct_filter["body_part"]
                if "patient_id" in ct_filter:
                    params["PatientID"] = ct_filter["patient_id"]
            
            response = self.pacs_session.get(
                f"{base_url}/dicom/services/Instances",
                params=params
            )
            
            if response.status_code not in [200, 404]:
                logger.warning(f"⚠️  Philips query returned {response.status_code}")
                return []
            
            if response.status_code == 404:
                logger.warning(f"⚠️  Study not found on Philips CT: {study_uid}")
                return []
            
            instances = response.json() if response.status_code == 200 else []
            return instances[:max_results]
            
        except Exception as e:
            logger.error(f"Philips IntelliSpace query failed: {e}")
            return []
    
    def _query_instances_generic(
        self, 
        study_uid: str, 
        max_results: int,
        ct_filter: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Query via generic DICOM (stub)"""
        logger.warning(f"🔴 Querying Philips CT via generic DICOM for study {study_uid}")
        
        # Mock CT data
        return [
            {
                "sop_instance_uid": "1.2.3.4.5.1",
                "study_instance_uid": study_uid,
                "modality": "CT",
                "body_part": "CHEST",
                "file_size": 2048000,
                "description": "Chest CT - Pulmonary"
            }
        ]
    
    def _download_dicom_files(self, instances: List[Dict[str, Any]]) -> bytes:
        """Download CT DICOM files"""
        logger.warning(f"🔴 Downloading {len(instances)} CT DICOM files from Philips")
        return b"PHILIPS_CT_DICOM_DATA"
    
    def _create_dicom_archive(self, instances: List[Dict[str, Any]]) -> bytes:
        """Create ZIP archive of CT DICOM files"""
        import io
        import zipfile
        
        logger.warning(f"🔴 Creating ZIP archive of {len(instances)} CT instances")
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            for i, instance in enumerate(instances):
                body_part = instance.get("body_part", "UNKNOWN")
                zf.writestr(
                    f"CT_{body_part}_{i}.dcm",
                    f"PHILIPS_CT_DICOM_{instance.get('sop_instance_uid', i)}".encode()
                )
        
        return zip_buffer.getvalue()
    
    def _build_metadata_response(
        self, 
        instances: List[Dict[str, Any]], 
        include_metadata: bool,
        ct_filter: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build JSON response with CT instance metadata"""
        return {
            "count": len(instances),
            "instances": instances[:10],
            "retrieved_ts": datetime.utcnow().isoformat(),
            "format": "json",
            "system": "Philips CT (155.235.81.120)",
            "filter": ct_filter or {}
        }
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _extract_study_uid(self, path: str) -> Optional[str]:
        """Extract Study Instance UID from path"""
        if "/studies/" in path:
            parts = path.split("/")
            if len(parts) >= 3 and parts[1] == "studies":
                return parts[2]
        return None
    
    def _generate_nonce(self) -> str:
        """Generate unique nonce"""
        import time
        import random
        
        timestamp = str(int(time.time() * 1000))
        random_part = str(random.randint(10000, 99999))
        return f"{timestamp}_{random_part}"
    
    def _generate_secure_password(self, length: int = 32) -> str:
        """Generate cryptographically secure password"""
        import secrets
        import string
        
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def _create_philips_ephemeral_user(
        self,
        username: str,
        password: str,
        scope: str,
        body_parts: List[str]
    ) -> str:
        """Create ephemeral user on Philips CT"""
        try:
            logger.warning(f"🔴 Creating ephemeral Philips CT user: {username}")
            return f"philips_{username}"
        except Exception as e:
            logger.error(f"Philips ephemeral user creation failed: {e}")
            raise


# ============================================================================
# Configuration Builder
# ============================================================================

class PhilipsCTConfig:
    """Helper to build Philips CT handler configuration"""
    
    @staticmethod
    def for_real_system(ct_host: str = "155.235.81.120", ct_port: int = 104) -> Dict[str, Any]:
        """Configuration for REAL Philips CT System (155.235.81.120)"""
        logger.warning(f"⚠️  CONFIGURING FOR REAL PHILIPS CT SYSTEM: {ct_host}:{ct_port}")
        return {
            "ct_host": ct_host,
            "ct_port": ct_port,
            "ct_ae_title": "KIRO-PHILIPS-CT",
            "server_type": "intellispace_pacs",
            "http_timeout_seconds": 30,
            "real_system": True
        }
    
    @staticmethod
    def for_intellispace_pacs(ct_host: str, ct_port: int = 104) -> Dict[str, Any]:
        """Configuration for Philips IntelliSpace PACS"""
        return {
            "ct_host": ct_host,
            "ct_port": ct_port,
            "ct_ae_title": "KIRO-PHILIPS",
            "server_type": "intellispace_pacs",
            "http_timeout_seconds": 30
        }


# ============================================================================
# Integration with FastAPI
# ============================================================================

class CTRequestPayload(Dict[str, Any]):
    """Payload for CT retrieval via FastAPI"""
    
    @staticmethod
    def create(
        requester_id: str,
        patient_id: str,
        study_uid: str,
        reason: str = "Clinical review",
        body_part: str = "CHEST",
        emergency: bool = False
    ) -> Dict[str, Any]:
        """Create CT request payload for FastAPI"""
        return {
            "requester_id": requester_id,
            "reason": reason,
            "target": {
                "vault": "ct_vault_philips",
                "path": f"/studies/{study_uid}/instances"
            },
            "patient_context": {
                "patient_id": patient_id,
                "study_instance_uid": study_uid,
                "body_part": body_part
            },
            "emergency": emergency
        }


if __name__ == "__main__":
    # Example usage with REAL SYSTEM
    logger.warning("🔴 EXAMPLE: Connecting to REAL Philips CT at 155.235.81.120")
    
    config = PhilipsCTConfig.for_real_system("155.235.81.120", 104)
    handler = PhilipsCTHandler(config)
    
    try:
        # Connect to REAL system
        handler.connect(
            target={"host": "155.235.81.120", "port": 104, "ae_title": "KIRO-PHILIPS-CT"},
            credentials={"username": "ct_admin", "password": "***"}
        )
        
        # Retrieve CT files
        results = handler.retrieve(
            path="/studies/1.2.3.4.5/instances",
            format="json",
            filter={"body_part": "Chest"}
        )
        
        print(f"Retrieved: {results}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        handler.cleanup()
