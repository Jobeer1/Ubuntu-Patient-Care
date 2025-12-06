"""
Orthanc Management API - Dashboard Router
Dashboard analytics, statistics, and overview endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import logging

from orthanc_management.api.auth import User
from orthanc_management.api.routers.auth import get_current_active_user, get_auth_manager
from orthanc_management.managers.doctor_manager import DoctorManager
from orthanc_management.managers.authorization_manager import AuthorizationManager
from orthanc_management.managers.config_manager import ConfigManager
from orthanc_management.managers.audit_manager import AuditManager
from orthanc_management.database.manager import DatabaseManager

logger = logging.getLogger(__name__)

# Pydantic models for dashboard responses
class SystemStats(BaseModel):
    total_doctors: int
    active_doctors: int
    total_authorizations: int
    active_authorizations: int
    expired_authorizations: int
    total_configurations: int
    active_configurations: int
    system_uptime: str
    last_backup: Optional[str]

class ActivityStats(BaseModel):
    daily_logins: int
    weekly_logins: int
    monthly_logins: int
    recent_authorizations: int
    recent_doctor_registrations: int
    recent_config_changes: int
    api_requests_today: int
    failed_login_attempts: int

class ComplianceStats(BaseModel):
    popia_compliant_authorizations: int
    consent_forms_generated: int
    data_retention_violations: int
    expired_authorizations_needing_action: int
    audit_log_entries_today: int
    security_incidents: int
    hpcsa_verifications_pending: int

class AlertsAndNotifications(BaseModel):
    critical_alerts: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    upcoming_expirations: List[Dict[str, Any]]
    system_notifications: List[Dict[str, Any]]
    pending_approvals: List[Dict[str, Any]]

class DashboardOverview(BaseModel):
    system_stats: SystemStats
    activity_stats: ActivityStats
    compliance_stats: ComplianceStats
    alerts_notifications: AlertsAndNotifications
    quick_actions: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]

class ChartData(BaseModel):
    labels: List[str]
    datasets: List[Dict[str, Any]]
    chart_type: str
    title: str
    description: Optional[str]

class ReportSummary(BaseModel):
    report_id: str
    title: str
    description: str
    generated_at: str
    file_path: Optional[str]
    data_points: int
    report_type: str

# Router instance
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Dependency to get database session
def get_db():
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

# Dependencies to get managers
def get_doctor_manager(db = Depends(get_db)):
    return DoctorManager(db)

def get_authorization_manager(db = Depends(get_db)):
    return AuthorizationManager(db)

def get_config_manager(db = Depends(get_db)):
    return ConfigManager(db)

def get_audit_manager(db = Depends(get_db)):
    return AuditManager(db)


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    current_user: User = Depends(get_current_active_user),
    doctor_manager: DoctorManager = Depends(get_doctor_manager),
    auth_manager: AuthorizationManager = Depends(get_authorization_manager),
    config_manager: ConfigManager = Depends(get_config_manager),
    audit_manager: AuditManager = Depends(get_audit_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Get comprehensive dashboard overview
    Requires 'read' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "read")
        
        # Get system statistics
        doctor_stats = doctor_manager.get_doctor_statistics()
        auth_stats = auth_manager.get_authorization_statistics()
        config_stats = config_manager.get_config_statistics()
        
        system_stats = SystemStats(
            total_doctors=doctor_stats["total_doctors"],
            active_doctors=doctor_stats["active_doctors"],
            total_authorizations=auth_stats["total_authorizations"],
            active_authorizations=auth_stats["active_authorizations"],
            expired_authorizations=auth_stats["expired_authorizations"],
            total_configurations=config_stats["total_configurations"],
            active_configurations=config_stats["active_configurations"],
            system_uptime="5 days, 12 hours",  # This would come from system monitoring
            last_backup=None  # This would come from backup system
        )
        
        # Get activity statistics
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        activity_stats = ActivityStats(
            daily_logins=10,  # These would come from audit logs
            weekly_logins=45,
            monthly_logins=180,
            recent_authorizations=auth_stats.get("recent_activity", [])[:5].__len__(),
            recent_doctor_registrations=3,
            recent_config_changes=config_stats.get("recent_changes", [])[:5].__len__(),
            api_requests_today=150,
            failed_login_attempts=2
        )
        
        # Get compliance statistics
        compliance_stats = ComplianceStats(
            popia_compliant_authorizations=auth_stats["active_authorizations"],
            consent_forms_generated=25,
            data_retention_violations=0,
            expired_authorizations_needing_action=auth_stats.get("pending_expiry", 0),
            audit_log_entries_today=50,
            security_incidents=0,
            hpcsa_verifications_pending=2
        )
        
        # Get alerts and notifications
        expiring_auths = auth_manager.get_expiring_authorizations(7)
        
        alerts_notifications = AlertsAndNotifications(
            critical_alerts=[],
            warnings=[
                {
                    "id": "warn_001",
                    "message": f"{len(expiring_auths)} authorizations expiring in 7 days",
                    "type": "expiration_warning",
                    "created_at": datetime.utcnow().isoformat()
                }
            ] if expiring_auths else [],
            upcoming_expirations=[
                {
                    "id": auth.id,
                    "patient_name": auth.patient_name,
                    "expiry_date": auth.expiry_date.isoformat() if auth.expiry_date else None,
                    "type": "authorization"
                } for auth in expiring_auths[:5]
            ],
            system_notifications=[
                {
                    "id": "sys_001",
                    "message": "System backup completed successfully",
                    "type": "info",
                    "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat()
                }
            ],
            pending_approvals=[]
        )
        
        # Quick actions for the current user role
        quick_actions = []
        if user_auth_manager.has_permission(current_user, "write"):
            quick_actions.extend([
                {"id": "add_doctor", "title": "Add New Doctor", "icon": "user-plus", "url": "/doctors/new"},
                {"id": "add_auth", "title": "Create Authorization", "icon": "shield-check", "url": "/authorizations/new"}
            ])
        
        if user_auth_manager.has_permission(current_user, "admin"):
            quick_actions.extend([
                {"id": "system_config", "title": "System Configuration", "icon": "settings", "url": "/configurations"},
                {"id": "audit_logs", "title": "View Audit Logs", "icon": "file-text", "url": "/audit"}
            ])
        
        # Recent activity (last 10 items)
        recent_activity = [
            {
                "id": "act_001",
                "type": "authorization_created",
                "description": "New authorization created for patient John Doe",
                "user": "Dr. Smith",
                "timestamp": (datetime.utcnow() - timedelta(minutes=30)).isoformat()
            },
            {
                "id": "act_002",
                "type": "doctor_registered",
                "description": "New doctor registered: Dr. Jane Wilson",
                "user": "Admin",
                "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat()
            }
        ]
        
        return DashboardOverview(
            system_stats=system_stats,
            activity_stats=activity_stats,
            compliance_stats=compliance_stats,
            alerts_notifications=alerts_notifications,
            quick_actions=quick_actions,
            recent_activity=recent_activity
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dashboard overview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard overview"
        )


@router.get("/charts/authorizations-trend", response_model=ChartData)
async def get_authorizations_trend_chart(
    days: int = Query(30, ge=7, le=365, description="Number of days to include"),
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthorizationManager = Depends(get_authorization_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Get authorizations trend chart data
    Requires 'read' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "read")
        
        # Get trend data (this would be implemented in AuthorizationManager)
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # Mock data - replace with actual implementation
        labels = []
        created_data = []
        expired_data = []
        
        for i in range(days):
            date_label = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            labels.append(date_label)
            created_data.append(max(0, 5 + (i % 7) - 2))  # Mock data
            expired_data.append(max(0, 2 + (i % 5) - 1))  # Mock data
        
        return ChartData(
            labels=labels,
            datasets=[
                {
                    "label": "Created",
                    "data": created_data,
                    "borderColor": "#10B981",
                    "backgroundColor": "rgba(16, 185, 129, 0.1)",
                    "tension": 0.4
                },
                {
                    "label": "Expired",
                    "data": expired_data,
                    "borderColor": "#EF4444",
                    "backgroundColor": "rgba(239, 68, 68, 0.1)",
                    "tension": 0.4
                }
            ],
            chart_type="line",
            title="Authorizations Trend",
            description=f"Created vs Expired authorizations over the last {days} days"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get authorizations trend chart: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chart data"
        )


@router.get("/charts/doctors-by-specialization", response_model=ChartData)
async def get_doctors_specialization_chart(
    current_user: User = Depends(get_current_active_user),
    doctor_manager: DoctorManager = Depends(get_doctor_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Get doctors by specialization chart data
    Requires 'read' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "read")
        
        # Get doctor statistics
        stats = doctor_manager.get_doctor_statistics()
        specialization_data = stats.get("by_specialization", {})
        
        labels = list(specialization_data.keys())
        data = list(specialization_data.values())
        
        # Generate colors for each specialization
        colors = [
            "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
            "#06B6D4", "#84CC16", "#F97316", "#EC4899", "#6B7280"
        ]
        
        return ChartData(
            labels=labels,
            datasets=[{
                "label": "Doctors by Specialization",
                "data": data,
                "backgroundColor": colors[:len(labels)],
                "borderWidth": 1
            }],
            chart_type="doughnut",
            title="Doctors by Specialization",
            description="Distribution of doctors across different specializations"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get doctors specialization chart: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chart data"
        )


@router.get("/charts/system-activity", response_model=ChartData)
async def get_system_activity_chart(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to include"),
    current_user: User = Depends(get_current_active_user),
    audit_manager: AuditManager = Depends(get_audit_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Get system activity chart data
    Requires 'read' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "read")
        
        # Mock data for system activity (replace with actual audit log analysis)
        labels = []
        api_requests = []
        logins = []
        
        for i in range(hours):
            hour_label = (datetime.utcnow() - timedelta(hours=hours-i-1)).strftime("%H:00")
            labels.append(hour_label)
            api_requests.append(max(0, 20 + (i % 8) + (i % 3)))  # Mock data
            logins.append(max(0, 3 + (i % 5)))  # Mock data
        
        return ChartData(
            labels=labels,
            datasets=[
                {
                    "label": "API Requests",
                    "data": api_requests,
                    "borderColor": "#3B82F6",
                    "backgroundColor": "rgba(59, 130, 246, 0.1)",
                    "yAxisID": "y"
                },
                {
                    "label": "User Logins",
                    "data": logins,
                    "borderColor": "#10B981",
                    "backgroundColor": "rgba(16, 185, 129, 0.1)",
                    "yAxisID": "y1"
                }
            ],
            chart_type="line",
            title="System Activity",
            description=f"API requests and user logins over the last {hours} hours"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get system activity chart: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chart data"
        )


@router.get("/alerts")
async def get_dashboard_alerts(
    severity: Optional[str] = Query(None, regex="^(critical|warning|info)$", description="Filter by severity"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of alerts"),
    current_user: User = Depends(get_current_active_user),
    auth_manager: AuthorizationManager = Depends(get_authorization_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Get current system alerts and notifications
    Requires 'read' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "read")
        
        alerts = []
        
        # Check for expiring authorizations
        expiring_auths = auth_manager.get_expiring_authorizations(7)
        if expiring_auths:
            alerts.append({
                "id": "exp_auths_001",
                "type": "expiring_authorizations",
                "severity": "warning",
                "title": "Authorizations Expiring Soon",
                "message": f"{len(expiring_auths)} authorization(s) expiring in the next 7 days",
                "count": len(expiring_auths),
                "action_url": "/authorizations?expiring=true",
                "created_at": datetime.utcnow().isoformat()
            })
        
        # Check for system health (mock)
        alerts.append({
            "id": "sys_health_001",
            "type": "system_health",
            "severity": "info",
            "title": "System Status",
            "message": "All systems operational",
            "created_at": datetime.utcnow().isoformat()
        })
        
        # Filter by severity if provided
        if severity:
            alerts = [alert for alert in alerts if alert["severity"] == severity]
        
        # Limit results
        alerts = alerts[:limit]
        
        return {
            "alerts": alerts,
            "total": len(alerts),
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dashboard alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alerts"
        )


@router.get("/quick-stats")
async def get_quick_stats(
    current_user: User = Depends(get_current_active_user),
    doctor_manager: DoctorManager = Depends(get_doctor_manager),
    auth_manager: AuthorizationManager = Depends(get_authorization_manager),
    config_manager: ConfigManager = Depends(get_config_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Get quick statistics for dashboard widgets
    Requires 'read' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "read")
        
        # Get basic statistics
        doctor_stats = doctor_manager.get_doctor_statistics()
        auth_stats = auth_manager.get_authorization_statistics()
        config_stats = config_manager.get_config_statistics()
        
        return {
            "doctors": {
                "total": doctor_stats["total_doctors"],
                "active": doctor_stats["active_doctors"],
                "change_24h": "+2"  # Mock data
            },
            "authorizations": {
                "total": auth_stats["total_authorizations"],
                "active": auth_stats["active_authorizations"],
                "expired": auth_stats["expired_authorizations"],
                "change_24h": "+5"  # Mock data
            },
            "configurations": {
                "total": config_stats["total_configurations"],
                "active": config_stats["active_configurations"],
                "change_24h": "0"  # Mock data
            },
            "system": {
                "uptime": "99.9%",
                "last_backup": "2 hours ago",
                "api_health": "healthy",
                "database_health": "healthy"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get quick stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quick statistics"
        )


@router.post("/generate-report")
async def generate_dashboard_report(
    report_type: str = Query(..., regex="^(summary|detailed|compliance|activity)$", description="Type of report"),
    start_date: Optional[date] = Query(None, description="Start date for report"),
    end_date: Optional[date] = Query(None, description="End date for report"),
    format: str = Query("pdf", regex="^(pdf|csv|excel)$", description="Report format"),
    current_user: User = Depends(get_current_active_user),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Generate dashboard report
    Requires 'read' permission
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "read")
        
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow().date()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Generate report (this would be implemented with actual reporting logic)
        report_id = f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Dashboard report generated by {current_user.username}: {report_type}")
        
        return {
            "report_id": report_id,
            "report_type": report_type,
            "format": format,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
            "download_url": f"/api/dashboard/reports/{report_id}/download",
            "status": "generating"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate dashboard report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )


@router.get("/user-activity/{user_id}")
async def get_user_activity(
    user_id: str,
    days: int = Query(7, ge=1, le=30, description="Number of days to include"),
    current_user: User = Depends(get_current_active_user),
    audit_manager: AuditManager = Depends(get_audit_manager),
    user_auth_manager = Depends(get_auth_manager)
):
    """
    Get activity for specific user (admin only or own activity)
    Requires 'read' permission and admin for other users
    """
    try:
        # Check permission
        user_auth_manager.require_permission(current_user, "read")
        
        # Check if user is accessing own activity or has admin permission
        if current_user.id != user_id:
            user_auth_manager.require_permission(current_user, "admin")
        
        # Get user activity (this would be implemented in AuditManager)
        activity = []  # Mock data
        
        return {
            "user_id": user_id,
            "period_days": days,
            "activity": activity,
            "summary": {
                "total_actions": len(activity),
                "login_count": 5,
                "last_activity": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user activity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user activity"
        )
