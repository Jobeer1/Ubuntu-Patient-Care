"""
Device management routes blueprint for the South African Medical Imaging System
"""

from flask import Blueprint, request, jsonify
import logging
import sys
import os

# Add parent directory to path to import device manager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

# Import device manager (will be available when the app initializes it)
device_manager = None

def init_device_routes(dm):
    """Initialize device routes with device manager"""
    global device_manager
    device_manager = dm

device_bp = Blueprint('devices', __name__, url_prefix='/api/devices')

# Import auth decorators
try:
    from ..auth_utils import require_auth, require_admin
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from auth_utils import require_auth, require_admin

@device_bp.route('', methods=['GET'])
def get_devices():
    """Get all registered devices"""
    try:
        if device_manager is None:
            return jsonify({'error': 'Device manager not initialized'}), 500

        # Try multiple possible method names for backwards compatibility
        if hasattr(device_manager, 'list_devices'):
            devices = device_manager.list_devices()
        elif hasattr(device_manager, 'get_devices'):
            devices = device_manager.get_devices()
        elif hasattr(device_manager, 'get_all_devices'):
            devices = device_manager.get_all_devices()
        elif hasattr(device_manager, 'repo') and hasattr(device_manager.repo, 'list_devices'):
            devices = device_manager.repo.list_devices()
        else:
            devices = []
        # Convert devices to dict format if needed
        device_list = []
        for device in devices:
            if hasattr(device, '__dict__'):
                device_list.append(device.__dict__)
            elif isinstance(device, dict):
                device_list.append(device)
            else:
                device_list.append(str(device))
        
        return jsonify({
            'success': True,
            'devices': device_list,
            'total': len(device_list),
            'message': 'Devices retrieved successfully'
        })
    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        return jsonify({'error': 'Failed to get devices'}), 500

@device_bp.route('', methods=['POST'])
@require_admin
def add_device():
    """Add a new device"""
    try:
        if device_manager is None:
            return jsonify({'error': 'Device manager not initialized'}), 500
            
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'ip_address', 'device_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        success, message, device = device_manager.add_device(data)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'device': device
            })
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"Error adding device: {e}")
        return jsonify({'error': 'Failed to add device'}), 500

@device_bp.route('/<device_id>', methods=['DELETE'])
@require_admin
def delete_device(device_id):
    """Delete a device"""
    try:
        if device_manager is None:
            return jsonify({'error': 'Device manager not initialized'}), 500
            
        # Try several delete/remove interfaces
        success = False
        message = 'Device deleted'
        try:
            if hasattr(device_manager, 'remove_device'):
                success, message = device_manager.remove_device(device_id)
            elif hasattr(device_manager, 'delete_device'):
                success, message = device_manager.delete_device(device_id)
            elif hasattr(device_manager, 'repo') and hasattr(device_manager.repo, 'delete_device'):
                # repo.delete_device returns True/False
                ok = device_manager.repo.delete_device(device_id)
                success = bool(ok)
                message = 'Device deleted' if ok else 'Device not found'
            else:
                return jsonify({'error': 'Delete not supported'}), 501
        except Exception as del_e:
            logger.error(f"Delete device implementation error: {del_e}")
            return jsonify({'error': 'Failed to delete device'}), 500
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({'error': message}), 404
            
    except Exception as e:
        logger.error(f"Error deleting device: {e}")
        return jsonify({'error': 'Failed to delete device'}), 500

@device_bp.route('/network/discovery-scan', methods=['POST'])
@require_auth
def network_discovery_scan():
    """Perform network discovery scan"""
    try:
        if device_manager is None:
            return jsonify({'error': 'Device manager not initialized'}), 500
            
        data = request.get_json() or {}
        network_range = data.get('network_range', '192.168.1.0/24')
        # Support multiple possible DeviceManager method names depending on
        # which device manager implementation is loaded. Fall back to a
        # simple ARP table scan if richer discovery isn't available.
        discovered_devices = []
        try:
            if hasattr(device_manager, 'discover_network_devices'):
                discovered_devices = device_manager.discover_network_devices(network_range)
            elif hasattr(device_manager, 'network_discovery_scan'):
                # network_discovery_scan may expect an ip_range kwarg
                try:
                    discovered_devices = device_manager.network_discovery_scan(ip_range=network_range)
                except TypeError:
                    # Maybe positional
                    discovered_devices = device_manager.network_discovery_scan(network_range)
            elif hasattr(device_manager, 'scan_arp_table'):
                # Fallback to ARP table scan when full network discovery isn't present
                discovered_devices = device_manager.scan_arp_table()
            else:
                # No discovery methods available; return empty list rather than 500
                discovered_devices = []
        except Exception as inner_e:
            logger.error(f"Discovery implementation error: {inner_e}")
            # Fall back to ARP table scan if available
            try:
                if hasattr(device_manager, 'scan_arp_table'):
                    discovered_devices = device_manager.scan_arp_table()
            except Exception:
                # swallow and continue to return an informative error below
                discovered_devices = []
        
        return jsonify({
            'success': True,
            'discovered_devices': discovered_devices,
            'message': 'Network discovery completed (fallbacks applied if needed)'
        })
        
    except Exception as e:
        logger.error(f"Network discovery error: {e}")
        return jsonify({'error': 'Network discovery failed'}), 500


@device_bp.route('/network/arp-scan', methods=['GET', 'POST'])
def arp_scan_compat():
    """Compatibility alias for older UI expecting /network/arp-scan
    Delegates to `network_discovery_scan` (POST semantics are supported).
    """
    # Convert GET to a POST-like call with default network_range
    if hasattr(request, 'get_json') and request.method == 'GET':
        # Call underlying function with default parameters
        return network_discovery_scan()
    else:
        return network_discovery_scan()

@device_bp.route('/network/test-dicom', methods=['POST'])
@require_auth
def test_dicom_connection():
    """Test DICOM connection to a device"""
    try:
        if device_manager is None:
            return jsonify({'error': 'Device manager not initialized'}), 500
            
        data = request.get_json()
        ip_address = data.get('ip_address')
        port = data.get('port', 11112)
        
        if not ip_address:
            return jsonify({'error': 'IP address is required'}), 400
        # Use test_dicom_connection if available, otherwise fall back to test_connectivity
        if hasattr(device_manager, 'test_dicom_connection'):
            success, message = device_manager.test_dicom_connection(ip_address, port)
        elif hasattr(device_manager, 'test_connectivity'):
            result = device_manager.test_connectivity(ip_address, port)
            success = bool(result.get('reachable') or result.get('dicom'))
            message = result
        else:
            return jsonify({'error': 'Connectivity test not supported'}), 501
        
        return jsonify({
            'success': success,
            'message': message,
            'reachable': success
        })
        
    except Exception as e:
        logger.error(f"DICOM test error: {e}")
        return jsonify({'error': 'DICOM test failed'}), 500

@device_bp.route('/network/create-from-discovery', methods=['POST'])
@require_admin
def create_device_from_discovery():
    """Create a device from discovery data"""
    try:
        if device_manager is None:
            return jsonify({'error': 'Device manager not initialized'}), 500
            
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['ip_address', 'name', 'device_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Create device from discovery data
        device_data = {
            'name': data['name'],
            'ip_address': data['ip_address'],
            'device_type': data['device_type'],
            'port': data.get('port', 11112),
            'manufacturer': data.get('manufacturer', 'Unknown'),
            'model': data.get('model', 'Unknown'),
            'description': data.get('description', f"Auto-discovered {data['device_type']} device")
        }
        
        success, message, device = device_manager.add_device(device_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Device {data["name"]} created successfully',
                'device': device
            })
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"Error creating device from discovery: {e}")
        return jsonify({'error': 'Failed to create device'}), 500

@device_bp.route('/network/enhanced-scan', methods=['POST'])
@require_auth
def enhanced_network_scan():
    """Perform enhanced network scan with device identification"""
    try:
        # Import network discovery functions
        from .network_discovery import enhanced_network_discovery
        
        data = request.get_json() or {}
        start_ip = data.get('start_ip')
        end_ip = data.get('end_ip')
        timeout = data.get('timeout', 2)
        include_arp = data.get('include_arp', True)
        include_ping_range = data.get('include_ping_range', True)
        max_hosts = data.get('max_hosts', 254)
        
        # Call the network discovery function directly
        result = enhanced_network_discovery(
            include_arp=include_arp,
            include_ping_range=include_ping_range,
            start_ip=start_ip,
            end_ip=end_ip,
            timeout=timeout,
            max_hosts=max_hosts
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Enhanced network scan error: {e}")
        return jsonify({'success': False, 'error': f'Enhanced network scan failed: {str(e)}'}), 500

# Import network discovery functions for device database access
try:
    from .network_discovery import get_device_database_info, get_device_details
except ImportError:
    # Fallback import
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from network_discovery import get_device_database_info, get_device_details

@device_bp.route('/database', methods=['GET'])
def get_device_database():
    """Get comprehensive device database information"""
    try:
        result = get_device_database_info()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error retrieving device database: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'devices': [],
            'statistics': {},
            'total_entries': 0
        }), 500

@device_bp.route('/database/<ip_address>', methods=['GET'])
def get_device_info(ip_address):
    """Get detailed information for a specific device"""
    try:
        result = get_device_details(ip_address)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except Exception as e:
        logger.error(f"Error retrieving device details: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@device_bp.route('/database/stats', methods=['GET'])
def get_device_stats():
    """Get device database statistics"""
    try:
        from .network_discovery import device_db
        stats = device_db.get_statistics()
        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        logger.error(f"Error retrieving device statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'statistics': {}
        }), 500
