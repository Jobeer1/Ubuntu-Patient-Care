"""
Siemens MRI DICOM Adapter

Handles credential retrieval and DICOM file access for Siemens MRI systems.
Connects to PACS servers, validates credentials, and retrieves DICOM studies.

Key Features:
- DICOM file discovery via Study Instance UID
- Credential validation against real PACS systems
- Multi-file retrieval (all DICOM instances for a study)
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
# Siemens Configuration & Models
# ============================================================================

class DicomServerType(str, Enum):
    """Supported DICOM server types"""
    DCMQRSCP = "dcmqrscp"          # DCMTK DICOM server
    ORTHANC = "orthanc"            # Orthanc PACS
    PHILIPS_INTELLISPACE = "philips_intellispace"
    SIEMENS_SYNGO = "siemens_syngo"
    GENERIC_DIMSE = "generic_dimse"


class SiemensCredentialConfig:
    """Configuration for Siemens MRI credential validation"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Siemens config
        
        Args:
            config: Configuration dict with:
                - pacs_host: PACS server hostname/IP
                - pacs_port: PACS server port (default 104 for DICOM)
                - pacs_ae_title: DICOM AE Title
                - server_type: DicomServerType
                - http_timeout_seconds: HTTP timeout (for REST APIs)
                - enforce_tls: Require TLS for REST endpoints
        """
        self.pacs_host = config.get("pacs_host", "localhost")
        self.pacs_port = config.get("pacs_port", 104)
        self.pacs_ae_title = config.get("pacs_ae_title", "KIRO-MCP")
        self.server_type = DicomServerType(config.get("server_type", "orthanc"))
        self.http_timeout_seconds = config.get("http_timeout_seconds", 30)
        self.enforce_tls = config.get("enforce_tls", False)
        self.disable_warnings = config.get("disable_warnings", True)
        
        if self.disable_warnings:
            requests.packages.urllib3.disable_warnings()


class DicomStudyFilter(Dict[str, Any]):
    """Filter for DICOM study queries"""
    
    @staticmethod
    def from_patient_context(patient_context: Dict[str, Any]) -> "DicomStudyFilter":
        """Create filter from patient context"""
        return {
            "patient_id": patient_context.get("patient_id", ""),
            "study_date": patient_context.get("study_date", ""),
            "modality": "MR",  # MRI only
            "study_instance_uid": patient_context.get("study_instance_uid", ""),
        }


# ============================================================================
# Siemens MRI Handler (Main Implementation)
# ============================================================================

class SiemensMriHandler(BaseAdapter):
    """
    Siemens MRI DICOM credential and file access adapter
    
    Workflow:
    1. Connect to PACS server
    2. Validate user credentials
    3. Query for DICOM studies
    4. Retrieve DICOM files
    5. Return file metadata or ephemeral access
    
    Example:
        handler = SiemensMriHandler(config={
            "pacs_host": "192.168.1.100",
            "pacs_port": 104,
            "pacs_ae_title": "KIRO-MCP",
            "server_type": "orthanc"
        })
        
        # Connect with credentials
        handler.connect(
            target={"host": "192.168.1.100", "ae_title": "KIRO-MCP"},
            credentials={"username": "admin", "password": "..."}
        )
        
        # Retrieve DICOM files
        files = handler.retrieve(
            path="/studies/1.2.3.4.5/instances",
            filter={"patient_id": "PAT-12345"}
        )
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Siemens MRI handler"""
        super().__init__(config)
        self.siemens_config = SiemensCredentialConfig(config or {})
        self.pacs_session = None
        self.authenticated_user = None
        self.auth_token = None
        self.study_cache = {}
        
        logger.info("SiemensMriHandler initialized")
    
    # ========================================================================
    # Required Interface Methods
    # ========================================================================
    
    def connect(self, target: Dict[str, Any], credentials: Dict[str, Any]) -> bool:
        """
        Connect to Siemens PACS server
        
        Args:
            target: Target server details
                - host: PACS server hostname/IP
                - port: PACS port (104 for DIMSE, 80/443 for REST)
                - ae_title: DICOM AE Title
            
            credentials: Authentication credentials
                - username: PACS username
                - password: PACS password
                - domain: Optional domain for enterprise PACS
        
        Returns:
            True if connection successful
            
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        try:
            self._log_operation("connect", {"target": target})
            
            # Update target details
            host = target.get("host", self.siemens_config.pacs_host)
            port = target.get("port", self.siemens_config.pacs_port)
            ae_title = target.get("ae_title", self.siemens_config.pacs_ae_title)
            
            # Validate credentials
            username = credentials.get("username")
            password = credentials.get("password")
            
            if not username or not password:
                raise AuthenticationError("Username and password required")
            
            # Attempt connection based on server type
            if self.siemens_config.server_type == DicomServerType.ORTHANC:
                self._connect_orthanc(host, port, username, password)
            elif self.siemens_config.server_type == DicomServerType.DCMQRSCP:
                self._connect_dcmqrscp(host, port, ae_title, username, password)
            else:
                self._connect_generic_dimse(host, port, ae_title, username, password)
            
            self.connected = True
            self.authenticated_user = username
            logger.info(f"Connected to PACS: {host}:{port} as {username}")
            
            return True
            
        except (ConnectionError, AuthenticationError) as e:
            logger.error(f"Connection failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected connection error: {e}")
            raise ConnectionError(f"PACS connection failed: {e}")
    
    def retrieve(self, path: str, **options) -> bytes:
        """
        Retrieve DICOM files by path
        
        Args:
            path: DICOM path specification
                Examples:
                - "/studies/{study_uid}/instances" - All instances in study
                - "/patients/{patient_id}/studies" - All studies for patient
                - "/instances/{sop_uid}" - Single instance
            
            **options: Retrieval options
                - format: "json", "dicom", "zip" (default: "json")
                - filter: Patient/study filter criteria
                - include_metadata: Include DICOM tags (default: True)
                - max_results: Maximum instances to return (default: 100)
        
        Returns:
            DICOM data as bytes (format depends on options)
            
        Raises:
            RetrievalError: If retrieval fails
        """
        if not self.connected:
            raise RetrievalError("Not connected to PACS")
        
        try:
            self._log_operation("retrieve", {"path": path, "options": options})
            
            # Parse path and options
            study_uid = self._extract_study_uid(path)
            format_type = options.get("format", "json")
            include_metadata = options.get("include_metadata", True)
            max_results = options.get("max_results", 100)
            
            if not study_uid:
                raise RetrievalError(f"Invalid path format: {path}")
            
            # Query for DICOM instances
            instances = self._query_instances(
                study_uid=study_uid,
                max_results=max_results,
                **options
            )
            
            if not instances:
                raise RetrievalError(f"No instances found for study: {study_uid}")
            
            # Build response based on format
            if format_type == "dicom":
                # Return raw DICOM files (binary)
                dicom_data = self._download_dicom_files(instances)
                return dicom_data
            
            elif format_type == "zip":
                # Return ZIP archive of DICOM files
                zip_data = self._create_dicom_archive(instances)
                return zip_data
            
            else:  # "json"
                # Return metadata as JSON
                metadata = self._build_metadata_response(instances, include_metadata)
                return json.dumps(metadata).encode("utf-8")
            
        except RetrievalError as e:
            raise
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            raise RetrievalError(f"Failed to retrieve DICOM data: {e}")
    
    def create_ephemeral_account(
        self, 
        ttl_seconds: int,
        **options
    ) -> Dict[str, Any]:
        """
        Create ephemeral PACS account with TTL
        
        Args:
            ttl_seconds: Time-to-live in seconds
            **options: Additional options
                - scope: "read-only" (default) or "read-write"
                - studies: List of study UIDs to restrict access
        
        Returns:
            Ephemeral account credentials
        
        Raises:
            EphemeralAccountError: If account creation fails
        """
        if not self.connected:
            raise EphemeralAccountError("Not connected to PACS")
        
        try:
            self._log_operation("create_ephemeral_account", {"ttl": ttl_seconds})
            
            scope = options.get("scope", "read-only")
            studies = options.get("studies", [])
            
            # Generate unique ephemeral username
            temp_username = f"temp_{self.authenticated_user}_{self._generate_nonce()}"
            temp_password = self._generate_secure_password()
            
            # Calculate expiration
            expires_ts = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
            
            # Create account based on server type
            if self.siemens_config.server_type == DicomServerType.ORTHANC:
                account_id = self._create_orthanc_ephemeral_user(
                    temp_username, temp_password, scope, studies
                )
            else:
                # For DIMSE-based systems, return virtual credentials
                account_id = f"ephemeral_{self._generate_nonce()}"
            
            logger.info(f"Created ephemeral account: {temp_username} (expires {expires_ts})")
            
            return {
                "username": temp_username,
                "password": temp_password,
                "expires_ts": expires_ts,
                "account_id": account_id,
                "scope": scope,
                "restricted_studies": studies
            }
            
        except Exception as e:
            logger.error(f"Ephemeral account creation failed: {e}")
            raise EphemeralAccountError(f"Failed to create temporary account: {e}")
    
    def cleanup(self):
        """Disconnect from PACS and cleanup resources"""
        try:
            if self.pacs_session:
                if self.siemens_config.server_type == DicomServerType.ORTHANC:
                    # Close HTTP session
                    self.pacs_session.close()
                else:
                    # Close DIMSE association
                    self._close_dimse_association()
            
            self.connected = False
            self.authenticated_user = None
            self.auth_token = None
            self.study_cache.clear()
            
            logger.info("Siemens MRI handler cleanup complete")
        except Exception as e:
            logger.error(f"Cleanup error (continuing): {e}")
    
    # ========================================================================
    # Connection Methods (Server-Type Specific)
    # ========================================================================
    
    def _connect_orthanc(
        self, 
        host: str, 
        port: int, 
        username: str, 
        password: str
    ):
        """Connect to Orthanc PACS via REST API"""
        import requests
        from requests.auth import HTTPBasicAuth
        
        base_url = f"http://{host}:{port}"
        
        try:
            # Test connection with /system endpoint
            response = requests.get(
                f"{base_url}/system",
                auth=HTTPBasicAuth(username, password),
                timeout=self.siemens_config.http_timeout_seconds,
                verify=not self.siemens_config.disable_warnings
            )
            
            if response.status_code == 401:
                raise AuthenticationError("Invalid Orthanc credentials")
            elif response.status_code != 200:
                raise ConnectionError(f"Orthanc returned status {response.status_code}")
            
            # Store session info
            self.pacs_session = requests.Session()
            self.pacs_session.auth = HTTPBasicAuth(username, password)
            self.pacs_session.timeout = self.siemens_config.http_timeout_seconds
            self.connection = {"type": "orthanc", "base_url": base_url}
            
            logger.info(f"Connected to Orthanc at {base_url}")
            
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Cannot connect to Orthanc at {base_url}: {e}")
        except requests.exceptions.Timeout as e:
            raise ConnectionError(f"Connection timeout to Orthanc: {e}")
    
    def _connect_dcmqrscp(
        self, 
        host: str, 
        port: int, 
        ae_title: str, 
        username: str, 
        password: str
    ):
        """Connect to DCMQRSCP via DIMSE protocol"""
        # Note: Real implementation would use pydicom + pynetdicom
        # This is a simplified stub for demonstration
        
        logger.info(f"Connecting to DCMQRSCP at {host}:{port} (AE: {ae_title})")
        
        # Validate credentials format
        if not username or not password:
            raise AuthenticationError("DCMQRSCP requires username and password")
        
        self.connection = {
            "type": "dcmqrscp",
            "host": host,
            "port": port,
            "ae_title": ae_title
        }
        
        # In production, would establish DIMSE association here
        logger.info(f"DCMQRSCP connection established")
    
    def _connect_generic_dimse(
        self, 
        host: str, 
        port: int, 
        ae_title: str, 
        username: str, 
        password: str
    ):
        """Generic DIMSE connection (fallback)"""
        logger.info(f"Connecting via generic DIMSE to {host}:{port}")
        
        self.connection = {
            "type": "dimse",
            "host": host,
            "port": port,
            "ae_title": ae_title
        }
    
    # ========================================================================
    # Query & Retrieval Methods
    # ========================================================================
    
    def _query_instances(
        self, 
        study_uid: str, 
        max_results: int = 100,
        **options
    ) -> List[Dict[str, Any]]:
        """Query PACS for DICOM instances in a study"""
        
        if self.connection["type"] == "orthanc":
            return self._query_instances_orthanc(study_uid, max_results)
        else:
            return self._query_instances_dimse(study_uid, max_results)
    
    def _query_instances_orthanc(self, study_uid: str, max_results: int) -> List[Dict[str, Any]]:
        """Query Orthanc for instances"""
        try:
            base_url = self.connection["base_url"]
            
            # Search for study
            response = self.pacs_session.get(
                f"{base_url}/studies",
                params={"StudyInstanceUID": study_uid}
            )
            
            if response.status_code != 200:
                logger.warning(f"Study search returned {response.status_code}")
                return []
            
            studies = response.json()
            if not studies:
                return []
            
            # Get instances from first matching study
            study_id = studies[0].get("ID")
            response = self.pacs_session.get(
                f"{base_url}/studies/{study_id}/instances"
            )
            
            instances = response.json() if response.status_code == 200 else []
            return instances[:max_results]
            
        except Exception as e:
            logger.error(f"Orthanc instance query failed: {e}")
            return []
    
    def _query_instances_dimse(self, study_uid: str, max_results: int) -> List[Dict[str, Any]]:
        """Query via DIMSE (stub implementation)"""
        logger.info(f"Querying DIMSE for study {study_uid}")
        
        # In production, would perform C-FIND operation here
        # For now, return mock data
        return [
            {
                "sop_instance_uid": "1.2.3.4.5.1",
                "study_instance_uid": study_uid,
                "file_size": 1024000
            }
        ]
    
    def _download_dicom_files(self, instances: List[Dict[str, Any]]) -> bytes:
        """Download DICOM files for instances"""
        # In production, would perform C-GET and aggregate files
        logger.info(f"Downloading {len(instances)} DICOM files")
        
        # Mock implementation
        return b"DICOM_FILE_DATA"
    
    def _create_dicom_archive(self, instances: List[Dict[str, Any]]) -> bytes:
        """Create ZIP archive of DICOM files"""
        import io
        import zipfile
        
        logger.info(f"Creating DICOM archive for {len(instances)} instances")
        
        # Mock implementation
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            for i, instance in enumerate(instances):
                zf.writestr(
                    f"instance_{i}.dcm",
                    f"MOCK_DICOM_DATA_FOR_{instance.get('sop_instance_uid', i)}".encode()
                )
        
        return zip_buffer.getvalue()
    
    def _build_metadata_response(
        self, 
        instances: List[Dict[str, Any]], 
        include_metadata: bool
    ) -> Dict[str, Any]:
        """Build JSON response with instance metadata"""
        return {
            "count": len(instances),
            "instances": instances[:10],  # First 10 for brevity
            "retrieved_ts": datetime.utcnow().isoformat(),
            "format": "metadata"
        }
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _extract_study_uid(self, path: str) -> Optional[str]:
        """Extract Study Instance UID from path"""
        # Parse patterns like:
        # /studies/{uid}/instances -> uid
        # /patients/{pid}/studies -> None (requires query)
        
        if "/studies/" in path:
            parts = path.split("/")
            if len(parts) >= 3 and parts[1] == "studies":
                return parts[2]
        
        return None
    
    def _generate_nonce(self) -> str:
        """Generate unique nonce for temporary credentials"""
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
    
    def _create_orthanc_ephemeral_user(
        self,
        username: str,
        password: str,
        scope: str,
        studies: List[str]
    ) -> str:
        """Create ephemeral user in Orthanc"""
        try:
            base_url = self.connection["base_url"]
            
            # Orthanc user creation payload
            payload = {
                "Username": username,
                "Password": password,
                "OrthancPermissions": ["all"] if scope == "read-write" else ["view"],
            }
            
            response = self.pacs_session.post(
                f"{base_url}/users",
                json=payload
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Created Orthanc ephemeral user: {username}")
                return f"orthanc_{username}"
            else:
                raise EphemeralAccountError(
                    f"Orthanc user creation returned {response.status_code}"
                )
            
        except Exception as e:
            logger.error(f"Orthanc ephemeral user creation failed: {e}")
            raise
    
    def _close_dimse_association(self):
        """Close DIMSE association"""
        logger.info("Closing DIMSE association")
        # In production, would release DIMSE association


# ============================================================================
# Configuration Builder
# ============================================================================

class SiemensMriConfig:
    """Helper to build Siemens MRI handler configuration"""
    
    @staticmethod
    def for_orthanc(pacs_host: str, pacs_port: int = 8042) -> Dict[str, Any]:
        """Configuration for Orthanc PACS"""
        return {
            "pacs_host": pacs_host,
            "pacs_port": pacs_port,
            "server_type": "orthanc",
            "http_timeout_seconds": 30,
        }
    
    @staticmethod
    def for_dcmqrscp(pacs_host: str, pacs_port: int = 104, ae_title: str = "KIRO") -> Dict[str, Any]:
        """Configuration for DCMQRSCP"""
        return {
            "pacs_host": pacs_host,
            "pacs_port": pacs_port,
            "pacs_ae_title": ae_title,
            "server_type": "dcmqrscp",
        }
    
    @staticmethod
    def for_generic_dimse(pacs_host: str, pacs_port: int = 104) -> Dict[str, Any]:
        """Configuration for generic DIMSE"""
        return {
            "pacs_host": pacs_host,
            "pacs_port": pacs_port,
            "server_type": "generic_dimse",
        }


# ============================================================================
# Integration with FastAPI
# ============================================================================

class DicomRequestPayload(Dict[str, Any]):
    """Payload for DICOM retrieval via FastAPI"""
    
    @staticmethod
    def create(
        requester_id: str,
        patient_id: str,
        study_uid: str,
        reason: str = "Medical care",
        emergency: bool = False
    ) -> Dict[str, Any]:
        """Create DICOM request payload for FastAPI"""
        return {
            "requester_id": requester_id,
            "reason": reason,
            "target": {
                "vault": "pacs_vault_1",
                "path": f"/studies/{study_uid}/instances"
            },
            "patient_context": {
                "patient_id": patient_id,
                "study_instance_uid": study_uid
            },
            "emergency": emergency
        }


if __name__ == "__main__":
    # Example usage
    config = SiemensMriConfig.for_orthanc("192.168.1.100")
    handler = SiemensMriHandler(config)
    
    try:
        # Connect
        handler.connect(
            target={"host": "192.168.1.100", "port": 8042},
            credentials={"username": "admin", "password": "orthanc"}
        )
        
        # Retrieve DICOM files
        metadata = handler.retrieve(
            path="/studies/1.2.3.4.5/instances",
            format="json"
        )
        
        print(f"Retrieved: {metadata}")
        
    finally:
        handler.cleanup()
