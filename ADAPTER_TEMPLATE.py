"""
Medical Adapter Template - Use this as base for Tasks 2.4-2.6

This template shows the structure for implementing medical adapters:
- Siemens MRI Adapter (Task 2.4)
- LIS Lab Adapter (Task 2.5)
- Philips CT Adapter (Task 2.6)

Replace ADAPTER_NAME with: SiemensMRI, LabLIS, or PhilipsCT
Replace SERVICE_NAME with: siemens-mri, lab-lis, or philips-ct
"""

import os
import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

class ADAPTERConfig:
    """Configuration for ADAPTER_NAME adapter"""
    
    # Connection settings
    HOST = os.getenv("ADAPTER_HOST", "0.0.0.0")
    PORT = int(os.getenv("ADAPTER_PORT", "8002"))  # Change port per adapter
    
    # MCP Server settings
    MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:8000/api/v1")
    MCP_TIMEOUT = 30
    
    # ADAPTER_NAME specific settings
    # TODO: Add vendor-specific configuration
    # VENDOR_HOST = os.getenv("VENDOR_HOST", "vendor.example.com")
    # VENDOR_PORT = int(os.getenv("VENDOR_PORT", "443"))
    # VENDOR_PROTOCOL = os.getenv("VENDOR_PROTOCOL", "https")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class CredentialRequest:
    """Credential request for ADAPTER_NAME"""
    req_id: str
    requester_id: str
    reason: str
    target_vault: str
    target_path: str
    patient_context: Dict[str, Any]
    emergency: bool
    expires_ts: str


@dataclass
class CredentialResponse:
    """Credential retrieved from vault"""
    vault_id: str
    path: str
    credential: str  # Encrypted
    expires_in: int


# ============================================================================
# ADAPTER_NAME Handler
# ============================================================================

class ADAPTERNameHandler:
    """
    Handler for ADAPTER_NAME device/system.
    
    Workflow:
    1. Create credential request via FastAPI
    2. Owner approves request
    3. Get access token from FastAPI
    4. Retrieve credential using token
    5. Connect to ADAPTER_NAME system
    6. Log audit event
    """
    
    def __init__(self, config: ADAPTERConfig = ADAPTERConfig):
        self.config = config
        self.mcp_client = MCPClient(config.MCP_SERVER_URL)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming request for ADAPTER_NAME credentials.
        
        Args:
            request_data: Request details including patient ID, resource path
            
        Returns:
            Response with success/failure status and details
        """
        try:
            # 1. Create credential request
            req_id = self.create_credential_request(request_data)
            self.logger.info(f"Created credential request: {req_id}")
            
            # 2. For emergency requests, auto-approve with special handling
            if request_data.get("emergency"):
                self.handle_emergency_approval(req_id)
            else:
                self.logger.info(f"Waiting for owner approval for {req_id}")
                # TODO: Implement approval notification/waiting
            
            # 3. Get access token
            token = self.get_access_token(req_id)
            self.logger.info(f"Obtained access token for {req_id}")
            
            # 4. Retrieve credential
            credential = self.retrieve_credential(req_id, token)
            self.logger.info(f"Retrieved credential for {req_id}")
            
            # 5. Connect to ADAPTER_NAME system
            result = self.connect_to_vendor_system(credential, request_data)
            
            # 6. Log successful completion
            self.log_completion(req_id, "SUCCESS", result)
            
            return {
                "status": "success",
                "req_id": req_id,
                "result": result
            }
        
        except Exception as e:
            self.logger.error(f"Error handling request: {str(e)}")
            self.log_completion(request_data.get("req_id"), "FAILED", str(e))
            
            return {
                "status": "error",
                "error": str(e)
            }
    
    def create_credential_request(self, request_data: Dict[str, Any]) -> str:
        """
        Create credential request via FastAPI.
        
        Returns:
            req_id: Unique request ID
        """
        response = self.mcp_client.post(
            "/requests",
            json={
                "requester_id": request_data.get("requester_id", "ADAPTER-AUTO"),
                "reason": f"ADAPTER_NAME access: {request_data.get('reason', 'No reason')}",
                "target_vault": request_data.get("target_vault", "clinic_main"),
                "target_path": request_data.get("target_path", "/ADAPTER_NAME/credentials"),
                "patient_context": request_data.get("patient_context", {}),
                "emergency": request_data.get("emergency", False)
            }
        )
        
        if response.status_code != 201:
            raise Exception(f"Failed to create request: {response.text}")
        
        return response.json()["req_id"]
    
    def handle_emergency_approval(self, req_id: str):
        """
        Handle emergency approval (out-of-band process).
        
        Note: In production, this would trigger:
        - SMS/email to owner
        - Phone callback
        - Manager override
        """
        self.logger.warning(f"Emergency request {req_id} requires immediate approval")
        # TODO: Implement emergency approval workflow
        # For now: This would wait for async approval
    
    def get_access_token(self, req_id: str) -> str:
        """
        Get access token after approval.
        
        Returns:
            token: Bearer token for credential retrieval
        """
        # Poll for approval (or implement webhook)
        for attempt in range(60):  # 5 minutes with 5s poll
            response = self.mcp_client.get(f"/requests/{req_id}")
            
            if response.status_code != 200:
                raise Exception(f"Failed to check request status: {response.text}")
            
            status = response.json()["status"]
            
            if status == "APPROVED":
                # Get token
                token_response = self.mcp_client.get(f"/requests/{req_id}/token")
                if token_response.status_code != 200:
                    raise Exception(f"Failed to get token: {token_response.text}")
                
                return token_response.json()["token"]
            
            elif status == "REJECTED":
                raise Exception("Request was rejected by owner")
            
            elif status == "EXPIRED":
                raise Exception("Request expired")
            
            # Wait before retry
            import time
            time.sleep(5)
        
        raise Exception("Timeout waiting for approval")
    
    def retrieve_credential(self, req_id: str, token: str) -> str:
        """
        Retrieve credential using token.
        
        Returns:
            credential: Encrypted credential value
        """
        response = self.mcp_client.post(
            "/credentials/retrieve",
            json={
                "token": token,
                "req_id": req_id
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve credential: {response.text}")
        
        return response.json()["credential"]
    
    def connect_to_vendor_system(self, credential: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Connect to ADAPTER_NAME system using retrieved credential.
        
        TODO: Implement vendor-specific connection logic
        
        Returns:
            Connection result with system info
        """
        # TODO: Replace with actual ADAPTER_NAME connection
        # Example:
        # - Decrypt credential
        # - Connect via SSH/API/DICOM
        # - Execute command or retrieve data
        # - Return results
        
        self.logger.info(f"TODO: Connect to ADAPTER_NAME system with context: {context}")
        
        return {
            "connected": True,
            "system": "ADAPTER_NAME",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def log_completion(self, req_id: str, status: str, details: Any):
        """
        Log completion event to audit trail.
        """
        response = self.mcp_client.get(f"/audit/log?limit=1")
        if response.status_code == 200:
            self.logger.info(f"Logged completion: {req_id} - {status}")


# ============================================================================
# MCP Client
# ============================================================================

class MCPClient:
    """Client for communicating with MCP Server"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get(self, path: str, **kwargs) -> requests.Response:
        """GET request"""
        url = f"{self.base_url}{path}"
        return self.session.get(url, **kwargs)
    
    def post(self, path: str, **kwargs) -> requests.Response:
        """POST request"""
        url = f"{self.base_url}{path}"
        return self.session.post(url, **kwargs)
    
    def put(self, path: str, **kwargs) -> requests.Response:
        """PUT request"""
        url = f"{self.base_url}{path}"
        return self.session.put(url, **kwargs)
    
    def delete(self, path: str, **kwargs) -> requests.Response:
        """DELETE request"""
        url = f"{self.base_url}{path}"
        return self.session.delete(url, **kwargs)


# ============================================================================
# Service Setup
# ============================================================================

def create_app():
    """Create FastAPI app for adapter service"""
    from fastapi import FastAPI, HTTPException
    
    app = FastAPI(
        title="ADAPTER_NAME Adapter",
        description="Adapter for ADAPTER_NAME system",
        version="1.0.0"
    )
    
    handler = ADAPTERNameHandler()
    
    @app.post("/request")
    async def handle_credential_request(request_data: Dict[str, Any]):
        """Handle credential request for ADAPTER_NAME"""
        result = handler.handle_request(request_data)
        
        if result["status"] != "success":
            raise HTTPException(status_code=400, detail=result)
        
        return result
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "service": "ADAPTER_NAME"}
    
    return app


if __name__ == "__main__":
    import uvicorn
    
    logging.basicConfig(
        level=ADAPTERConfig.LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    app = create_app()
    
    uvicorn.run(
        app,
        host=ADAPTERConfig.HOST,
        port=ADAPTERConfig.PORT,
        log_level="info"
    )
