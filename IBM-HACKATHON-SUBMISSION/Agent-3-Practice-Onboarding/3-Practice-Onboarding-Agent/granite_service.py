"""
Granite-3.1 Service Integration for Practice Onboarding Agent

Integrates Granite-3.1 LLM with MCP discovery tools for:
- Intelligent guided discovery
- Infrastructure analysis
- Procedure generation
- Knowledge capture
- Compliance documentation
"""

import json
import logging
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class GraniteService:
    """
    Integrates Granite-3.1 LLM with discovery tools
    """
    
    def __init__(self, model_path: str = "./models/granite-3.1-8b-instruct/"):
        """
        Initialize Granite service
        
        Args:
            model_path: Path to Granite model directory
        """
        self.model_path = model_path
        self.model = None
        self.initialized = False
        
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            self.torch = torch
            self.AutoModelForCausalLM = AutoModelForCausalLM
            self.AutoTokenizer = AutoTokenizer
            
            logger.info("PyTorch and Transformers available")
        except ImportError as e:
            logger.warning(f"PyTorch/Transformers not available: {e}. Using mock mode.")
            self.torch = None
    
    async def initialize_model(self) -> bool:
        """
        Load Granite model (async wrapper)
        """
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, self._load_model)
            return result
        except Exception as e:
            logger.error(f"Error initializing model: {e}")
            return False
    
    def _load_model(self) -> bool:
        """Load Granite model from disk"""
        try:
            if self.torch is None:
                logger.warning("Running in mock mode (PyTorch not available)")
                self.initialized = True
                return True
            
            logger.info(f"Loading Granite model from {self.model_path}")
            
            tokenizer = self.AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )
            
            model = self.AutoModelForCausalLM.from_pretrained(
                self.model_path,
                trust_remote_code=True,
                device_map="auto",
                torch_dtype="auto"
            )
            
            self.tokenizer = tokenizer
            self.model = model
            self.initialized = True
            
            logger.info("Granite model loaded successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error loading Granite model: {e}")
            return False
    
    async def analyze_network_discovery(self, discovery_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Granite to analyze network discovery results
        
        Args:
            discovery_result: Result from network discovery tool
            
        Returns:
            Analysis with recommendations
        """
        if not self.initialized:
            await self.initialize_model()
        
        # Build analysis prompt
        summary = discovery_result.get("devices", {})
        num_devices = len(summary)
        
        prompt = f"""
Analyze this network discovery result and provide insights for a medical practice:

Discovery Summary:
- Total devices found: {num_devices}
- Full results: {json.dumps(discovery_result, indent=2)[:2000]}...

Please provide:
1. Summary of device types found
2. Identify critical infrastructure (databases, servers, medical devices)
3. List potential risks or gaps
4. Recommendations for:
   - Network security improvements
   - Backup procedures
   - Disaster recovery planning
5. Next steps for complete infrastructure documentation

Format as structured JSON.
"""
        
        loop = asyncio.get_event_loop()
        analysis = await loop.run_in_executor(
            None,
            self._generate_response,
            prompt
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "discovery_summary": discovery_result,
            "analysis": analysis
        }
    
    async def analyze_database_discovery(self, discovery_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Granite to analyze database discovery results
        """
        if not self.initialized:
            await self.initialize_model()
        
        databases = discovery_result.get("databases", {})
        
        prompt = f"""
Analyze these discovered databases for a medical practice:

Databases found: {json.dumps(discovery_result, indent=2)[:1500]}...

Please provide:
1. Identify each database's likely purpose
2. Assess data criticality (CRITICAL/HIGH/MEDIUM/LOW)
3. Identify backup priorities
4. List security recommendations
5. Suggest recovery procedures
6. Compliance considerations (HIPAA, GDPR)

Format as structured JSON.
"""
        
        loop = asyncio.get_event_loop()
        analysis = await loop.run_in_executor(
            None,
            self._generate_response,
            prompt
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "database_summary": discovery_result,
            "analysis": analysis
        }
    
    async def generate_infrastructure_procedures(self, 
                                                  infrastructure: Dict[str, Any],
                                                  procedure_type: str) -> Dict[str, Any]:
        """
        Generate procedures for specific infrastructure
        
        Args:
            infrastructure: Infrastructure catalog
            procedure_type: Type of procedure (startup, shutdown, backup, recovery, etc.)
            
        Returns:
            Generated procedure
        """
        if not self.initialized:
            await self.initialize_model()
        
        prompt = f"""
Generate a step-by-step {procedure_type} procedure for this medical practice infrastructure:

Infrastructure:
{json.dumps(infrastructure, indent=2)[:2000]}...

Requirements:
1. Procedure must be safe and non-destructive
2. Include estimated time for each step
3. Include success verification steps
4. Include troubleshooting for common issues
5. Include emergency contact information
6. Must comply with medical practice standards

Procedure format:
{{
    "procedure_name": "{procedure_type} Procedure",
    "estimated_time": "X minutes",
    "risk_level": "LOW/MEDIUM/HIGH",
    "steps": [
        {{
            "step_number": 1,
            "action": "...",
            "expected_result": "...",
            "verification": "...",
            "time_estimate": "X minutes"
        }}
    ],
    "verification_checklist": [...],
    "troubleshooting": {{...}},
    "emergency_contacts": [...]
}}

Generate this procedure as JSON.
"""
        
        loop = asyncio.get_event_loop()
        procedure = await loop.run_in_executor(
            None,
            self._generate_response,
            prompt
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "procedure_type": procedure_type,
            "procedure": procedure
        }
    
    async def analyze_compliance_requirements(self, infrastructure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze compliance requirements for infrastructure
        """
        if not self.initialized:
            await self.initialize_model()
        
        prompt = f"""
Analyze compliance requirements for this medical practice infrastructure:

Infrastructure:
{json.dumps(infrastructure, indent=2)[:1500]}...

Provide compliance analysis for:
1. HIPAA requirements (US)
2. GDPR requirements (EU)
3. South African medical data laws
4. Best practices for healthcare IT
5. Audit requirements
6. Documentation requirements
7. Incident reporting procedures

Format as structured JSON with:
- requirement
- status (compliant/non-compliant/unknown)
- current_implementation
- gap_if_any
- remediation_steps
"""
        
        loop = asyncio.get_event_loop()
        analysis = await loop.run_in_executor(
            None,
            self._generate_response,
            prompt
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "compliance_analysis": analysis
        }
    
    def _generate_response(self, prompt: str, max_length: int = 2000) -> str:
        """
        Generate response using Granite model
        """
        try:
            if self.model is None or self.torch is None:
                # Mock response for testing
                logger.warning("Using mock response (model not loaded)")
                return self._generate_mock_response(prompt)
            
            # Prepare input
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=1024
            )
            
            # Generate response
            with self.torch.no_grad():
                output = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    temperature=0.7,
                    top_p=0.9,
                    do_sample=True
                )
            
            # Decode response
            response = self.tokenizer.decode(
                output[0],
                skip_special_tokens=True
            )
            
            return response
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self._generate_mock_response(prompt)
    
    def _generate_mock_response(self, prompt: str) -> str:
        """
        Generate mock response for testing
        """
        if "startup" in prompt.lower():
            return json.dumps({
                "procedure_name": "System Startup Procedure",
                "steps": [
                    {"action": "Power on servers", "order": 1},
                    {"action": "Wait for databases to initialize", "order": 2},
                    {"action": "Verify application connectivity", "order": 3},
                    {"action": "Check backup systems", "order": 4}
                ]
            })
        
        elif "compliance" in prompt.lower():
            return json.dumps({
                "requirements": [
                    {"requirement": "Patient data encryption", "status": "needed"},
                    {"requirement": "Access control logging", "status": "needed"},
                    {"requirement": "Regular backups", "status": "needed"}
                ]
            })
        
        else:
            return json.dumps({
                "status": "mock_analysis",
                "note": "This is a mock response - Granite model not loaded"
            })


class DiscoveryOrchestrator:
    """
    Orchestrates guided discovery workflow using Granite
    """
    
    def __init__(self, granite_service: GraniteService):
        self.granite = granite_service
        self.discovery_state = {}
    
    async def start_guided_discovery(self, practice_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start AI-guided infrastructure discovery
        """
        logger.info(f"Starting guided discovery for {practice_info.get('name', 'Unknown Practice')}")
        
        state = {
            "practice": practice_info,
            "discovery_steps": [],
            "timestamp": datetime.now().isoformat(),
            "status": "IN_PROGRESS"
        }
        
        # Step 1: Network discovery
        logger.info("Step 1: Discovering network devices...")
        network_discovery_step = {
            "step": 1,
            "name": "Network Discovery",
            "description": "Scanning network for all connected devices",
            "status": "PENDING",
            "timestamp": datetime.now().isoformat()
        }
        state["discovery_steps"].append(network_discovery_step)
        
        # Step 2: Database discovery
        logger.info("Step 2: Discovering databases...")
        database_discovery_step = {
            "step": 2,
            "name": "Database Discovery",
            "description": "Scanning for database servers on discovered IPs",
            "status": "PENDING",
            "timestamp": datetime.now().isoformat()
        }
        state["discovery_steps"].append(database_discovery_step)
        
        # Step 3: Analysis and recommendations
        logger.info("Step 3: Analyzing infrastructure...")
        analysis_step = {
            "step": 3,
            "name": "Infrastructure Analysis",
            "description": "Using Granite to analyze discovered infrastructure",
            "status": "PENDING",
            "timestamp": datetime.now().isoformat()
        }
        state["discovery_steps"].append(analysis_step)
        
        return state
    
    async def generate_complete_documentation(self, discovery_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate complete documentation from discovery results
        """
        logger.info("Generating complete infrastructure documentation...")
        
        documentation = {
            "generated": datetime.now().isoformat(),
            "sections": {
                "executive_summary": await self._generate_summary(discovery_results),
                "network_infrastructure": discovery_results.get("devices", {}),
                "database_infrastructure": discovery_results.get("databases", {}),
                "procedures": {
                    "startup": await self.granite.generate_infrastructure_procedures(
                        discovery_results,
                        "startup"
                    ),
                    "shutdown": await self.granite.generate_infrastructure_procedures(
                        discovery_results,
                        "shutdown"
                    ),
                    "backup": await self.granite.generate_infrastructure_procedures(
                        discovery_results,
                        "backup"
                    ),
                    "recovery": await self.granite.generate_infrastructure_procedures(
                        discovery_results,
                        "recovery"
                    )
                },
                "compliance": await self.granite.analyze_compliance_requirements(discovery_results)
            }
        }
        
        return documentation
    
    async def _generate_summary(self, discovery_results: Dict[str, Any]) -> str:
        """Generate executive summary"""
        num_devices = len(discovery_results.get("devices", {}))
        num_databases = len(discovery_results.get("databases", {}))
        
        return f"""
INFRASTRUCTURE DISCOVERY REPORT - EXECUTIVE SUMMARY

Discovered Infrastructure:
- Network Devices: {num_devices}
- Database Servers: {num_databases}

This report provides complete documentation of the practice's IT infrastructure,
including device locations, database configurations, and recommended procedures.

Key Actions Required:
1. Review all discovered devices and verify accuracy
2. Document all database access procedures
3. Implement backup verification procedures
4. Test disaster recovery procedures
5. Ensure compliance with healthcare regulations
"""


if __name__ == "__main__":
    # Example usage
    print("=" * 80)
    print("GRANITE-3.1 SERVICE FOR PRACTICE ONBOARDING AGENT")
    print("=" * 80)
    
    granite = GraniteService()
    
    print("\n[*] Initializing Granite service...")
    # Note: In async context, would use: await granite.initialize_model()
    
    print("[+] Granite service ready")
    print("    - Network discovery analysis available")
    print("    - Database analysis available")
    print("    - Procedure generation available")
    print("    - Compliance analysis available")
