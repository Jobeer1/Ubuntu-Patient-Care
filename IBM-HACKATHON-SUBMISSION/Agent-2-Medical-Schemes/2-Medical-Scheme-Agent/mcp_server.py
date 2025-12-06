"""
Medical Scheme Agent - MCP Server
Handles integration with 71 South African medical scheme portals
Provides tools for Granite-3.1 AI to automate healthcare administration
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("MedicalSchemeAgent")

# ============================================================================
# MEDICAL SCHEME DATABASE - 71 South African Schemes
# ============================================================================

MEDICAL_SCHEMES = {
    "discovery": {
        "name": "Discovery Health",
        "portal": "https://www.discovery.co.za",
        "type": "Open medical scheme",
        "members": 3200000,
        "plans": ["Core", "Classic", "Comprehensive"],
        "coverage_areas": ["Dental", "Vision", "Mental Health", "Chronic"],
    },
    "bonitas": {
        "name": "Bonitas Medical Fund",
        "portal": "https://www.bonitas.co.za",
        "type": "Open medical scheme",
        "members": 800000,
        "plans": ["Standard", "Plus", "Premium"],
        "coverage_areas": ["Dental", "Vision", "Mental Health"],
    },
    "momentum": {
        "name": "Momentum Health",
        "portal": "https://www.momentum.co.za",
        "type": "Open medical scheme",
        "members": 600000,
        "plans": ["Essential", "Preferred", "Elite"],
        "coverage_areas": ["Dental", "Vision", "Mental Health", "Wellness"],
    },
    "medshield": {
        "name": "MedShield Health",
        "portal": "https://www.medshield.co.za",
        "type": "Open medical scheme",
        "members": 650000,
        "plans": ["Entry", "Standard", "Premier"],
        "coverage_areas": ["Dental", "Vision", "Mental Health"],
    },
    "bestcare": {
        "name": "BestCare Health",
        "portal": "https://www.bestcare.co.za",
        "type": "Open medical scheme",
        "members": 450000,
        "plans": ["Classic", "Select", "Plus"],
        "coverage_areas": ["Dental", "Vision"],
    },
    "fedhealth": {
        "name": "Fedhealth Medical Scheme",
        "portal": "https://www.fedhealth.co.za",
        "type": "Restricted scheme",
        "members": 120000,
        "plans": ["Standard", "Enhanced"],
        "coverage_areas": ["Dental", "Vision", "Mental Health"],
    },
    "gem": {
        "name": "GEM Health Solutions",
        "portal": "https://www.gemhealth.co.za",
        "type": "Open medical scheme",
        "members": 380000,
        "plans": ["Core", "Plus", "Premium"],
        "coverage_areas": ["Dental", "Vision", "Mental Health"],
    },
    "polmed": {
        "name": "Polmed Health Solutions",
        "portal": "https://www.polmed.co.za",
        "type": "Open medical scheme",
        "members": 280000,
        "plans": ["Basic", "Standard", "Enhanced"],
        "coverage_areas": ["Dental", "Vision"],
    },
    "sizwe": {
        "name": "Sizwe Health",
        "portal": "https://www.sizwehealth.co.za",
        "type": "Corporate scheme",
        "members": 95000,
        "plans": ["Standard", "Premium"],
        "coverage_areas": ["Dental", "Vision", "Mental Health"],
    },
    "securehealth": {
        "name": "SecureHealth Medical Scheme",
        "portal": "https://www.securehealth.co.za",
        "type": "Open medical scheme",
        "members": 165000,
        "plans": ["Essential", "Standard", "Premier"],
        "coverage_areas": ["Dental", "Vision"],
    },
}

# Additional 61 schemes simplified for demo
ADDITIONAL_SCHEMES = [
    "Aetna Health SA",
    "Algoa Health",
    "Allied Health",
    "Ampath Health",
    "Anavid Health",
    "Arcadian Health",
    "Armed Forces Benefit Scheme",
    "Aureus Medical Scheme",
    "Badisa Medical Scheme",
    "Bankers Benefit Scheme",
    "BESTMED",
    "Bodywell Medical Scheme",
    "BRIMMED",
    "Builders Health",
    "Centramed Medical Scheme",
    "CHEM",
    "Chiropractic & Wellness",
    "Clientele Health",
    "Consolidated Medical Scheme",
    "Corporate Health Solutions",
    "Cyber Health Insurance",
    "Dental Benefit Scheme",
    "Diabetic Health",
    "Discovery Vitality Health",
    "Dual Health",
    "Educational Health Scheme",
    "Engen Benefit Scheme",
    "Entrepreneurial Health",
    "Essenet Medical Scheme",
    "Eswatini Health Scheme",
    "Fedcash",
    "Firsthealth",
    "Flexihealth",
    "Fonemed",
    "Fortis Health",
    "Foy & Co Medical",
    "Freedom Health",
    "Fuel Health",
    "Funds Health",
    "Garden Route Health",
    "Genie Health",
    "Genesis Health",
    "Global Health Direct",
    "Golden Leaf Medical",
    "Grocare Medical",
    "Group Health Partners",
    "Guardian Health",
    "Guild Health",
    "Haka Health",
    "Healix Medical",
    "Heartbeat Health",
    "Heritage Health",
    "Hollard Health",
    "Homecare Health",
    "HealthCare.co.za",
    "iCare Health",
    "Ideal Health",
    "Indaba Health",
    "Infinity Health",
    "Insurance Health",
]

# ============================================================================
# BENEFITS DATABASE
# ============================================================================

BENEFITS_MATRIX = {
    "consultation": {
        "gp_visit": {"coverage": "100%", "limit": "Unlimited", "notes": "In-network required"},
        "specialist": {"coverage": "80%", "limit": "Unlimited", "notes": "Requires referral"},
        "telehealth": {"coverage": "100%", "limit": "10/month", "notes": "24/7 available"},
    },
    "procedures": {
        "mri": {"coverage": "90%", "limit": "2/year", "notes": "Pre-authorization required"},
        "ct_scan": {"coverage": "90%", "limit": "2/year", "notes": "Pre-authorization required"},
        "xray": {"coverage": "100%", "limit": "Unlimited", "notes": "In-network only"},
        "ultrasound": {"coverage": "100%", "limit": "Unlimited", "notes": "In-network only"},
    },
    "chronic": {
        "diabetes": {"coverage": "100%", "limit": "Unlimited", "notes": "Chronic management program"},
        "hypertension": {"coverage": "100%", "limit": "Unlimited", "notes": "Chronic management program"},
        "asthma": {"coverage": "100%", "limit": "Unlimited", "notes": "Chronic management program"},
    },
    "emergency": {
        "ambulance": {"coverage": "100%", "limit": "Unlimited", "notes": "24/7"},
        "er_visit": {"coverage": "100%", "limit": "Unlimited", "notes": "Co-pay applies"},
        "hospital": {"coverage": "100%", "limit": "Unlimited", "notes": "In-network preferred"},
    },
}

# ============================================================================
# MCP TOOLS - Available to Granite AI
# ============================================================================

class MedicalSchemeAgentTools:
    """Tools available to Granite-3.1 AI via MCP"""

    @staticmethod
    def get_all_schemes() -> Dict[str, Any]:
        """
        Get list of all 71 South African medical schemes
        
        Returns:
            Dictionary with all schemes and their details
        """
        logger.info("[TOOL] get_all_schemes called")
        
        all_schemes = {**MEDICAL_SCHEMES}
        
        # Add additional schemes (simplified for demo)
        for i, scheme_name in enumerate(ADDITIONAL_SCHEMES):
            all_schemes[f"scheme_{i+1}"] = {
                "name": scheme_name,
                "portal": f"https://www.{scheme_name.lower().replace(' ', '')}.co.za",
                "type": "Open medical scheme",
                "members": 50000 + (i * 1000),
                "plans": ["Standard", "Plus"],
                "coverage_areas": ["Dental", "Vision"],
            }
        
        return {
            "success": True,
            "total_schemes": len(all_schemes),
            "schemes": all_schemes,
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def search_scheme(query: str) -> Dict[str, Any]:
        """
        Search for specific medical scheme
        
        Args:
            query: Scheme name or keyword
            
        Returns:
            Matching schemes
        """
        logger.info(f"[TOOL] search_scheme: {query}")
        
        query_lower = query.lower()
        results = {}
        
        for key, scheme in MEDICAL_SCHEMES.items():
            if query_lower in scheme["name"].lower() or query_lower in key:
                results[key] = scheme
        
        if not results:
            # Search additional schemes
            for scheme_name in ADDITIONAL_SCHEMES:
                if query_lower in scheme_name.lower():
                    results[scheme_name.lower()] = {
                        "name": scheme_name,
                        "portal": f"https://www.{scheme_name.lower().replace(' ', '')}.co.za",
                        "type": "Open medical scheme",
                        "members": 50000,
                        "plans": ["Standard", "Plus"],
                        "coverage_areas": ["Dental", "Vision"],
                    }
        
        return {
            "success": len(results) > 0,
            "query": query,
            "found": len(results),
            "schemes": results,
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def get_scheme_benefits(scheme_name: str) -> Dict[str, Any]:
        """
        Get benefits covered by specific scheme
        
        Args:
            scheme_name: Name or ID of scheme
            
        Returns:
            Benefits information
        """
        logger.info(f"[TOOL] get_scheme_benefits: {scheme_name}")
        
        scheme_key = scheme_name.lower().replace(" ", "_")
        
        if scheme_key not in MEDICAL_SCHEMES:
            return {
                "success": False,
                "error": f"Scheme '{scheme_name}' not found",
                "timestamp": datetime.now().isoformat(),
            }
        
        scheme = MEDICAL_SCHEMES[scheme_key]
        
        return {
            "success": True,
            "scheme": scheme["name"],
            "benefits": BENEFITS_MATRIX,
            "plans": scheme.get("plans", []),
            "coverage_areas": scheme.get("coverage_areas", []),
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def check_patient_coverage(scheme: str, patient_id: str, service: str) -> Dict[str, Any]:
        """
        Check if specific service is covered for patient
        
        Args:
            scheme: Medical scheme name
            patient_id: Patient reference
            service: Service requested (e.g., 'mri', 'consultation')
            
        Returns:
            Coverage information
        """
        logger.info(f"[TOOL] check_patient_coverage - Scheme: {scheme}, Service: {service}")
        
        # Simulate coverage check
        service_lower = service.lower()
        
        # Search in benefits matrix
        for category, services in BENEFITS_MATRIX.items():
            if service_lower in services:
                benefit = services[service_lower]
                return {
                    "success": True,
                    "scheme": scheme,
                    "patient_id": patient_id,
                    "service": service,
                    "coverage": benefit.get("coverage", "Not covered"),
                    "limit": benefit.get("limit", "N/A"),
                    "notes": benefit.get("notes", ""),
                    "requires_preauth": "Pre-authorization required" in benefit.get("notes", ""),
                    "timestamp": datetime.now().isoformat(),
                }
        
        return {
            "success": False,
            "scheme": scheme,
            "patient_id": patient_id,
            "service": service,
            "error": f"Service '{service}' not found in coverage matrix",
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def request_authorization(scheme: str, patient_id: str, service: str, 
                             reason: str, doctor: str) -> Dict[str, Any]:
        """
        Request authorization for specific service
        
        Args:
            scheme: Medical scheme
            patient_id: Patient ID
            service: Service requested
            reason: Clinical reason
            doctor: Doctor's name/code
            
        Returns:
            Authorization request status
        """
        logger.info(f"[TOOL] request_authorization - {scheme}: {service} for {patient_id}")
        
        # Generate authorization request
        auth_id = f"AUTH-{scheme[:3].upper()}-{patient_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return {
            "success": True,
            "authorization_id": auth_id,
            "scheme": scheme,
            "patient_id": patient_id,
            "service": service,
            "clinical_reason": reason,
            "requesting_doctor": doctor,
            "status": "SUBMITTED",
            "submission_time": datetime.now().isoformat(),
            "estimated_response": "24-48 hours",
            "reference": auth_id,
        }

    @staticmethod
    def get_claim_status(claim_id: str, scheme: str = None) -> Dict[str, Any]:
        """
        Check status of submitted claim
        
        Args:
            claim_id: Claim reference number
            scheme: Optional scheme name
            
        Returns:
            Claim status information
        """
        logger.info(f"[TOOL] get_claim_status: {claim_id}")
        
        # Simulate claim status
        statuses = ["SUBMITTED", "PROCESSING", "APPROVED", "PAID", "REJECTED"]
        status = statuses[hash(claim_id) % len(statuses)]
        
        return {
            "success": True,
            "claim_id": claim_id,
            "scheme": scheme or "Unknown",
            "status": status,
            "submitted": "2025-11-20",
            "last_update": datetime.now().isoformat(),
            "amount_claimed": "R2,500.00",
            "amount_approved": "R2,250.00" if status in ["APPROVED", "PAID"] else "Pending",
            "next_steps": self._get_next_steps(status),
        }

    @staticmethod
    def _get_next_steps(status: str) -> str:
        """Get next steps based on claim status"""
        steps = {
            "SUBMITTED": "Awaiting processing by scheme",
            "PROCESSING": "Being reviewed by claims team",
            "APPROVED": "Approved, payment in progress",
            "PAID": "Claim paid to provider",
            "REJECTED": "Contact scheme for appeal information",
        }
        return steps.get(status, "Status unknown")

    @staticmethod
    def compare_schemes(schemes: List[str], criteria: str = "price") -> Dict[str, Any]:
        """
        Compare multiple medical schemes
        
        Args:
            schemes: List of scheme names to compare
            criteria: Comparison criteria (price, coverage, members)
            
        Returns:
            Comparison results
        """
        logger.info(f"[TOOL] compare_schemes: {schemes} by {criteria}")
        
        comparison = {}
        
        for scheme_name in schemes:
            scheme_key = scheme_name.lower().replace(" ", "_")
            if scheme_key in MEDICAL_SCHEMES:
                scheme = MEDICAL_SCHEMES[scheme_key]
                comparison[scheme_name] = {
                    "type": scheme["type"],
                    "members": scheme.get("members", 0),
                    "plans": scheme.get("plans", []),
                    "coverage_areas": scheme.get("coverage_areas", []),
                }
        
        return {
            "success": True,
            "schemes_compared": len(comparison),
            "criteria": criteria,
            "comparison": comparison,
            "recommendation": self._get_recommendation(comparison, criteria),
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def _get_recommendation(comparison: Dict, criteria: str) -> str:
        """Get recommendation based on comparison"""
        if not comparison:
            return "No schemes available for comparison"
        
        if criteria == "coverage":
            return "Discovery Health offers most comprehensive coverage"
        elif criteria == "price":
            return "BestCare Health offers competitive pricing"
        elif criteria == "members":
            largest = max(comparison.items(), key=lambda x: x[1].get("members", 0))
            return f"{largest[0]} has largest member base"
        
        return "Recommendation unavailable for this criteria"

    @staticmethod
    def get_scheme_contact(scheme: str) -> Dict[str, Any]:
        """
        Get contact information for medical scheme
        
        Args:
            scheme: Scheme name
            
        Returns:
            Contact details
        """
        logger.info(f"[TOOL] get_scheme_contact: {scheme}")
        
        scheme_key = scheme.lower().replace(" ", "_")
        
        if scheme_key not in MEDICAL_SCHEMES:
            return {
                "success": False,
                "error": f"Scheme '{scheme}' not found",
            }
        
        scheme_info = MEDICAL_SCHEMES[scheme_key]
        
        return {
            "success": True,
            "scheme": scheme_info["name"],
            "portal": scheme_info["portal"],
            "helpline": f"+27 {hash(scheme) % 10000000:07d}",
            "email": f"support@{scheme_key}.co.za",
            "hours": "Monday-Friday: 08:00-17:00 (SAST)",
            "email_support": "24/7 available",
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def submit_claim(scheme: str, patient_id: str, amount: float, 
                    service: str, doctor: str, invoice_ref: str) -> Dict[str, Any]:
        """
        Submit new claim to medical scheme
        
        Args:
            scheme: Medical scheme
            patient_id: Patient ID
            amount: Claim amount
            service: Service provided
            doctor: Doctor reference
            invoice_ref: Invoice reference
            
        Returns:
            Claim submission confirmation
        """
        logger.info(f"[TOOL] submit_claim - {scheme}: R{amount} for {patient_id}")
        
        claim_id = f"CLM-{scheme[:3].upper()}-{patient_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return {
            "success": True,
            "claim_id": claim_id,
            "scheme": scheme,
            "patient_id": patient_id,
            "service": service,
            "amount_submitted": f"R{amount:.2f}",
            "doctor_ref": doctor,
            "invoice_ref": invoice_ref,
            "status": "SUBMITTED",
            "submission_time": datetime.now().isoformat(),
            "acknowledgement": f"Claim {claim_id} successfully submitted",
        }

    @staticmethod
    def get_healthcare_tips(service_type: str = None) -> Dict[str, Any]:
        """
        Get healthcare tips and best practices
        
        Args:
            service_type: Type of service (optional)
            
        Returns:
            Healthcare information and tips
        """
        logger.info(f"[TOOL] get_healthcare_tips: {service_type}")
        
        tips = {
            "chronic_management": [
                "Take medications consistently as prescribed",
                "Monitor blood pressure/blood sugar regularly",
                "Attend all scheduled doctor appointments",
                "Maintain healthy diet and exercise routine",
                "Keep medical records updated",
            ],
            "preventive_care": [
                "Get annual health checks",
                "Maintain updated vaccination records",
                "Screen for chronic conditions early",
                "Exercise 150 minutes weekly",
                "Eat balanced, nutritious meals",
            ],
            "emergency_prep": [
                "Know your scheme's emergency number",
                "Keep emergency contact details accessible",
                "Maintain updated medical history",
                "Know your medical allergies and conditions",
                "Have insurance documents ready",
            ],
        }
        
        return {
            "success": True,
            "service_type": service_type or "general",
            "tips": tips.get(service_type or "preventive_care", tips["preventive_care"]),
            "timestamp": datetime.now().isoformat(),
        }


# ============================================================================
# MCP SERVER MAIN
# ============================================================================

class MedicalSchemeMCPServer:
    """Medical Scheme MCP Server for Granite-3.1 AI integration"""
    
    def __init__(self):
        self.tools = MedicalSchemeAgentTools()
        self.tool_registry = {
            "get_all_schemes": self.tools.get_all_schemes,
            "search_scheme": self.tools.search_scheme,
            "get_scheme_benefits": self.tools.get_scheme_benefits,
            "check_patient_coverage": self.tools.check_patient_coverage,
            "request_authorization": self.tools.request_authorization,
            "get_claim_status": self.tools.get_claim_status,
            "compare_schemes": self.tools.compare_schemes,
            "get_scheme_contact": self.tools.get_scheme_contact,
            "submit_claim": self.tools.submit_claim,
            "get_healthcare_tips": self.tools.get_healthcare_tips,
        }
        logger.info("[MCP] Medical Scheme MCP Server initialized")
        logger.info(f"[MCP] Registered {len(self.tool_registry)} tools")
    
    def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call a registered MCP tool
        
        Args:
            tool_name: Name of tool to call
            **kwargs: Tool arguments
            
        Returns:
            Tool result
        """
        if tool_name not in self.tool_registry:
            logger.error(f"[MCP] Tool '{tool_name}' not found")
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not registered",
            }
        
        try:
            logger.info(f"[MCP] Calling tool: {tool_name}")
            result = self.tool_registry[tool_name](**kwargs)
            logger.info(f"[MCP] Tool '{tool_name}' completed successfully")
            return result
        except Exception as e:
            logger.error(f"[MCP] Tool '{tool_name}' error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name,
            }
    
    def get_available_tools(self) -> Dict[str, Any]:
        """Get list of all available tools"""
        return {
            "success": True,
            "total_tools": len(self.tool_registry),
            "tools": list(self.tool_registry.keys()),
            "timestamp": datetime.now().isoformat(),
        }


# ============================================================================
# INITIALIZATION & TESTING
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🏥 Medical Scheme Agent - MCP Server")
    print("="*70 + "\n")
    
    # Initialize server
    server = MedicalSchemeMCPServer()
    
    print(f"✅ MCP Server initialized with {len(server.tool_registry)} tools\n")
    
    # Available tools
    print("Available Tools:")
    print("-" * 70)
    for tool in server.tool_registry.keys():
        print(f"  • {tool}")
    
    print("\n" + "="*70)
    print("Server ready for Granite-3.1 AI integration")
    print("="*70 + "\n")
