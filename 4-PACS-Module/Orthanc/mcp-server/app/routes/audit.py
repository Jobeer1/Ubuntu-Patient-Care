"""Audit log routes"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])

class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    user_id: int
    user_email: str
    action: str
    resource: str = None
    ip_address: str = None
    success: bool
    failure_reason: str = None
    
    class Config:
        from_attributes = True

@router.get("/logs", response_model=List[AuditLogResponse])
async def get_audit_logs(limit: int = 100, db: Session = Depends(get_db)):
    """Get recent audit logs (admin only)"""
    logs = AuditService.get_recent_logs(db, limit=limit)
    return logs

@router.get("/user/{user_id}", response_model=List[AuditLogResponse])
async def get_user_audit_logs(user_id: int, limit: int = 100, db: Session = Depends(get_db)):
    """Get audit logs for specific user"""
    logs = AuditService.get_user_logs(db, user_id, limit=limit)
    return logs

@router.get("/action/{action}", response_model=List[AuditLogResponse])
async def get_logs_by_action(action: str, limit: int = 100, db: Session = Depends(get_db)):
    """Get audit logs by action type"""
    logs = AuditService.get_logs_by_action(db, action, limit=limit)
    return logs
