"""
Medical Scheme Agent - REST API and Orchestration
Orchestrates MCP tools and Granite-3.1 LLM for healthcare automation
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from mcp_server import MedicalSchemeMCPServer
from granite_service import get_granite_medical_service, init_granite_medical_service

logger = logging.getLogger("MedicalSchemeAgent")

# ============================================================================
# MEDICAL SCHEME AGENT ORCHESTRATOR
# ============================================================================

class MedicalSchemeAgentOrchestrator:
    """
    Orchestrates MCP server, Granite AI, and healthcare workflows
    Provides unified interface for medical scheme automation
    """
    
    def __init__(self, use_granite: bool = True):
        """
        Initialize orchestrator
        
        Args:
            use_granite: Whether to use Granite-3.1 LLM (not Gemini)
        """
        logger.info("[Orchestrator] Initializing Medical Scheme Agent")
        
        self.use_granite = use_granite
        self.mcp_server = MedicalSchemeMCPServer()
        self.granite_service = init_granite_medical_service() if use_granite else None
        self.request_history = []
        
        logger.info("[Orchestrator] Agent initialized successfully")
        logger.info(f"[Orchestrator] Using Granite-3.1: {self.use_granite}")
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming agent request
        
        Args:
            request: Request with action, parameters, and context
            
        Returns:
            Response with results and AI analysis
        """
        request_id = request.get("request_id", f"REQ-{datetime.now().timestamp()}")
        action = request.get("action")
        params = request.get("params", {})
        context = request.get("context", {})
        
        logger.info(f"[Agent] Processing request {request_id}: {action}")
        
        try:
            # Route to appropriate handler
            if action == "check_benefits":
                return self._handle_check_benefits(request_id, params, context)
            elif action == "request_auth":
                return self._handle_request_auth(request_id, params, context)
            elif action == "submit_claim":
                return self._handle_submit_claim(request_id, params, context)
            elif action == "track_claim":
                return self._handle_track_claim(request_id, params, context)
            elif action == "compare_schemes":
                return self._handle_compare_schemes(request_id, params, context)
            elif action == "find_scheme":
                return self._handle_find_scheme(request_id, params, context)
            elif action == "get_contact":
                return self._handle_get_contact(request_id, params, context)
            elif action == "health_tips":
                return self._handle_health_tips(request_id, params, context)
            else:
                return self._error_response(request_id, f"Unknown action: {action}")
        
        except Exception as e:
            logger.error(f"[Agent] Error processing request: {str(e)}")
            return self._error_response(request_id, str(e))
    
    def _handle_check_benefits(self, request_id: str, params: Dict, 
                              context: Dict) -> Dict[str, Any]:
        """Check patient benefits and coverage"""
        logger.info(f"[Agent] {request_id}: Checking benefits")
        
        scheme = params.get("scheme")
        patient_id = params.get("patient_id")
        service = params.get("service")
        
        if not all([scheme, patient_id, service]):
            return self._error_response(request_id, "Missing required parameters: scheme, patient_id, service")
        
        # Call MCP tool
        coverage = self.mcp_server.call_tool(
            "check_patient_coverage",
            scheme=scheme,
            patient_id=patient_id,
            service=service
        )
        
        # Get AI analysis if Granite available
        ai_analysis = None
        if self.use_granite and self.granite_service:
            ai_analysis = self.granite_service.generate_response(
                f"Explain coverage for {service} under {scheme} scheme",
                context={
                    "coverage": coverage.get("coverage"),
                    "limit": coverage.get("limit"),
                    "notes": coverage.get("notes"),
                }
            )
        
        return {
            "success": True,
            "request_id": request_id,
            "action": "check_benefits",
            "coverage": coverage,
            "ai_analysis": ai_analysis.get("response") if ai_analysis else None,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _handle_request_auth(self, request_id: str, params: Dict,
                            context: Dict) -> Dict[str, Any]:
        """Request authorization for service"""
        logger.info(f"[Agent] {request_id}: Requesting authorization")
        
        scheme = params.get("scheme")
        patient_id = params.get("patient_id")
        service = params.get("service")
        reason = params.get("reason")
        doctor = params.get("doctor")
        
        if not all([scheme, patient_id, service, reason, doctor]):
            return self._error_response(request_id, "Missing required parameters")
        
        # Call MCP tool
        auth = self.mcp_server.call_tool(
            "request_authorization",
            scheme=scheme,
            patient_id=patient_id,
            service=service,
            reason=reason,
            doctor=doctor
        )
        
        # Get AI confirmation if Granite available
        ai_confirmation = None
        if self.use_granite and self.granite_service:
            ai_confirmation = self.granite_service.generate_response(
                f"Confirm authorization request submission for {service}",
                context=auth
            )
        
        return {
            "success": True,
            "request_id": request_id,
            "action": "request_auth",
            "authorization": auth,
            "ai_confirmation": ai_confirmation.get("response") if ai_confirmation else None,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _handle_submit_claim(self, request_id: str, params: Dict,
                            context: Dict) -> Dict[str, Any]:
        """Submit medical claim"""
        logger.info(f"[Agent] {request_id}: Submitting claim")
        
        required = ["scheme", "patient_id", "amount", "service", "doctor", "invoice_ref"]
        if not all(k in params for k in required):
            return self._error_response(request_id, f"Missing required parameters: {', '.join(required)}")
        
        # Call MCP tool
        claim = self.mcp_server.call_tool(
            "submit_claim",
            scheme=params["scheme"],
            patient_id=params["patient_id"],
            amount=params["amount"],
            service=params["service"],
            doctor=params["doctor"],
            invoice_ref=params["invoice_ref"]
        )
        
        # Get AI summary if Granite available
        ai_summary = None
        if self.use_granite and self.granite_service:
            ai_summary = self.granite_service.generate_response(
                f"Summarize claim submission of R{params['amount']} for {params['service']}",
                context=claim
            )
        
        return {
            "success": True,
            "request_id": request_id,
            "action": "submit_claim",
            "claim": claim,
            "ai_summary": ai_summary.get("response") if ai_summary else None,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _handle_track_claim(self, request_id: str, params: Dict,
                           context: Dict) -> Dict[str, Any]:
        """Track claim status"""
        logger.info(f"[Agent] {request_id}: Tracking claim")
        
        claim_id = params.get("claim_id")
        scheme = params.get("scheme")
        
        if not claim_id:
            return self._error_response(request_id, "Missing claim_id parameter")
        
        # Call MCP tool
        status = self.mcp_server.call_tool(
            "get_claim_status",
            claim_id=claim_id,
            scheme=scheme
        )
        
        return {
            "success": True,
            "request_id": request_id,
            "action": "track_claim",
            "claim_status": status,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _handle_compare_schemes(self, request_id: str, params: Dict,
                               context: Dict) -> Dict[str, Any]:
        """Compare medical schemes"""
        logger.info(f"[Agent] {request_id}: Comparing schemes")
        
        schemes = params.get("schemes", [])
        criteria = params.get("criteria", "coverage")
        
        if not schemes or len(schemes) < 2:
            return self._error_response(request_id, "Provide at least 2 schemes to compare")
        
        # Call MCP tool
        comparison = self.mcp_server.call_tool(
            "compare_schemes",
            schemes=schemes,
            criteria=criteria
        )
        
        # Get AI analysis if Granite available
        ai_analysis = None
        if self.use_granite and self.granite_service:
            ai_analysis = self.granite_service.generate_response(
                f"Analyze comparison of {', '.join(schemes)} schemes based on {criteria}",
                context=comparison
            )
        
        return {
            "success": True,
            "request_id": request_id,
            "action": "compare_schemes",
            "comparison": comparison,
            "ai_analysis": ai_analysis.get("response") if ai_analysis else None,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _handle_find_scheme(self, request_id: str, params: Dict,
                           context: Dict) -> Dict[str, Any]:
        """Search for medical scheme"""
        logger.info(f"[Agent] {request_id}: Searching for scheme")
        
        query = params.get("query")
        
        if not query:
            return self._error_response(request_id, "Missing query parameter")
        
        # Call MCP tool
        result = self.mcp_server.call_tool(
            "search_scheme",
            query=query
        )
        
        return {
            "success": True,
            "request_id": request_id,
            "action": "find_scheme",
            "search_result": result,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _handle_get_contact(self, request_id: str, params: Dict,
                           context: Dict) -> Dict[str, Any]:
        """Get scheme contact information"""
        logger.info(f"[Agent] {request_id}: Getting contact info")
        
        scheme = params.get("scheme")
        
        if not scheme:
            return self._error_response(request_id, "Missing scheme parameter")
        
        # Call MCP tool
        contact = self.mcp_server.call_tool(
            "get_scheme_contact",
            scheme=scheme
        )
        
        return {
            "success": True,
            "request_id": request_id,
            "action": "get_contact",
            "contact_info": contact,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _handle_health_tips(self, request_id: str, params: Dict,
                           context: Dict) -> Dict[str, Any]:
        """Get healthcare tips"""
        logger.info(f"[Agent] {request_id}: Getting health tips")
        
        service_type = params.get("service_type")
        
        # Call MCP tool
        tips = self.mcp_server.call_tool(
            "get_healthcare_tips",
            service_type=service_type
        )
        
        return {
            "success": True,
            "request_id": request_id,
            "action": "health_tips",
            "tips": tips,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _error_response(self, request_id: str, error: str) -> Dict[str, Any]:
        """Generate error response"""
        logger.error(f"[Agent] {request_id}: {error}")
        
        return {
            "success": False,
            "request_id": request_id,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get agent operational status"""
        return {
            "agent": "Medical Scheme Agent",
            "status": "operational",
            "mcp_tools": self.mcp_server.get_available_tools(),
            "granite_enabled": self.use_granite,
            "granite_loaded": self.granite_service.model_loaded if self.use_granite else False,
            "timestamp": datetime.now().isoformat(),
        }


# ============================================================================
# SIMPLE API INTERFACE
# ============================================================================

class MedicalSchemeAPI:
    """Simple REST-like API for Medical Scheme Agent"""
    
    def __init__(self):
        """Initialize API"""
        self.orchestrator = MedicalSchemeAgentOrchestrator(use_granite=True)
        logger.info("[API] Medical Scheme API initialized")
    
    def process_request(self, request_json: str) -> str:
        """
        Process JSON request
        
        Args:
            request_json: JSON string with request
            
        Returns:
            JSON response string
        """
        try:
            request = json.loads(request_json)
            response = self.orchestrator.handle_request(request)
            return json.dumps(response, indent=2, default=str)
        except json.JSONDecodeError:
            return json.dumps({
                "success": False,
                "error": "Invalid JSON format"
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, indent=2)
    
    def get_status(self) -> str:
        """Get API status"""
        return json.dumps(self.orchestrator.get_agent_status(), indent=2)


# ============================================================================
# DEMONSTRATION & TESTING
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🏥 Medical Scheme Agent - Orchestrator & API")
    print("="*70 + "\n")
    
    # Initialize orchestrator
    orchestrator = MedicalSchemeAgentOrchestrator(use_granite=True)
    
    # Display status
    status = orchestrator.get_agent_status()
    print(f"✅ Agent Status: {status['status']}")
    print(f"✅ Granite Enabled: {status['granite_enabled']}")
    print(f"✅ Available MCP Tools: {status['mcp_tools']['total_tools']}\n")
    
    # Test request 1: Find scheme
    print("Test 1: Finding medical scheme")
    print("-" * 70)
    request1 = {
        "request_id": "test-001",
        "action": "find_scheme",
        "params": {"query": "Discovery"},
        "context": {}
    }
    result1 = orchestrator.handle_request(request1)
    print(f"Scheme found: {result1['search_result']['found']} result(s)")
    
    # Test request 2: Check benefits
    print("\nTest 2: Checking patient benefits")
    print("-" * 70)
    request2 = {
        "request_id": "test-002",
        "action": "check_benefits",
        "params": {
            "scheme": "discovery",
            "patient_id": "PAT-00123",
            "service": "mri"
        },
        "context": {}
    }
    result2 = orchestrator.handle_request(request2)
    print(f"Coverage: {result2['coverage']['coverage']}")
    print(f"Limit: {result2['coverage']['limit']}")
    
    # Test request 3: Compare schemes
    print("\nTest 3: Comparing schemes")
    print("-" * 70)
    request3 = {
        "request_id": "test-003",
        "action": "compare_schemes",
        "params": {
            "schemes": ["discovery", "bonitas", "momentum"],
            "criteria": "coverage"
        },
        "context": {}
    }
    result3 = orchestrator.handle_request(request3)
    print(f"Schemes compared: {result3['comparison']['schemes_compared']}")
    
    print("\n" + "="*70)
    print("✅ Orchestrator & API ready for deployment")
    print("="*70 + "\n")
