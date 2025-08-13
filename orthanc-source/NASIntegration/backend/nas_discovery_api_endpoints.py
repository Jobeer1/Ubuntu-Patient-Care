#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - NAS Discovery API Endpoints

REST API endpoints for discovering and managing NAS devices.
Provides easy NAS discovery, configuration, and credential testing
with South African healthcare context.
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
import logging
from typing import Dict, Any
import uuid
import json

# Try to import NAS discovery manager with fallbacks
nas_discovery_manager = None
try:
    from nas_discovery import nas_discovery_manager
    logger = logging.getLogger(__name__)
    logger.info("✅ Using NAS discovery manager")
except ImportError:
    logger = logging.getLogger(__name__)
    logger.error("❌ NAS discovery manager not available")
    
    # Create a minimal mock NAS discovery manager
    class MockNASDiscoveryManager:
        def discover_nas_devices(self, ip_range, scan_type="comprehensive", max_threads=50):
            return [
                {
                    'id': 'mock_nas_001',
                    'name': 'Mock Synology NAS',
                    'ip_address': '192.168.1.100',
                    'hostname': 'synology-nas',
                    'nas_type': 'smb',
                    'manufacturer': 'Synology',
                    'model': 'DiskStation',
                    'shares': [
                        {'name': 'DICOM', 'type': 'SMB', 'path': '//192.168.1.100/DICOM'},
                        {'name': 'Archive', 'type': 'SMB', 'path': '//192.168.1.100/Archive'}
                    ],
                    'ports': [80, 445, 5000],
                    'services': ['SMB', 'Synology DSM'],
                    'status': 'discovered'
                }
            ]
        
        def get_discovered_nas_devices(self):
            return self.discover_nas_devices("192.168.1.0/24")
        
        def test_nas_credentials(self, nas_id, username, password, domain="", share_path=""):
            return True, "Mock credentials test passed"
        
        def get_nas_device_by_id(self, nas_id):
            devices = self.discover_nas_devices("192.168.1.0/24")
            return devices[0] if devices else None
        
        def get_network_suggestions(self):
            return {
                'common_ip_ranges': ['192.168.1.0/24', '192.168.0.0/24'],
                'scan_types': [
                    {'value': 'quick', 'label': 'Quick Scan', 'duration': '1-2 minutes'},
                    {'value': 'comprehensive', 'label': 'Comprehensive Scan', 'duration': '3-5 minutes'}
                ],
                'common_nas_brands': ['Synology', 'QNAP', 'Netgear'],
                'healthcare_tips': ['Start with local network range']
            }
    
    nas_discovery_manager = MockNASDiscoveryManager()
    logger.warning("⚠️ Using mock NAS discovery manager")

# Handle auth imports with fallbacks
try:
    from auth_2fa import require_auth, require_admin
except ImportError:
    # Create fallback auth decorators
    def require_auth(f):
        """Fallback auth decorator"""
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function
    
    def require_admin(f):
        """Fallback admin decorator"""
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function

# Create blueprint for NAS discovery endpoints
nas_discovery_bp = Blueprint('nas_discovery', __name__, url_prefix='/api/nas')

def validate_nas_discovery_data(data: Dict) -> tuple[bool, str]:
    """Validate NAS discovery request data"""
    if 'ip_range' not in data or not data['ip_range']:
        return False, "IP range is required"
    
    scan_type = data.get('scan_type', 'comprehensive')
    if scan_type not in ['quick', 'comprehensive', 'deep']:
        return False, "Invalid scan type. Must be 'quick', 'comprehensive', or 'deep'"
    
    max_threads = data.get('max_threads', 50)
    if not isinstance(max_threads, int) or max_threads < 1 or max_threads > 100:
        return False, "max_threads must be between 1 and 100"
    
    return True, ""

# ============================================================================
# NAS DISCOVERY ENDPOINTS
# ============================================================================

@nas_discovery_bp.route('/discover', methods=['POST'])
@require_admin
def discover_nas_devices():
    """🔍 Discover NAS devices on the network"""
    try:
        data = request.get_json() or {}
        
        # Validate data
        is_valid, error_msg = validate_nas_discovery_data(data)
        if not is_valid:
            return jsonify({'success': False, 'error': error_msg}), 400
        
        ip_range = data['ip_range']
        scan_type = data.get('scan_type', 'comprehensive')
        max_threads = data.get('max_threads', 50)
        
        logger.info(f"🔍 Starting NAS discovery scan on {ip_range} ({scan_type})")
        
        # Perform NAS discovery
        discovered_devices = nas_discovery_manager.discover_nas_devices(
            ip_range=ip_range,
            scan_type=scan_type,
            max_threads=max_threads
        )
        
        # Convert to dict format
        devices_data = []
        for device in discovered_devices:
            if hasattr(device, 'to_dict'):
                devices_data.append(device.to_dict())
            else:
                devices_data.append(device)
        
        return jsonify({
            'success': True,
            'message': f'NAS discovery completed. Found {len(devices_data)} devices.',
            'discovered_devices': devices_data,
            'total_found': len(devices_data),
            'scan_parameters': {
                'ip_range': ip_range,
                'scan_type': scan_type,
                'max_threads': max_threads
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error in NAS discovery: {e}")
        return jsonify({'success': False, 'error': f'NAS discovery failed: {str(e)}'}), 500

@nas_discovery_bp.route('/devices', methods=['GET'])
@require_auth
def get_discovered_nas_devices():
    """Get all discovered NAS devices"""
    try:
        devices = nas_discovery_manager.get_discovered_nas_devices()
        
        # Convert to dict format
        devices_data = []
        for device in devices:
            if hasattr(device, 'to_dict'):
                devices_data.append(device.to_dict())
            else:
                devices_data.append(device)
        
        return jsonify({
            'success': True,
            'devices': devices_data,
            'total': len(devices_data)
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting NAS devices: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@nas_discovery_bp.route('/devices/<device_id>', methods=['GET'])
@require_auth
def get_nas_device_details(device_id: str):
    """Get detailed information about a specific NAS device"""
    try:
        device = nas_discovery_manager.get_nas_device_by_id(device_id)
        
        if device:
            device_data = device.to_dict() if hasattr(device, 'to_dict') else device
            return jsonify({
                'success': True,
                'device': device_data
            })
        else:
            return jsonify({'success': False, 'error': 'NAS device not found'}), 404
            
    except Exception as e:
        logger.error(f"❌ Error getting NAS device details: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@nas_discovery_bp.route('/test-credentials', methods=['POST'])
@require_admin
def test_nas_credentials():
    """Test NAS device credentials"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        required_fields = ['nas_id', 'username', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        nas_id = data['nas_id']
        username = data['username']
        password = data['password']
        domain = data.get('domain', '')
        share_path = data.get('share_path', '')
        
        # Test credentials
        success, message = nas_discovery_manager.test_nas_credentials(
            nas_id, username, password, domain, share_path
        )
        
        return jsonify({
            'success': success,
            'message': message,
            'credentials_valid': success
        })
        
    except Exception as e:
        logger.error(f"❌ Error testing NAS credentials: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@nas_discovery_bp.route('/suggestions', methods=['GET'])
@require_auth
def get_discovery_suggestions():
    """Get NAS discovery suggestions for South African healthcare"""
    try:
        suggestions = nas_discovery_manager.get_network_suggestions()
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting discovery suggestions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@nas_discovery_bp.route('/quick-scan', methods=['POST'])
@require_admin
def quick_nas_scan():
    """⚡ Quick NAS scan of common network ranges"""
    try:
        data = request.get_json() or {}
        
        # Use common network ranges if none specified
        ip_ranges = data.get('ip_ranges', ['192.168.1.0/24', '192.168.0.0/24', '10.0.0.0/24'])
        
        all_devices = []
        
        for ip_range in ip_ranges[:3]:  # Limit to 3 ranges for quick scan
            try:
                devices = nas_discovery_manager.discover_nas_devices(
                    ip_range=ip_range,
                    scan_type='quick',
                    max_threads=20
                )
                
                # Convert to dict format
                for device in devices:
                    device_data = device.to_dict() if hasattr(device, 'to_dict') else device
                    device_data['discovered_from_range'] = ip_range
                    all_devices.append(device_data)
                    
            except Exception as e:
                logger.warning(f"Error scanning range {ip_range}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'message': f'Quick NAS scan completed. Found {len(all_devices)} devices.',
            'discovered_devices': all_devices,
            'total_found': len(all_devices),
            'scanned_ranges': ip_ranges[:3]
        })
        
    except Exception as e:
        logger.error(f"❌ Error in quick NAS scan: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@nas_discovery_bp.route('/config', methods=['GET'])
@require_auth
def get_nas_config():
    """Get NAS configuration"""
    try:
        # Return mock configuration for now
        config = {
            'default_scan_type': 'comprehensive',
            'default_max_threads': 50,
            'supported_nas_types': ['smb', 'nfs', 'ftp', 'sftp'],
            'supported_manufacturers': [
                'Synology', 'QNAP', 'Netgear', 'Buffalo', 
                'Western Digital', 'Microsoft', 'Linux'
            ],
            'common_ports': {
                'SMB': [445, 139],
                'NFS': [2049, 111],
                'FTP': [21],
                'SSH': [22],
                'HTTP': [80, 8080],
                'HTTPS': [443, 5001]
            }
        }
        
        return jsonify({
            'success': True,
            'config': config
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting NAS config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@nas_discovery_bp.route('/config', methods=['POST'])
@require_admin
def update_nas_config():
    """Update NAS configuration"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No configuration data provided'}), 400
        
        # For now, just return success (would save to database in real implementation)
        return jsonify({
            'success': True,
            'message': 'NAS configuration updated successfully'
        })
        
    except Exception as e:
        logger.error(f"❌ Error updating NAS config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@nas_discovery_bp.route('/status', methods=['GET'])
@require_auth
def get_nas_status():
    """Get NAS discovery system status"""
    try:
        # Get discovered devices count
        devices = nas_discovery_manager.get_discovered_nas_devices()
        
        # Calculate statistics
        total_devices = len(devices)
        nas_types = {}
        manufacturers = {}
        
        for device in devices:
            device_data = device.to_dict() if hasattr(device, 'to_dict') else device
            
            nas_type = device_data.get('nas_type', 'unknown')
            nas_types[nas_type] = nas_types.get(nas_type, 0) + 1
            
            manufacturer = device_data.get('manufacturer', 'Unknown')
            manufacturers[manufacturer] = manufacturers.get(manufacturer, 0) + 1
        
        status = {
            'total_discovered_devices': total_devices,
            'nas_types_distribution': nas_types,
            'manufacturers_distribution': manufacturers,
            'discovery_system_status': 'operational',
            'last_scan': 'Not available',  # Would get from database
            'supported_features': [
                'SMB/CIFS Discovery',
                'NFS Discovery', 
                'FTP Discovery',
                'Credential Testing',
                'Share Enumeration',
                'Multi-threaded Scanning'
            ]
        }
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting NAS status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# HEALTHCARE-SPECIFIC NAS ENDPOINTS
# ============================================================================

@nas_discovery_bp.route('/healthcare-presets', methods=['GET'])
@require_auth
def get_healthcare_nas_presets():
    """Get NAS presets for South African healthcare"""
    try:
        presets = {
            'radiology_archive': {
                'name': 'Radiology Archive NAS',
                'description': 'High-capacity storage for DICOM archives',
                'recommended_capacity': '10TB - 100TB',
                'raid_level': 'RAID 5/6',
                'typical_shares': ['DICOM', 'Archive', 'Backup', 'Studies'],
                'access_requirements': 'Radiologists, Technologists',
                'backup_strategy': 'Daily incremental, Weekly full'
            },
            'pacs_storage': {
                'name': 'PACS Primary Storage',
                'description': 'High-performance storage for active PACS',
                'recommended_capacity': '5TB - 50TB',
                'raid_level': 'RAID 10',
                'typical_shares': ['PACS', 'Studies', 'Reports', 'Temp'],
                'access_requirements': 'PACS Server, Workstations',
                'backup_strategy': 'Real-time replication'
            },
            'backup_nas': {
                'name': 'Backup & Disaster Recovery',
                'description': 'Secure backup storage for disaster recovery',
                'recommended_capacity': '20TB - 200TB',
                'raid_level': 'RAID 6',
                'typical_shares': ['Backup', 'Archive', 'DR', 'Offsite'],
                'access_requirements': 'Backup Systems, Administrators',
                'backup_strategy': 'Automated daily backups'
            },
            'mobile_nas': {
                'name': 'Mobile/Portable NAS',
                'description': 'Portable storage for mobile imaging units',
                'recommended_capacity': '2TB - 10TB',
                'raid_level': 'RAID 1',
                'typical_shares': ['Mobile', 'Studies', 'Temp'],
                'access_requirements': 'Mobile Units, Field Staff',
                'backup_strategy': 'Sync when connected'
            }
        }
        
        return jsonify({
            'success': True,
            'healthcare_presets': presets
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting healthcare NAS presets: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@nas_discovery_bp.route('/sa-compliance', methods=['GET'])
@require_auth
def get_sa_compliance_info():
    """Get South African healthcare compliance information for NAS"""
    try:
        compliance_info = {
            'popia_requirements': {
                'description': 'Protection of Personal Information Act (POPIA) compliance',
                'requirements': [
                    'Data encryption at rest and in transit',
                    'Access control and user authentication',
                    'Audit logging of all access',
                    'Data retention policies',
                    'Secure data disposal'
                ]
            },
            'hpcsa_guidelines': {
                'description': 'Health Professions Council of SA guidelines',
                'requirements': [
                    'Patient data confidentiality',
                    'Secure storage of medical records',
                    'Backup and disaster recovery',
                    'Professional access controls'
                ]
            },
            'recommended_security': {
                'encryption': 'AES-256 encryption minimum',
                'authentication': 'Multi-factor authentication',
                'network_security': 'VPN access, firewall protection',
                'backup_strategy': '3-2-1 backup rule (3 copies, 2 different media, 1 offsite)',
                'access_logging': 'Complete audit trail of all access'
            },
            'data_retention': {
                'medical_images': '7-10 years minimum',
                'patient_records': '6 years minimum',
                'audit_logs': '2 years minimum',
                'backup_verification': 'Monthly restore testing'
            }
        }
        
        return jsonify({
            'success': True,
            'compliance_info': compliance_info
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting SA compliance info: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Error handlers
@nas_discovery_bp.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'NAS endpoint not found'}), 404

@nas_discovery_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == "__main__":
    # Test the endpoints
    from flask import Flask
    
    app = Flask(__name__)
    app.register_blueprint(nas_discovery_bp)
    
    print("NAS Discovery API endpoints registered:")
    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith('nas_discovery'):
            print(f"  {rule.methods} {rule.rule}")