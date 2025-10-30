"""
Enhanced MCP API Routes with Web Scraping Integration
Provides REST API endpoints for all MCP tools including portal scraping
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
import asyncio
from datetime import datetime

from app.services.enhanced_scraping_tools import (
    get_enhanced_mcp_tools,
    ENHANCED_TOOL_HANDLERS,
    validate_medical_aid_live,
    extract_member_benefits_live,
    store_portal_credentials,
    bulk_member_verification,
    auto_register_practice,
    monitor_portal_availability,
    list_supported_schemes
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Request/Response Models
class MCPToolRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]

class MCPToolResponse(BaseModel):
    success: bool
    result: Any = None
    error: str = None
    tool_name: str
    timestamp: str
    execution_time_ms: int = None

class BulkMemberRequest(BaseModel):
    members: List[Dict[str, str]]
    max_concurrent: int = 3

class PortalCredentialsRequest(BaseModel):
    scheme_code: str
    username: str
    password: str
    notes: str = ""

class PracticeRegistrationRequest(BaseModel):
    scheme_code: str
    practice_name: str
    practice_number: str
    contact_person: str
    email: str
    phone: str
    address: Dict[str, str] = {}
    speciality: str
    hpcsa_number: str

@router.get("/tools")
async def get_mcp_tools():
    """Get list of all available MCP tools with enhanced scraping capabilities"""
    try:
        tools = get_enhanced_mcp_tools()
        
        return {
            "success": True,
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
                for tool in tools
            ],
            "total_tools": len(tools),
            "scraping_enabled": True,
            "api_free_solution": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Failed to get MCP tools: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tools", response_model=MCPToolResponse)
async def execute_mcp_tool(request: MCPToolRequest):
    """Execute any MCP tool with web scraping capabilities"""
    start_time = datetime.now()
    
    try:
        logger.info(f"🔧 Executing tool: {request.name}")
        
        # Check if tool exists
        if request.name not in ENHANCED_TOOL_HANDLERS:
            available_tools = list(ENHANCED_TOOL_HANDLERS.keys())
            raise HTTPException(
                status_code=400, 
                detail=f"Tool '{request.name}' not found. Available tools: {available_tools}"
            )
        
        # Execute tool
        handler = ENHANCED_TOOL_HANDLERS[request.name]
        
        # Handle async vs sync functions
        if asyncio.iscoroutinefunction(handler):
            result = await handler(request.arguments)
        else:
            result = handler(request.arguments)
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return MCPToolResponse(
            success=True,
            result=result,
            tool_name=request.name,
            timestamp=datetime.now().isoformat(),
            execution_time_ms=int(execution_time)
        )
        
    except Exception as e:
        logger.error(f"❌ Tool execution failed for {request.name}: {str(e)}")
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return MCPToolResponse(
            success=False,
            error=str(e),
            tool_name=request.name,
            timestamp=datetime.now().isoformat(),
            execution_time_ms=int(execution_time)
        )

# Specialized endpoints for common operations

@router.post("/validate-member")
async def validate_member_live(
    member_number: str,
    scheme_code: str,
    id_number: Optional[str] = None,
    use_cached: bool = True
):
    """Validate medical aid member using live portal scraping"""
    try:
        result = await validate_medical_aid_live({
            "member_number": member_number,
            "scheme_code": scheme_code,
            "id_number": id_number,
            "use_cached": use_cached
        })
        
        return {
            "success": True,
            "validation_result": result,
            "data_source": "live_portal_scraping",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Member validation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract-benefits")
async def extract_benefits_live(
    member_number: str,
    scheme_code: str,
    include_utilization: bool = True
):
    """Extract member benefits using live portal scraping"""
    try:
        result = await extract_member_benefits_live({
            "member_number": member_number,
            "scheme_code": scheme_code,
            "include_utilization": include_utilization
        })
        
        return {
            "success": True,
            "benefits_data": result,
            "data_source": "live_portal_scraping",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Benefits extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/store-credentials")
async def store_credentials(request: PortalCredentialsRequest):
    """Store portal login credentials securely"""
    try:
        result = await store_portal_credentials({
            "scheme_code": request.scheme_code,
            "username": request.username,
            "password": request.password,
            "notes": request.notes
        })
        
        return {
            "success": True,
            "credential_result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Credential storage failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-verification")
async def bulk_member_verification_endpoint(request: BulkMemberRequest):
    """Perform bulk member verification across multiple schemes"""
    try:
        result = await bulk_member_verification({
            "members": request.members,
            "max_concurrent": request.max_concurrent
        })
        
        return {
            "success": True,
            "bulk_results": result,
            "total_members": len(request.members),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Bulk verification failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auto-register")
async def auto_register_practice_endpoint(request: PracticeRegistrationRequest):
    """Automatically register practice with medical scheme portal"""
    try:
        result = await auto_register_practice({
            "scheme_code": request.scheme_code,
            "practice_name": request.practice_name,
            "practice_number": request.practice_number,
            "contact_person": request.contact_person,
            "email": request.email,
            "phone": request.phone,
            "address": request.address,
            "speciality": request.speciality,
            "hpcsa_number": request.hpcsa_number
        })
        
        return {
            "success": True,
            "registration_result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Auto-registration failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portal-status")
async def get_portal_status():
    """Get availability status of all medical scheme portals"""
    try:
        result = await monitor_portal_availability({
            "include_response_times": True
        })
        
        return {
            "success": True,
            "portal_status": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Portal status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/supported-schemes")
async def get_supported_schemes(include_details: bool = False):
    """Get list of all supported medical schemes"""
    try:
        result = list_supported_schemes({
            "include_details": include_details
        })
        
        return {
            "success": True,
            "schemes_data": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Scheme listing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint for the enhanced MCP API"""
    try:
        # Quick health checks
        schemes = list_supported_schemes({"include_details": False})
        
        return {
            "status": "healthy",
            "service": "Enhanced MCP Medical Server",
            "version": "2.0.0",
            "features": {
                "web_scraping": True,
                "ai_integration": True,
                "portal_management": True,
                "bulk_operations": True,
                "auto_registration": True
            },
            "supported_schemes": len(schemes.get("schemes", [])),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Background task endpoints
@router.post("/background/portal-monitoring")
async def start_portal_monitoring(background_tasks: BackgroundTasks):
    """Start background portal monitoring task"""
    try:
        background_tasks.add_task(continuous_portal_monitoring)
        
        return {
            "success": True,
            "message": "Portal monitoring started in background",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Background monitoring failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/background/bulk-sync")
async def start_bulk_sync(background_tasks: BackgroundTasks, scheme_codes: List[str]):
    """Start background bulk data synchronization"""
    try:
        background_tasks.add_task(bulk_data_sync, scheme_codes)
        
        return {
            "success": True,
            "message": f"Bulk sync started for {len(scheme_codes)} schemes",
            "schemes": scheme_codes,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Background sync failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Background task functions
async def continuous_portal_monitoring():
    """Continuously monitor portal availability"""
    logger.info("🔍 Starting continuous portal monitoring...")
    
    while True:
        try:
            await monitor_portal_availability({"include_response_times": True})
            await asyncio.sleep(300)  # Check every 5 minutes
        except Exception as e:
            logger.error(f"❌ Portal monitoring error: {str(e)}")
            await asyncio.sleep(60)  # Wait 1 minute on error

async def bulk_data_sync(scheme_codes: List[str]):
    """Perform bulk data synchronization"""
    logger.info(f"🔄 Starting bulk sync for {len(scheme_codes)} schemes...")
    
    try:
        for scheme_code in scheme_codes:
            # Perform sync operations for each scheme
            logger.info(f"Syncing {scheme_code}...")
            await asyncio.sleep(10)  # Simulate sync work
            
        logger.info("✅ Bulk sync completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Bulk sync failed: {str(e)}")

# Error handlers
@router.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        "success": False,
        "error": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.now().isoformat()
    }

@router.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"❌ Unhandled exception: {str(exc)}")
    return {
        "success": False,
        "error": "Internal server error",
        "timestamp": datetime.now().isoformat()
    }