"""Audit logging service"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models import AuditLog

class AuditService:
    """Audit logging service"""
    
    @staticmethod
    def log_event(
        db: Session,
        user_id: int,
        user_email: str,
        action: str,
        resource: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        failure_reason: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AuditLog:
        """Log an audit event"""
        log = AuditLog(
            user_id=user_id,
            user_email=user_email,
            action=action,
            resource=resource,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason,
            session_id=session_id,
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
    
    @staticmethod
    def get_user_logs(db: Session, user_id: int, limit: int = 100) -> List[AuditLog]:
        """Get audit logs for a specific user"""
        return db.query(AuditLog)\
            .filter(AuditLog.user_id == user_id)\
            .order_by(AuditLog.timestamp.desc())\
            .limit(limit)\
            .all()
    
    @staticmethod
    def get_recent_logs(db: Session, limit: int = 100) -> List[AuditLog]:
        """Get recent audit logs"""
        return db.query(AuditLog)\
            .order_by(AuditLog.timestamp.desc())\
            .limit(limit)\
            .all()
    
    @staticmethod
    def get_logs_by_action(db: Session, action: str, limit: int = 100) -> List[AuditLog]:
        """Get audit logs by action type"""
        return db.query(AuditLog)\
            .filter(AuditLog.action == action)\
            .order_by(AuditLog.timestamp.desc())\
            .limit(limit)\
            .all()
