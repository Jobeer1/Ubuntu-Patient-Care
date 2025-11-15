"""
NAS Discovery and Connection API Endpoints

Provides REST API for:
- Discovering NAS devices on network
- Enumerating shares on discovered devices
- Scanning shares for databases
- Testing connections with credentials
- Storing discovered connections
"""

from flask import Blueprint, request, jsonify
import logging
from services.nas_discovery import nas_manager, DatabaseTypeDetector
import threading

logger = logging.getLogger(__name__)

nas_discovery_bp = Blueprint('nas_discovery', __name__, url_prefix='/api/nas/discovery')


@nas_discovery_bp.route('/scan-network', methods=['POST'])
def scan_network():
    """
    Scan network for NAS devices
    
    Request: {
        "subnet": "155.235.81",  # optional
        "timeout": 2  # optional
    }
    
    Response: {
        "success": bool,
        "scanning": bool,  # if True, continue polling /status
        "devices": [...]
    }
    """
    try:
        data = request.get_json() or {}
        subnet = data.get('subnet', '155.235.81')
        timeout = data.get('timeout', 2)
        
        logger.info(f"Starting network scan of {subnet}.* subnet")
        
        # Run scan in background thread
        thread = threading.Thread(
            target=nas_manager.discovery.discover_devices_on_network,
            args=(subnet, timeout),
            daemon=True
        )
        thread.start()
        
        return jsonify({
            'success': True,
            'scanning': True,
            'message': f'Scanning {subnet}.* subnet for NAS devices...',
            'subnet': subnet
        })
    
    except Exception as e:
        logger.error(f"Error starting network scan: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@nas_discovery_bp.route('/discovered-devices', methods=['GET'])
def get_discovered_devices():
    """Get list of discovered NAS devices"""
    try:
        devices = list(nas_manager.discovery.discovered_devices.values())
        
        return jsonify({
            'success': True,
            'count': len(devices),
            'devices': devices
        })
    
    except Exception as e:
        logger.error(f"Error getting discovered devices: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@nas_discovery_bp.route('/enumerate-shares', methods=['POST'])
def enumerate_shares():
    """
    Enumerate shares on a NAS device
    
    Request: {
        "nas_host": "155.235.81.49",
        "username": "optional",
        "password": "optional"
    }
    
    Response: {
        "success": bool,
        "shares": [...]
    }
    """
    try:
        data = request.get_json()
        nas_host = data.get('nas_host')
        username = data.get('username')
        password = data.get('password')
        
        if not nas_host:
            return jsonify({
                'success': False,
                'error': 'nas_host is required'
            }), 400
        
        logger.info(f"Enumerating shares on {nas_host}")
        shares = nas_manager.discovery.enumerate_shares(nas_host, username, password)
        
        return jsonify({
            'success': True,
            'nas_host': nas_host,
            'count': len(shares),
            'shares': shares
        })
    
    except Exception as e:
        logger.error(f"Error enumerating shares: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@nas_discovery_bp.route('/scan-share', methods=['POST'])
def scan_share():
    """
    Scan a share for databases
    
    Request: {
        "share_path": "\\\\192.168.1.1\\DICOM",
        "username": "optional",
        "password": "optional",
        "max_depth": 3
    }
    
    Response: {
        "success": bool,
        "databases": [...]
    }
    """
    try:
        data = request.get_json()
        share_path = data.get('share_path')
        username = data.get('username')
        password = data.get('password')
        max_depth = data.get('max_depth', 3)
        
        if not share_path:
            return jsonify({
                'success': False,
                'error': 'share_path is required'
            }), 400
        
        logger.info(f"Scanning share: {share_path}")
        databases = nas_manager.discovery.scan_share_for_databases(
            share_path, username, password, max_depth
        )
        
        return jsonify({
            'success': True,
            'share_path': share_path,
            'count': len(databases),
            'databases': databases
        })
    
    except Exception as e:
        logger.error(f"Error scanning share: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@nas_discovery_bp.route('/detect-database-type', methods=['POST'])
def detect_database_type():
    """
    Detect database type in a path
    
    Request: {
        "path": "\\\\192.168.1.1\\DICOM\\Database1"
    }
    
    Response: {
        "success": bool,
        "database_type": "DICOM_STORAGE|DATABASE|MIXED|UNKNOWN",
        "details": {...}
    }
    """
    try:
        data = request.get_json()
        path = data.get('path')
        
        if not path:
            return jsonify({
                'success': False,
                'error': 'path is required'
            }), 400
        
        detector = DatabaseTypeDetector()
        result = detector.detect_database_type(path)
        
        return jsonify({
            'success': True,
            'path': path,
            'database_type': result['type'],
            'details': result
        })
    
    except Exception as e:
        logger.error(f"Error detecting database type: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@nas_discovery_bp.route('/test-connection', methods=['POST'])
def test_connection():
    """
    Test connection to a NAS share
    
    Request: {
        "nas_host": "192.168.1.1",
        "share_name": "DICOM",
        "username": "optional",
        "password": "optional"
    }
    
    Response: {
        "success": bool,
        "connected": bool,
        "message": "..."
    }
    """
    try:
        data = request.get_json()
        nas_host = data.get('nas_host')
        share_name = data.get('share_name')
        username = data.get('username')
        password = data.get('password')
        
        if not nas_host or not share_name:
            return jsonify({
                'success': False,
                'error': 'nas_host and share_name are required'
            }), 400
        
        logger.info(f"Testing connection to \\\\{nas_host}\\{share_name}")
        connected, message = nas_manager.test_connection(nas_host, share_name, username, password)
        
        return jsonify({
            'success': True,
            'connected': connected,
            'message': message,
            'nas_host': nas_host,
            'share_name': share_name
        })
    
    except Exception as e:
        logger.error(f"Error testing connection: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@nas_discovery_bp.route('/save-connection', methods=['POST'])
def save_connection():
    """
    Save a discovered connection for later use
    
    Request: {
        "nas_host": "192.168.1.1",
        "share_name": "DICOM",
        "username": "optional",
        "password": "optional",
        "database_type": "optional"
    }
    
    Response: {
        "success": bool,
        "message": "..."
    }
    """
    try:
        data = request.get_json()
        nas_host = data.get('nas_host')
        share_name = data.get('share_name')
        username = data.get('username')
        password = data.get('password')
        database_type = data.get('database_type')
        
        if not nas_host or not share_name:
            return jsonify({
                'success': False,
                'error': 'nas_host and share_name are required'
            }), 400
        
        logger.info(f"Saving connection to \\\\{nas_host}\\{share_name}")
        saved = nas_manager.save_connection(nas_host, share_name, username, password, database_type)
        
        if saved:
            return jsonify({
                'success': True,
                'message': f'Saved connection to {nas_host}\\{share_name}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save connection'
            }), 500
    
    except Exception as e:
        logger.error(f"Error saving connection: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@nas_discovery_bp.route('/stored-connections', methods=['GET'])
def get_stored_connections():
    """Get list of stored connections"""
    try:
        connections = nas_manager.current_connections
        
        return jsonify({
            'success': True,
            'count': len(connections),
            'connections': list(connections.values())
        })
    
    except Exception as e:
        logger.error(f"Error getting stored connections: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
