"""
Orthanc Management Business Logic - Audit Manager
Handles audit logging operations and compliance reporting
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
import json

from ..database.manager import DatabaseManager
from ..models.audit_log import AuditLog


class AuditManager:
    """
    Business logic manager for audit logs and compliance reporting
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_log(self, user_id: str = None, user_type: str = 'system',
                   user_name: str = None, hpcsa_number: str = None,
                   action: str = None, resource_type: str = None,
                   resource_id: str = None, details: Dict[str, Any] = None,
                   ip_address: str = None, user_agent: str = None,
                   session_id: str = None, request_method: str = None,
                   request_url: str = None, success: bool = True,
                   error_message: str = None, response_code: str = None,
                   data_accessed: List[str] = None, patient_ids: List[str] = None,
                   study_uids: List[str] = None, compliance_category: str = None) -> Tuple[AuditLog, list]:
        """
        Create a new audit log entry
        
        Returns:
            Tuple of (audit_log, validation_errors)
        """
        try:
            with self.db_manager.get_session() as session:
                # Create audit log
                log = AuditLog(
                    user_id=user_id,
                    user_type=user_type,
                    user_name=user_name,
                    hpcsa_number=hpcsa_number,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    session_id=session_id,
                    request_method=request_method,
                    request_url=request_url,
                    success=success,
                    error_message=error_message,
                    response_code=response_code,
                    compliance_category=compliance_category
                )
                
                # Set JSON fields
                if details:
                    log.set_details(details)
                if data_accessed:
                    log.set_data_accessed(data_accessed)
                if patient_ids:
                    log.set_patient_ids(patient_ids)
                if study_uids:
                    log.set_study_uids(study_uids)
                
                # Validate
                errors = log.validate()
                if errors:
                    return None, errors
                
                # Save
                session.add(log)
                session.commit()
                
                return log, []
                
        except Exception as e:
            return None, [f"Database error: {str(e)}"]
    
    def get_log_by_id(self, log_id: str) -> Optional[AuditLog]:
        """Get audit log by ID"""
        try:
            with self.db_manager.get_session() as session:
                return session.query(AuditLog).filter(AuditLog.id == log_id).first()
        except Exception:
            return None
    
    def search_logs(self, user_id: str = None, user_type: str = None,
                   action: str = None, resource_type: str = None,
                   resource_id: str = None, patient_id: str = None,
                   study_uid: str = None, compliance_category: str = None,
                   start_date: datetime = None, end_date: datetime = None,
                   success: bool = None, ip_address: str = None,
                   hpcsa_number: str = None, limit: int = 1000,
                   offset: int = 0, order_by: str = 'timestamp',
                   order_direction: str = 'desc') -> List[AuditLog]:
        """
        Search audit logs with comprehensive filtering
        """
        try:
            with self.db_manager.get_session() as session:
                query = session.query(AuditLog)
                
                # Apply filters
                if user_id:
                    query = query.filter(AuditLog.user_id == user_id)
                
                if user_type:
                    query = query.filter(AuditLog.user_type == user_type)
                
                if action:
                    query = query.filter(AuditLog.action == action)
                
                if resource_type:
                    query = query.filter(AuditLog.resource_type == resource_type)
                
                if resource_id:
                    query = query.filter(AuditLog.resource_id == resource_id)
                
                if compliance_category:
                    query = query.filter(AuditLog.compliance_category == compliance_category)
                
                if start_date:
                    query = query.filter(AuditLog.timestamp >= start_date)
                
                if end_date:
                    query = query.filter(AuditLog.timestamp <= end_date)
                
                if success is not None:
                    query = query.filter(AuditLog.success == success)
                
                if ip_address:
                    query = query.filter(AuditLog.ip_address == ip_address)
                
                if hpcsa_number:
                    query = query.filter(AuditLog.hpcsa_number == hpcsa_number)
                
                # Patient and study filters (JSON field searches)
                if patient_id:
                    query = query.filter(AuditLog.patient_ids.contains(f'"{patient_id}"'))
                
                if study_uid:
                    query = query.filter(AuditLog.study_uids.contains(f'"{study_uid}"'))
                
                # Order by
                order_col = getattr(AuditLog, order_by, AuditLog.timestamp)
                if order_direction.lower() == 'asc':
                    query = query.order_by(asc(order_col))
                else:
                    query = query.order_by(desc(order_col))
                
                # Pagination
                if offset:
                    query = query.offset(offset)
                if limit:
                    query = query.limit(limit)
                
                return query.all()
                
        except Exception:
            return []
    
    def get_patient_access_logs(self, patient_id: str, start_date: datetime = None,
                              end_date: datetime = None) -> List[AuditLog]:
        """Get all audit logs for patient data access"""
        try:
            with self.db_manager.get_session() as session:
                query = session.query(AuditLog).filter(
                    AuditLog.patient_ids.contains(f'"{patient_id}"')
                )
                
                if start_date:
                    query = query.filter(AuditLog.timestamp >= start_date)
                
                if end_date:
                    query = query.filter(AuditLog.timestamp <= end_date)
                
                return query.order_by(desc(AuditLog.timestamp)).all()
                
        except Exception:
            return []
    
    def get_doctor_activity_logs(self, hpcsa_number: str, start_date: datetime = None,
                               end_date: datetime = None) -> List[AuditLog]:
        """Get all audit logs for a doctor's activity"""
        try:
            with self.db_manager.get_session() as session:
                query = session.query(AuditLog).filter(
                    AuditLog.hpcsa_number == hpcsa_number
                )
                
                if start_date:
                    query = query.filter(AuditLog.timestamp >= start_date)
                
                if end_date:
                    query = query.filter(AuditLog.timestamp <= end_date)
                
                return query.order_by(desc(AuditLog.timestamp)).all()
                
        except Exception:
            return []
    
    def get_security_logs(self, start_date: datetime = None, end_date: datetime = None,
                         failed_only: bool = False) -> List[AuditLog]:
        """Get security-relevant audit logs"""
        try:
            with self.db_manager.get_session() as session:
                security_actions = [
                    'login', 'logout', 'login_failed', 'password_change', 'account_locked',
                    'grant_access', 'revoke_access', 'config_change', 'user_management'
                ]
                
                query = session.query(AuditLog).filter(
                    or_(
                        AuditLog.action.in_(security_actions),
                        AuditLog.success == False
                    )
                )
                
                if failed_only:
                    query = query.filter(AuditLog.success == False)
                
                if start_date:
                    query = query.filter(AuditLog.timestamp >= start_date)
                
                if end_date:
                    query = query.filter(AuditLog.timestamp <= end_date)
                
                return query.order_by(desc(AuditLog.timestamp)).all()
                
        except Exception:
            return []
    
    def get_compliance_report(self, start_date: datetime, end_date: datetime,
                            compliance_category: str = None) -> Dict[str, Any]:
        """Generate compliance report for specified period"""
        try:
            with self.db_manager.get_session() as session:
                query = session.query(AuditLog).filter(
                    and_(
                        AuditLog.timestamp >= start_date,
                        AuditLog.timestamp <= end_date
                    )
                )
                
                if compliance_category:
                    query = query.filter(AuditLog.compliance_category == compliance_category)
                
                logs = query.all()
                
                # Generate report statistics
                total_actions = len(logs)
                successful_actions = sum(1 for log in logs if log.success)
                failed_actions = total_actions - successful_actions
                
                # User activity breakdown
                user_activity = {}
                for log in logs:
                    user_key = log.hpcsa_number or log.user_id or 'unknown'
                    if user_key not in user_activity:
                        user_activity[user_key] = {
                            'user_name': log.user_name,
                            'user_type': log.user_type,
                            'total_actions': 0,
                            'failed_actions': 0,
                            'patient_data_access': 0
                        }
                    
                    user_activity[user_key]['total_actions'] += 1
                    if not log.success:
                        user_activity[user_key]['failed_actions'] += 1
                    if log.is_patient_data_access():
                        user_activity[user_key]['patient_data_access'] += 1
                
                # Action type breakdown
                action_stats = {}
                for log in logs:
                    action = log.action
                    if action not in action_stats:
                        action_stats[action] = {'count': 0, 'failed': 0}
                    action_stats[action]['count'] += 1
                    if not log.success:
                        action_stats[action]['failed'] += 1
                
                # Patient data access summary
                unique_patients = set()
                unique_studies = set()
                for log in logs:
                    if log.is_patient_data_access():
                        unique_patients.update(log.get_patient_ids())
                        unique_studies.update(log.get_study_uids())
                
                # Daily activity
                daily_activity = {}
                for log in logs:
                    day = log.timestamp.date().isoformat()
                    if day not in daily_activity:
                        daily_activity[day] = {'total': 0, 'failed': 0, 'patient_access': 0}
                    daily_activity[day]['total'] += 1
                    if not log.success:
                        daily_activity[day]['failed'] += 1
                    if log.is_patient_data_access():
                        daily_activity[day]['patient_access'] += 1
                
                return {
                    'report_period': {
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat(),
                        'compliance_category': compliance_category
                    },
                    'summary': {
                        'total_actions': total_actions,
                        'successful_actions': successful_actions,
                        'failed_actions': failed_actions,
                        'success_rate': (successful_actions / total_actions * 100) if total_actions > 0 else 0,
                        'unique_patients_accessed': len(unique_patients),
                        'unique_studies_accessed': len(unique_studies)
                    },
                    'user_activity': user_activity,
                    'action_statistics': action_stats,
                    'daily_activity': daily_activity,
                    'generated_at': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {'error': str(e)}
    
    def get_failed_login_attempts(self, hours_back: int = 24,
                                ip_address: str = None) -> List[AuditLog]:
        """Get failed login attempts in specified time period"""
        try:
            with self.db_manager.get_session() as session:
                start_time = datetime.utcnow() - timedelta(hours=hours_back)
                
                query = session.query(AuditLog).filter(
                    and_(
                        AuditLog.action == 'login_failed',
                        AuditLog.timestamp >= start_time
                    )
                )
                
                if ip_address:
                    query = query.filter(AuditLog.ip_address == ip_address)
                
                return query.order_by(desc(AuditLog.timestamp)).all()
                
        except Exception:
            return []
    
    def detect_suspicious_activity(self, hours_back: int = 24) -> Dict[str, Any]:
        """Detect potentially suspicious activity patterns"""
        try:
            with self.db_manager.get_session() as session:
                start_time = datetime.utcnow() - timedelta(hours=hours_back)
                
                logs = session.query(AuditLog).filter(
                    AuditLog.timestamp >= start_time
                ).all()
                
                suspicious_patterns = {
                    'multiple_failed_logins': {},
                    'unusual_access_patterns': {},
                    'bulk_data_access': {},
                    'off_hours_access': [],
                    'suspicious_ips': set()
                }
                
                # Analyze patterns
                user_failures = {}
                ip_failures = {}
                user_patient_access = {}
                
                for log in logs:
                    # Failed login tracking
                    if log.action == 'login_failed':
                        user_key = log.user_id or log.ip_address
                        user_failures[user_key] = user_failures.get(user_key, 0) + 1
                        
                        ip_failures[log.ip_address] = ip_failures.get(log.ip_address, 0) + 1
                        
                        # Flag IPs with many failures
                        if ip_failures[log.ip_address] >= 5:
                            suspicious_patterns['suspicious_ips'].add(log.ip_address)
                    
                    # Patient data access patterns
                    if log.is_patient_data_access() and log.user_id:
                        if log.user_id not in user_patient_access:
                            user_patient_access[log.user_id] = set()
                        user_patient_access[log.user_id].update(log.get_patient_ids())
                    
                    # Off-hours access (outside 7 AM - 7 PM)
                    if log.timestamp.hour < 7 or log.timestamp.hour > 19:
                        if log.is_patient_data_access():
                            suspicious_patterns['off_hours_access'].append({
                                'timestamp': log.timestamp.isoformat(),
                                'user_id': log.user_id,
                                'user_name': log.user_name,
                                'action': log.action,
                                'patient_ids': log.get_patient_ids()
                            })
                
                # Flag multiple failed logins
                for user, count in user_failures.items():
                    if count >= 3:
                        suspicious_patterns['multiple_failed_logins'][user] = count
                
                # Flag bulk data access
                for user, patients in user_patient_access.items():
                    if len(patients) >= 10:  # Accessed 10+ different patients
                        suspicious_patterns['bulk_data_access'][user] = len(patients)
                
                return suspicious_patterns
                
        except Exception as e:
            return {'error': str(e)}
    
    def cleanup_old_logs(self, days_to_keep: int = 365) -> int:
        """Clean up audit logs older than specified days"""
        try:
            with self.db_manager.get_session() as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
                
                # Count logs to be deleted
                count = session.query(AuditLog).filter(
                    AuditLog.timestamp < cutoff_date
                ).count()
                
                # Delete old logs
                session.query(AuditLog).filter(
                    AuditLog.timestamp < cutoff_date
                ).delete()
                
                session.commit()
                
                # Log the cleanup
                self.create_log(
                    user_type='system',
                    action='cleanup_audit_logs',
                    resource_type='system',
                    details={
                        'logs_deleted': count,
                        'cutoff_date': cutoff_date.isoformat(),
                        'days_kept': days_to_keep
                    },
                    compliance_category='security'
                )
                
                return count
                
        except Exception:
            return 0
    
    def export_logs(self, start_date: datetime, end_date: datetime,
                   filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Export audit logs for external analysis"""
        try:
            logs = self.search_logs(
                start_date=start_date,
                end_date=end_date,
                limit=None,  # No limit for export
                **(filters or {})
            )
            
            export_data = []
            for log in logs:
                export_data.append(log.to_dict(include_sensitive=True))
            
            return export_data
            
        except Exception:
            return []
    
    def get_audit_statistics(self, days_back: int = 30) -> Dict[str, Any]:
        """Get audit log statistics"""
        try:
            with self.db_manager.get_session() as session:
                start_date = datetime.utcnow() - timedelta(days=days_back)
                
                total = session.query(AuditLog).filter(
                    AuditLog.timestamp >= start_date
                ).count()
                
                successful = session.query(AuditLog).filter(
                    and_(
                        AuditLog.timestamp >= start_date,
                        AuditLog.success == True
                    )
                ).count()
                
                failed = total - successful
                
                # User type breakdown
                user_types = session.query(
                    AuditLog.user_type,
                    func.count(AuditLog.id)
                ).filter(
                    AuditLog.timestamp >= start_date
                ).group_by(AuditLog.user_type).all()
                
                # Action breakdown
                actions = session.query(
                    AuditLog.action,
                    func.count(AuditLog.id)
                ).filter(
                    AuditLog.timestamp >= start_date
                ).group_by(AuditLog.action).order_by(
                    desc(func.count(AuditLog.id))
                ).limit(10).all()
                
                # Compliance categories
                compliance = session.query(
                    AuditLog.compliance_category,
                    func.count(AuditLog.id)
                ).filter(
                    and_(
                        AuditLog.timestamp >= start_date,
                        AuditLog.compliance_category.isnot(None)
                    )
                ).group_by(AuditLog.compliance_category).all()
                
                return {
                    'period_days': days_back,
                    'total_logs': total,
                    'successful_actions': successful,
                    'failed_actions': failed,
                    'success_rate': (successful / total * 100) if total > 0 else 0,
                    'user_type_breakdown': dict(user_types),
                    'top_actions': dict(actions),
                    'compliance_breakdown': dict(compliance)
                }
                
        except Exception as e:
            return {'error': str(e)}
    
    def log_login(self, user_id: str, user_type: str, user_name: str,
                 success: bool, ip_address: str = None, hpcsa_number: str = None,
                 error_message: str = None, user_agent: str = None,
                 session_id: str = None) -> AuditLog:
        """Convenience method for logging authentication attempts"""
        log, _ = self.create_log(
            user_id=user_id,
            user_type=user_type,
            user_name=user_name,
            hpcsa_number=hpcsa_number,
            action='login' if success else 'login_failed',
            resource_type='session',
            resource_id=user_id,
            success=success,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            compliance_category='hpcsa' if user_type == 'doctor' else 'security'
        )
        return log
    
    def log_patient_access(self, user_id: str, user_type: str, user_name: str,
                          action: str, patient_id: str, study_uid: str = None,
                          hpcsa_number: str = None, details: Dict[str, Any] = None,
                          ip_address: str = None, success: bool = True) -> AuditLog:
        """Convenience method for logging patient data access"""
        log, _ = self.create_log(
            user_id=user_id,
            user_type=user_type,
            user_name=user_name,
            hpcsa_number=hpcsa_number,
            action=action,
            resource_type='patient',
            resource_id=patient_id,
            details=details,
            patient_ids=[patient_id],
            study_uids=[study_uid] if study_uid else None,
            ip_address=ip_address,
            success=success,
            compliance_category='hpcsa' if user_type == 'doctor' else 'popia'
        )
        return log
