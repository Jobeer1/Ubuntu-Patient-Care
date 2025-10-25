"""
Discovery blueprint: network discovery and related endpoints.
Extracted from nas_core.py to improve structure and maintainability.
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from .nas_utils import save_discovered_devices, load_discovered_devices
from .network_discovery import get_arp_table, ping_range, enhanced_network_discovery, validate_network_range
from .device_management import DeviceManager

# Import auth decorators
try:
    from ..auth_utils import require_auth
except ImportError:
    # Fallback for direct execution
    from auth_utils import require_auth

logger = logging.getLogger(__name__)

discovery_bp = Blueprint('nas_discovery', __name__)
# Note: blueprint for discovery-related routes

def _truthy(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.strip().lower() in ('1', 'true', 'yes', 'on')
    return False

device_manager = DeviceManager()


@discovery_bp.route('/discover', methods=['GET'])
def discover_devices():
    """Discover devices on the network using ARP table"""
    try:
        logger.info("Starting device discovery")
        discovered_devices = get_arp_table()
        if not discovered_devices:
            return jsonify({
                'success': False,
                'message': 'No devices found in network discovery',
                'discovered_devices': [],
                'total_devices': 0
            })

        formatted_devices = []
        for device in discovered_devices:
            ip_address = device.get('ip_address', 'Unknown')
            mac_address = device.get('mac_address', 'Unknown')
            custom_name = None
            if mac_address != 'Unknown':
                custom_name = device_manager.get_device_name(mac_address)
            hostname = custom_name or device.get('hostname', 'Unknown Device')
            formatted_device = {
                'ip_address': ip_address,
                'mac_address': mac_address,
                'hostname': hostname,
                'manufacturer': device.get('manufacturer', 'Unknown'),
                'type': device.get('type', 'Unknown'),
                'last_seen': device.get('last_seen', 'Unknown'),
                'source': device.get('source', 'ARP Table'),
                'via_arp': bool(device.get('via_arp', False)),
                'custom_name': custom_name
            }
            formatted_devices.append(formatted_device)

        logger.info(f"Device discovery completed: {len(formatted_devices)} devices found")
        save_discovered_devices(formatted_devices, 'Device Discovery')

        return jsonify({
            'success': True,
            'message': f'Found {len(formatted_devices)} devices on the network',
            'discovered_devices': formatted_devices,
            'total_devices': len(formatted_devices),
            'discovery_method': 'ARP Table',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Device discovery error: {e}")
        return jsonify({
            'success': False,
            'error': f'Device discovery failed: {str(e)}',
            'discovered_devices': [],
            'total_devices': 0
        }), 500


@discovery_bp.route('/ping', methods=['POST'])
@require_auth
def ping_device():
    """Ping a specific device - alias for ping_device_endpoint"""
    return ping_device_endpoint()


@discovery_bp.route('/ping_device', methods=['POST'])
@require_auth
def ping_device_endpoint():
    """Ping a specific device"""
    try:
        data = request.get_json()
        if not data or 'ip_address' not in data:
            return jsonify({ 'success': False, 'error': 'IP address is required' }), 400
        ip_address = data['ip_address']
        timeout = data.get('timeout', 3)
        logger.info(f"Pinging device: {ip_address}")
        # delegate to network_discovery or nas_utils implementation
        from .nas_utils import ping_device, update_device_ping_result
        result = ping_device(ip_address, timeout)
        update_device_ping_result(ip_address, result)
        return jsonify({ 'success': True, 'ping_result': result, 'timestamp': datetime.now().isoformat() })
    except Exception as e:
        logger.error(f"Ping device error: {e}")
        return jsonify({ 'success': False, 'error': f'Ping failed: {str(e)}' }), 500


@discovery_bp.route('/ping_range', methods=['POST'])
@require_auth
def ping_range_endpoint():
    """Ping a range of IP addresses"""
    try:
        data = request.get_json()
        if not data or 'start_ip' not in data or 'end_ip' not in data:
            return jsonify({ 'success': False, 'error': 'Start IP and End IP are required' }), 400
        start_ip = data['start_ip']
        end_ip = data['end_ip']
        timeout = data.get('timeout', 2)
        max_hosts = data.get('max_hosts')
        max_concurrent = data.get('max_concurrent', 10)
        logger.info(f"Pinging range: {start_ip} to {end_ip}")
        try:
            if max_hosts is None:
                max_hosts_val = 254
            else:
                max_hosts_val = int(max_hosts)
        except Exception:
            max_hosts_val = 254
        if max_hosts_val < 1:
            max_hosts_val = 1
        elif max_hosts_val > 1024:
            max_hosts_val = 1024
        result = ping_range(start_ip, end_ip, timeout, max_concurrent, max_hosts=max_hosts_val)
        return jsonify({ 'success': True, 'ping_range_result': result, 'timestamp': datetime.now().isoformat() })
    except Exception as e:
        logger.error(f"Ping range error: {e}")
        return jsonify({ 'success': False, 'error': f'Ping range failed: {str(e)}' }), 500


@discovery_bp.route('/enhanced_discovery', methods=['POST'])
@require_auth
def enhanced_discovery_endpoint():
    """Enhanced network discovery with multiple methods"""
    try:
        data = request.get_json() or {}
        include_arp = data.get('include_arp', True)
        raw_include_range = None
        for key in ('include_ping_range', 'includePingRange', 'include_ping', 'includeRange'):
            if key in data:
                raw_include_range = data.get(key)
                break
        include_ping_range = _truthy(raw_include_range) if raw_include_range is not None else False
        raw_port_scan = None
        for key in ('include_port_scan', 'includePortScan', 'portScan'):
            if key in data:
                raw_port_scan = data.get(key)
                break
        include_port_scan = _truthy(raw_port_scan) if raw_port_scan is not None else False
        start_ip = data.get('start_ip') or data.get('startIp') or data.get('startIpAddress')
        end_ip = data.get('end_ip') or data.get('endIp') or data.get('endIpAddress')
        timeout = data.get('timeout', 2)
        network_range = data.get('network_range') or data.get('networkRange')
        if (not start_ip or not end_ip) and network_range:
            try:
                import ipaddress
                net = ipaddress.IPv4Network(network_range, strict=False)
                hosts = list(net.hosts())
                if hosts:
                    start_ip = start_ip or str(hosts[0])
                    end_ip = end_ip or str(hosts[-1])
                    include_ping_range = True
            except Exception as e:
                logger.debug(f"Could not derive start/end from network_range {network_range}: {e}")
        if not include_ping_range and start_ip and end_ip:
            include_ping_range = True
        logger.info(f"Enhanced discovery: ARP={include_arp}, Range={include_ping_range}, start={start_ip}, end={end_ip}")
        raw_max = data.get('max_hosts')
        try:
            if raw_max is None:
                max_hosts_val = 254
            else:
                max_hosts_val = int(raw_max)
        except Exception:
            max_hosts_val = 254
        if max_hosts_val < 1:
            max_hosts_val = 1
        elif max_hosts_val > 1024:
            max_hosts_val = 1024
        result = enhanced_network_discovery(
            include_arp=include_arp,
            include_ping_range=include_ping_range,
            start_ip=start_ip,
            end_ip=end_ip,
            timeout=timeout,
            include_port_scan=include_port_scan,
            max_hosts=max_hosts_val
        )
        if result.get('success') and result.get('discovered_devices'):
            methods_used = result.get('methods_used', [])
            discovery_method = f"Enhanced Discovery ({', '.join(methods_used)})"
            save_discovered_devices(result['discovered_devices'], discovery_method)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Enhanced discovery error: {e}")
        return jsonify({ 'success': False, 'error': f'Enhanced discovery failed: {str(e)}' }), 500


@discovery_bp.route('/validate_network', methods=['POST'])
def validate_network():
    """Validate network range for scanning"""
    try:
        data = request.get_json()
        if not data or 'network_range' not in data:
            return jsonify({ 'success': False, 'error': 'Network range is required' }), 400
        network_range = data['network_range']
        current_network = data.get('current_network', '155.235.81.0/24')
        result = validate_network_range(network_range, current_network)
        return jsonify({ 'success': True, 'validation_result': result })
    except Exception as e:
        logger.error(f"Validate network error: {e}")
        return jsonify({ 'success': False, 'error': f'Network validation failed: {str(e)}' }), 500


@discovery_bp.route('/arp-table', methods=['GET'])
def arp_table():
    """Get ARP table - legacy endpoint for frontend compatibility"""
    try:
        logger.info("ARP table request received")
        discovered_devices = get_arp_table()
        if not discovered_devices:
            logger.info("No devices returned from ARP discovery (empty list)")
            return jsonify({
                'success': False,
                'message': 'No devices found in ARP table or ARP command failed',
                'devices': [],
                'arp_entries': [],
                'discovered_devices': [],
                'total': 0,
                'total_entries': 0
            })
        formatted_devices = []
        for device in discovered_devices:
            ip_address = device.get('ip_address', 'Unknown')
            mac_address = device.get('mac_address', 'Unknown')
            custom_name = None
            if mac_address != 'Unknown':
                custom_name = device_manager.get_device_name(mac_address)
            hostname = custom_name or device.get('hostname', 'Unknown Device')
            formatted_device = {
                'ip_address': ip_address,
                'mac_address': mac_address,
                'hostname': hostname,
                'manufacturer': device.get('manufacturer', 'Unknown'),
                'type': device.get('type', 'Unknown'),
                'last_seen': device.get('last_seen', 'Unknown'),
                'source': device.get('source', 'ARP Table'),
                'via_arp': bool(device.get('via_arp', False)),
                'custom_name': custom_name
            }
            formatted_devices.append(formatted_device)
        logger.info(f"ARP table discovery completed: {len(formatted_devices)} devices found")
        save_discovered_devices(formatted_devices, 'ARP Table')
        return jsonify({
            'success': True,
            'message': f'Found {len(formatted_devices)} devices in ARP table',
            'devices': formatted_devices,
            'arp_entries': formatted_devices,
            'discovered_devices': formatted_devices,
            'total': len(formatted_devices),
            'total_entries': len(formatted_devices),
            'discovery_method': 'ARP Table',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"ARP table error: {e}")
        return jsonify({ 'success': False, 'error': f'ARP table discovery failed: {str(e)}', 'devices': [], 'total': 0 }), 500


@discovery_bp.route('/discover-devices', methods=['GET', 'POST'])
def discover_devices_legacy():
    """Legacy discover devices endpoint"""
    return discover_devices()


@discovery_bp.route('/scan-device', methods=['POST'])
@require_auth
def scan_device_endpoint():
    """Scan a specific device for open ports"""
    try:
        data = request.get_json()
        if not data or 'ip_address' not in data:
            return jsonify({ 'success': False, 'error': 'IP address is required' }), 400
        ip_address = data['ip_address']
        ports = data.get('ports', [104, 11112, 8042, 80, 443])  # Default medical imaging ports
        timeout = data.get('timeout', 2)
        logger.info(f"Scanning device: {ip_address} on ports {ports}")
        
        # Prefer NAS-specific scanner for requests coming from NAS UI
        # Fallback to the generic network_discovery scanner if NAS-specific not present
        nas_scan = None
        net_scan = None
        try:
            from .nas_utils import scan_device_ports as nas_scan
        except Exception:
            nas_scan = None

        try:
            from .network_discovery import scan_device_ports as net_scan
        except Exception:
            net_scan = None

        # Allow explicit override via request (scan_type/context)
        scan_type = None
        if isinstance(data, dict):
            scan_type = data.get('scan_type') or data.get('context') or data.get('type')

        scan_func = None
        if isinstance(scan_type, str):
            st = scan_type.strip().lower()
            if st in ('nas', 'storage') and nas_scan:
                scan_func = nas_scan
            elif st in ('medical', 'imaging', 'dicom') and net_scan:
                scan_func = net_scan

        # Default: prefer nas_scan for NAS blueprint, otherwise network scanner
        if not scan_func:
            scan_func = nas_scan or net_scan

        if not scan_func:
            return jsonify({ 'success': False, 'error': 'No scan implementation available on server' }), 500

        logger.info(f"Using scan implementation: {scan_func.__module__}.{scan_func.__name__}")

        scan_result = scan_func(ip_address, ports, timeout)
        
        return jsonify({ 
            'success': True, 
            'scan_result': scan_result, 
            'timestamp': datetime.now().isoformat() 
        })
    except Exception as e:
        logger.error(f"Scan device error: {e}")
        return jsonify({ 'success': False, 'error': f'Scan failed: {str(e)}' }), 500


@discovery_bp.route('/enhanced-discover', methods=['POST'])
def enhanced_discover():
    """Enhanced discovery endpoint"""
    return enhanced_discovery_endpoint()


@discovery_bp.route('/cached-devices', methods=['GET'])
def get_cached_devices():
    """Get cached discovered devices from JSON database"""
    try:
        cached_data = load_discovered_devices()
        return jsonify({
            'success': True,
            'devices': cached_data.get('devices', []),
            'arp_entries': cached_data.get('devices', []),
            'discovered_devices': cached_data.get('devices', []),
            'total': len(cached_data.get('devices', [])),
            'total_entries': len(cached_data.get('devices', [])),
            'last_discovery': cached_data.get('last_discovery'),
            'discovery_method': cached_data.get('discovery_method', 'Cached'),
            'discovery_count': cached_data.get('discovery_count', 0),
            'message': f"Retrieved {len(cached_data.get('devices', []))} cached devices"
        })
    except Exception as e:
        logger.error(f"Get cached devices error: {e}")
        return jsonify({ 'success': False, 'error': f'Failed to get cached devices: {str(e)}', 'devices': [], 'total': 0 }), 500


@discovery_bp.route('/network-settings', methods=['GET'])
@require_auth
def get_network_settings():
    """Get network settings"""
    try:
        from .nas_utils import get_network_settings
        settings = get_network_settings()
        return jsonify({ 'success': True, 'settings': settings })
    except Exception as e:
        logger.error(f"Get network settings error: {e}")
        return jsonify({ 'success': False, 'error': str(e) }), 500


@discovery_bp.route('/network-settings', methods=['POST'])
@require_auth
def save_network_settings():
    """Save network settings"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({ 'success': False, 'error': 'Request data is required' }), 400
        from .nas_utils import save_network_settings
        result = save_network_settings(data)
        if result:
            return jsonify({ 'success': True, 'message': 'Network settings saved successfully' })
        else:
            return jsonify({ 'success': False, 'error': 'Failed to save network settings' }), 500
    except Exception as e:
        logger.error(f"Save network settings error: {e}")
        return jsonify({ 'success': False, 'error': f'Failed to save network settings: {str(e)}' }), 500
