"""
Flask API Routes for South African Healthcare Admin Dashboard
Provides REST endpoints for user management, group management, and secure sharing
"""

from flask import Blueprint, request, jsonify, current_app, url_for, session
from flask_cors import cross_origin
from datetime import datetime, timedelta
import secrets
import json
import logging
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, NotFound

from sa_user_group_manager import sa_user_manager, SAHealthcareUser, SAHealthcareGroup, UserRole, Province, FacilityType
from sa_secure_link_manager import sa_link_manager, SASecureShare, ShareType, RecipientType, AccessLevel

logger = logging.getLogger(__name__)

# Create blueprint
admin_api = Blueprint('sa_admin_api', __name__, url_prefix='/api/admin')

def require_admin():
    """Check admin privileges - throws exception if not authorized"""
    # Debug session state
    logger.info(f"Session check - Session keys: {list(session.keys()) if session else 'No session'}")
    logger.info(f"Session user_id: {session.get('user_id')}")
    logger.info(f"Session username: {session.get('username')}")
    logger.info(f"Session role: {session.get('role')}")
    
    # Check if user is logged in
    if not session.get('user_id'):
        logger.warning("Admin access denied: No user_id in session")
        raise Unauthorized("Authentication required")
    
    # Check if user has admin role
    if session.get('role') != 'admin':
        logger.warning(f"Admin access denied: User role is '{session.get('role')}', not 'admin'")
        raise Forbidden("Admin privileges required")
    
    logger.info("Admin access granted")
    return True
    
    # Original authentication logic (commented for debugging)
    # # Check session-based authentication first
    # if 'user_id' in session and 'username' in session:
    #     # Get user from session
    #     username = session.get('username')
    #     # Check if user exists in our demo users and has admin role
    #     from auth_api import DEMO_USERS
    #     user = DEMO_USERS.get(username)
    #     if user and user['role'] == 'admin':
    #         return True
    
    # # Fallback to Authorization header check
    # auth_header = request.headers.get('Authorization')
    # if auth_header and 'admin' in auth_header:
    #     return True
    
    # raise Unauthorized("Admin privileges required")

def get_current_user():
    """Get current authenticated user"""
    # Try session first
    if 'user_id' in session and 'username' in session:
        username = session.get('username')
        from auth_api import DEMO_USERS
        user = DEMO_USERS.get(username)
        if user:
            return {
                'id': user['id'],
                'name': user['name'],
                'role': user['role'],
                'facility_id': user.get('facility', 'default_facility'),
                'username': username
            }
    
    # Fallback to mock admin user
    return {
        'id': 'admin_001',
        'name': 'System Administrator',
        'role': 'admin',
        'facility_id': 'admin_facility',
        'username': 'admin'
    }

@admin_api.route('/debug/session', methods=['GET'])
@cross_origin(supports_credentials=True)
def debug_session():
    """Debug endpoint to check session state"""
    try:
        session_info = {
            'session_exists': 'user_id' in session,
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'role': session.get('role'),  # Include role in debug output
            'session_token': session.get('session_token'),
            'login_time': session.get('login_time'),
            'session_keys': list(session.keys()) if session else []
        }
        
        return jsonify({
            'message': 'Session debug info',
            'session': session_info,
            'is_admin': session.get('role') == 'admin'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api.route('/test', methods=['POST', 'GET'])
@cross_origin(supports_credentials=True)
def test_endpoint():
    """Test endpoint to debug content type issues"""
    try:
        return jsonify({
            'method': request.method,
            'content_type': request.content_type,
            'is_json': request.is_json,
            'form_data': dict(request.form) if request.form else None,
            'json_data': request.get_json(silent=True),
            'headers': dict(request.headers),
            'message': 'Test endpoint working'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api.route('/users', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_users():
    """Get all users in the system"""
    try:
        # Enable authentication
        require_admin()
        
        # DEBUG: Log request details
        logger.info("=== GET /users endpoint called ===")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Session data: {dict(session)}")
        logger.info("Authentication bypassed for testing")
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '')
        role_filter = request.args.get('role', '')
        province_filter = request.args.get('province', '')
        facility_filter = request.args.get('facility_type', '')
        
        # For now, return mock users until the user manager is fully implemented
        mock_users = [
            {
                'user_id': 'admin_001',  # Use user_id to match frontend
                'id': 'admin_001',
                'username': 'admin',
                'email': 'admin@hospital.co.za',
                'name': 'System Administrator',
                'role': 'admin',
                'facility_name': 'System Administration',
                'facility_type': 'public_hospital',
                'province': 'gauteng',
                'hpcsa_number': None,
                'phone_number': '+27-11-123-4567',
                'is_active': True,
                'created_at': datetime.now().isoformat(),
                'last_login': datetime.now().isoformat(),  # Show recent login
                'two_factor_enabled': False
            },
            {
                'user_id': 'doc_001',  # Use user_id to match frontend
                'id': 'doc_001',
                'username': 'doctor',
                'email': 'doctor@hospital.co.za',
                'name': 'Dr. Sarah Mthembu',
                'role': 'radiologist',
                'facility_name': 'Chris Hani Baragwanath Hospital',
                'facility_type': 'public_hospital',
                'province': 'gauteng',
                'hpcsa_number': 'PR0123456',
                'phone_number': '+27-11-987-6543',
                'is_active': True,
                'created_at': datetime.now().isoformat(),
                'last_login': datetime.now().isoformat(),
                'two_factor_enabled': False
            }
        ]
        
        return jsonify({
            'success': True,
            'users': mock_users,
            'total': len(mock_users),
            'page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return jsonify({'error': str(e)}), 500

@admin_api.route('/users', methods=['POST'])
@cross_origin(supports_credentials=True)
def create_user():
    """Create new user"""
    try:
        require_admin()
        current_user = get_current_user()
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['username', 'email', 'role']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Check if username already exists (mock check)
        if data['username'] in ['admin', 'doctor', 'nurse']:
            return jsonify({'success': False, 'error': 'Username already exists'}), 400
        
        # Create new user (mock implementation)
        new_user_id = f"user_{secrets.token_urlsafe(8)}"
        new_user = {
            'user_id': new_user_id,
            'id': new_user_id,
            'username': data['username'],
            'email': data['email'],
            'name': data.get('name', data['username'].title()),
            'role': data['role'],
            'facility_name': data.get('facility_name', 'Default Facility'),
            'facility_type': data.get('facility_type', 'public_hospital'),
            'province': data.get('province', 'gauteng'),
            'hpcsa_number': data.get('hpcsa_number'),
            'phone_number': data.get('phone_number'),
            'is_active': True,
            'created_at': datetime.now().isoformat(),
            'last_login': None,
            'two_factor_enabled': False
        }
        
        logger.info(f"Created new user: {new_user['username']}")
        
        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'user_id': new_user_id,
            'user': new_user
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_api.route('/users/<user_id>', methods=['DELETE'])
@cross_origin(supports_credentials=True)
def deactivate_user(user_id):
    """Deactivate user (soft delete)"""
    try:
        require_admin()
        current_user = get_current_user()
        
        # Mock implementation - in real system, this would deactivate the user
        logger.info(f"Deactivating user: {user_id}")
        
        # Don't allow deleting the current admin user
        if user_id == 'admin_001':
            return jsonify({'success': False, 'error': 'Cannot delete the system administrator'}), 400
        
        return jsonify({'success': True, 'message': 'User deactivated successfully'})
        
    except Exception as e:
        logger.error(f"Error deactivating user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_api.route('/users/<user_id>', methods=['PUT'])
@cross_origin(supports_credentials=True)
def update_user(user_id):
    """Update existing user"""
    try:
        require_admin()
        current_user = get_current_user()
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Mock implementation - in real system, this would update the user
        logger.info(f"Updating user: {user_id} with data: {data}")
        
        # Simulate update success
        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_api.route('/groups', methods=['GET'])
def get_groups():
    """Get all groups"""
    try:
        require_admin()
        
        groups = sa_user_manager.get_all_groups()
        
        groups_data = []
        for group in groups:
            group_data = {
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'province': group.province.value if group.province else None,
                'facility_type': group.facility_type.value if group.facility_type else None,
                'permissions': group.permissions,
                'is_active': group.is_active,
                'created_at': group.created_at.isoformat(),
                'member_count': len(sa_user_manager.get_group_members(group.id))
            }
            groups_data.append(group_data)
        
        return jsonify({'groups': groups_data})
        
    except Exception as e:
        logger.error(f"Error fetching groups: {e}")
        return jsonify({'error': str(e)}), 500

@admin_api.route('/shares', methods=['GET'])
def get_shares():
    """Get all secure shares"""
    try:
        require_admin()
        
        # Return mock shares for now
        mock_shares = [
            {
                'id': 'share_001',
                'share_token': 'sample_token_123',
                'content_type': 'study',
                'content_ids': ['study_001'],
                'sharer_name': 'Dr. Sarah Mthembu',
                'sharer_facility': 'Chris Hani Baragwanath Hospital',
                'recipient_type': 'doctor',
                'recipient_name': 'Dr. John Smith',
                'recipient_email': 'john.smith@specialist.co.za',
                'access_level': 'view_download',
                'expires_at': (datetime.now() + timedelta(days=7)).isoformat(),
                'created_at': datetime.now().isoformat(),
                'purpose': 'Second Opinion',
                'patient_name': 'John Doe',
                'patient_id': 'P001',
                'study_description': 'Chest X-Ray',
                'requires_otp': False,
                'max_access_count': 10,
                'access_count': 2,
                'is_active': True,
                'province': 'Gauteng',
                'medical_aid_scheme': None,
                'reference_number': None
            }
        ]
        
        return jsonify({'shares': mock_shares})
        
    except Exception as e:
        logger.error(f"Error fetching shares: {e}")
        return jsonify({'error': str(e)}), 500

@admin_api.route('/shares', methods=['POST'])
def create_share():
    """Create new secure share"""
    try:
        require_admin()
        current_user = get_current_user()
        
        data = request.get_json()
        if not data:
            raise BadRequest("No data provided")
        
        # Validate required fields
        required_fields = ['content_type', 'content_ids', 'recipient_name', 
                          'access_level', 'patient_name', 'patient_id', 'purpose']
        for field in required_fields:
            if field not in data:
                raise BadRequest(f"Missing required field: {field}")
        
        # Calculate expiration
        expires_in_days = data.get('expires_in_days', 7)
        expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        # Create share object
        share = SASecureShare(
            id=secrets.token_urlsafe(16),
            share_token="",  # Will be generated
            content_type=ShareType(data['content_type']),
            content_ids=data['content_ids'],
            sharer_id=current_user['id'],
            sharer_name=current_user['name'],
            sharer_facility=current_user.get('facility_id', 'Admin Facility'),
            recipient_type=RecipientType(data.get('recipient_type', 'doctor')),
            recipient_name=data['recipient_name'],
            recipient_email=data.get('recipient_email'),
            recipient_phone=data.get('recipient_phone'),
            access_level=AccessLevel(data['access_level']),
            expires_at=expires_at,
            created_at=datetime.now(),
            purpose=data['purpose'],
            patient_name=data['patient_name'],
            patient_id=data['patient_id'],
            study_description=data.get('study_description', ''),
            requires_otp=data.get('requires_otp', False),
            max_access_count=data.get('max_access_count', 10),
            province=data.get('province', ''),
            medical_aid_scheme=data.get('medical_aid_scheme'),
            reference_number=data.get('reference_number')
        )
        
        # Create share
        share_token = sa_link_manager.create_share(share)
        
        if share_token:
            # Generate share URL
            base_url = request.host_url.rstrip('/')
            share_url = sa_link_manager.generate_share_url(base_url, share_token)
            
            # Generate QR code
            qr_code = sa_link_manager.generate_qr_code(share_url)
            
            return jsonify({
                'message': 'Secure share created successfully',
                'share_id': share.id,
                'share_url': share_url,
                'qr_code': qr_code,
                'expires_at': expires_at.isoformat()
            }), 201
        else:
            return jsonify({'error': 'Failed to create share'}), 400
            
    except Exception as e:
        logger.error(f"Error creating share: {e}")
        return jsonify({'error': str(e)}), 500

@admin_api.route('/shares/<share_id>/revoke', methods=['POST'])
def revoke_share(share_id):
    """Revoke a secure share"""
    try:
        require_admin()
        current_user = get_current_user()
        
        if sa_link_manager.revoke_share(share_id, current_user['id']):
            return jsonify({'message': 'Share revoked successfully'})
        else:
            return jsonify({'error': 'Failed to revoke share'}), 400
            
    except Exception as e:
        logger.error(f"Error revoking share: {e}")
        return jsonify({'error': str(e)}), 500

@admin_api.route('/shares/<share_id>/qr', methods=['GET'])
def get_share_qr(share_id):
    """Get QR code for share"""
    try:
        require_admin()
        
        share = sa_link_manager.get_share_by_token(share_id)  # TODO: Get by ID instead
        if not share:
            raise NotFound("Share not found")
        
        base_url = request.host_url.rstrip('/')
        share_url = sa_link_manager.generate_share_url(base_url, share.share_token)
        qr_code = sa_link_manager.generate_qr_code(share_url)
        
        return jsonify({
            'qr_code': qr_code,
            'share_url': share_url
        })
        
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        return jsonify({'error': str(e)}), 500

@admin_api.route('/audit-log', methods=['GET'])
def get_audit_log():
    """Get audit log entries"""
    try:
        require_admin()
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        user_filter = request.args.get('user_id', '')
        action_filter = request.args.get('action', '')
        
        # TODO: Implement audit log retrieval
        # For now, return empty list
        return jsonify({
            'audit_entries': [],
            'total': 0,
            'page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        logger.error(f"Error fetching audit log: {e}")
        return jsonify({'error': str(e)}), 500

@admin_api.route('/stats', methods=['GET'])
def get_admin_stats():
    """Get dashboard statistics"""
    try:
        require_admin()
        
        # Get basic stats
        total_users = len(sa_user_manager.get_all_users())
        active_users = len([u for u in sa_user_manager.get_all_users() if u.is_active])
        total_groups = len(sa_user_manager.get_all_groups())
        
        # Share stats
        all_shares = sa_link_manager.get_user_shares('admin')  # TODO: Implement admin view
        active_shares = len([s for s in all_shares if s.is_active and s.expires_at > datetime.now()])
        expired_shares = len([s for s in all_shares if s.expires_at <= datetime.now()])
        
        # Province distribution
        users = sa_user_manager.get_all_users()
        province_stats = {}
        for user in users:
            province = user.province.value
            province_stats[province] = province_stats.get(province, 0) + 1
        
        return jsonify({
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': total_users - active_users,
            'total_groups': total_groups,
            'active_shares': active_shares,
            'expired_shares': expired_shares,
            'total_shares': len(all_shares),
            'province_distribution': province_stats
        })
        
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({'error': str(e)}), 500

# Error handlers
@admin_api.errorhandler(BadRequest)
def handle_bad_request(e):
    return jsonify({'error': str(e)}), 400

@admin_api.errorhandler(Unauthorized)
def handle_unauthorized(e):
    return jsonify({'error': 'Authentication required'}), 401

@admin_api.errorhandler(Forbidden)
def handle_forbidden(e):
    return jsonify({'error': 'Insufficient privileges'}), 403

@admin_api.errorhandler(NotFound)
def handle_not_found(e):
    return jsonify({'error': 'Resource not found'}), 404
