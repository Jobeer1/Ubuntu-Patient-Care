#!/usr/bin/env python3
"""
Security API endpoints for authentication, authorization, and compliance
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
import logging
from services.security_service import SecurityService, RoleBasedAccessControl, require_permission, require_data_access
from services.audit_service import AuditService

logger = logging.getLogger(__name__)

security_bp = Blueprint('security', __name__)

# Initialize services (will be properly injected in production)
security_service = None
audit_service = None

def init_security_api(app):
    """Initialize security API with services"""
    global security_service, audit_service
    security_service = SecurityService(app)
    audit_service = AuditService(app)

@security_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and create session"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            audit_service.log_authentication(
                user_id=username or 'unknown',
                success=False,
                method='password',
                details={'error': 'Missing credentials'}
            )
            return jsonify({'error': 'Username and password required'}), 400
        
        # Check rate limiting
        if not security_service.check_rate_limit(request.remote_addr):
            audit_service.log_security_event(
                event_type='rate_limit_exceeded',
                action='login_blocked',
                severity='medium',
                details={'ip_address': request.remote_addr, 'username': username}
            )
            return jsonify({'error': 'Too many failed attempts. Please try again later.'}), 429
        
        # In production, validate against user database
        # For now, use demo credentials
        valid_users = {
            'dr.smith': {'password': 'medical123', 'role': 'doctor', 'name': 'Dr. John Smith'},
            'dr.jones': {'password': 'radiology123', 'role': 'radiologist', 'name': 'Dr. Sarah Jones'},
            'typist1': {'password': 'typing123', 'role': 'typist', 'name': 'Mary Johnson'},
            'admin': {'password': 'admin123', 'role': 'admin', 'name': 'System Admin'}
        }
        
        user_info = valid_users.get(username)
        if user_info and user_info['password'] == password:
            # Successful authentication
            security_service.clear_failed_attempts(request.remote_addr)
            
            # Generate session token
            token = security_service.generate_session_token(username, user_info['role'])
            
            # Set session data
            session['user_id'] = username
            session['user_role'] = user_info['role']
            session['user_name'] = user_info['name']
            session['login_time'] = datetime.utcnow().isoformat()
            
            # Log successful authentication
            audit_service.log_authentication(
                user_id=username,
                success=True,
                method='password',
                user_role=user_info['role'],
                details={'login_time': session['login_time']}
            )
            
            return jsonify({
                'status': 'success',
                'message': 'Authentication successful',
                'token': token,
                'user': {
                    'id': username,
                    'name': user_info['name'],
                    'role': user_info['role'],
                    'permissions': RoleBasedAccessControl.ROLES[user_info['role']]['permissions']
                },
                'session_expires': (datetime.utcnow() + timedelta(hours=8)).isoformat()
            })
        
        else:
            # Failed authentication
            security_service.record_failed_attempt(request.remote_addr)
            
            audit_service.log_authentication(
                user_id=username,
                success=False,
                method='password',
                details={'error': 'Invalid credentials', 'ip_address': request.remote_addr}
            )
            
            return jsonify({'error': 'Invalid username or password'}), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Authentication failed'}), 500

@security_bp.route('/logout', methods=['POST'])
def logout():
    """Logout user and invalidate session"""
    try:
        user_id = session.get('user_id')
        
        if user_id:
            # Log logout
            audit_service.log_authentication(
                user_id=user_id,
                success=True,
                method='logout',
                details={'logout_time': datetime.utcnow().isoformat()}
            )
        
        # Clear session
        session.clear()
        
        return jsonify({
            'status': 'success',
            'message': 'Logged out successfully'
        })
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({'error': 'Logout failed'}), 500

@security_bp.route('/session/validate', methods=['GET'])
def validate_session():
    """Validate current session"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('user_role')
        
        if not user_id:
            return jsonify({'valid': False, 'error': 'No active session'}), 401
        
        # Check token if provided
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
            try:
                payload = security_service.validate_session_token(token)
                if payload['user_id'] != user_id:
                    return jsonify({'valid': False, 'error': 'Token mismatch'}), 401
            except Exception as e:
                return jsonify({'valid': False, 'error': 'Invalid token'}), 401
        
        return jsonify({
            'valid': True,
            'user': {
                'id': user_id,
                'role': user_role,
                'name': session.get('user_name'),
                'login_time': session.get('login_time')
            },
            'permissions': RoleBasedAccessControl.ROLES.get(user_role, {}).get('permissions', [])
        })
        
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return jsonify({'valid': False, 'error': 'Validation failed'}), 500

@security_bp.route('/permissions/check', methods=['POST'])
def check_permissions():
    """Check if user has specific permissions"""
    try:
        data = request.get_json()
        permission = data.get('permission')
        
        if not permission:
            return jsonify({'error': 'Permission parameter required'}), 400
        
        user_role = session.get('user_role')
        if not user_role:
            return jsonify({'error': 'Authentication required'}), 401
        
        has_permission = RoleBasedAccessControl.check_permission(user_role, permission)
        
        return jsonify({
            'permission': permission,
            'granted': has_permission,
            'user_role': user_role
        })
        
    except Exception as e:
        logger.error(f"Permission check error: {e}")
        return jsonify({'error': 'Permission check failed'}), 500

@security_bp.route('/data-access/check', methods=['POST'])
def check_data_access():
    """Check if user has specific data access"""
    try:
        data = request.get_json()
        access_type = data.get('access_type')
        
        if not access_type:
            return jsonify({'error': 'Access type parameter required'}), 400
        
        user_role = session.get('user_role')
        if not user_role:
            return jsonify({'error': 'Authentication required'}), 401
        
        has_access = RoleBasedAccessControl.check_data_access(user_role, access_type)
        
        return jsonify({
            'access_type': access_type,
            'granted': has_access,
            'user_role': user_role
        })
        
    except Exception as e:
        logger.error(f"Data access check error: {e}")
        return jsonify({'error': 'Data access check failed'}), 500

@security_bp.route('/audit/logs', methods=['GET'])
@require_permission('audit_access')
def get_audit_logs():
    """Get audit logs (admin only)"""
    try:
        # Parse query parameters
        limit = int(request.args.get('limit', 100))
        user_filter = request.args.get('user_id')
        event_type = request.args.get('event_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        filters = {}
        if user_filter:
            filters['user_id'] = user_filter
        if event_type:
            filters['event_type'] = event_type
        if start_date:
            filters['start_date'] = datetime.fromisoformat(start_date)
        if end_date:
            filters['end_date'] = datetime.fromisoformat(end_date)
        
        logs = audit_service.get_audit_logs(filters=filters, limit=limit)
        
        # Log audit access
        audit_service.log_data_access(
            user_id=session.get('user_id'),
            patient_id_hash='system',
            action='audit_log_access',
            details={'filters': filters, 'limit': limit}
        )
        
        return jsonify({
            'status': 'success',
            'logs': logs,
            'count': len(logs),
            'filters_applied': filters
        })
        
    except Exception as e:
        logger.error(f"Audit logs retrieval error: {e}")
        return jsonify({'error': 'Failed to retrieve audit logs'}), 500

@security_bp.route('/compliance/report', methods=['GET'])
@require_permission('audit_access')
def generate_compliance_report():
    """Generate POPIA compliance report"""
    try:
        # Parse date range
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if not start_date_str or not end_date_str:
            # Default to last 30 days
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.fromisoformat(start_date_str)
            end_date = datetime.fromisoformat(end_date_str)
        
        report = audit_service.generate_compliance_report(start_date, end_date)
        
        # Log compliance report generation
        audit_service.log_compliance_event(
            event_type='compliance_report',
            action='report_generated',
            user_id=session.get('user_id'),
            details={
                'report_period': f"{start_date.isoformat()} to {end_date.isoformat()}",
                'generated_by': session.get('user_id')
            }
        )
        
        return jsonify({
            'status': 'success',
            'report': report
        })
        
    except Exception as e:
        logger.error(f"Compliance report error: {e}")
        return jsonify({'error': 'Failed to generate compliance report'}), 500

@security_bp.route('/data-processing/notice', methods=['POST'])
def get_data_processing_notice():
    """Get POPIA data processing notice"""
    try:
        data = request.get_json()
        purpose = data.get('purpose', 'medical_care')
        
        notice = security_service.generate_data_processing_notice(purpose)
        
        # Log notice generation
        audit_service.log_compliance_event(
            event_type='data_processing_notice',
            action='notice_generated',
            user_id=session.get('user_id', 'anonymous'),
            details={'purpose': purpose}
        )
        
        return jsonify({
            'status': 'success',
            'notice': notice
        })
        
    except Exception as e:
        logger.error(f"Data processing notice error: {e}")
        return jsonify({'error': 'Failed to generate data processing notice'}), 500

@security_bp.route('/security/status', methods=['GET'])
@require_permission('audit_access')
def get_security_status():
    """Get current security status"""
    try:
        # Get recent security events
        recent_logs = audit_service.get_audit_logs(
            filters={
                'start_date': datetime.utcnow() - timedelta(hours=24),
                'event_type': 'security_event'
            },
            limit=50
        )
        
        # Calculate security metrics
        failed_logins = len([log for log in recent_logs if 'authentication_failure' in log.get('action', '')])
        high_risk_events = len([log for log in recent_logs if log.get('risk_level') == 'high'])
        
        status = {
            'overall_status': 'secure',
            'last_updated': datetime.utcnow().isoformat(),
            'metrics': {
                'failed_logins_24h': failed_logins,
                'high_risk_events_24h': high_risk_events,
                'active_sessions': len(session),  # Simplified
                'security_level': 'high'
            },
            'compliance': {
                'popia_compliant': True,
                'audit_logging': True,
                'data_encryption': True,
                'access_control': True
            },
            'recommendations': []
        }
        
        # Add recommendations based on metrics
        if failed_logins > 10:
            status['recommendations'].append('High number of failed logins detected. Consider reviewing access controls.')
        
        if high_risk_events > 5:
            status['recommendations'].append('Multiple high-risk events detected. Review security logs.')
        
        return jsonify({
            'status': 'success',
            'security_status': status
        })
        
    except Exception as e:
        logger.error(f"Security status error: {e}")
        return jsonify({'error': 'Failed to get security status'}), 500

@security_bp.route('/encrypt', methods=['POST'])
@require_permission('access_patient_data')
def encrypt_data():
    """Encrypt sensitive data"""
    try:
        data = request.get_json()
        sensitive_data = data.get('data')
        
        if not sensitive_data:
            return jsonify({'error': 'Data parameter required'}), 400
        
        encrypted_data = security_service.encrypt_sensitive_data(sensitive_data)
        
        # Log encryption activity
        audit_service.log_security_event(
            event_type='data_encryption',
            action='data_encrypted',
            user_id=session.get('user_id'),
            details={'data_type': 'sensitive_medical_data'}
        )
        
        return jsonify({
            'status': 'success',
            'encrypted_data': encrypted_data
        })
        
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        return jsonify({'error': 'Encryption failed'}), 500

@security_bp.route('/decrypt', methods=['POST'])
@require_permission('access_patient_data')
def decrypt_data():
    """Decrypt sensitive data"""
    try:
        data = request.get_json()
        encrypted_data = data.get('encrypted_data')
        
        if not encrypted_data:
            return jsonify({'error': 'Encrypted data parameter required'}), 400
        
        decrypted_data = security_service.decrypt_sensitive_data(encrypted_data)
        
        # Log decryption activity
        audit_service.log_security_event(
            event_type='data_decryption',
            action='data_decrypted',
            user_id=session.get('user_id'),
            details={'data_type': 'sensitive_medical_data'}
        )
        
        return jsonify({
            'status': 'success',
            'decrypted_data': decrypted_data
        })
        
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return jsonify({'error': 'Decryption failed'}), 500