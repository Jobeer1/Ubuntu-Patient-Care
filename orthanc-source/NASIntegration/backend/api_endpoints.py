"""
Main API Endpoints for Orthanc NAS Integration
Combines all modules: NAS, Users, Images, and 2FA
"""

from flask import Blueprint, request, jsonify, session, send_file
from functools import wraps
import json
import os
import io
from datetime import datetime
from typing import Dict, Any

# Import our modules
from nas_connector import nas_connector
from user_db import user_db, User, UserRole
from image_db import image_db, DicomImage
from orthanc_2fa_integration import OrthancTwoFactorIntegration

# Create Blueprint for main API endpoints
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Initialize 2FA integration
two_factor_integration = OrthancTwoFactorIntegration()

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') or session.get('role') != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def require_2fa_if_enabled(f):
    """Decorator to require 2FA verification if enabled for user"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        user_role = session.get('role', 'user')
        
        if two_factor_integration.is_2fa_required_for_user(user_id, user_role):
            if not session.get('2fa_verified'):
                return jsonify({
                    'error': '2FA verification required',
                    'requires_2fa': True
                }), 403
        
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@api_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'pin' not in data:
            return jsonify({'error': 'Username and PIN required'}), 400
        
        username = data['username']
        pin = data['pin']
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        # Authenticate user
        success, user, message = user_db.authenticate_user(username, pin, ip_address, user_agent)
        
        if not success:
            return jsonify({'error': message}), 401
        
        # Set session data
        session['user_id'] = user.user_id
        session['username'] = user.username
        session['role'] = user.role
        session['email'] = user.email
        
        # Create session in database
        session_id = user_db.create_session(user.user_id, ip_address, user_agent)
        session['session_id'] = session_id
        
        # Get 2FA requirements
        requirements = two_factor_integration.get_user_2fa_requirements(user.user_id, user.role)
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            '2fa_requirements': requirements,
            'message': 'Login successful'
        })
        
    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

@api_bp.route('/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    try:
        session_id = session.get('session_id')
        if session_id:
            user_db.invalidate_session(session_id)
        
        session.clear()
        return jsonify({'success': True, 'message': 'Logged out successfully'})
        
    except Exception as e:
        return jsonify({'error': f'Logout failed: {str(e)}'}), 500

@api_bp.route('/profile', methods=['GET'])
@require_auth
def get_profile():
    """Get current user profile"""
    try:
        user_id = session.get('user_id')
        user = user_db.get_user_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get 2FA status
        requirements = two_factor_integration.get_user_2fa_requirements(user_id, user.role)
        
        # Get user preferences
        preferences = user_db.get_user_preferences(user_id)
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            '2fa_status': requirements,
            'preferences': preferences
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get profile: {str(e)}'}), 500

@api_bp.route('/profile', methods=['PUT'])
@require_auth
@require_2fa_if_enabled
def update_profile():
    """Update current user profile"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_id = session.get('user_id')
        user = user_db.get_user_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update allowed fields
        if 'email' in data:
            user.email = data['email']
        if 'phone_number' in data:
            user.phone_number = data['phone_number']
        
        # Update PIN if provided
        if 'new_pin' in data:
            user.pin_hash = user_db._hash_pin(data['new_pin'])
        
        if user_db.update_user(user):
            # Update preferences if provided
            if 'preferences' in data:
                user_db.update_user_preferences(user_id, data['preferences'])
            
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully'
            })
        else:
            return jsonify({'error': 'Failed to update profile'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to update profile: {str(e)}'}), 500

# ============================================================================
# USER MANAGEMENT ENDPOINTS (Admin Only)
# ============================================================================

@api_bp.route('/admin/users', methods=['GET'])
@require_admin
@require_2fa_if_enabled
def admin_list_users():
    """List all users (admin only)"""
    try:
        users = user_db.list_users()
        users_data = []
        
        for user in users:
            user_dict = user.to_dict()
            # Add 2FA status
            requirements = two_factor_integration.get_user_2fa_requirements(user.user_id, user.role)
            user_dict['2fa_status'] = requirements
            users_data.append(user_dict)
        
        return jsonify({
            'success': True,
            'users': users_data
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to list users: {str(e)}'}), 500

@api_bp.route('/admin/users', methods=['POST'])
@require_admin
@require_2fa_if_enabled
def admin_create_user():
    """Create new user (admin only)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['username', 'email', 'pin', 'role']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create user object
        user = User(
            user_id=user_db._generate_user_id(),
            username=data['username'],
            email=data['email'],
            role=data['role'],
            pin_hash=user_db._hash_pin(data['pin']),
            phone_number=data.get('phone_number', ''),
            enabled_auth_methods='["pin"]'
        )
        
        if user_db.create_user(user):
            return jsonify({
                'success': True,
                'message': f'User {user.username} created successfully',
                'user': user.to_dict()
            })
        else:
            return jsonify({'error': 'Failed to create user'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to create user: {str(e)}'}), 500

@api_bp.route('/admin/users/<user_id>', methods=['PUT'])
@require_admin
@require_2fa_if_enabled
def admin_update_user(user_id: str):
    """Update user (admin only)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user = user_db.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update allowed fields
        if 'email' in data:
            user.email = data['email']
        if 'role' in data:
            user.role = data['role']
        if 'phone_number' in data:
            user.phone_number = data['phone_number']
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'new_pin' in data:
            user.pin_hash = user_db._hash_pin(data['new_pin'])
        
        if user_db.update_user(user):
            return jsonify({
                'success': True,
                'message': 'User updated successfully',
                'user': user.to_dict()
            })
        else:
            return jsonify({'error': 'Failed to update user'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to update user: {str(e)}'}), 500

@api_bp.route('/admin/users/<user_id>', methods=['DELETE'])
@require_admin
@require_2fa_if_enabled
def admin_delete_user(user_id: str):
    """Delete user (admin only)"""
    try:
        if user_db.delete_user(user_id):
            return jsonify({
                'success': True,
                'message': 'User deleted successfully'
            })
        else:
            return jsonify({'error': 'Failed to delete user'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to delete user: {str(e)}'}), 500

# ============================================================================
# NAS MANAGEMENT ENDPOINTS
# ============================================================================

@api_bp.route('/nas/config', methods=['GET'])
@require_admin
@require_2fa_if_enabled
def get_nas_config():
    """Get NAS configuration (admin only)"""
    try:
        config = nas_connector.config.copy()
        # Remove sensitive information
        if 'password' in config:
            config['password'] = '***' if config['password'] else ''
        
        return jsonify({
            'success': True,
            'config': config
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get NAS config: {str(e)}'}), 500

@api_bp.route('/nas/config', methods=['POST'])
@require_admin
@require_2fa_if_enabled
def update_nas_config():
    """Update NAS configuration (admin only)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No configuration data provided'}), 400
        
        if nas_connector.update_config(data):
            return jsonify({
                'success': True,
                'message': 'NAS configuration updated successfully'
            })
        else:
            return jsonify({'error': 'Failed to update NAS configuration'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to update NAS config: {str(e)}'}), 500

@api_bp.route('/nas/test', methods=['POST'])
@require_admin
@require_2fa_if_enabled
def test_nas_connection():
    """Test NAS connection (admin only)"""
    try:
        success, message = nas_connector.test_connection()
        
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        return jsonify({'error': f'NAS test failed: {str(e)}'}), 500

@api_bp.route('/nas/status', methods=['GET'])
@require_auth
def get_nas_status():
    """Get NAS status"""
    try:
        status = nas_connector.get_status()
        space_info = nas_connector.get_space_info()
        
        return jsonify({
            'success': True,
            'status': status,
            'space': space_info
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get NAS status: {str(e)}'}), 500

@api_bp.route('/nas/browse', methods=['GET'])
@require_auth
@require_2fa_if_enabled
def browse_nas():
    """Browse NAS directories"""
    try:
        path = request.args.get('path', '/')
        
        if not nas_connector.is_connected:
            if not nas_connector.connect():
                return jsonify({'error': 'Failed to connect to NAS'}), 500
        
        files = nas_connector.list_files(path)
        
        return jsonify({
            'success': True,
            'path': path,
            'files': files
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to browse NAS: {str(e)}'}), 500

# ============================================================================
# 🌐 NAS DISCOVERY ENDPOINTS - EXTREMELY EASY NAS ADDITION
# ============================================================================

@api_bp.route('/nas/discover', methods=['POST'])
@require_admin
@require_2fa_if_enabled
def discover_nas_devices():
    """🔍 Discover NAS devices on the network"""
    try:
        data = request.get_json() or {}
        ip_range = data.get('ip_range')
        max_threads = data.get('max_threads', 50)
        
        # Perform NAS discovery
        discovered_nas = nas_connector.discover_nas_devices(ip_range, max_threads)
        
        # Filter out high-priority NAS devices
        recommended_nas = [
            nas for nas in discovered_nas 
            if nas.get('priority_score', 0) > 50
        ]
        
        return jsonify({
            'success': True,
            'message': f'NAS discovery completed. Found {len(discovered_nas)} potential NAS devices.',
            'discovered_nas': discovered_nas,
            'recommended_nas': recommended_nas,
            'total_found': len(discovered_nas),
            'recommended_count': len(recommended_nas)
        })
        
    except Exception as e:
        return jsonify({'error': f'NAS discovery failed: {str(e)}'}), 500

@api_bp.route('/nas/discovery-suggestions', methods=['GET'])
@require_admin
def get_nas_discovery_suggestions():
    """Get NAS discovery suggestions"""
    try:
        suggestions = nas_connector.get_nas_discovery_suggestions()
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get suggestions: {str(e)}'}), 500

@api_bp.route('/nas/create-from-discovery', methods=['POST'])
@require_admin
@require_2fa_if_enabled
def create_nas_from_discovery():
    """🎯 Create NAS configuration from discovered device"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        discovered_nas = data.get('discovered_nas')
        additional_config = data.get('additional_config', {})
        
        if not discovered_nas:
            return jsonify({'error': 'Discovered NAS data is required'}), 400
        
        # Create NAS configuration from discovery
        success, message = nas_connector.create_nas_from_discovery(
            discovered_nas, additional_config
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'config': nas_connector.config
            })
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'Failed to create NAS configuration: {str(e)}'}), 500

@api_bp.route('/nas/quick-connect', methods=['POST'])
@require_admin
@require_2fa_if_enabled
def quick_connect_nas():
    """⚡ Quick NAS connection setup"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Required fields for quick connect
        required_fields = ['host', 'username', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Set up basic configuration
        config = {
            'enabled': True,
            'type': data.get('type', 'smb'),
            'host': data['host'],
            'port': data.get('port', 445 if data.get('type', 'smb') == 'smb' else 2049),
            'share': data.get('share', 'dicom'),
            'username': data['username'],
            'password': data['password'],
            'domain': data.get('domain', ''),
            'path': data.get('path', '/orthanc')
        }
        
        # Update NAS configuration
        success = nas_connector.update_config(config)
        
        if success:
            # Test connection
            test_success, test_message = nas_connector.test_connection()
            
            return jsonify({
                'success': True,
                'message': 'NAS configured successfully',
                'connection_test': {
                    'success': test_success,
                    'message': test_message
                },
                'config': nas_connector.config
            })
        else:
            return jsonify({'error': 'Failed to save NAS configuration'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Quick connect failed: {str(e)}'}), 500

# ============================================================================
# IMAGE MANAGEMENT ENDPOINTS
# ============================================================================

@api_bp.route('/images', methods=['GET'])
@require_auth
def get_images():
    """Get images for current user"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role')
        
        # Check if 2FA is required
        if two_factor_integration.is_2fa_required_for_user(user_id, user_role):
            if not session.get('2fa_verified'):
                return jsonify({
                    'error': '2FA verification required',
                    'requires_2fa': True
                }), 403
        
        # Get query parameters
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Build filters
        filters = {}
        if request.args.get('patient_name'):
            filters['patient_name'] = request.args.get('patient_name')
        if request.args.get('patient_id'):
            filters['patient_id'] = request.args.get('patient_id')
        if request.args.get('modality'):
            filters['modality'] = request.args.get('modality')
        if request.args.get('study_date_from'):
            filters['study_date_from'] = request.args.get('study_date_from')
        if request.args.get('study_date_to'):
            filters['study_date_to'] = request.args.get('study_date_to')
        
        # For non-admin users, filter by user_id
        search_user_id = None if user_role == 'admin' else user_id
        
        images = image_db.search_images(search_user_id, filters, limit, offset)
        images_data = [img.to_dict() for img in images]
        
        return jsonify({
            'success': True,
            'images': images_data,
            'count': len(images_data),
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get images: {str(e)}'}), 500

@api_bp.route('/images/<image_id>', methods=['GET'])
@require_auth
def get_image_details(image_id: str):
    """Get detailed image information"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role')
        
        image = image_db.get_image_by_id(image_id)
        if not image:
            return jsonify({'error': 'Image not found'}), 404
        
        # Check access permissions
        if user_role != 'admin' and image.owner_user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Log access
        image_db.log_image_access(
            image_id, user_id, None, 
            request.remote_addr, request.headers.get('User-Agent', ''), 'view'
        )
        
        # Get tags
        tags = image_db.get_image_tags(image_id)
        
        image_dict = image.to_dict()
        image_dict['tags'] = tags
        
        return jsonify({
            'success': True,
            'image': image_dict
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get image details: {str(e)}'}), 500

@api_bp.route('/images/<image_id>/share', methods=['POST'])
@require_auth
@require_2fa_if_enabled
def share_image(image_id: str):
    """Create shared link for image"""
    try:
        data = request.get_json() or {}
        user_id = session.get('user_id')
        user_role = session.get('role')
        
        image = image_db.get_image_by_id(image_id)
        if not image:
            return jsonify({'error': 'Image not found'}), 404
        
        # Check access permissions
        if user_role != 'admin' and image.owner_user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Create shared link
        recipient_email = data.get('recipient_email', '')
        expires_hours = int(data.get('expires_hours', 24))
        max_views = int(data.get('max_views', -1))
        
        shared_link = image_db.create_shared_link(
            image_id, user_id, recipient_email, expires_hours, max_views
        )
        
        if shared_link:
            # Generate full URL
            base_url = request.url_root.rstrip('/')
            share_url = f"{base_url}/share/{shared_link.access_token}"
            
            return jsonify({
                'success': True,
                'shared_link': shared_link.to_dict(),
                'share_url': share_url,
                'message': 'Shared link created successfully'
            })
        else:
            return jsonify({'error': 'Failed to create shared link'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to share image: {str(e)}'}), 500

@api_bp.route('/images/<image_id>/tags', methods=['POST'])
@require_auth
@require_2fa_if_enabled
def add_image_tag(image_id: str):
    """Add tag to image"""
    try:
        data = request.get_json()
        if not data or 'tag_name' not in data:
            return jsonify({'error': 'Tag name required'}), 400
        
        user_id = session.get('user_id')
        user_role = session.get('role')
        
        image = image_db.get_image_by_id(image_id)
        if not image:
            return jsonify({'error': 'Image not found'}), 404
        
        # Check access permissions
        if user_role != 'admin' and image.owner_user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        tag_name = data['tag_name']
        tag_value = data.get('tag_value', '')
        
        if image_db.add_image_tag(image_id, tag_name, tag_value):
            return jsonify({
                'success': True,
                'message': 'Tag added successfully'
            })
        else:
            return jsonify({'error': 'Failed to add tag'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to add tag: {str(e)}'}), 500

@api_bp.route('/shared/<access_token>', methods=['GET'])
def view_shared_image(access_token: str):
    """View shared image via access token"""
    try:
        result = image_db.get_shared_link_by_token(access_token)
        if not result:
            return jsonify({'error': 'Invalid or expired shared link'}), 404
        
        shared_link, image = result
        
        # Increment view count
        image_db.increment_link_views(shared_link.link_id)
        
        # Log access
        image_db.log_image_access(
            image.image_id, None, access_token,
            request.remote_addr, request.headers.get('User-Agent', ''), 'view'
        )
        
        return jsonify({
            'success': True,
            'image': image.to_dict(),
            'shared_link': shared_link.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to view shared image: {str(e)}'}), 500

# ============================================================================
# STATISTICS AND DASHBOARD ENDPOINTS
# ============================================================================

@api_bp.route('/dashboard/stats', methods=['GET'])
@require_auth
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        user_id = session.get('user_id')
        user_role = session.get('role')
        
        # Get user-specific or system-wide stats based on role
        stats_user_id = None if user_role == 'admin' else user_id
        
        # Get image statistics
        image_stats = image_db.get_image_stats(stats_user_id)
        
        # Get user statistics (admin only)
        user_stats = {}
        if user_role == 'admin':
            user_stats = user_db.get_user_stats()
        
        # Get NAS status
        nas_status = nas_connector.get_status()
        nas_space = nas_connector.get_space_info()
        
        # Get 2FA statistics (admin only)
        tfa_stats = {}
        if user_role == 'admin':
            tfa_stats = two_factor_integration.two_factor_auth.get_2fa_stats()
        
        return jsonify({
            'success': True,
            'stats': {
                'images': image_stats,
                'users': user_stats,
                'nas': {
                    'status': nas_status,
                    'space': nas_space
                },
                '2fa': tfa_stats
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get dashboard stats: {str(e)}'}), 500

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        return jsonify({
            'success': True,
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'nas': nas_connector.is_connected,
                'database': True,  # If we can respond, DB is working
                '2fa': two_factor_integration.two_factor_auth.get_config()['enabled']
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Error handlers
@api_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@api_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized'}), 401

@api_bp.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Forbidden'}), 403

@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@api_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500