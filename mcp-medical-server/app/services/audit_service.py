"""Audit Service for logging access and authentication events"""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import AuditLog
from typing import Optional

class AuditService:
    """Service for auditing access and events"""
    
    # Event types
    EVENT_LOGIN = "login"
    EVENT_LOGOUT = "logout"
    EVENT_ACCESS_DENIED = "access_denied"
    EVENT_DOCUMENT_VIEWED = "document_viewed"
    EVENT_DOCUMENT_EXPORTED = "document_exported"
    EVENT_ROLE_CHANGED = "role_changed"
    EVENT_PERMISSION_GRANTED = "permission_granted"
    EVENT_PERMISSION_REVOKED = "permission_revoked"
    EVENT_OAUTH_LOGIN = "oauth_login"
    EVENT_STUDY_VIEWED = "study_viewed"
    EVENT_REPORT_CREATED = "report_created"
    EVENT_REPORT_MODIFIED = "report_modified"
    
    @staticmethod
    def log_event(
        db: Session,
        user_id: Optional[int],
        event_type: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        status: str = "success"
    ) -> AuditLog:
        """Log an audit event"""
        
        audit_log = AuditLog(
            user_id=user_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details,
            ip_address=ip_address,
            status=status,
            timestamp=datetime.utcnow()
        )
        
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        return audit_log
    
    @staticmethod
    def log_action(
        db: Session,
        user_id: Optional[int],
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        status: str = "success"
    ) -> AuditLog:
        """Log a user action (shorthand for log_event)"""
        return AuditService.log_event(
            db=db,
            user_id=user_id,
            event_type=action,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details,
            ip_address=ip_address,
            status=status
        )
    
    @staticmethod
    def log_login(db: Session, user_id: int, method: str = "local", ip_address: Optional[str] = None):
        """Log a login event"""
        return AuditService.log_event(
            db=db,
            user_id=user_id,
            event_type=AuditService.EVENT_LOGIN,
            action=f"login_{method}",
            details=f"User logged in via {method}",
            ip_address=ip_address,
            status="success"
        )
    
    @staticmethod
    def log_logout(db: Session, user_id: int, ip_address: Optional[str] = None):
        """Log a logout event"""
        return AuditService.log_event(
            db=db,
            user_id=user_id,
            event_type=AuditService.EVENT_LOGOUT,
            details="User logged out",
            ip_address=ip_address,
            status="success"
        )
    
    @staticmethod
    def log_access_denied(
        db: Session,
        user_id: Optional[int],
        resource_type: str,
        resource_id: str,
        reason: str,
        ip_address: Optional[str] = None
    ):
        """Log an access denied event"""
        return AuditService.log_event(
            db=db,
            user_id=user_id,
            event_type=AuditService.EVENT_ACCESS_DENIED,
            resource_type=resource_type,
            resource_id=resource_id,
            details=f"Access denied: {reason}",
            ip_address=ip_address,
            status="denied"
        )
    
    @staticmethod
    def log_document_viewed(db: Session, user_id: int, document_id: str, ip_address: Optional[str] = None):
        """Log a document view event"""
        return AuditService.log_event(
            db=db,
            user_id=user_id,
            event_type=AuditService.EVENT_DOCUMENT_VIEWED,
            resource_type="document",
            resource_id=document_id,
            details=f"Document {document_id} viewed",
            ip_address=ip_address,
            status="success"
        )
    
    @staticmethod
    def log_document_exported(db: Session, user_id: int, document_id: str, format: str, ip_address: Optional[str] = None):
        """Log a document export event"""
        return AuditService.log_event(
            db=db,
            user_id=user_id,
            event_type=AuditService.EVENT_DOCUMENT_EXPORTED,
            resource_type="document",
            resource_id=document_id,
            action="export",
            details=f"Document exported as {format}",
            ip_address=ip_address,
            status="success"
        )
    
    @staticmethod
    def log_role_changed(db: Session, user_id: int, old_role: str, new_role: str, changed_by: int, ip_address: Optional[str] = None):
        """Log a role change event"""
        return AuditService.log_event(
            db=db,
            user_id=user_id,
            event_type=AuditService.EVENT_ROLE_CHANGED,
            resource_type="user",
            resource_id=str(user_id),
            action="role_change",
            details=f"Role changed from {old_role} to {new_role} by user {changed_by}",
            ip_address=ip_address,
            status="success"
        )
    
    @staticmethod
    def get_audit_logs(db: Session, user_id: Optional[int] = None, limit: int = 100):
        """Get audit logs, optionally filtered by user"""
        query = db.query(AuditLog)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    @staticmethod
    def get_user_activity_summary(db: Session, user_id: int, days: int = 30):
        """Get activity summary for a user over specified days"""
        from datetime import timedelta
        start_date = datetime.utcnow() - timedelta(days=days)
        
        logs = db.query(AuditLog).filter(
            AuditLog.user_id == user_id,
            AuditLog.timestamp >= start_date
        ).all()
        
        return {
            "total_events": len(logs),
            "events_by_type": _count_by_field(logs, "event_type"),
            "events_by_status": _count_by_field(logs, "status"),
            "last_activity": logs[0].timestamp if logs else None
        }

def _count_by_field(items, field):
    """Helper to count items by a specific field"""
    counts = {}
    for item in items:
        value = getattr(item, field)
        counts[value] = counts.get(value, 0) + 1
    return counts
