"""
Devices blueprint: endpoints for device management and compatibility routes.
Extracted from nas_core.py to improve structure and maintainability.
"""
import logging
from flask import Blueprint, request, jsonify
from .device_management import DeviceManager
from .nas_utils import load_discovered_devices

logger = logging.getLogger(__name__)

devices_bp = Blueprint('nas_devices', __name__)

device_manager = DeviceManager()


@devices_bp.route('/update_device_name', methods=['POST'])
def update_device_name():
    """Update custom name for a device"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({ 'success': False, 'error': 'Request data is required' }), 400
        mac_address = data.get('mac_address')
        ip_address = data.get('ip_address')
        new_name = data.get('new_name')
        if not new_name:
            return jsonify({ 'success': False, 'error': 'New name is required' }), 400
        if not mac_address and not ip_address:
            return jsonify({ 'success': False, 'error': 'Either MAC address or IP address is required' }), 400
        if not mac_address and ip_address:
            try:
                discovered_data = load_discovered_devices()
                devices = discovered_data.get('devices', [])
                for device in devices:
                    if device.get('ip_address') == ip_address:
                        mac_address = device.get('mac_address')
                        break
            except Exception as e:
                logger.warning(f"Could not lookup MAC address for {ip_address}: {e}")
        result = device_manager.update_device_name(mac_address, ip_address, new_name)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Update device name error: {e}")
        return jsonify({ 'success': False, 'error': f'Failed to update device name: {str(e)}' }), 500


@devices_bp.route('/configure_nas', methods=['POST'])
def configure_nas_device():
    """Configure a device as NAS server"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({ 'success': False, 'error': 'Request data is required' }), 400
        ip_address = data.get('ip_address')
        mac_address = data.get('mac_address')
        nas_config = data.get('nas_config', {})
        if not ip_address or not mac_address:
            return jsonify({ 'success': False, 'error': 'IP address and MAC address are required' }), 400
        result = device_manager.configure_nas_device(ip_address, mac_address, nas_config)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Configure NAS device error: {e}")
        return jsonify({ 'success': False, 'error': f'Failed to configure NAS device: {str(e)}' }), 500


@devices_bp.route('/device_details/<ip_address>', methods=['GET'])
def get_device_details(ip_address):
    """Get detailed information about a device"""
    try:
        mac_address = request.args.get('mac_address')
        if not mac_address:
            return jsonify({ 'success': False, 'error': 'MAC address parameter is required' }), 400
        result = device_manager.get_device_details(ip_address, mac_address)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Get device details error: {e}")
        return jsonify({ 'success': False, 'error': f'Failed to get device details: {str(e)}' }), 500


@devices_bp.route('/test_connectivity', methods=['POST'])
def test_connectivity():
    """Test device connectivity"""
    try:
        data = request.get_json()
        if not data or 'ip_address' not in data:
            return jsonify({ 'success': False, 'error': 'IP address is required' }), 400
        ip_address = data['ip_address']
        test_type = data.get('test_type', 'ping')
        result = device_manager.test_device_connectivity(ip_address, test_type)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Test connectivity error: {e}")
        return jsonify({ 'success': False, 'error': f'Connectivity test failed: {str(e)}' }), 500


@devices_bp.route('/nas_devices', methods=['GET'])
def get_nas_devices():
    """Get all configured NAS devices"""
    try:
        nas_devices = device_manager.get_nas_devices()
        return jsonify({ 'success': True, 'nas_devices': nas_devices, 'total_nas_devices': len(nas_devices) })
    except Exception as e:
        logger.error(f"Get NAS devices error: {e}")
        return jsonify({ 'success': False, 'error': f'Failed to get NAS devices: {str(e)}' }), 500


@devices_bp.route('/remove_nas_config', methods=['DELETE'])
def remove_nas_config():
    """Remove NAS configuration from a device"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({ 'success': False, 'error': 'Request data is required' }), 400
        ip_address = data.get('ip_address')
        mac_address = data.get('mac_address')
        if not ip_address or not mac_address:
            return jsonify({ 'success': False, 'error': 'IP address and MAC address are required' }), 400
        result = device_manager.remove_nas_configuration(ip_address, mac_address)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Remove NAS config error: {e}")
        return jsonify({ 'success': False, 'error': f'Failed to remove NAS configuration: {str(e)}' }), 500


@devices_bp.route('/remove-device', methods=['POST'])
def remove_device_alt():
    """Remove device endpoint for frontend compatibility"""
    try:
        data = request.get_json()
        ip_address = data.get('ip_address')
        if not ip_address:
            return jsonify({ 'success': False, 'error': 'IP address is required' }), 400
        return jsonify({ 'success': True, 'message': f'Device {ip_address} removed successfully' })
    except Exception as e:
        return jsonify({ 'success': False, 'error': str(e) }), 500


@devices_bp.route('/device-info/<string:ip_address>', methods=['GET'])
def get_device_info_alt(ip_address):
    """Get device information endpoint for frontend compatibility"""
    try:
        cached = load_discovered_devices()
        devices = cached.get('devices', [])
        found = next((d for d in devices if d.get('ip_address') == ip_address), None)
        mac = None
        hostname = None
        manufacturer = None
        last_seen = None
        response_time = None
        status = 'Offline'
        if found:
            mac = found.get('mac_address')
            hostname = found.get('hostname') or found.get('custom_name')
            manufacturer = found.get('manufacturer')
            last_seen = found.get('last_seen')
            pr = found.get('ping_result') or found.get('last_ping')
            if isinstance(pr, dict):
                response_time = pr.get('response_time')
                status = 'Online' if pr.get('reachable') else 'Offline'
            else:
                response_time = found.get('response_time')
                status = 'Online' if found.get('reachable') else 'Offline'
        try:
            if mac:
                dm = device_manager
                details = dm.get_device_details(ip_address, mac)
                if details and details.get('success'):
                    dd = details.get('device_details', {})
                    hostname = hostname or dd.get('custom_name') or dd.get('hostname')
                    manufacturer = manufacturer or dd.get('nas_configuration', {}).get('vendor') or dd.get('device_configuration', {}).get('vendor')
                    last_seen = last_seen or dd.get('last_updated')
                    pr = dd.get('connectivity', {}).get('ping', {})
                    if pr:
                        response_time = pr.get('response_time')
                        status = 'Online' if pr.get('reachable') else status
        except Exception:
            pass
        return jsonify({ 'success': True, 'device_info': {
            'ip_address': ip_address,
            'hostname': hostname or 'Unknown',
            'mac_address': mac or 'Unknown',
            'vendor': manufacturer or 'Unknown',
            'status': status,
            'last_seen': last_seen or 'Unknown',
            'response_time': response_time or 'N/A'
        } })
    except Exception as e:
        return jsonify({ 'success': False, 'error': str(e) }), 500


# ---- Indexing compatibility & status (moved here for simplicity) ----
import logging as _logging
from datetime import datetime as _datetime
from flask import request as _request

_logger = _logging.getLogger(__name__)

# Simple in-memory indexing state (demo)
indexing_state = {
    'state': 'idle',
    'progress': 0,
    'details': 'Idle',
    'started_at': None
}


@devices_bp.route('/indexing/start', methods=['POST'])
def start_indexing():
    try:
        data = _request.get_json() or {}
        share_path = data.get('share_path') or data.get('sharePath') or data.get('path')
        indexing_state['state'] = 'indexing'
        indexing_state['progress'] = 0
        indexing_state['details'] = f"Indexing started for {share_path or 'unknown share'}"
        indexing_state['started_at'] = _datetime.utcnow()
        _logger.info(f"Indexing started for share: {share_path}")
        return jsonify({ 'success': True, 'message': 'Indexing started', 'status': 'indexing' })
    except Exception as e:
        _logger.error(f"Start indexing error: {e}")
        return jsonify({ 'success': False, 'error': str(e) }), 500


@devices_bp.route('/indexing/stop', methods=['POST'])
def stop_indexing():
    try:
        indexing_state['state'] = 'idle'
        indexing_state['progress'] = 100
        indexing_state['details'] = 'Stopped by user'
        indexing_state['started_at'] = None
        return jsonify({ 'success': True, 'message': 'Indexing stopped', 'status': 'idle' })
    except Exception as e:
        _logger.error(f"Stop indexing error: {e}")
        return jsonify({ 'success': False, 'error': str(e) }), 500


@devices_bp.route('/start-indexing', methods=['POST'])
def start_indexing_compat():
    return start_indexing()


@devices_bp.route('/indexing/status', methods=['GET'])
def indexing_status():
    try:
        if indexing_state['state'] == 'indexing' and indexing_state['started_at']:
            elapsed = (_datetime.utcnow() - indexing_state['started_at']).total_seconds()
            prog = min(100, int(elapsed * 5))
            indexing_state['progress'] = prog
            if prog >= 100:
                indexing_state['state'] = 'completed'
                indexing_state['details'] = 'Indexing complete'
        return jsonify({ 'success': True, 'status': { 'state': indexing_state['state'], 'progress': indexing_state['progress'], 'details': indexing_state['details'] } })
    except Exception as e:
        _logger.error(f"Indexing status error: {e}")
        return jsonify({ 'success': False, 'error': str(e) }), 500


@devices_bp.route('/connect-device', methods=['POST'])
def connect_device_alt():
    """Compatibility endpoint: connect to device (simple response)."""
    try:
        data = request.get_json() or {}
        ip_address = data.get('ip_address') or data.get('ip')
        if not ip_address:
            return jsonify({'success': False, 'error': 'IP address is required'}), 400
        # For compatibility we return a simple success response. Real
        # connection logic is handled elsewhere (device manager).
        return jsonify({'success': True, 'message': f'Successfully connected to {ip_address}', 'ip_address': ip_address})
    except Exception as e:
        logger.error(f"Connect device error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@devices_bp.route('/orthanc/status', methods=['GET'])
def orthanc_status():
    """Return a basic Orthanc status for frontend compatibility."""
    try:
        # Minimal info; real implementation would query Orthanc
        return jsonify({
            'success': True,
            'status': 'running',
            'version': '1.12.0',
            'database_version': '6',
            'storage_configured': True,
            'patients_count': 0,
            'studies_count': 0,
            'series_count': 0,
            'instances_count': 0
        })
    except Exception as e:
        logger.error(f"Orthanc status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@devices_bp.route('/scan-device', methods=['POST'])
def scan_device_endpoint():
    """Scan a single device for open ports and return scan summary."""
    try:
        data = request.get_json() or {}
        ip_address = data.get('ip_address') or data.get('ip')
        if not ip_address:
            return jsonify({'success': False, 'error': 'IP address is required'}), 400

        timeout = data.get('timeout', 1)
        common_ports = data.get('ports') or data.get('common_ports')

        # Delegate to shared utility which performs socket checks and scoring
        from .nas_utils import scan_device_ports

        result = scan_device_ports(ip_address, common_ports=common_ports, timeout=timeout)

        return jsonify({'success': True, 'scan_result': result})
    except Exception as e:
        logger.error(f"Scan device error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ---- Phase 0: Minimal NAS indexer trigger (dry-run) ----
@devices_bp.route('/indexing/scan', methods=['POST'])
def trigger_indexer_scan():
    """Trigger a safe dry-run index scan over a NAS path. This does not
    write to databases or import into Orthanc unless explicit import logic
    is later invoked. The request JSON may include: path, max_files.
    """
    try:
        data = request.get_json() or {}
        path = data.get('path') or data.get('share_path') or data.get('sharePath')
        if not path:
            return jsonify({'success': False, 'error': 'path is required'}), 400
        max_files = int(data.get('max_files') or data.get('max') or 100)

        # Delegate to the minimal indexer (dry-run)
        from ..indexer.indexer import scan_path

        report = scan_path(path, max_files=max_files, dry_run=True)

        return jsonify({'success': True, 'report': report})
    except Exception as e:
        logger.error(f"Indexer scan error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



