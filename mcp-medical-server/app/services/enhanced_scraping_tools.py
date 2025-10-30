"""
Enhanced MCP Tools with Medical Scheme Web Scraping Integration
Eliminates API dependency by scraping portal data directly
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from mcp.types import Tool, TextContent

from app.services.medical_scheme_scraper import MedicalSchemePortalScraper
from app.services.portal_automation import PortalCredentialsManager, MedicalSchemeAutoRegistration, BulkPortalOperations
from app.services.claude_bedrock_service import ClaudeBedrockService

logger = logging.getLogger(__name__)

# Initialize services
scraper = MedicalSchemePortalScraper()
credentials_manager = PortalCredentialsManager()
auto_registration = MedicalSchemeAutoRegistration(scraper)
bulk_operations = BulkPortalOperations(scraper, credentials_manager)
claude_service = ClaudeBedrockService()

# Enhanced MCP Tools with Web Scraping
def get_enhanced_mcp_tools() -> List[Tool]:
    """Get all MCP tools including web scraping capabilities"""
    
    return [
        # Original MCP Tools (enhanced with scraping)
        Tool(
            name="validate_medical_aid_live",
            description="Validate medical aid member by scraping portal directly (no API required)",
            inputSchema={
                "type": "object",
                "properties": {
                    "member_number": {"type": "string", "description": "Medical aid member number"},
                    "scheme_code": {"type": "string", "description": "Scheme code (e.g., DISCOVERY, MOMENTUM)"},
                    "id_number": {"type": "string", "description": "SA ID number (optional for validation)"},
                    "use_cached": {"type": "boolean", "description": "Use cached data if available", "default": True}
                },
                "required": ["member_number", "scheme_code"]
            }
        ),
        
        Tool(
            name="extract_member_benefits_live",
            description="Extract detailed member benefits by scraping portal (real-time data)",
            inputSchema={
                "type": "object",
                "properties": {
                    "member_number": {"type": "string", "description": "Medical aid member number"},
                    "scheme_code": {"type": "string", "description": "Scheme code"},
                    "include_utilization": {"type": "boolean", "description": "Include benefit utilization data", "default": True}
                },
                "required": ["member_number", "scheme_code"]
            }
        ),
        
        Tool(
            name="get_claims_history_live",
            description="Extract claims history by scraping portal (real-time data)",
            inputSchema={
                "type": "object",
                "properties": {
                    "member_number": {"type": "string", "description": "Medical aid member number"},
                    "scheme_code": {"type": "string", "description": "Scheme code"},
                    "months": {"type": "integer", "description": "Number of months to retrieve", "default": 12}
                },
                "required": ["member_number", "scheme_code"]
            }
        ),
        
        Tool(
            name="check_preauth_status_live",
            description="Check pre-authorization status by scraping portal",
            inputSchema={
                "type": "object",
                "properties": {
                    "scheme_code": {"type": "string", "description": "Scheme code"},
                    "preauth_number": {"type": "string", "description": "Pre-authorization number (optional)"},
                    "member_number": {"type": "string", "description": "Member number to filter results"}
                },
                "required": ["scheme_code"]
            }
        ),
        
        # Portal Management Tools
        Tool(
            name="store_portal_credentials",
            description="Securely store medical scheme portal login credentials",
            inputSchema={
                "type": "object", 
                "properties": {
                    "scheme_code": {"type": "string", "description": "Medical scheme code"},
                    "username": {"type": "string", "description": "Portal username/email"},
                    "password": {"type": "string", "description": "Portal password"},
                    "notes": {"type": "string", "description": "Optional notes about the account"}
                },
                "required": ["scheme_code", "username", "password"]
            }
        ),
        
        Tool(
            name="test_portal_login", 
            description="Test login to medical scheme portal with stored credentials",
            inputSchema={
                "type": "object",
                "properties": {
                    "scheme_code": {"type": "string", "description": "Medical scheme code"},
                    "force_relogin": {"type": "boolean", "description": "Force new login even if session exists", "default": False}
                },
                "required": ["scheme_code"]
            }
        ),
        
        Tool(
            name="bulk_member_verification",
            description="Verify multiple members across different schemes (batch operation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "members": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "scheme": {"type": "string"},
                                "member_number": {"type": "string"},
                                "id_number": {"type": "string"}
                            },
                            "required": ["scheme", "member_number"]
                        }
                    },
                    "max_concurrent": {"type": "integer", "description": "Maximum concurrent operations", "default": 3}
                },
                "required": ["members"]
            }
        ),
        
        # Auto-Registration Tools
        Tool(
            name="auto_register_practice",
            description="Automatically register practice with medical scheme portal",
            inputSchema={
                "type": "object",
                "properties": {
                    "scheme_code": {"type": "string", "description": "Medical scheme code"},
                    "practice_name": {"type": "string", "description": "Practice name"},
                    "practice_number": {"type": "string", "description": "Practice number"},
                    "contact_person": {"type": "string", "description": "Contact person name"},
                    "email": {"type": "string", "description": "Email address"},
                    "phone": {"type": "string", "description": "Phone number"},
                    "address": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string"},
                            "city": {"type": "string"},
                            "postal_code": {"type": "string"},
                            "province": {"type": "string"}
                        }
                    },
                    "speciality": {"type": "string", "description": "Medical speciality"},
                    "hpcsa_number": {"type": "string", "description": "HPCSA registration number"}
                },
                "required": ["scheme_code", "practice_name", "contact_person", "email", "phone", "hpcsa_number"]
            }
        ),
        
        Tool(
            name="get_registration_requirements",
            description="Get registration requirements for medical scheme portal",
            inputSchema={
                "type": "object",
                "properties": {
                    "scheme_code": {"type": "string", "description": "Medical scheme code (optional for all)"}
                }
            }
        ),
        
        # Monitoring and Status Tools
        Tool(
            name="monitor_portal_availability",
            description="Check availability status of all medical scheme portals",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_response_times": {"type": "boolean", "description": "Include response time measurements", "default": True}
                }
            }
        ),
        
        Tool(
            name="list_supported_schemes",
            description="List all supported medical schemes with portal scraping capabilities",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_details": {"type": "boolean", "description": "Include detailed scheme information", "default": False}
                }
            }
        ),
        
        Tool(
            name="get_scraping_statistics",
            description="Get statistics about web scraping operations",
            inputSchema={
                "type": "object",
                "properties": {
                    "scheme_code": {"type": "string", "description": "Specific scheme (optional for all)"},
                    "days": {"type": "integer", "description": "Number of days to include", "default": 7}
                }
            }
        )
    ]

# Enhanced Tool Implementations
async def validate_medical_aid_live(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Live medical aid validation by scraping portal
    Eliminates need for API access
    """
    try:
        member_number = arguments.get("member_number")
        scheme_code = arguments.get("scheme_code")
        id_number = arguments.get("id_number")
        use_cached = arguments.get("use_cached", True)
        
        logger.info(f"🔍 Live validation for {member_number} on {scheme_code}")
        
        # Check cache first if requested
        if use_cached:
            # Implementation would check cache here
            pass
        
        # Get stored credentials
        credentials = credentials_manager.get_credentials(scheme_code)
        if not credentials:
            return {
                "valid": False,
                "error": f"No credentials stored for {scheme_code}",
                "setup_required": True,
                "message": f"Please store credentials using 'store_portal_credentials' tool"
            }
        
        # Login to portal
        login_success = await scraper.login_to_portal(
            scheme_code,
            credentials["username"],
            credentials["password"]
        )
        
        if not login_success:
            return {
                "valid": False,
                "error": "Portal login failed",
                "credentials_issue": True,
                "message": "Please check stored credentials"
            }
        
        # Search for member
        member_data = await scraper.search_member(scheme_code, member_number, id_number)
        
        if "error" in member_data:
            return {
                "valid": False,
                "error": member_data["error"],
                "scheme_code": scheme_code,
                "member_number": member_number
            }
        
        # Enhance with Claude AI analysis
        try:
            claude_analysis = await claude_service.analyze_medical_query(
                f"Analyze this medical aid member validation result from {scheme_code}",
                member_data
            )
            member_data["ai_analysis"] = claude_analysis
        except Exception as e:
            logger.warning(f"Claude analysis failed: {str(e)}")
        
        # Format response
        result = {
            "valid": True,
            "member_number": member_number,
            "scheme_code": scheme_code,
            "data_source": "live_portal_scraping",
            "timestamp": datetime.now().isoformat(),
            **member_data
        }
        
        # Close session
        await scraper.close_session(scheme_code)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Live validation failed: {str(e)}")
        return {
            "valid": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def extract_member_benefits_live(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract live member benefits from portal
    """
    try:
        member_number = arguments.get("member_number")
        scheme_code = arguments.get("scheme_code")
        include_utilization = arguments.get("include_utilization", True)
        
        logger.info(f"💰 Extracting benefits for {member_number} on {scheme_code}")
        
        # Get credentials and login
        credentials = credentials_manager.get_credentials(scheme_code)
        if not credentials:
            return {"error": f"No credentials stored for {scheme_code}"}
        
        login_success = await scraper.login_to_portal(
            scheme_code,
            credentials["username"], 
            credentials["password"]
        )
        
        if not login_success:
            return {"error": "Portal login failed"}
        
        # Extract benefits
        benefits_data = await scraper.get_member_benefits(scheme_code, member_number)
        
        # Get additional utilization data if requested
        if include_utilization:
            try:
                claims_data = await scraper.get_claims_history(scheme_code, member_number, 12)
                benefits_data["utilization_summary"] = claims_data
            except Exception as e:
                logger.warning(f"Could not get utilization data: {str(e)}")
        
        # Enhance with Claude AI analysis
        try:
            claude_analysis = await claude_service.analyze_medical_query(
                f"Analyze member benefits and utilization for cost optimization opportunities",
                benefits_data
            )
            benefits_data["ai_analysis"] = claude_analysis
            benefits_data["cost_optimization"] = claude_analysis.get("cost_optimization", [])
        except Exception as e:
            logger.warning(f"Claude analysis failed: {str(e)}")
        
        benefits_data.update({
            "member_number": member_number,
            "scheme_code": scheme_code,
            "data_source": "live_portal_scraping",
            "timestamp": datetime.now().isoformat()
        })
        
        await scraper.close_session(scheme_code)
        return benefits_data
        
    except Exception as e:
        logger.error(f"❌ Benefits extraction failed: {str(e)}")
        return {"error": str(e)}

async def store_portal_credentials(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store portal credentials securely
    """
    try:
        scheme_code = arguments.get("scheme_code")
        username = arguments.get("username")
        password = arguments.get("password")
        notes = arguments.get("notes", "")
        
        success = credentials_manager.store_credentials(scheme_code, username, password, notes)
        
        if success:
            # Test the credentials
            try:
                test_login = await scraper.login_to_portal(scheme_code, username, password)
                await scraper.close_session(scheme_code)
                
                return {
                    "success": True,
                    "scheme_code": scheme_code,
                    "username": username,
                    "credentials_tested": True,
                    "login_successful": test_login,
                    "message": "Credentials stored and tested successfully" if test_login else "Credentials stored but login test failed"
                }
            except Exception as e:
                return {
                    "success": True,
                    "scheme_code": scheme_code,
                    "username": username,
                    "credentials_tested": False,
                    "test_error": str(e),
                    "message": "Credentials stored but could not test login"
                }
        else:
            return {
                "success": False,
                "error": "Failed to store credentials"
            }
            
    except Exception as e:
        logger.error(f"❌ Credential storage failed: {str(e)}")
        return {"success": False, "error": str(e)}

async def bulk_member_verification(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bulk member verification across multiple schemes
    """
    try:
        members = arguments.get("members", [])
        max_concurrent = arguments.get("max_concurrent", 3)
        
        logger.info(f"🔍 Starting bulk verification for {len(members)} members")
        
        # Use bulk operations service
        results = await bulk_operations.bulk_member_verification(members)
        
        # Enhance with Claude AI summary
        try:
            claude_summary = await claude_service.analyze_medical_query(
                f"Analyze bulk member verification results and provide insights",
                results
            )
            results["ai_summary"] = claude_summary
            results["recommendations"] = claude_summary.get("recommendations", [])
        except Exception as e:
            logger.warning(f"Claude analysis failed: {str(e)}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Bulk verification failed: {str(e)}")
        return {"error": str(e)}

async def auto_register_practice(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Automatically register practice with medical scheme
    """
    try:
        from app.services.portal_automation import AutoRegistrationRequest
        
        # Create registration request
        request = AutoRegistrationRequest(
            scheme_code=arguments.get("scheme_code"),
            practice_name=arguments.get("practice_name"),
            practice_number=arguments.get("practice_number"),
            contact_person=arguments.get("contact_person"),
            email=arguments.get("email"),
            phone=arguments.get("phone"),
            address=arguments.get("address", {}),
            speciality=arguments.get("speciality"),
            hpcsa_number=arguments.get("hpcsa_number")
        )
        
        logger.info(f"🚀 Auto-registering practice with {request.scheme_code}")
        
        # Perform auto-registration
        result = await auto_registration.auto_register(request)
        
        # Enhance with Claude AI guidance
        try:
            claude_guidance = await claude_service.analyze_medical_query(
                f"Provide guidance for medical scheme registration process and next steps",
                result
            )
            result["ai_guidance"] = claude_guidance
            result["next_steps_detailed"] = claude_guidance.get("next_steps", [])
        except Exception as e:
            logger.warning(f"Claude guidance failed: {str(e)}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Auto-registration failed: {str(e)}")
        return {"error": str(e)}

async def monitor_portal_availability(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Monitor availability of all medical scheme portals
    """
    try:
        include_response_times = arguments.get("include_response_times", True)
        
        logger.info("🔍 Monitoring portal availability...")
        
        # Use bulk operations service
        availability = await bulk_operations.monitor_portal_availability()
        
        # Enhance with Claude AI insights
        try:
            claude_insights = await claude_service.analyze_medical_query(
                "Analyze medical scheme portal availability and provide operational insights",
                availability
            )
            availability["ai_insights"] = claude_insights
            availability["recommendations"] = claude_insights.get("recommendations", [])
        except Exception as e:
            logger.warning(f"Claude analysis failed: {str(e)}")
        
        return availability
        
    except Exception as e:
        logger.error(f"❌ Portal monitoring failed: {str(e)}")
        return {"error": str(e)}

def list_supported_schemes(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    List all supported medical schemes
    """
    try:
        include_details = arguments.get("include_details", False)
        
        schemes = scraper.get_supported_schemes()
        
        result = {
            "total_schemes": len(schemes),
            "schemes": schemes,
            "scraping_enabled": True,
            "api_free": True
        }
        
        if include_details:
            detailed_schemes = {}
            for scheme_code in schemes:
                scheme_info = scraper.get_scheme_info(scheme_code)
                detailed_schemes[scheme_code] = scheme_info
            
            result["detailed_schemes"] = detailed_schemes
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Scheme listing failed: {str(e)}")
        return {"error": str(e)}

# Tool execution mapping
ENHANCED_TOOL_HANDLERS = {
    "validate_medical_aid_live": validate_medical_aid_live,
    "extract_member_benefits_live": extract_member_benefits_live,
    "get_claims_history_live": lambda args: scraper.get_claims_history(args["scheme_code"], args["member_number"], args.get("months", 12)),
    "check_preauth_status_live": lambda args: scraper.check_preauth_status(args["scheme_code"], args.get("preauth_number")),
    "store_portal_credentials": store_portal_credentials,
    "test_portal_login": lambda args: scraper.login_to_portal(args["scheme_code"], *credentials_manager.get_credentials(args["scheme_code"]).values()),
    "bulk_member_verification": bulk_member_verification,
    "auto_register_practice": auto_register_practice,
    "get_registration_requirements": lambda args: auto_registration.get_registration_requirements(args.get("scheme_code")) if args.get("scheme_code") else auto_registration.get_all_registration_requirements(),
    "monitor_portal_availability": monitor_portal_availability,
    "list_supported_schemes": list_supported_schemes,
    "get_scraping_statistics": lambda args: {"message": "Statistics feature coming soon"}
}