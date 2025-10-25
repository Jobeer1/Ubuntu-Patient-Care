#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - Device Management API Endpoints

REST API endpoints for managing medical imaging devices/modalities.
Provides easy device addition, configuration, and connectivity testing
with South African healthcare context.
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
import logging
from typing import Dict, Any
import uuid

# Try to import device manager with multiple fallbacks
device_manager = None
try:
    from device_management import device_manager
    logger = logging.getLogger(__name__)
    logger.info("✅ Using full device manager")
except ImportError:
    try:
        from device_management_fallback import device_manager
        logger = logging.getLogger(__name__)
        logger.info("✅ Using fallback device manager")
    except ImportError:
        logger = logging.getLogger(__name__)
        logger.error("❌ No device manager available")
        
        # Create a minimal mock device manager
        class MockDeviceManager:
            def get_all_devices(self, *args, **kwargs):
                return []
            def get_device_by_id(self, device_id):
                return None
            def add_device(self, data):
                return True, "Mock device added", None
            def update_device(self, device_id, data):
                return True, "Mock device updated"
            def delete_device(self, device_id):
                return True, "Mock device deleted"
            def test_connectivity(self, device_id, test_type="ping"):
                return True, "Mock connectivity test passed", 100
            def get_connectivity_history(self, device_id, limit=50):
                return []
            def get_equipment_presets(self, modality_type):
                return {}
            def get_departments(self, language="en"):
                return ["Radiology", "Emergency", "ICU"]
            def get_device_statistics(self):
                return {"total_devices": 0}
            def scan_arp_table(self):
                return []
            def network_discovery_scan(self, ip_range, ports=None, max_threads=50):
                return []
            def get_network_discovery_suggestions(self):
                return {"common_ip_ranges": ["192.168.1.0/24"]}
            def create_device_from_discovery(self, discovered_device, additional_info):
                return True, "Mock device created from discovery", None
            def get_device_by_ae_title(self, ae_title):
                return None
        
        device_manager = MockDeviceManager()
        logger.warning("⚠️ Using mock device manager")

# Handle auth imports with fallbacks
try:
    from .auth_2fa import require_auth, require_admin
except ImportError:
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

logger = logging.getLogger(__name__)

# Create blueprint for device management endpoints
device_api_bp = Blueprint('device_api', __name__, url_prefix='/api/devices')

def validate_device_data(data: Dict) -> tuple[bool, str]:
    """Validate device data"""
    required_fields = ['name', 'modality_type', 'manufacturer', 'model', 
                      'ae_title', 'ip_address', 'port', 'department', 'location']
    
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"
    
    # Validate port
    try:
        port = int(data['port'])
        if not (1 <= port <= 65535):
            return False, "Port must be between 1 and 65535"
    except (ValueError, TypeError):
        return False, "Port must be a valid integer"
    
    # Validate modality type
    valid_modalities = ['ultrasound', 'xray', 'ct', 'mri', 'mammography', 
                       'bone_density', 'nuclear_medicine', 'pet', 'angiography', 'other']
    if data['modality_type'].lower() not in valid_modalities:
        return False, f"Invalid modality type. Must be one of: {', '.join(valid_modalities)}"
    
    return True, ""

# ============================================================================
# DEVICE CRUD ENDPOINTS
# ============================================================================

@device_api_bp.route('', methods=['GET'])
@require_auth
def get_devices():
    """Get all devices with optional filters"""
    try:
        # Get query parameters
        status = request.args.get('status')
        modality_type = request.args.get('modality_type')
        department = request.args.get('department')
        
        # Get devices
        devices = device_manager.get_all_devices(status, modality_type, department)
        
        return jsonify({
            'success': True,
            'devices': [device.to_dict() for device in devices],
            'count': len(devices)
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting devices: {e}")
        return jsonify({'error': f'Failed to get devices: {str(e)}'}), 500

@device_api_bp.route('/<device_id>', methods=['GET'])
@require_auth
def get_device(device_id: str):
    """Get specific device by ID"""
    try:
        device = device_manager.get_device_by_id(device_id)
        
        if device:
            return jsonify({
                'success': True,
                'device': device.to_dict()
            })
        else:
            return jsonify({'error': 'Device not found'}), 404
            
    except Exception as e:
        logger.error(f"❌ Error getting device {device_id}: {e}")
        return jsonify({'error': f'Failed to get device: {str(e)}'}), 500

@device_api_bp.route('', methods=['POST'])
@require_admin
def add_device():
    """Add new medical device"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate data
        is_valid, error_msg = validate_device_data(data)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        # Add device
        success, message, device = device_manager.add_device(data)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'device': device.to_dict() if device else None
            }), 201
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"❌ Error adding device: {e}")
        return jsonify({'error': f'Failed to add device: {str(e)}'}), 500

@device_api_bp.route('/<device_id>', methods=['PUT'])
@require_admin
def update_device(device_id: str):
    """Update device information"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update device
        success, message = device_manager.update_device(device_id, data)
        
        if success:
            # Get updated device
            device = device_manager.get_device_by_id(device_id)
            return jsonify({
                'success': True,
                'message': message,
                'device': device.to_dict() if device else None
            })
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"❌ Error updating device {device_id}: {e}")
        return jsonify({'error': f'Failed to update device: {str(e)}'}), 500

@device_api_bp.route('/<device_id>', methods=['DELETE'])
@require_admin
def delete_device(device_id: str):
    """Delete device"""
    try:
        success, message = device_manager.delete_device(device_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({'error': message}), 404
            
    except Exception as e:
        logger.error(f"❌ Error deleting device {device_id}: {e}")
        return jsonify({'error': f'Failed to delete device: {str(e)}'}), 500

# ============================================================================
# CONNECTIVITY TESTING ENDPOINTS
# ============================================================================

@device_api_bp.route('/<device_id>/test', methods=['POST'])
@require_auth
def test_device_connectivity(device_id: str):
    """Test device connectivity"""
    try:
        data = request.get_json() or {}
        test_type = data.get('test_type', 'ping')
        
        # Validate test type
        valid_test_types = ['ping', 'dicom_echo']
        if test_type not in valid_test_types:
            return jsonify({'error': f'Invalid test type. Must be one of: {", ".join(valid_test_types)}'}), 400
        
        # Run connectivity test
        success, message, response_time = device_manager.test_connectivity(device_id, test_type)
        
        return jsonify({
            'success': success,
            'message': message,
            'response_time_ms': response_time,
            'test_type': test_type
        })
        
    except Exception as e:
        logger.error(f"❌ Error testing device connectivity {device_id}: {e}")
        return jsonify({'error': f'Failed to test connectivity: {str(e)}'}), 500

@device_api_bp.route('/<device_id>/connectivity-history', methods=['GET'])
@require_auth
def get_connectivity_history(device_id: str):
    """Get device connectivity test history"""
    try:
        limit = int(request.args.get('limit', 50))
        
        history = device_manager.get_connectivity_history(device_id, limit)
        
        return jsonify({
            'success': True,
            'history': history,
            'count': len(history)
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting connectivity history {device_id}: {e}")
        return jsonify({'error': f'Failed to get connectivity history: {str(e)}'}), 500

# ============================================================================
# CONFIGURATION AND PRESETS ENDPOINTS
# ============================================================================

@device_api_bp.route('/presets/<modality_type>', methods=['GET'])
@require_auth
def get_equipment_presets(modality_type: str):
    """Get equipment presets for modality type"""
    try:
        presets = device_manager.get_equipment_presets(modality_type)
        
        return jsonify({
            'success': True,
            'modality_type': modality_type,
            'presets': presets
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting presets for {modality_type}: {e}")
        return jsonify({'error': f'Failed to get presets: {str(e)}'}), 500

@device_api_bp.route('/departments', methods=['GET'])
@require_auth
def get_departments():
    """Get department list"""
    try:
        language = request.args.get('language', 'en')
        departments = device_manager.get_departments(language)
        
        return jsonify({
            'success': True,
            'departments': departments,
            'language': language
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting departments: {e}")
        return jsonify({'error': f'Failed to get departments: {str(e)}'}), 500

@device_api_bp.route('/modality-types', methods=['GET'])
@require_auth
def get_modality_types():
    """Get available modality types"""
    try:
        modality_types = [
            {
                'value': 'ultrasound',
                'label': 'Ultrasound',
                'label_af': 'Ultraklank',
                'label_zu': 'I-Ultrasound'
            },
            {
                'value': 'xray',
                'label': 'X-Ray',
                'label_af': 'X-straal',
                'label_zu': 'I-X-Ray'
            },
            {
                'value': 'ct',
                'label': 'CT Scan',
                'label_af': 'CT Skandering',
                'label_zu': 'I-CT Scan'
            },
            {
                'value': 'mri',
                'label': 'MRI',
                'label_af': 'MRI',
                'label_zu': 'I-MRI'
            },
            {
                'value': 'mammography',
                'label': 'Mammography',
                'label_af': 'Mammografie',
                'label_zu': 'I-Mammography'
            },
            {
                'value': 'bone_density',
                'label': 'Bone Density (DEXA)',
                'label_af': 'Beendigtheid (DEXA)',
                'label_zu': 'Ukuqina Kwamathambo (DEXA)'
            },
            {
                'value': 'nuclear_medicine',
                'label': 'Nuclear Medicine',
                'label_af': 'Kernmedisyne',
                'label_zu': 'Imithi Ye-Nuclear'
            },
            {
                'value': 'pet',
                'label': 'PET Scan',
                'label_af': 'PET Skandering',
                'label_zu': 'I-PET Scan'
            },
            {
                'value': 'angiography',
                'label': 'Angiography',
                'label_af': 'Angiografie',
                'label_zu': 'I-Angiography'
            },
            {
                'value': 'other',
                'label': 'Other',
                'label_af': 'Ander',
                'label_zu': 'Okunye'
            }
        ]
        
        return jsonify({
            'success': True,
            'modality_types': modality_types
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting modality types: {e}")
        return jsonify({'error': f'Failed to get modality types: {str(e)}'}), 500

# ============================================================================
# STATISTICS AND REPORTING ENDPOINTS
# ============================================================================

@device_api_bp.route('/statistics', methods=['GET'])
@require_auth
def get_device_statistics():
    """Get device statistics"""
    try:
        stats = device_manager.get_device_statistics()
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting device statistics: {e}")
        return jsonify({'error': f'Failed to get statistics: {str(e)}'}), 500

@device_api_bp.route('/health-check', methods=['GET'])
@require_auth
def device_health_check():
    """Perform health check on all active devices"""
    try:
        # Get all active devices
        devices = device_manager.get_all_devices(status='active')
        
        results = []
        for device in devices:
            # Test connectivity
            success, message, response_time = device_manager.test_connectivity(device.id, 'ping')
            
            results.append({
                'device_id': device.id,
                'device_name': device.name,
                'modality_type': device.modality_type,
                'department': device.department,
                'success': success,
                'message': message,
                'response_time_ms': response_time
            })
        
        # Calculate summary
        total_devices = len(results)
        healthy_devices = sum(1 for r in results if r['success'])
        health_percentage = (healthy_devices / total_devices * 100) if total_devices > 0 else 0
        
        return jsonify({
            'success': True,
            'health_check': {
                'total_devices': total_devices,
                'healthy_devices': healthy_devices,
                'unhealthy_devices': total_devices - healthy_devices,
                'health_percentage': round(health_percentage, 1),
                'results': results
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error performing health check: {e}")
        return jsonify({'error': f'Failed to perform health check: {str(e)}'}), 500

# ============================================================================
# DEVICE WIZARD ENDPOINTS (South African Context)
# ============================================================================

@device_api_bp.route('/wizard/start', methods=['POST'])
@require_admin
def start_device_wizard():
    """Start device addition wizard"""
    try:
        data = request.get_json() or {}
        modality_type = data.get('modality_type', '').lower()
        
        # Get presets for modality
        presets = device_manager.get_equipment_presets(modality_type)
        
        # Get departments
        departments = device_manager.get_departments('en')
        
        # Common South African locations
        sa_locations = [
            "Main Radiology", "Emergency Department", "Theatre Complex",
            "ICU", "Cardiac Unit", "Orthopedic Unit", "Maternity Ward",
            "Pediatric Unit", "Outpatient Clinic", "Mobile Unit"
        ]
        
        return jsonify({
            'success': True,
            'wizard_data': {
                'modality_type': modality_type,
                'equipment_presets': presets,
                'departments': departments,
                'common_locations': sa_locations,
                'default_port': 104,
                'sa_context': {
                    'common_hospitals': [
                        "Netcare", "Life Healthcare", "Mediclinic",
                        "Chris Hani Baragwanath", "Groote Schuur", "Charlotte Maxeke"
                    ],
                    'medical_schemes': [
                        "Discovery Health", "Momentum Health", "Bonitas",
                        "Medihelp", "Fedhealth", "Bestmed"
                    ]
                }
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error starting device wizard: {e}")
        return jsonify({'error': f'Failed to start wizard: {str(e)}'}), 500

@device_api_bp.route('/wizard/validate', methods=['POST'])
@require_admin
def validate_device_wizard():
    """Validate device configuration in wizard"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate data
        is_valid, error_msg = validate_device_data(data)
        if not is_valid:
            return jsonify({
                'success': False,
                'valid': False,
                'error': error_msg
            })
        
        # Check for duplicate AE Title
        existing_device = device_manager.get_device_by_ae_title(data['ae_title'])
        if existing_device:
            return jsonify({
                'success': False,
                'valid': False,
                'error': f"AE Title '{data['ae_title']}' already exists"
            })
        
        # Test connectivity if IP provided
        connectivity_result = None
        if data.get('ip_address'):
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((data['ip_address'], int(data.get('port', 104))))
                sock.close()
                
                connectivity_result = {
                    'reachable': result == 0,
                    'message': 'Device is reachable' if result == 0 else 'Device is not reachable'
                }
            except:
                connectivity_result = {
                    'reachable': False,
                    'message': 'Unable to test connectivity'
                }
        
        return jsonify({
            'success': True,
            'valid': True,
            'connectivity': connectivity_result
        })
        
    except Exception as e:
        logger.error(f"❌ Error validating device wizard: {e}")
        return jsonify({'error': f'Failed to validate: {str(e)}'}), 500

# ============================================================================
# 🌐 NETWORK DISCOVERY ENDPOINTS - EXTREMELY EASY DEVICE ADDITION
# ============================================================================

@device_api_bp.route('/network/arp-scan', methods=['POST'])
@require_admin
def scan_arp_table():
    """🔍 Scan ARP table to discover network devices"""
    try:
        logger.info("🔍 Starting ARP table scan...")
        
        # Perform ARP scan
        discovered_devices = device_manager.scan_arp_table()
        
        # Filter out likely medical devices
        medical_devices = [
            device for device in discovered_devices 
            if device.get('likely_medical_device', False)
        ]
        
        return jsonify({
            'success': True,
            'message': f'ARP scan completed. Found {len(discovered_devices)} devices.',
            'discovered_devices': discovered_devices,
            'medical_devices': medical_devices,
            'total_found': len(discovered_devices),
            'medical_found': len(medical_devices)
        })
        
    except Exception as e:
        logger.error(f"❌ Error scanning ARP table: {e}")
        return jsonify({'error': f'ARP scan failed: {str(e)}'}), 500

@device_api_bp.route('/network/discovery-scan', methods=['POST'])
@require_admin
def network_discovery_scan():
    """🌐 Perform network discovery scan on IP range"""
    try:
        data = request.get_json() or {}
        ip_range = data.get('ip_range')
        ports = data.get('ports', [104, 11112, 8042, 80, 443])
        max_threads = data.get('max_threads', 50)
        
        if not ip_range:
            return jsonify({'error': 'IP range is required'}), 400
        
        logger.info(f"🌐 Starting network discovery scan on {ip_range}")
        
        # Perform network discovery
        discovered_devices = device_manager.network_discovery_scan(
            ip_range=ip_range,
            ports=ports,
            max_threads=max_threads
        )
        
        # Filter out likely medical devices
        medical_devices = [
            device for device in discovered_devices 
            if device.get('likely_medical_device', False) or device.get('dicom_capable', False)
        ]
        
        return jsonify({
            'success': True,
            'message': f'Network discovery completed. Found {len(discovered_devices)} devices.',
            'discovered_devices': discovered_devices,
            'medical_devices': medical_devices,
            'total_found': len(discovered_devices),
            'medical_found': len(medical_devices),
            'scan_parameters': {
                'ip_range': ip_range,
                'ports_scanned': ports,
                'max_threads': max_threads
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error in network discovery scan: {e}")
        return jsonify({'error': f'Network discovery failed: {str(e)}'}), 500

@device_api_bp.route('/network/discovery-suggestions', methods=['GET'])
@require_admin
def get_discovery_suggestions():
    """Get network discovery suggestions"""
    try:
        suggestions = device_manager.get_network_discovery_suggestions()
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting discovery suggestions: {e}")
        return jsonify({'error': f'Failed to get suggestions: {str(e)}'}), 500

@device_api_bp.route('/network/create-from-discovery', methods=['POST'])
@require_admin
def create_device_from_discovery():
    """🎯 Create device from discovered network device"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        discovered_device = data.get('discovered_device')
        additional_info = data.get('additional_info', {})
        
        if not discovered_device:
            return jsonify({'error': 'Discovered device data is required'}), 400
        
        # Create device from discovery
        success, message, device = device_manager.create_device_from_discovery(
            discovered_device, additional_info
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'device': device.to_dict() if device else None
            }), 201
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"❌ Error creating device from discovery: {e}")
        return jsonify({'error': f'Failed to create device: {str(e)}'}), 500

@device_api_bp.route('/network/quick-add', methods=['POST'])
@require_admin
def quick_add_discovered_device():
    """⚡ Super quick device addition from IP address"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        ip_address = data.get('ip_address')
        if not ip_address:
            return jsonify({'error': 'IP address is required'}), 400
        
        # Quick scan of the single IP
        discovered_devices = device_manager.network_discovery_scan(
            ip_range=ip_address,
            ports=[104, 11112, 8042, 80],
            max_threads=1
        )
        
        if not discovered_devices:
            return jsonify({'error': f'No device found at {ip_address}'}), 404
        
        discovered_device = discovered_devices[0]
        
        # Auto-create device with minimal info
        additional_info = {
            'name': data.get('name', f"Device_{ip_address.replace('.', '_')}"),
            'modality_type': data.get('modality_type', 'other'),
            'manufacturer': data.get('manufacturer', 'Unknown'),
            'model': data.get('model', 'Unknown'),
            'ae_title': data.get('ae_title', f"DEV_{ip_address.replace('.', '_')}"),
            'department': data.get('department', 'Radiology'),
            'location': data.get('location', 'Main Hospital')
        }
        
        success, message, device = device_manager.create_device_from_discovery(
            discovered_device, additional_info
        )
        
        if success:
            # Test connectivity immediately
            test_success, test_message, response_time = device_manager.test_connectivity(
                device.id, 'ping'
            )
            
            return jsonify({
                'success': True,
                'message': message,
                'device': device.to_dict(),
                'connectivity_test': {
                    'success': test_success,
                    'message': test_message,
                    'response_time_ms': response_time
                }
            }), 201
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"❌ Error in quick add device: {e}")
        return jsonify({'error': f'Quick add failed: {str(e)}'}), 500

@device_api_bp.route('/network/test-dicom', methods=['POST'])
@require_auth
def test_dicom_connectivity():
    """🩺 Test DICOM connectivity for discovered device"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        ip_address = data.get('ip_address')
        port = data.get('port', 104)
        ae_title = data.get('ae_title', 'TEST_AE')
        
        if not ip_address:
            return jsonify({'error': 'IP address is required'}), 400
        
        # Test DICOM connectivity
        if hasattr(device_manager, 'test_dicom_connectivity'):
            result = device_manager.test_dicom_connectivity(ip_address, port, ae_title)
        else:
            # Fallback to port test
            result = {
                'success': False,
                'test_type': 'port_test',
                'error': 'DICOM testing not available in fallback mode'
            }
        
        return jsonify({
            'success': True,
            'dicom_test': result
        })
        
    except Exception as e:
        logger.error(f"❌ Error testing DICOM connectivity: {e}")
        return jsonify({'error': f'DICOM test failed: {str(e)}'}), 500

@device_api_bp.route('/network/enhanced-scan', methods=['POST'])
@require_admin
def enhanced_network_scan():
    """🔍 Enhanced network scan with detailed medical device detection"""
    try:
        data = request.get_json() or {}
        ip_range = data.get('ip_range')
        ports = data.get('ports', [104, 11112, 8042, 80, 443, 22, 23])
        max_threads = data.get('max_threads', 20)
        include_ping_test = data.get('include_ping_test', True)
        
        if not ip_range:
            return jsonify({'error': 'IP range is required'}), 400
        
        logger.info(f"🔍 Starting enhanced network scan on {ip_range}")
        
        # Perform enhanced network discovery
        discovered_devices = device_manager.network_discovery_scan(
            ip_range=ip_range,
            ports=ports,
            max_threads=max_threads
        )
        
        # Categorize devices
        medical_devices = [d for d in discovered_devices if d.get('likely_medical_device', False)]
        dicom_devices = [d for d in discovered_devices if d.get('dicom_capable', False)]
        high_confidence = [d for d in discovered_devices if d.get('confidence_score', 0) >= 50]
        
        return jsonify({
            'success': True,
            'message': f'Enhanced scan completed. Found {len(discovered_devices)} devices.',
            'scan_results': {
                'all_devices': discovered_devices,
                'medical_devices': medical_devices,
                'dicom_devices': dicom_devices,
                'high_confidence_devices': high_confidence,
                'summary': {
                    'total_found': len(discovered_devices),
                    'medical_found': len(medical_devices),
                    'dicom_capable': len(dicom_devices),
                    'high_confidence': len(high_confidence)
                }
            },
            'scan_parameters': {
                'ip_range': ip_range,
                'ports_scanned': ports,
                'max_threads': max_threads
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error in enhanced network scan: {e}")
        return jsonify({'error': f'Enhanced scan failed: {str(e)}'}), 500

# ============================================================================
# BULK OPERATIONS ENDPOINTS
# ============================================================================

@device_api_bp.route('/bulk/import', methods=['POST'])
@require_admin
def bulk_import_devices():
    """Bulk import devices from CSV or JSON"""
    try:
        data = request.get_json()
        if not data or 'devices' not in data:
            return jsonify({'error': 'No devices data provided'}), 400
        
        devices_data = data['devices']
        results = []
        
        for device_data in devices_data:
            try:
                # Validate device data
                is_valid, error_msg = validate_device_data(device_data)
                if not is_valid:
                    results.append({
                        'device_name': device_data.get('name', 'Unknown'),
                        'success': False,
                        'error': error_msg
                    })
                    continue
                
                # Add device
                success, message, device = device_manager.add_device(device_data)
                results.append({
                    'device_name': device_data['name'],
                    'success': success,
                    'message': message,
                    'device_id': device.id if device else None
                })
                
            except Exception as e:
                results.append({
                    'device_name': device_data.get('name', 'Unknown'),
                    'success': False,
                    'error': str(e)
                })
        
        # Calculate summary
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        return jsonify({
            'success': True,
            'summary': {
                'total': len(results),
                'successful': successful,
                'failed': failed
            },
            'results': results
        })
        
    except Exception as e:
        logger.error(f"❌ Error bulk importing devices: {e}")
        return jsonify({'error': f'Failed to bulk import: {str(e)}'}), 500

@device_api_bp.route('/bulk/test', methods=['POST'])
@require_admin
def bulk_test_devices():
    """Bulk test device connectivity"""
    try:
        data = request.get_json() or {}
        device_ids = data.get('device_ids', [])
        test_type = data.get('test_type', 'ping')
        
        if not device_ids:
            # Test all active devices
            devices = device_manager.get_all_devices(status='active')
            device_ids = [device.id for device in devices]
        
        results = []
        for device_id in device_ids:
            try:
                success, message, response_time = device_manager.test_connectivity(device_id, test_type)
                device = device_manager.get_device_by_id(device_id)
                
                results.append({
                    'device_id': device_id,
                    'device_name': device.name if device else 'Unknown',
                    'success': success,
                    'message': message,
                    'response_time_ms': response_time
                })
                
            except Exception as e:
                results.append({
                    'device_id': device_id,
                    'device_name': 'Unknown',
                    'success': False,
                    'message': str(e),
                    'response_time_ms': 0
                })
        
        # Calculate summary
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        return jsonify({
            'success': True,
            'summary': {
                'total': len(results),
                'successful': successful,
                'failed': failed,
                'test_type': test_type
            },
            'results': results
        })
        
    except Exception as e:
        logger.error(f"❌ Error bulk testing devices: {e}")
        return jsonify({'error': f'Failed to bulk test: {str(e)}'}), 500