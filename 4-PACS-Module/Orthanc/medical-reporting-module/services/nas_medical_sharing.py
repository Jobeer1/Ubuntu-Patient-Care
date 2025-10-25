"""
NAS Medical Sharing Service
Secure medical image sharing with HIPAA compliance and Orthanc integration
"""

import secrets
import string
import logging
from datetime import datetime, timedelta
from .nas_database_operations import create_medical_share, get_medical_shares, update_share_access

logger = logging.getLogger(__name__)

def generate_secure_share_link(share_data):
    """Generate a secure sharing link for patient images"""
    try:
        # Extract required data
        patient_info = share_data.get('patient_info', '')
        expiry_hours = int(share_data.get('expiry_hours', 24))
        orthanc_study_uid = share_data.get('orthanc_study_uid', '')
        
        if not patient_info:
            return {
                'success': False,
                'error': 'Patient information is required'
            }
        
        # Generate secure identifiers
        share_id = generate_share_id()
        access_code = generate_access_code()
        
        # Calculate expiry time
        created_at = datetime.now()
        expires_at = created_at + timedelta(hours=expiry_hours)
        
        # Create share record
        share_record = {
            'share_id': share_id,
            'patient_info': patient_info,
            'access_code': access_code,
            'created_at': created_at.isoformat(),
            'expires_at': expires_at.isoformat(),
            'orthanc_study_uid': orthanc_study_uid
        }
        
        success = create_medical_share(share_record)
        
        if success:
            # Generate secure URLs
            base_url = "https://localhost:5000"  # This should come from config
            share_url = f"{base_url}/api/nas/medical-share/{share_id}"
            
            logger.info(f"🔐 Generated secure share link: {share_id}")
            
            return {
                'success': True,
                'share_id': share_id,
                'access_code': access_code,
                'share_url': share_url,
                'expires_at': expires_at.isoformat(),
                'orthanc_study_uid': orthanc_study_uid,
                'message': 'Secure sharing link generated successfully'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to create sharing record'
            }
            
    except Exception as e:
        logger.error(f"Error generating share link: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def generate_share_id():
    """Generate a secure, URL-safe share ID"""
    # Use URL-safe characters: letters, numbers, hyphens
    chars = string.ascii_letters + string.digits + '-'
    return ''.join(secrets.choice(chars) for _ in range(16))

def generate_access_code():
    """Generate a 6-digit access code"""
    return ''.join(secrets.choice(string.digits) for _ in range(6))

def verify_share_access(share_id, access_code):
    """Verify access to a medical share"""
    try:
        # Get all shares and find the matching one
        shares = get_medical_shares()
        
        target_share = None
        for share in shares:
            if share['share_id'] == share_id:
                target_share = share
                break
        
        if not target_share:
            return {
                'success': False,
                'message': 'Invalid sharing link'
            }
        
        # Check if expired
        expires_at = datetime.fromisoformat(target_share['expires_at'])
        if datetime.now() > expires_at:
            return {
                'success': False,
                'message': 'This sharing link has expired'
            }
        
        # Verify access code
        if target_share['access_code'] != access_code.upper():
            return {
                'success': False,
                'message': 'Invalid access code'
            }
        
        # Update access tracking
        update_share_access(share_id)
        
        logger.info(f"✅ Share access verified: {share_id}")
        
        return {
            'success': True,
            'message': 'Access granted',
            'share_data': {
                'patient_info': target_share['patient_info'],
                'created_at': target_share['created_at'],
                'orthanc_study_uid': target_share['orthanc_study_uid']
            }
        }
        
    except Exception as e:
        logger.error(f"Error verifying share access: {e}")
        return {
            'success': False,
            'message': f'Verification error: {str(e)}'
        }

def get_share_statistics():
    """Get sharing statistics for admin dashboard"""
    try:
        shares = get_medical_shares()
        
        total_shares = len(shares)
        active_shares = 0
        expired_shares = 0
        accessed_shares = 0
        
        now = datetime.now()
        
        for share in shares:
            expires_at = datetime.fromisoformat(share['expires_at'])
            
            if now <= expires_at:
                active_shares += 1
            else:
                expired_shares += 1
            
            if share['access_count'] and share['access_count'] > 0:
                accessed_shares += 1
        
        return {
            'total_shares': total_shares,
            'active_shares': active_shares,
            'expired_shares': expired_shares,
            'accessed_shares': accessed_shares,
            'access_rate': round(accessed_shares / total_shares * 100, 1) if total_shares > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting share statistics: {e}")
        return {
            'total_shares': 0,
            'active_shares': 0,
            'expired_shares': 0,
            'accessed_shares': 0,
            'access_rate': 0
        }

def cleanup_expired_shares():
    """Clean up expired sharing records (should be run periodically)"""
    try:
        shares = get_medical_shares()
        expired_count = 0
        now = datetime.now()
        
        # Note: In a full implementation, we would delete expired shares from the database
        # For now, we just count them
        for share in shares:
            expires_at = datetime.fromisoformat(share['expires_at'])
            if now > expires_at:
                expired_count += 1
        
        logger.info(f"🧹 Found {expired_count} expired shares for cleanup")
        return expired_count
        
    except Exception as e:
        logger.error(f"Error cleaning up expired shares: {e}")
        return 0

def validate_share_permissions(share_id, user_info=None):
    """Validate user permissions for a medical share"""
    try:
        # This is a placeholder for more sophisticated permission checking
        # In a full implementation, this would check user roles, departments, etc.
        
        # For now, we just verify the share exists
        shares = get_medical_shares()
        
        for share in shares:
            if share['share_id'] == share_id:
                # Check if not expired
                expires_at = datetime.fromisoformat(share['expires_at'])
                if datetime.now() <= expires_at:
                    return {
                        'valid': True,
                        'permissions': ['view', 'download'],
                        'share_info': share
                    }
                else:
                    return {
                        'valid': False,
                        'reason': 'expired',
                        'permissions': []
                    }
        
        return {
            'valid': False,
            'reason': 'not_found',
            'permissions': []
        }
        
    except Exception as e:
        logger.error(f"Error validating share permissions: {e}")
        return {
            'valid': False,
            'reason': 'error',
            'permissions': []
        }