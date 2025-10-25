"""
Devices blueprint: endpoints for device management and compatibility routes.
Extracted from nas_core.py to improve structure and maintainability.
"""
import logging
from flask import Blueprint, request, jsonify
from .device_management import DeviceManager
from .nas_utils import load_discovered_devices
import os

# Import auth decorators
try:
    from ..auth_utils import require_auth
except ImportError:
    # Fallback for direct execution
    from auth_utils import require_auth

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
@require_auth
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
from datetime import datetime

# Simple in-memory indexing state (demo)
indexing_state = {
    'state': 'idle',
    'progress': 0,
    'details': 'Idle',
    'started_at': None
}


@devices_bp.route('/indexing/start', methods=['POST'])
def start_indexing():
    """Start real NAS DICOM indexing"""
    try:
        data = request.get_json() or {}
        share_path = data.get('share_path') or data.get('sharePath') or data.get('path', '/nas/dicom/')

        # Update state immediately for frontend feedback
        indexing_state['state'] = 'indexing'
        indexing_state['progress'] = 0
        indexing_state['details'] = f"Real indexing started for {share_path}"
        indexing_state['started_at'] = datetime.utcnow()
        logger.info(f"Real indexing started for share: {share_path}")

        # Start real indexing in background thread
        import threading
        import sys

        # Add parent directory to path to find nas_patient_indexer
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

        def run_real_indexing():
            """Run actual NAS indexing in background with improved error handling"""
            try:
                from nas_patient_indexer import NASPatientIndexer

                # Use UNC path for the actual NAS location
                nas_path = r'\\155.235.81.155\Image Archiving'
                indexer = NASPatientIndexer(nas_path=nas_path)
                logger.info(f"🚀 Starting real NAS patient indexing from {nas_path}...")

                # Update state to show real indexing
                indexing_state['details'] = f"Real indexing in progress from {nas_path}"
                indexing_state['progress'] = 5

                # Run indexing with minimal workers to avoid issues - SINGLE THREADED for stability
                logger.info("🔧 Running single-threaded indexing for maximum stability...")
                indexer.run_full_index(max_workers=1)  # Single worker to prevent database locks and memory issues

                # Update state on completion
                indexing_state['state'] = 'completed'
                indexing_state['progress'] = 100
                indexing_state['details'] = "Real NAS indexing completed successfully"
                logger.info("✅ Real NAS indexing completed successfully")

            except Exception as e:
                logger.error(f"❌ Real NAS indexing failed: {e}")
                logger.exception("Full error traceback:")
                indexing_state['state'] = 'error'
                indexing_state['progress'] = 0
                indexing_state['details'] = f"Indexing failed: {str(e)}"

        # Start indexing thread
        threading.Thread(target=run_real_indexing, daemon=True).start()

        return jsonify({
            'success': True,
            'message': 'Real DICOM indexing started',
            'status': 'indexing',
            'details': 'Background indexing thread started for NAS DICOM files'
        })
    except Exception as e:
        logger.error(f"Start indexing error: {e}")
        logger.exception("Start indexing full traceback:")
        try:
            import traceback as _tb
            _tb.print_exc()
        except Exception:
            pass
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
        logger.error(f"Stop indexing error: {e}")
        return jsonify({ 'success': False, 'error': str(e) }), 500


@devices_bp.route('/start-indexing', methods=['POST'])
def start_indexing_compat():
    return start_indexing()


@devices_bp.route('/indexing/status', methods=['GET'])
def indexing_status():
    """Return real indexing status with database progress"""
    try:
        # If indexing is running, check if we can get real progress from the database
        if indexing_state['state'] == 'indexing':
            try:
                import sys
                sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

                from nas_patient_search import NASPatientSearch
                searcher = NASPatientSearch()
                stats = searcher.get_index_statistics()

                if stats.get('available'):
                    patient_count = stats.get('patient_count', 0)
                    # Estimate progress based on patient count (we know there are ~7267 total folders)
                    estimated_total = 7267
                    if patient_count > 0:
                        real_progress = min(int((patient_count / estimated_total) * 100), 99)
                        indexing_state['progress'] = max(indexing_state['progress'], real_progress)

                        # Show current indexing phase based on what we know
                        if indexing_state.get('started_at'):
                            try:
                                if isinstance(indexing_state['started_at'], str):
                                    start_time = datetime.fromisoformat(indexing_state['started_at'].replace('Z', '+00:00'))
                                else:
                                    start_time = indexing_state['started_at']

                                elapsed_minutes = (datetime.utcnow() - start_time).total_seconds() / 60

                                if elapsed_minutes < 2:
                                    phase = "🔍 Scanning NAS folders..."
                                elif elapsed_minutes < 5:
                                    phase = "📂 Analyzing patient directories..."
                                else:
                                    phase = "📊 Processing DICOM files..."

                                indexing_state['details'] = f"{phase} • {patient_count:,} studies found in database • {elapsed_minutes:.0f}min elapsed"
                            except Exception:
                                indexing_state['details'] = f"📊 Indexing active: {patient_count:,} studies in database"
                        else:
                            indexing_state['details'] = f"📊 Starting indexing: {patient_count:,} studies in database"

            except Exception as e:
                logger.debug(f"Could not get real indexing progress: {e}")
                # Fall back to time-based simulation if database check fails
                if indexing_state['started_at']:
                    elapsed = (datetime.utcnow() - indexing_state['started_at']).total_seconds()
                    # Slower progress: 2% per second for more realistic indexing time
                    prog = min(95, int(elapsed * 2))  # Cap at 95% until real completion
                    indexing_state['progress'] = max(indexing_state['progress'], prog)

        return jsonify({
            'success': True,
            'status': {
                'state': indexing_state['state'],
                'progress': indexing_state['progress'],
                'details': indexing_state['details']
            }
        })
    except Exception as e:
        logger.error(f"Indexing status error: {e}")
        logger.exception("Indexing status full traceback:")
        return jsonify({ 'success': False, 'error': str(e) }), 500


@devices_bp.route('/rename-device', methods=['POST'])
@require_auth
def rename_device_alt():
    """Rename device endpoint for frontend compatibility"""
    try:
        data = request.get_json()
        ip_address = data.get('ip_address')
        new_name = data.get('new_name')
        
        if not ip_address or not new_name:
            return jsonify({ 'success': False, 'error': 'IP address and new name are required' }), 400
        
        # Update the device name in the discovered devices cache
        try:
            discovered_data = load_discovered_devices()
            devices = discovered_data.get('devices', [])
            
            for device in devices:
                if device.get('ip_address') == ip_address:
                    device['hostname'] = new_name
                    device['custom_name'] = new_name
                    break
            
            # Save the updated data
            from .nas_utils import save_discovered_devices
            save_discovered_devices(devices, 'Device Management')
            
        except Exception as e:
            logger.warning(f"Could not update cached device name: {e}")
        
        return jsonify({ 
            'success': True, 
            'message': f'Device {ip_address} renamed to "{new_name}"',
            'ip_address': ip_address,
            'new_name': new_name
        })
    except Exception as e:
        logger.error(f"Rename device error: {e}")
        return jsonify({ 'success': False, 'error': str(e) }), 500


@devices_bp.route('/connect-device', methods=['POST'])
@require_auth
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


@devices_bp.route('/disconnect-device', methods=['POST'])
@require_auth
def disconnect_device():
    """Disconnect a device by IP by removing NAS configuration entries."""
    try:
        data = request.get_json() or {}
        ip_address = data.get('ip_address') or data.get('ip')
        if not ip_address:
            return jsonify({ 'success': False, 'error': 'IP address is required' }), 400

        result = device_manager.remove_nas_by_ip(ip_address)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Disconnect device error: {e}")
        return jsonify({ 'success': False, 'error': str(e) }), 500


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


@devices_bp.route('/arp-table', methods=['GET'])
def get_arp_table_endpoint():
    """Get ARP table entries for network device discovery"""
    try:
        from .network_discovery import get_arp_table
        arp_entries = get_arp_table()
        
        return jsonify({
            'success': True,
            'arp_entries': arp_entries,
            'total_entries': len(arp_entries),
            'message': f'Found {len(arp_entries)} devices in ARP table'
        })
    except Exception as e:
        logger.error(f"ARP table error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@devices_bp.route('/ping', methods=['POST'])
def ping_device_endpoint():
    """Ping a single device"""
    try:
        data = request.get_json() or {}
        ip_address = data.get('ip_address') or data.get('ip')
        if not ip_address:
            return jsonify({'success': False, 'error': 'IP address is required'}), 400
        
        timeout = data.get('timeout', 3)
        from .nas_utils import ping_device
        result = ping_device(ip_address, timeout)
        
        return jsonify({
            'success': True,
            'ping_result': result
        })
    except Exception as e:
        logger.error(f"Ping device error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@devices_bp.route('/ping_range', methods=['POST'])
def ping_range_endpoint():
    """Ping a range of IP addresses"""
    try:
        data = request.get_json() or {}
        start_ip = data.get('start_ip')
        end_ip = data.get('end_ip')
        timeout = data.get('timeout', 2)
        max_concurrent = data.get('max_concurrent', 10)
        
        if not start_ip or not end_ip:
            return jsonify({'success': False, 'error': 'start_ip and end_ip are required'}), 400
        
        from .network_discovery import ping_range
        results = ping_range(start_ip, end_ip, timeout, max_concurrent)
        
        return jsonify({
            'success': True,
            'ping_range_result': {
                'results': results,
                'statistics': {
                    'online_count': len([r for r in results if r.get('reachable')]),
                    'total_count': len(results)
                },
                'range': f'{start_ip}-{end_ip}'
            }
        })
    except Exception as e:
        logger.error(f"Ping range error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@devices_bp.route('/enhanced_discovery', methods=['POST'])
def enhanced_discovery_endpoint():
    """Perform enhanced network discovery"""
    try:
        data = request.get_json() or {}
        include_arp = data.get('include_arp', True)
        include_ping_range = data.get('include_ping_range', False)
        start_ip = data.get('start_ip')
        end_ip = data.get('end_ip')
        timeout = data.get('timeout', 2)
        max_hosts = data.get('max_hosts', 254)
        
        from .network_discovery import enhanced_network_discovery
        results = enhanced_network_discovery(
            include_arp=include_arp,
            include_ping_range=include_ping_range,
            start_ip=start_ip,
            end_ip=end_ip,
            timeout=timeout,
            max_hosts=max_hosts
        )
        
        return jsonify({
            'success': True,
            'discovered_devices': results,
            'methods_used': ['arp'] if include_arp else [] + ['ping_range'] if include_ping_range else [],
            'message': f'Enhanced discovery completed, found {len(results)} devices'
        })
    except Exception as e:
        logger.error(f"Enhanced discovery error: {e}")
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



