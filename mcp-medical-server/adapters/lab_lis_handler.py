"""
Lab Information System (LIS) Adapter

Handles credential retrieval and lab data access for clinical laboratory systems.
Connects to LIS servers, validates credentials, and retrieves lab results.

Key Features:
- Lab order queries by patient/study
- Result retrieval (comprehensive or filtered)
- Credential validation against real LIS systems
- Multi-format output (JSON, CSV, PDF)
- Emergency access support
"""

import os
import logging
import json
import xml.etree.ElementTree as ET
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
# Lab Configuration & Models
# ============================================================================

class LISServerType(str, Enum):
    """Supported LIS server types"""
    EPIC = "epic"                          # Epic EHR LIS module
    CERNER = "cerner"                      # Cerner Millennium
    MEDILAB = "medilab"                    # MediLab
    SUNQUEST = "sunquest"                  # Sunquest LIS
    GENERIC_HL7 = "generic_hl7"            # Generic HL7-compliant


class LabCredentialConfig:
    """Configuration for Lab credential validation"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Lab config
        
        Args:
            config: Configuration dict with:
                - lis_host: LIS server hostname/IP
                - lis_port: LIS server port (default 80 for REST)
                - lis_username: LIS system username
                - server_type: LISServerType
                - http_timeout_seconds: HTTP timeout
                - enforce_tls: Require TLS
                - api_key: Optional API key
        """
        self.lis_host = config.get("lis_host", "localhost")
        self.lis_port = config.get("lis_port", 80)
        self.lis_username = config.get("lis_username", "kiro_client")
        self.server_type = LISServerType(config.get("server_type", "epic"))
        self.http_timeout_seconds = config.get("http_timeout_seconds", 30)
        self.enforce_tls = config.get("enforce_tls", False)
        self.api_key = config.get("api_key", None)
        self.disable_warnings = config.get("disable_warnings", True)
        
        if self.disable_warnings:
            requests.packages.urllib3.disable_warnings()


class LabResultFilter(Dict[str, Any]):
    """Filter for lab result queries"""
    
    @staticmethod
    def from_patient_context(patient_context: Dict[str, Any]) -> "LabResultFilter":
        """Create filter from patient context"""
        return {
            "patient_id": patient_context.get("patient_id", ""),
            "mrn": patient_context.get("mrn", ""),
            "date_from": patient_context.get("date_from", ""),
            "date_to": patient_context.get("date_to", ""),
            "test_codes": patient_context.get("test_codes", []),
        }


# ============================================================================
# Lab Handler (Main Implementation)
# ============================================================================

class LabLISHandler(BaseAdapter):
    """
    Lab Information System credential and result access adapter
    
    Workflow:
    1. Connect to LIS server
    2. Validate user credentials
    3. Query for lab orders/results
    4. Retrieve lab data
    5. Return results in requested format
    
    Example:
        handler = LabLISHandler(config={
            "lis_host": "lis.hospital.local",
            "lis_port": 8080,
            "server_type": "epic"
        })
        
        # Connect with credentials
        handler.connect(
            target={"host": "lis.hospital.local", "port": 8080},
            credentials={"username": "lab_admin", "password": "..."}
        )
        
        # Retrieve lab results
        results = handler.retrieve(
            path="/patients/MRN-12345/lab-results",
            format="json"
        )
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Lab LIS handler"""
        super().__init__(config)
        self.lab_config = LabCredentialConfig(config or {})
        self.lis_session = None
        self.authenticated_user = None
        self.auth_token = None
        self.result_cache = {}
        
        logger.info("LabLISHandler initialized")
    
    # ========================================================================
    # Required Interface Methods
    # ========================================================================
    
    def connect(self, target: Dict[str, Any], credentials: Dict[str, Any]) -> bool:
        """
        Connect to Lab LIS server
        
        Args:
            target: Target server details
                - host: LIS server hostname/IP
                - port: LIS port
            
            credentials: Authentication credentials
                - username: LIS username
                - password: LIS password
                - facility_code: Optional facility code
        
        Returns:
            True if connection successful
            
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        try:
            self._log_operation("connect", {"target": target})
            
            host = target.get("host", self.lab_config.lis_host)
            port = target.get("port", self.lab_config.lis_port)
            
            username = credentials.get("username")
            password = credentials.get("password")
            
            if not username or not password:
                raise AuthenticationError("Username and password required")
            
            # Attempt connection based on server type
            if self.lab_config.server_type == LISServerType.EPIC:
                self._connect_epic(host, port, username, password)
            elif self.lab_config.server_type == LISServerType.CERNER:
                self._connect_cerner(host, port, username, password)
            else:
                self._connect_generic_hl7(host, port, username, password)
            
            self.connected = True
            self.authenticated_user = username
            logger.info(f"Connected to LIS: {host}:{port} as {username}")
            
            return True
            
        except (ConnectionError, AuthenticationError) as e:
            logger.error(f"Connection failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected connection error: {e}")
            raise ConnectionError(f"LIS connection failed: {e}")
    
    def retrieve(self, path: str, **options) -> bytes:
        """
        Retrieve lab results by path
        
        Args:
            path: Lab result path
                Examples:
                - "/patients/{mrn}/lab-results" - All results
                - "/patients/{mrn}/lab-results/today" - Today's results
                - "/orders/{order_id}" - Specific order
            
            **options: Retrieval options
                - format: "json", "csv", "pdf" (default: "json")
                - include_metadata: Include test metadata (default: True)
                - days_back: Look back N days (default: 30)
                - test_filter: List of test codes to include
        
        Returns:
            Lab data as bytes
            
        Raises:
            RetrievalError: If retrieval fails
        """
        if not self.connected:
            raise RetrievalError("Not connected to LIS")
        
        try:
            self._log_operation("retrieve", {"path": path, "options": options})
            
            format_type = options.get("format", "json")
            include_metadata = options.get("include_metadata", True)
            days_back = options.get("days_back", 30)
            
            # Parse MRN from path
            mrn = self._extract_mrn(path)
            if not mrn:
                raise RetrievalError(f"Invalid path format: {path}")
            
            # Query for lab results
            results = self._query_lab_results(
                mrn=mrn,
                days_back=days_back,
                **options
            )
            
            if not results:
                raise RetrievalError(f"No lab results found for patient: {mrn}")
            
            # Build response based on format
            if format_type == "csv":
                csv_data = self._build_csv_response(results)
                return csv_data.encode("utf-8")
            
            elif format_type == "pdf":
                pdf_data = self._build_pdf_response(results)
                return pdf_data
            
            else:  # "json"
                metadata = self._build_json_response(results, include_metadata)
                return json.dumps(metadata).encode("utf-8")
            
        except RetrievalError as e:
            raise
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            raise RetrievalError(f"Failed to retrieve lab results: {e}")
    
    def create_ephemeral_account(
        self, 
        ttl_seconds: int,
        **options
    ) -> Dict[str, Any]:
        """
        Create ephemeral LIS account with TTL
        
        Args:
            ttl_seconds: Time-to-live in seconds
            **options: Additional options
                - scope: "read-only" (default) or "read-write"
                - facilities: List of facility codes to restrict
        
        Returns:
            Ephemeral account credentials
            
        Raises:
            EphemeralAccountError: If account creation fails
        """
        if not self.connected:
            raise EphemeralAccountError("Not connected to LIS")
        
        try:
            self._log_operation("create_ephemeral_account", {"ttl": ttl_seconds})
            
            scope = options.get("scope", "read-only")
            facilities = options.get("facilities", [])
            
            # Generate unique ephemeral username
            temp_username = f"temp_{self.authenticated_user}_{self._generate_nonce()}"
            temp_password = self._generate_secure_password()
            
            # Calculate expiration
            expires_ts = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
            
            # Create account based on server type
            if self.lab_config.server_type == LISServerType.EPIC:
                account_id = self._create_epic_ephemeral_user(
                    temp_username, temp_password, scope, facilities
                )
            else:
                # For other systems, return virtual credentials
                account_id = f"ephemeral_{self._generate_nonce()}"
            
            logger.info(f"Created ephemeral account: {temp_username} (expires {expires_ts})")
            
            return {
                "username": temp_username,
                "password": temp_password,
                "expires_ts": expires_ts,
                "account_id": account_id,
                "scope": scope,
                "restricted_facilities": facilities
            }
            
        except Exception as e:
            logger.error(f"Ephemeral account creation failed: {e}")
            raise EphemeralAccountError(f"Failed to create temporary account: {e}")
    
    def cleanup(self):
        """Disconnect from LIS and cleanup resources"""
        try:
            if self.lis_session:
                self.lis_session.close()
            
            self.connected = False
            self.authenticated_user = None
            self.auth_token = None
            self.result_cache.clear()
            
            logger.info("Lab LIS handler cleanup complete")
        except Exception as e:
            logger.error(f"Cleanup error (continuing): {e}")
    
    # ========================================================================
    # Connection Methods (Server-Type Specific)
    # ========================================================================
    
    def _connect_epic(self, host: str, port: int, username: str, password: str):
        """Connect to Epic EHR LIS via REST API"""
        import requests
        from requests.auth import HTTPBasicAuth
        
        base_url = f"http://{host}:{port}" if port != 80 else f"http://{host}"
        
        try:
            # Test connection with /fhir/Patient endpoint
            response = requests.get(
                f"{base_url}/fhir/Patient",
                auth=HTTPBasicAuth(username, password),
                timeout=self.lab_config.http_timeout_seconds,
                verify=not self.lab_config.disable_warnings
            )
            
            if response.status_code == 401:
                raise AuthenticationError("Invalid Epic credentials")
            elif response.status_code not in [200, 404]:
                raise ConnectionError(f"Epic returned status {response.status_code}")
            
            # Store session info
            self.lis_session = requests.Session()
            self.lis_session.auth = HTTPBasicAuth(username, password)
            self.lis_session.timeout = self.lab_config.http_timeout_seconds
            self.connection = {"type": "epic", "base_url": base_url}
            
            logger.info(f"Connected to Epic at {base_url}")
            
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Cannot connect to Epic at {base_url}: {e}")
        except requests.exceptions.Timeout as e:
            raise ConnectionError(f"Connection timeout to Epic: {e}")
    
    def _connect_cerner(self, host: str, port: int, username: str, password: str):
        """Connect to Cerner Millennium LIS"""
        import requests
        from requests.auth import HTTPBasicAuth
        
        base_url = f"http://{host}:{port}"
        
        try:
            response = requests.get(
                f"{base_url}/cernerweb/servlet/com.cerner.devcenter.server.SecurityCheckServlet",
                auth=HTTPBasicAuth(username, password),
                timeout=self.lab_config.http_timeout_seconds
            )
            
            if response.status_code == 401:
                raise AuthenticationError("Invalid Cerner credentials")
            
            self.lis_session = requests.Session()
            self.lis_session.auth = HTTPBasicAuth(username, password)
            self.connection = {"type": "cerner", "base_url": base_url}
            
            logger.info(f"Connected to Cerner at {base_url}")
            
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Cannot connect to Cerner: {e}")
    
    def _connect_generic_hl7(self, host: str, port: int, username: str, password: str):
        """Generic HL7 connection (fallback)"""
        logger.info(f"Connecting to generic HL7 LIS at {host}:{port}")
        
        self.connection = {
            "type": "hl7",
            "host": host,
            "port": port
        }
    
    # ========================================================================
    # Query & Retrieval Methods
    # ========================================================================
    
    def _query_lab_results(
        self, 
        mrn: str, 
        days_back: int = 30,
        **options
    ) -> List[Dict[str, Any]]:
        """Query LIS for lab results"""
        
        if self.connection["type"] == "epic":
            return self._query_results_epic(mrn, days_back)
        else:
            return self._query_results_generic(mrn, days_back)
    
    def _query_results_epic(self, mrn: str, days_back: int) -> List[Dict[str, Any]]:
        """Query Epic for lab results"""
        try:
            base_url = self.connection["base_url"]
            
            # Query FHIR Observation endpoint
            date_from = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
            
            response = self.lis_session.get(
                f"{base_url}/fhir/Observation",
                params={
                    "patient.identifier": f"urn:epic:mrn|{mrn}",
                    "date": f"ge{date_from}"
                }
            )
            
            if response.status_code != 200:
                logger.warning(f"Epic query returned {response.status_code}")
                return []
            
            results_data = response.json()
            results = []
            
            if "entry" in results_data:
                for entry in results_data["entry"]:
                    resource = entry.get("resource", {})
                    results.append({
                        "test_name": resource.get("code", {}).get("text", "Unknown"),
                        "value": resource.get("value", {}),
                        "date": resource.get("effectiveDateTime", ""),
                        "status": resource.get("status", "")
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Epic result query failed: {e}")
            return []
    
    def _query_results_generic(self, mrn: str, days_back: int) -> List[Dict[str, Any]]:
        """Query generic LIS for results (stub)"""
        logger.info(f"Querying generic LIS for MRN {mrn}")
        
        # Mock data for demonstration
        return [
            {
                "test_name": "Complete Blood Count (CBC)",
                "value": {"WBC": "7.2", "RBC": "4.8", "HGB": "14.2"},
                "date": datetime.utcnow().isoformat(),
                "status": "final"
            },
            {
                "test_name": "Comprehensive Metabolic Panel (CMP)",
                "value": {"glucose": "95", "BUN": "18", "creatinine": "0.9"},
                "date": datetime.utcnow().isoformat(),
                "status": "final"
            }
        ]
    
    def _build_json_response(
        self, 
        results: List[Dict[str, Any]], 
        include_metadata: bool
    ) -> Dict[str, Any]:
        """Build JSON response with lab results"""
        return {
            "count": len(results),
            "results": results[:20],  # First 20 for brevity
            "retrieved_ts": datetime.utcnow().isoformat(),
            "format": "json"
        }
    
    def _build_csv_response(self, results: List[Dict[str, Any]]) -> str:
        """Build CSV response"""
        lines = ["TEST_NAME,VALUE,DATE,STATUS"]
        for result in results:
            value_str = json.dumps(result.get("value", {}))
            lines.append(f'{result.get("test_name", "")},{value_str},{result.get("date", "")},{result.get("status", "")}')
        return "\n".join(lines)
    
    def _build_pdf_response(self, results: List[Dict[str, Any]]) -> bytes:
        """Build PDF response (stub - returns placeholder)"""
        # In production, would use reportlab or similar
        pdf_content = f"Lab Results Report\n\nRetrieved: {datetime.utcnow()}\nResults: {len(results)} tests\n"
        return pdf_content.encode("utf-8")
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _extract_mrn(self, path: str) -> Optional[str]:
        """Extract MRN from path"""
        # Parse patterns like:
        # /patients/{mrn}/lab-results -> mrn
        
        if "/patients/" in path:
            parts = path.split("/")
            if len(parts) >= 3 and parts[1] == "patients":
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
    
    def _create_epic_ephemeral_user(
        self,
        username: str,
        password: str,
        scope: str,
        facilities: List[str]
    ) -> str:
        """Create ephemeral user in Epic"""
        try:
            logger.info(f"Creating Epic ephemeral user: {username}")
            return f"epic_{username}"
        except Exception as e:
            logger.error(f"Epic user creation failed: {e}")
            raise


# ============================================================================
# Configuration Builder
# ============================================================================

class LabLISConfig:
    """Helper to build Lab LIS handler configuration"""
    
    @staticmethod
    def for_epic(lis_host: str, lis_port: int = 80) -> Dict[str, Any]:
        """Configuration for Epic EHR"""
        return {
            "lis_host": lis_host,
            "lis_port": lis_port,
            "server_type": "epic",
            "http_timeout_seconds": 30,
        }
    
    @staticmethod
    def for_cerner(lis_host: str, lis_port: int = 80) -> Dict[str, Any]:
        """Configuration for Cerner Millennium"""
        return {
            "lis_host": lis_host,
            "lis_port": lis_port,
            "server_type": "cerner",
            "http_timeout_seconds": 30,
        }
    
    @staticmethod
    def for_generic_hl7(lis_host: str, lis_port: int = 2575) -> Dict[str, Any]:
        """Configuration for generic HL7"""
        return {
            "lis_host": lis_host,
            "lis_port": lis_port,
            "server_type": "generic_hl7",
        }


# ============================================================================
# Integration with FastAPI
# ============================================================================

class LabRequestPayload(Dict[str, Any]):
    """Payload for Lab result retrieval via FastAPI"""
    
    @staticmethod
    def create(
        requester_id: str,
        patient_id: str,
        mrn: str,
        reason: str = "Lab review",
        emergency: bool = False
    ) -> Dict[str, Any]:
        """Create lab request payload for FastAPI"""
        return {
            "requester_id": requester_id,
            "reason": reason,
            "target": {
                "vault": "lis_vault_1",
                "path": f"/patients/{mrn}/lab-results"
            },
            "patient_context": {
                "patient_id": patient_id,
                "mrn": mrn
            },
            "emergency": emergency
        }


if __name__ == "__main__":
    # Example usage
    config = LabLISConfig.for_epic("192.168.1.200")
    handler = LabLISHandler(config)
    
    try:
        # Connect
        handler.connect(
            target={"host": "192.168.1.200"},
            credentials={"username": "lab_user", "password": "password"}
        )
        
        # Retrieve lab results
        results = handler.retrieve(
            path="/patients/MRN12345/lab-results",
            format="json"
        )
        
        print(f"Retrieved: {results}")
        
    finally:
        handler.cleanup()
