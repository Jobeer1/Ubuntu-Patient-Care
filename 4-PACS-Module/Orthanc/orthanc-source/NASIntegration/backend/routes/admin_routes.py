"""
Admin routes blueprint for user management and reporting
"""

from flask import Blueprint, request, jsonify
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# Import auth decorators
try:
    from ..auth_utils import require_admin, require_auth
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from auth_utils import require_admin, require_auth

@admin_bp.route('/dashboard/stats', methods=['GET'])
@require_admin
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        stats = {
            'total_users': 145,
            'active_users': 128,
            'total_doctors': 23,
            'active_doctors': 20,
            'total_devices': 12,
            'online_devices': 9,
            'total_studies': 1247,
            'recent_studies': 45,
            'storage_used_gb': 2847,
            'storage_total_gb': 5000,
            'system_uptime': '15 days, 8 hours',
            'last_backup': '2025-08-14T22:00:00Z'
        }
        
        return jsonify({
            'success': True,
            'stats': stats,
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting dashboard stats: {e}")
        return jsonify({'error': 'Failed to get dashboard stats'}), 500

@admin_bp.route('/dashboard/activity', methods=['GET'])
@require_admin
def get_recent_activity():
    """Get recent system activity"""
    try:
        activity = [
            {
                'id': 1,
                'type': 'user_login',
                'user': 'dr.smith',
                'description': 'Dr. Smith logged in',
                'timestamp': '2025-08-15T08:45:00Z'
            },
            {
                'id': 2,
                'type': 'study_upload',
                'user': 'tech.jones',
                'description': 'New CT study uploaded',
                'timestamp': '2025-08-15T08:30:00Z'
            },
            {
                'id': 3,
                'type': 'device_connected',
                'user': 'system',
                'description': 'MRI Scanner connected',
                'timestamp': '2025-08-15T08:15:00Z'
            }
        ]
        
        return jsonify({
            'success': True,
            'activity': activity,
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting recent activity: {e}")
        return jsonify({'error': 'Failed to get recent activity'}), 500

@admin_bp.route('/users', methods=['GET'])
@require_admin
def get_all_users():
    """Get all users for admin management"""
    try:
        # Mock data for now - replace with actual database queries
        users = [
            {
                'id': '1',
                'username': 'admin',
                'email': 'admin@hospital.co.za',
                'full_name': 'System Administrator',
                'role': 'admin',
                'is_active': True,
                'created_at': '2025-08-01T09:00:00Z',
                'last_login': '2025-08-14T14:00:00Z',
                'department': 'IT'
            },
            {
                'id': '2',
                'username': 'dr.smith',
                'email': 'smith@hospital.co.za',
                'full_name': 'Dr. John Smith',
                'role': 'doctor',
                'is_active': True,
                'created_at': '2025-08-05T10:00:00Z',
                'last_login': '2025-08-14T13:30:00Z',
                'department': 'Radiology',
                'hpcsa_number': 'MP123456'
            },
            {
                'id': '3',
                'username': 'tech.jones',
                'email': 'jones@hospital.co.za',
                'full_name': 'Sarah Jones',
                'role': 'technician',
                'is_active': True,
                'created_at': '2025-08-07T11:00:00Z',
                'last_login': '2025-08-14T12:00:00Z',
                'department': 'Radiology'
            }
        ]
        
        return jsonify({
            'users': users,
            'total': len(users)
        })
        
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({'error': 'Failed to get users'}), 500

@admin_bp.route('/users/<user_id>/status', methods=['PUT'])
@require_admin
def update_user_status(user_id):
    """Update user status (active/inactive)"""
    try:
        data = request.get_json()
        is_active = data.get('is_active', True)
        
        # Mock update - replace with actual database update
        logger.info(f"Updating user {user_id} status to {'active' if is_active else 'inactive'}")
        
        return jsonify({
            'success': True,
            'message': f'User status updated to {"active" if is_active else "inactive"}'
        })
        
    except Exception as e:
        logger.error(f"Error updating user status: {e}")
        return jsonify({'error': 'Failed to update user status'}), 500

@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@require_admin
def delete_user(user_id):
    """Delete a user"""
    try:
        # Mock deletion - replace with actual database deletion
        logger.info(f"Deleting user {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({'error': 'Failed to delete user'}), 500

@admin_bp.route('/reports/<report_type>', methods=['GET'])
@require_admin
def get_report_data(report_type):
    """Get report data by type"""
    try:
        if report_type == 'user-activity':
            data = {
                'report_type': 'user-activity',
                'title': 'User Activity Report',
                'generated_at': datetime.utcnow().isoformat(),
                'data': [
                    {'user': 'dr.smith', 'logins': 25, 'studies_viewed': 150, 'last_login': '2025-08-14T13:30:00Z'},
                    {'user': 'tech.jones', 'logins': 18, 'studies_viewed': 89, 'last_login': '2025-08-14T12:00:00Z'},
                    {'user': 'admin', 'logins': 45, 'studies_viewed': 200, 'last_login': '2025-08-14T14:00:00Z'}
                ]
            }
        elif report_type == 'system-usage':
            data = {
                'report_type': 'system-usage',
                'title': 'System Usage Report',
                'generated_at': datetime.utcnow().isoformat(),
                'data': {
                    'cpu_usage': [65, 72, 58, 69, 71],
                    'memory_usage': [78, 82, 75, 80, 77],
                    'storage_usage': [85, 86, 87, 88, 89],
                    'network_traffic': [120, 135, 98, 142, 156]
                }
            }
        elif report_type == 'device-status':
            data = {
                'report_type': 'device-status',
                'title': 'Device Status Report',
                'generated_at': datetime.utcnow().isoformat(),
                'data': [
                    {'device': 'MRI Scanner 1', 'status': 'online', 'uptime': '99.8%', 'last_maintenance': '2025-08-01'},
                    {'device': 'CT Scanner 1', 'status': 'online', 'uptime': '98.5%', 'last_maintenance': '2025-07-28'},
                    {'device': 'X-Ray Unit 1', 'status': 'maintenance', 'uptime': '95.2%', 'last_maintenance': '2025-08-10'}
                ]
            }
        else:
            return jsonify({'error': 'Invalid report type'}), 400
        
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return jsonify({'error': 'Failed to generate report'}), 500

@admin_bp.route('/reports/export', methods=['GET'])
@require_admin
def export_report():
    """Export report in specified format"""
    try:
        report_type = request.args.get('type', 'user-activity')
        format_type = request.args.get('format', 'pdf')
        
        # Mock export - replace with actual export functionality
        if format_type == 'pdf':
            # Return mock PDF content
            return jsonify({
                'success': True,
                'download_url': f'/downloads/report_{report_type}.pdf',
                'message': 'PDF export completed'
            })
        elif format_type == 'csv':
            # Return mock CSV content
            return jsonify({
                'success': True,
                'download_url': f'/downloads/report_{report_type}.csv',
                'message': 'CSV export completed'
            })
        else:
            return jsonify({'error': 'Invalid export format'}), 400
            
    except Exception as e:
        logger.error(f"Error exporting report: {e}")
        return jsonify({'error': 'Failed to export report'}), 500

@admin_bp.route('/users', methods=['POST'])
@require_admin
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'full_name', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Mock user creation - replace with actual database insertion
        new_user = {
            'id': str(len([]) + 1),  # Mock ID generation
            'username': data['username'],
            'email': data['email'],
            'full_name': data['full_name'],
            'role': data.get('role', 'user'),
            'department': data.get('department', ''),
            'hpcsa_number': data.get('hpcsa_number', ''),
            'is_active': True,
            'created_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Creating new user: {data['username']}")
        
        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'user': new_user
        })
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({'error': 'Failed to create user'}), 500

@admin_bp.route('/users/<user_id>', methods=['PUT'])
@require_admin
def update_user(user_id):
    """Update user information"""
    try:
        data = request.get_json()
        
        # Mock user update - replace with actual database update
        logger.info(f"Updating user {user_id} with data: {data}")
        
        return jsonify({
            'success': True,
            'message': 'User updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return jsonify({'error': 'Failed to update user'}), 500
