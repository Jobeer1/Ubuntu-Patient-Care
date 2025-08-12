"""
Orthanc Management API - Audit Router
Audit logging and compliance tracking endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import logging

from orthanc_management.api.auth import User
from orthanc_management.api.routers.auth import get_current_active_user, get_auth_manager
from orthanc_management.managers.audit_manager import AuditManager
from orthanc_management.database.manager import DatabaseManager

logger = logging.getLogger(__name__)

# Pydantic models
class AuditLogResponse(BaseModel):
    id: str
    event_type: str
    user_id: Optional[str]
    resource_id: Optional[str]
    resource_type: Optional[str]
    action: str
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    compliance_category: Optional[str]
    risk_level: str
    created_at: str

class AuditListResponse(BaseModel):
    logs: List[AuditLogResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

# Router instance
router = APIRouter(prefix="/audit", tags=["Audit Logs"])

# Dependency to get database session
def get_db():
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

# Dependency to get audit manager
def get_audit_manager(db = Depends(get_db)):
    return AuditManager(db)


@router.get("/", response_model=AuditListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_active_user),
    audit_manager: AuditManager = Depends(get_audit_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    List audit logs with filtering
    Requires 'admin' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "admin")
        
        # Build filters
        filters = {}
        if event_type:
            filters["event_type"] = event_type
        if user_id:
            filters["user_id"] = user_id
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date
        
        # Get audit logs
        result = audit_manager.get_logs_paginated(
            page=page,
            per_page=per_page,
            filters=filters
        )
        
        return AuditListResponse(
            logs=[AuditLogResponse(**log.to_dict()) for log in result["logs"]],
            total=result["total"],
            page=page,
            per_page=per_page,
            total_pages=result["total_pages"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list audit logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit logs"
        )


@router.get("/export")
async def export_audit_logs(
    format: str = Query("csv", regex="^(csv|json|pdf)$", description="Export format"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_active_user),
    audit_manager: AuditManager = Depends(get_audit_manager),
    auth_manager = Depends(get_auth_manager)
):
    """
    Export audit logs for compliance
    Requires 'admin' permission
    """
    try:
        # Check permission
        auth_manager.require_permission(current_user, "admin")
        
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow().date()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Export audit logs
        export_data = audit_manager.export_logs(format, start_date, end_date)
        
        logger.info(f"Audit logs exported by {current_user.username}: {format}")
        
        from fastapi.responses import Response
        return Response(
            content=export_data,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename=audit_logs_{start_date}_{end_date}.{format}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export audit logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export audit logs"
        )
