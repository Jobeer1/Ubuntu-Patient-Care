"""
MCP Server for Practice Onboarding Agent - Discovery Tools

Exposes discovery tools as MCP Tools that Granite-3.1 can call:
- Network Discovery Tool
- Database Discovery Tool
- Device Classification Tool
- Infrastructure Catalog Tool
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from mcp.server import Server
from mcp.types import Tool, TextContent, ToolResult
import mcp.types as types

from network_discovery_tools import NetworkDiscovery, ServiceDiscovery
from database_discovery_tools import DatabaseDiscovery, DatabaseAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP Server
server = Server("practice-onboarding-agent")


class DiscoveryToolsManager:
    """
    Manages all discovery tools and maintains infrastructure catalog
    """
    
    def __init__(self):
        self.network_discovery = NetworkDiscovery()
        self.database_discovery = DatabaseDiscovery()
        self.infrastructure_catalog = {}
        self.last_discovery = None
        
    async def discover_network_range(self, network_cidr: str, timeout: int = 5) -> Dict[str, Any]:
        """
        Tool: Discover devices on a network range
        """
        logger.info(f"Starting network discovery for {network_cidr}")
        
        try:
            # Run discovery in thread to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.network_discovery.discover_network_range,
                network_cidr,
                timeout
            )
            
            self.last_discovery = {
                "type": "network",
                "network": network_cidr,
                "timestamp": datetime.now().isoformat(),
                "results": result
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Error discovering network: {e}")
            return {
                "error": str(e),
                "status": "FAILED"
            }
    
    async def discover_current_network(self) -> Dict[str, Any]:
        """
        Tool: Auto-detect and discover current network
        """
        logger.info("Starting auto-discovery of current network")
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.network_discovery.discover_specific_network
            )
            
            self.last_discovery = {
                "type": "current_network",
                "timestamp": datetime.now().isoformat(),
                "results": result
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Error discovering current network: {e}")
            return {
                "error": str(e),
                "status": "FAILED"
            }
    
    async def probe_database_servers(self, ips: List[str]) -> Dict[str, Any]:
        """
        Tool: Probe list of IPs for database servers
        """
        logger.info(f"Starting database discovery on {len(ips)} IPs")
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.database_discovery.probe_database_servers,
                ips
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error probing for databases: {e}")
            return {
                "error": str(e),
                "status": "FAILED"
            }
    
    async def get_device_summary(self) -> Dict[str, Any]:
        """
        Tool: Get summary of discovered devices by type
        """
        try:
            loop = asyncio.get_event_loop()
            summary = await loop.run_in_executor(
                None,
                self.network_discovery.get_device_summary
            )
            return summary
        except Exception as e:
            logger.error(f"Error getting device summary: {e}")
            return {"error": str(e)}
    
    async def get_database_summary(self) -> Dict[str, Any]:
        """
        Tool: Get summary of discovered databases
        """
        try:
            loop = asyncio.get_event_loop()
            summary = await loop.run_in_executor(
                None,
                self.database_discovery.get_database_summary
            )
            return summary
        except Exception as e:
            logger.error(f"Error getting database summary: {e}")
            return {"error": str(e)}
    
    async def analyze_database(self, ip: str, port: int, db_type: str) -> Dict[str, Any]:
        """
        Tool: Analyze database for medical practice usage
        """
        db_info = {
            "ip": ip,
            "port": port,
            "type": db_type
        }
        
        try:
            loop = asyncio.get_event_loop()
            analysis = await loop.run_in_executor(
                None,
                DatabaseAnalyzer.analyze_database,
                db_info
            )
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing database: {e}")
            return {"error": str(e)}
    
    async def get_infrastructure_catalog(self) -> Dict[str, Any]:
        """
        Tool: Get complete infrastructure catalog from discovery results
        """
        try:
            catalog = {
                "catalog_generated": datetime.now().isoformat(),
                "devices": self.network_discovery.discovered_devices,
                "databases": self.database_discovery.discovered_databases,
                "device_summary": await self.get_device_summary(),
                "database_summary": await self.get_database_summary()
            }
            return catalog
        except Exception as e:
            logger.error(f"Error generating catalog: {e}")
            return {"error": str(e)}
    
    async def export_discovery_results(self, filename: str = "discovery_results.json") -> Dict[str, Any]:
        """
        Tool: Export all discovery results to JSON file
        """
        try:
            catalog = await self.get_infrastructure_catalog()
            
            with open(filename, 'w') as f:
                json.dump(catalog, f, indent=2)
            
            logger.info(f"Discovery results exported to {filename}")
            return {
                "status": "SUCCESS",
                "filename": filename,
                "message": f"Discovery results saved to {filename}"
            }
        except Exception as e:
            logger.error(f"Error exporting results: {e}")
            return {"error": str(e), "status": "FAILED"}


# Initialize discovery manager
discovery_manager = DiscoveryToolsManager()


# Define MCP Tools
@server.list_tools()
async def list_tools() -> List[Tool]:
    """
    List all available tools for the agent
    """
    return [
        Tool(
            name="discover_network_range",
            description="Discover all devices on a specific network range (CIDR notation). Scans for servers, NAS, medical devices, VMs, PCs, and network equipment.",
            inputSchema={
                "type": "object",
                "properties": {
                    "network_cidr": {
                        "type": "string",
                        "description": "Network in CIDR notation (e.g., '192.168.1.0/24')"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Ping timeout in seconds (default: 5)",
                        "default": 5
                    }
                },
                "required": ["network_cidr"]
            }
        ),
        Tool(
            name="discover_current_network",
            description="Auto-detect and discover all devices on the current network. Identifies network range automatically and scans.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="probe_database_servers",
            description="Probe a list of IP addresses for database servers (MySQL, PostgreSQL, SQL Server, MongoDB). Identifies database type and status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ips": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of IP addresses to probe for databases"
                    }
                },
                "required": ["ips"]
            }
        ),
        Tool(
            name="get_device_summary",
            description="Get summary of all discovered devices grouped by type (NAS, servers, medical devices, etc.)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_database_summary",
            description="Get summary of all discovered databases (count by type, accessibility status).",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="analyze_database",
            description="Analyze a specific database to identify its likely use (medical records, billing, etc.) and provide recommendations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ip": {
                        "type": "string",
                        "description": "IP address of database server"
                    },
                    "port": {
                        "type": "integer",
                        "description": "Port number of database"
                    },
                    "db_type": {
                        "type": "string",
                        "enum": ["MySQL", "PostgreSQL", "SQL Server", "MongoDB"],
                        "description": "Type of database"
                    }
                },
                "required": ["ip", "port", "db_type"]
            }
        ),
        Tool(
            name="get_infrastructure_catalog",
            description="Get complete infrastructure catalog from all discovery results. Includes devices and databases.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="export_discovery_results",
            description="Export all discovery results to a JSON file for documentation and analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Output filename (default: discovery_results.json)"
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """
    Execute a tool and return results
    """
    logger.info(f"Tool called: {name} with args: {arguments}")
    
    try:
        if name == "discover_network_range":
            result = await discovery_manager.discover_network_range(
                arguments["network_cidr"],
                arguments.get("timeout", 5)
            )
        
        elif name == "discover_current_network":
            result = await discovery_manager.discover_current_network()
        
        elif name == "probe_database_servers":
            result = await discovery_manager.probe_database_servers(
                arguments["ips"]
            )
        
        elif name == "get_device_summary":
            result = await discovery_manager.get_device_summary()
        
        elif name == "get_database_summary":
            result = await discovery_manager.get_database_summary()
        
        elif name == "analyze_database":
            result = await discovery_manager.analyze_database(
                arguments["ip"],
                arguments["port"],
                arguments["db_type"]
            )
        
        elif name == "get_infrastructure_catalog":
            result = await discovery_manager.get_infrastructure_catalog()
        
        elif name == "export_discovery_results":
            result = await discovery_manager.export_discovery_results(
                arguments.get("filename", "discovery_results.json")
            )
        
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        # Return result as text
        result_text = json.dumps(result, indent=2, default=str)
        return [TextContent(type="text", text=result_text)]
    
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        error_result = {"error": str(e), "tool": name}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]


async def main():
    """
    Main server loop
    """
    logger.info("Starting Practice Onboarding Agent - Discovery Tools MCP Server")
    
    # Use stdio transport
    async with server:
        logger.info("MCP Server ready for connections on stdio")
        await asyncio.sleep(float('inf'))


if __name__ == "__main__":
    asyncio.run(main())
