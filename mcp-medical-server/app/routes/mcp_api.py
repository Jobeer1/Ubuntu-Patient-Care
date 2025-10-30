"""
API routes for MCP tool testing and system status
Provides endpoints for the React UI to interact with MCP server
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import logging
import psutil
import time
from datetime import datetime, timedelta
import sqlite3
import os

logger = logging.getLogger(__name__)

router = APIRouter()

class MCPToolRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]

class SystemStatusResponse(BaseModel):
    mcp_server: str
    database: str
    uptime: str
    memory_usage: str
    cpu_usage: str
    active_connections: int

# Track server start time for uptime calculation
server_start_time = datetime.now()

@router.get("/status")
async def get_system_status():
    """Get overall system status"""
    try:
        # Calculate uptime
        uptime = datetime.now() - server_start_time
        uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds % 3600) // 60}m"
        
        # Get system metrics
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Check database connection
        db_status = "healthy"
        try:
            # Assuming SQLite database
            conn = sqlite3.connect("medical_schemes.db")
            conn.execute("SELECT 1")
            conn.close()
        except Exception:
            db_status = "error"
        
        return {
            "mcp_server": "healthy",
            "database": db_status,
            "uptime": uptime_str,
            "memory_usage": f"{memory.percent}%",
            "cpu_usage": f"{cpu_percent}%", 
            "active_connections": 1,  # Mock value
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get system status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/detailed-status")
async def get_detailed_system_status():
    """Get detailed system information"""
    try:
        # System metrics
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Database size (assuming SQLite)
        db_size = "Unknown"
        try:
            if os.path.exists("medical_schemes.db"):
                db_size_bytes = os.path.getsize("medical_schemes.db")
                db_size = f"{db_size_bytes / (1024*1024):.1f} MB"
        except Exception:
            pass
        
        uptime = datetime.now() - server_start_time
        
        return {
            "uptime": f"{uptime.days} days, {uptime.seconds // 3600} hours",
            "memory_usage": f"{memory.used // (1024*1024)} MB / {memory.total // (1024*1024)} MB ({memory.percent}%)",
            "cpu_usage": f"{psutil.cpu_percent(interval=1)}%",
            "disk_usage": f"{disk.used // (1024*1024*1024)} GB / {disk.total // (1024*1024*1024)} GB",
            "database_size": db_size,
            "active_connections": 1,
            "python_version": f"{psutil.process_iter}",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get detailed status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance")
async def get_performance_data():
    """Get performance metrics over time"""
    try:
        # Generate mock performance data for the last 24 hours
        now = datetime.now()
        performance_data = []
        
        for i in range(24):
            timestamp = now - timedelta(hours=i)
            performance_data.append({
                "timestamp": timestamp.strftime("%H:%M"),
                "response_time": 150 + (i * 10) + (i % 3) * 50,  # Mock response times
                "cpu_usage": 20 + (i % 5) * 15,  # Mock CPU usage
                "memory_usage": 40 + (i % 4) * 10,  # Mock memory usage
                "requests_per_minute": 50 + (i % 7) * 20  # Mock request rate
            })
        
        return {
            "history": list(reversed(performance_data)),
            "current": {
                "response_time": 180,
                "cpu_usage": psutil.cpu_percent(interval=1),
                "memory_usage": psutil.virtual_memory().percent,
                "requests_per_minute": 75
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/call-tool")
async def call_mcp_tool(request: MCPToolRequest):
    """
    Call an MCP tool with provided arguments
    This endpoint bridges the React UI with the MCP server functionality
    """
    try:
        logger.info(f"Calling MCP tool: {request.name} with args: {request.arguments}")
        
        # Import the MCP server's tool execution logic
        # This is a simplified version - in production you'd call the actual MCP server
        
        # Mock responses for demonstration
        mock_responses = {
            "validate_medical_aid": {
                "valid": True,
                "member_number": request.arguments.get("member_number"),
                "scheme_code": request.arguments.get("scheme_code"),
                "plan_name": "Executive Plan",
                "status": "Active",
                "benefits_remaining": "85%",
                "annual_limit": "R500,000",
                "used_amount": "R75,000"
            },
            "validate_preauth_requirements": {
                "required": True,
                "procedure_code": request.arguments.get("procedure_code"),
                "scheme_code": request.arguments.get("scheme_code"),
                "typical_approval_time": "24-48 hours",
                "required_documents": [
                    "Clinical motivation letter",
                    "Relevant medical history",
                    "Alternative treatment attempts"
                ],
                "approval_criteria": [
                    "Clinical indication must be appropriate",
                    "Conservative treatment attempted",
                    "Specialist referral included"
                ]
            },
            "estimate_patient_cost": {
                "total_cost": "R12,500",
                "medical_aid_portion": "R10,000",
                "patient_portion": "R2,500",
                "co_payment": "20%",
                "excess": "R500",
                "annual_limit_impact": "R10,000 deducted from annual limit",
                "breakdown": {
                    "procedure_fee": "R8,000",
                    "facility_fee": "R3,000", 
                    "anaesthetist_fee": "R1,500"
                }
            },
            "create_preauth_request": {
                "preauth_id": f"PA{int(time.time())}",
                "status": "submitted",
                "reference_number": f"REF{int(time.time())}",
                "estimated_processing_time": "24-48 hours",
                "submission_date": datetime.now().isoformat(),
                "patient_id": request.arguments.get("patient_id"),
                "procedure_code": request.arguments.get("procedure_code"),
                "clinical_indication": request.arguments.get("clinical_indication"),
                "next_steps": [
                    "Request submitted to medical scheme",
                    "Clinical review in progress",
                    "Response expected within 48 hours"
                ]
            },
            "check_preauth_status": {
                "preauth_id": request.arguments.get("preauth_id"),
                "status": "approved",
                "approval_date": datetime.now().isoformat(),
                "reference_number": "APPR123456",
                "approved_amount": "R10,000",
                "conditions": [
                    "Valid for 30 days from approval date",
                    "Must be performed at contracted facility",
                    "Prior authorization number must be quoted"
                ],
                "contact_details": {
                    "medical_scheme": "0860 123 456",
                    "reference": "APPR123456"
                }
            },
            "list_pending_preauths": {
                "pending_requests": [
                    {
                        "preauth_id": "PA001",
                        "patient_id": "P001",
                        "procedure_code": "0190",
                        "status": "pending_review",
                        "submission_date": "2024-03-15T10:30:00",
                        "urgency": "routine"
                    },
                    {
                        "preauth_id": "PA002", 
                        "patient_id": "P002",
                        "procedure_code": "0191",
                        "status": "additional_info_required",
                        "submission_date": "2024-03-14T14:45:00",
                        "urgency": "urgent"
                    }
                ],
                "total_count": 2,
                "status_filter": request.arguments.get("status", "all")
            }
        }
        
        # Return appropriate mock response
        if request.name in mock_responses:
            response = mock_responses[request.name]
            response["execution_time"] = "0.25s"
            response["timestamp"] = datetime.now().isoformat()
            response["tool_name"] = request.name
            return response
        else:
            return {
                "error": f"Tool '{request.name}' not implemented yet",
                "available_tools": list(mock_responses.keys()),
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"MCP tool call failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")

@router.get("/stats")
async def get_mcp_stats():
    """Get MCP server usage statistics"""
    try:
        # Mock statistics - in production these would come from actual usage logs
        return {
            "tool_usage": [
                {"tool": "validate_medical_aid", "count": 234},
                {"tool": "create_preauth_request", "count": 189},
                {"tool": "estimate_patient_cost", "count": 156},
                {"tool": "check_preauth_status", "count": 123},
                {"tool": "validate_preauth_requirements", "count": 98},
                {"tool": "list_pending_preauths", "count": 67}
            ],
            "recent_activities": [
                {
                    "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
                    "action": "Pre-auth request created for CT scan",
                    "status": "success",
                    "user": "system"
                },
                {
                    "timestamp": (datetime.now() - timedelta(minutes=12)).isoformat(), 
                    "action": "Medical aid validation completed",
                    "status": "success",
                    "user": "system"
                },
                {
                    "timestamp": (datetime.now() - timedelta(minutes=18)).isoformat(),
                    "action": "Patient cost estimation",
                    "status": "success", 
                    "user": "system"
                }
            ],
            "daily_stats": {
                "total_requests": 89,
                "successful_requests": 87,
                "failed_requests": 2,
                "average_response_time": "0.34s",
                "success_rate": "97.8%"
            },
            "top_procedures": [
                {"code": "0190", "name": "CT Scan - Chest", "count": 45},
                {"code": "0191", "name": "MRI - Brain", "count": 32},
                {"code": "0015", "name": "Ultrasound - Abdominal", "count": 28}
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get MCP stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))