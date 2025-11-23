"""
Practice Onboarding Agent Orchestrator

Coordinates all discovery, analysis, and documentation workflows
using MCP tools and Granite-3.1 AI
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class PracticeOnboardingOrchestrator:
    """
    Main orchestrator for practice onboarding workflows
    """
    
    def __init__(self):
        """Initialize orchestrator"""
        self.discovery_results = {}
        self.current_practice = None
        self.workflow_history = []
        self.infrastructure_catalog = None
        
        # Import discovery tools
        try:
            from mcp_server import discovery_manager
            from granite_service import GraniteService, DiscoveryOrchestrator
            
            self.discovery_manager = discovery_manager
            self.granite_service = GraniteService()
            self.granite_orchestrator = DiscoveryOrchestrator(self.granite_service)
        except ImportError as e:
            logger.warning(f"MCP tools not available: {e}")
            self.discovery_manager = None
            self.granite_service = None
            self.granite_orchestrator = None
    
    async def initialize(self) -> bool:
        """Initialize orchestrator and load models"""
        try:
            logger.info("Initializing Practice Onboarding Orchestrator...")
            
            if self.granite_service:
                await self.granite_service.initialize_model()
            
            logger.info("Orchestrator initialized successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error initializing orchestrator: {e}")
            return False
    
    async def start_new_practice_onboarding(self, practice_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start onboarding workflow for a new practice
        
        Args:
            practice_info: Practice details (name, location, network info, etc.)
            
        Returns:
            Onboarding workflow status
        """
        logger.info(f"Starting onboarding for practice: {practice_info.get('name', 'Unknown')}")
        
        self.current_practice = practice_info
        
        workflow = {
            "practice_name": practice_info.get("name"),
            "started_at": datetime.now().isoformat(),
            "status": "IN_PROGRESS",
            "phases": []
        }
        
        try:
            # Phase 1: Network Discovery
            logger.info("[Phase 1] Starting network discovery...")
            network_phase = await self._phase_1_network_discovery(practice_info)
            workflow["phases"].append(network_phase)
            
            # Phase 2: Database Discovery
            logger.info("[Phase 2] Starting database discovery...")
            database_phase = await self._phase_2_database_discovery(network_phase.get("discovered_ips", []))
            workflow["phases"].append(database_phase)
            
            # Phase 3: Infrastructure Analysis
            logger.info("[Phase 3] Analyzing infrastructure...")
            analysis_phase = await self._phase_3_analysis()
            workflow["phases"].append(analysis_phase)
            
            # Phase 4: Procedure Generation
            logger.info("[Phase 4] Generating procedures...")
            procedures_phase = await self._phase_4_procedures()
            workflow["phases"].append(procedures_phase)
            
            # Phase 5: Documentation
            logger.info("[Phase 5] Generating documentation...")
            documentation_phase = await self._phase_5_documentation()
            workflow["phases"].append(documentation_phase)
            
            workflow["status"] = "COMPLETE"
            workflow["completed_at"] = datetime.now().isoformat()
            
            self.workflow_history.append(workflow)
            
            return workflow
        
        except Exception as e:
            logger.error(f"Error in onboarding workflow: {e}")
            workflow["status"] = "FAILED"
            workflow["error"] = str(e)
            return workflow
    
    async def _phase_1_network_discovery(self, practice_info: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 1: Network Discovery"""
        
        phase = {
            "phase": 1,
            "name": "Network Discovery",
            "started_at": datetime.now().isoformat(),
            "status": "COMPLETE"
        }
        
        try:
            if not self.discovery_manager:
                logger.warning("Discovery manager not available, using mock data")
                phase["discovered_devices"] = {}
                phase["discovered_ips"] = []
                return phase
            
            # Get network range to scan
            network_cidr = practice_info.get("network_cidr", "auto")
            
            if network_cidr == "auto":
                logger.info("Auto-detecting network range...")
                result = await self.discovery_manager.discover_current_network()
            else:
                logger.info(f"Discovering network range: {network_cidr}")
                result = await self.discovery_manager.discover_network_range(network_cidr)
            
            if result.get("status") == "COMPLETE":
                # Extract discovered devices
                devices = result.get("devices", {})
                phase["discovered_devices"] = devices
                phase["device_count"] = len(devices)
                phase["discovered_ips"] = list(devices.keys())
                
                # Get device summary
                summary = await self.discovery_manager.get_device_summary()
                phase["device_summary"] = summary
                
                logger.info(f"Phase 1 complete: {len(devices)} devices discovered")
            
            return phase
        
        except Exception as e:
            logger.error(f"Error in phase 1: {e}")
            phase["status"] = "FAILED"
            phase["error"] = str(e)
            return phase
    
    async def _phase_2_database_discovery(self, ips: List[str]) -> Dict[str, Any]:
        """Phase 2: Database Discovery"""
        
        phase = {
            "phase": 2,
            "name": "Database Discovery",
            "started_at": datetime.now().isoformat(),
            "status": "COMPLETE"
        }
        
        try:
            if not ips:
                logger.warning("No IPs to probe for databases")
                phase["discovered_databases"] = {}
                return phase
            
            if not self.discovery_manager:
                logger.warning("Discovery manager not available")
                phase["discovered_databases"] = {}
                return phase
            
            logger.info(f"Probing {len(ips)} IPs for databases...")
            
            # Probe for databases
            result = await self.discovery_manager.probe_database_servers(ips)
            
            if result.get("status") == "COMPLETE":
                databases = result.get("databases", {})
                phase["discovered_databases"] = databases
                phase["database_count"] = len(databases)
                
                # Get database summary
                summary = await self.discovery_manager.get_database_summary()
                phase["database_summary"] = summary
                
                logger.info(f"Phase 2 complete: {len(databases)} databases discovered")
            
            return phase
        
        except Exception as e:
            logger.error(f"Error in phase 2: {e}")
            phase["status"] = "FAILED"
            phase["error"] = str(e)
            return phase
    
    async def _phase_3_analysis(self) -> Dict[str, Any]:
        """Phase 3: Infrastructure Analysis using Granite"""
        
        phase = {
            "phase": 3,
            "name": "Infrastructure Analysis",
            "started_at": datetime.now().isoformat(),
            "status": "COMPLETE"
        }
        
        try:
            if not self.discovery_manager:
                logger.warning("Discovery manager not available")
                return phase
            
            # Get full infrastructure catalog
            catalog = await self.discovery_manager.get_infrastructure_catalog()
            self.infrastructure_catalog = catalog
            
            # Analyze with Granite if available
            if self.granite_service:
                logger.info("Analyzing with Granite-3.1...")
                
                network_analysis = await self.granite_service.analyze_network_discovery(catalog)
                phase["network_analysis"] = network_analysis
                
                database_analysis = await self.granite_service.analyze_database_discovery(catalog)
                phase["database_analysis"] = database_analysis
                
                compliance = await self.granite_service.analyze_compliance_requirements(catalog)
                phase["compliance_analysis"] = compliance
            
            logger.info("Phase 3 complete: Infrastructure analyzed")
            return phase
        
        except Exception as e:
            logger.error(f"Error in phase 3: {e}")
            phase["status"] = "FAILED"
            phase["error"] = str(e)
            return phase
    
    async def _phase_4_procedures(self) -> Dict[str, Any]:
        """Phase 4: Procedure Generation"""
        
        phase = {
            "phase": 4,
            "name": "Procedure Generation",
            "started_at": datetime.now().isoformat(),
            "status": "COMPLETE"
        }
        
        try:
            if not self.granite_service or not self.infrastructure_catalog:
                logger.warning("Granite service or infrastructure catalog not available")
                return phase
            
            logger.info("Generating procedures with Granite-3.1...")
            
            # Generate critical procedures
            procedures = {}
            
            for proc_type in ["startup", "shutdown", "backup", "recovery", "emergency_access"]:
                logger.info(f"Generating {proc_type} procedure...")
                procedure = await self.granite_service.generate_infrastructure_procedures(
                    self.infrastructure_catalog,
                    proc_type
                )
                procedures[proc_type] = procedure
            
            phase["procedures"] = procedures
            
            logger.info("Phase 4 complete: Procedures generated")
            return phase
        
        except Exception as e:
            logger.error(f"Error in phase 4: {e}")
            phase["status"] = "FAILED"
            phase["error"] = str(e)
            return phase
    
    async def _phase_5_documentation(self) -> Dict[str, Any]:
        """Phase 5: Documentation Generation"""
        
        phase = {
            "phase": 5,
            "name": "Documentation",
            "started_at": datetime.now().isoformat(),
            "status": "COMPLETE"
        }
        
        try:
            if not self.discovery_manager:
                logger.warning("Discovery manager not available")
                return phase
            
            logger.info("Exporting discovery results...")
            
            # Export results
            export_result = await self.discovery_manager.export_discovery_results(
                f"discovery_results_{self.current_practice.get('name', 'practice')}.json"
            )
            phase["export"] = export_result
            
            # Generate complete documentation
            if self.granite_orchestrator and self.infrastructure_catalog:
                logger.info("Generating complete documentation...")
                documentation = await self.granite_orchestrator.generate_complete_documentation(
                    self.infrastructure_catalog
                )
                phase["documentation"] = documentation
            
            logger.info("Phase 5 complete: Documentation generated")
            return phase
        
        except Exception as e:
            logger.error(f"Error in phase 5: {e}")
            phase["status"] = "FAILED"
            phase["error"] = str(e)
            return phase
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status"""
        return {
            "current_practice": self.current_practice,
            "workflow_count": len(self.workflow_history),
            "last_workflow": self.workflow_history[-1] if self.workflow_history else None,
            "all_workflows": self.workflow_history
        }
    
    async def export_workflow_results(self, filename: Optional[str] = None) -> str:
        """Export workflow results to file"""
        if not filename:
            practice_name = self.current_practice.get("name", "practice") if self.current_practice else "unknown"
            filename = f"onboarding_results_{practice_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            results = {
                "export_timestamp": datetime.now().isoformat(),
                "practice": self.current_practice,
                "workflows": self.workflow_history,
                "infrastructure_catalog": self.infrastructure_catalog
            }
            
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"Results exported to {filename}")
            return filename
        
        except Exception as e:
            logger.error(f"Error exporting results: {e}")
            return None


async def main():
    """
    Example usage
    """
    print("=" * 80)
    print("PRACTICE ONBOARDING AGENT - ORCHESTRATOR")
    print("=" * 80)
    
    # Initialize orchestrator
    orchestrator = PracticeOnboardingOrchestrator()
    await orchestrator.initialize()
    
    # Example practice
    practice_info = {
        "name": "Riverside Medical Practice",
        "location": "Cape Town, South Africa",
        "network_cidr": "192.168.1.0/24",
        "staff_count": 15,
        "patient_count": 5000
    }
    
    print(f"\n[*] Starting onboarding for: {practice_info['name']}")
    print(f"    Location: {practice_info['location']}")
    print(f"    Network: {practice_info['network_cidr']}")
    
    # Run onboarding workflow
    workflow = await orchestrator.start_new_practice_onboarding(practice_info)
    
    print(f"\n[+] Onboarding workflow completed")
    print(f"    Status: {workflow['status']}")
    print(f"    Phases completed: {len(workflow['phases'])}")
    
    # Export results
    export_file = await orchestrator.export_workflow_results()
    print(f"    Results exported to: {export_file}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())
