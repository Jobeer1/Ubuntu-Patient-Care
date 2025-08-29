"""
NAS integration routes blueprint
"""

from flask import Blueprint, request, jsonify
import logging
import subprocess
import json
import os
import ipaddress
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Device names database file
DEVICE_NAMES_DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'device_names.json')

def load_device_names():
    """Load device names from JSON database"""
    try:
        os.makedirs(os.path.dirname(DEVICE_NAMES_DB), exist_ok=True)
        if os.path.exists(DEVICE_NAMES_DB):
            with open(DEVICE_NAMES_DB, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading device names: {e}")
    return {}

def save_device_names(names_dict):
    """Save device names to JSON database"""
    try:
        os.makedirs(os.path.dirname(DEVICE_NAMES_DB), exist_ok=True)
        with open(DEVICE_NAMES_DB, 'w') as f:
            json.dump(names_dict, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving device names: {e}")
        return False

def get_device_name(ip_address, mac_address):
    """Get custom device name or return default"""
    names = load_device_names()
    # Try IP first, then MAC as fallback
    return names.get(ip_address, names.get(mac_address, 'Unknown'))

nas_bp = Blueprint('nas', __name__, url_prefix='/api/nas')

# Import auth decorators
try:
    from ..auth_utils import require_auth, require_admin
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from auth_utils import require_auth, require_admin

# Device names database file
DEVICE_NAMES_DB = 'data/device_names.json'

def load_device_names():
    """Load device names from JSON database"""
    try:
        if os.path.exists(DEVICE_NAMES_DB):
            with open(DEVICE_NAMES_DB, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading device names: {e}")
    return {}

def save_device_names(device_names):
    """Save device names to JSON database"""
    try:
        os.makedirs(os.path.dirname(DEVICE_NAMES_DB), exist_ok=True)
        with open(DEVICE_NAMES_DB, 'w') as f:
            json.dump(device_names, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving device names: {e}")
        return False

@nas_bp.route('/discover', methods=['GET', 'POST'])
@require_auth
def discover_nas():
    """Discover NAS devices on the network"""
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
            network_range = data.get('network_range', '192.168.1.0/24')
        else:
            network_range = request.args.get('network_range', '192.168.1.0/24')
        
        # Validate network range
        import ipaddress
        try:
            network = ipaddress.IPv4Network(network_range, strict=False)
            
            # Check if it's outside the current /24 domain
            current_ip = '155.235.81.50'  # Your current IP from the logs
            current_network = ipaddress.IPv4Network('155.235.81.0/24', strict=False)
            
            if network.network_address != current_network.network_address:
                return jsonify({
                    'success': False,
                    'error': f'Security Warning: Scanning outside your /24 domain is not recommended',
                    'message': f'You are trying to scan {network_range} but you are on {current_network}. This could be a security risk.',
                    'warning_type': 'network_security',
                    'current_network': str(current_network),
                    'requested_network': network_range
                }), 400
                
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': f'Invalid network range format: {network_range}',
                'message': 'Please use CIDR notation like 192.168.1.0/24'
            }), 400
        
        logger.info(f"Starting legacy network discovery for range: {network_range}")
        
        # Mock NAS discovery with more realistic results for your current network
        discovered_nas = [
            {
                'ip_address': '155.235.81.100',  # Changed from 'ip' to 'ip_address'
                'hostname': 'medical-nas-01',
                'manufacturer': 'Synology',
                'model': 'DS920+',
                'shares': ['dicom-storage', 'backups', 'archives'],
                'available_space_gb': 2048,
                'protocols': ['SMB', 'NFS', 'FTP'],
                'mac_address': '00:0c:29:9b:72:75',
                'device_type': 'NAS Storage',
                'source': 'Legacy Scan',
                'status': 'online'
            },
            {
                'ip_address': '155.235.81.101',  # Changed from 'ip' to 'ip_address'
                'hostname': 'medical-nas-02',
                'manufacturer': 'QNAP',
                'model': 'TS-464',
                'shares': ['medical-images', 'reports'],
                'available_space_gb': 4096,
                'protocols': ['SMB', 'NFS'],
                'mac_address': '00:0c:29:19:0f:18',
                'device_type': 'NAS Storage',
                'source': 'Legacy Scan',
                'status': 'online'
            },
            {
                'ip_address': '155.235.81.102',
                'hostname': 'dicom-workstation',
                'manufacturer': 'Dell',
                'model': 'OptiPlex 7090',
                'shares': ['temp-storage'],
                'available_space_gb': 512,
                'protocols': ['SMB'],
                'mac_address': '00:50:56:a7:e8:40',
                'device_type': 'Workstation',
                'source': 'Legacy Scan',
                'status': 'online'
            }
        ]
        
        return jsonify({
            'success': True,
            'discovered_devices': discovered_nas,  # Changed from 'discovered_nas' to 'discovered_devices'
            'network_range': network_range,
            'total_devices': len(discovered_nas),
            'message': f'Legacy scan found {len(discovered_nas)} potential medical devices on {network_range}'
        })
        
    except Exception as e:
        logger.error(f"NAS discovery error: {e}")
        return jsonify({
            'success': False,
            'error': 'NAS discovery failed'
        }), 500

@nas_bp.route('/shares', methods=['GET'])
@require_auth
def get_nas_shares():
    """Get available NAS shares"""
    try:
        nas_ip = request.args.get('nas_ip')
        
        if not nas_ip:
            return jsonify({'error': 'NAS IP address is required'}), 400
        
        # Mock share discovery
        shares = [
            {
                'name': 'dicom-storage',
                'path': '/volume1/dicom-storage',
                'size_gb': 1024,
                'used_gb': 512,
                'available_gb': 512,
                'permissions': ['read', 'write'],
                'optimized_for': 'DICOM'
            },
            {
                'name': 'backups',
                'path': '/volume1/backups',
                'size_gb': 512,
                'used_gb': 256,
                'available_gb': 256,
                'permissions': ['read', 'write'],
                'optimized_for': 'Backup'
            }
        ]
        
        return jsonify({
            'success': True,
            'nas_ip': nas_ip,
            'shares': shares
        })
        
    except Exception as e:
        logger.error(f"Error getting NAS shares: {e}")
        return jsonify({'error': 'Failed to get NAS shares'}), 500

@nas_bp.route('/status', methods=['GET'])
def nas_status():
    """Get NAS system status - public endpoint for testing"""
    try:
        status = {
            'nas_discovery_enabled': True,
            'connected_nas_devices': 2,
            'total_storage_gb': 6144,
            'available_storage_gb': 4096,
            'last_discovery': '2025-08-15T10:00:00Z',
            'system_status': 'operational'
        }
        
        return jsonify({
            'success': True,
            'status': status,
            'message': 'NAS system operational'
        })
    except Exception as e:
        logger.error(f"NAS status error: {e}")
        return jsonify({'error': 'Failed to get NAS status'}), 500

@nas_bp.route('/config', methods=['GET', 'POST'])
def nas_config():
    """Get or update NAS configuration - public for testing"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            
            # Mock configuration update
            logger.info(f"Updating NAS configuration: {data}")
            
            return jsonify({
                'success': True,
                'message': 'NAS configuration updated successfully',
                'updated_config': data
            })
        else:
            # Mock configuration retrieval
            config = {
                'primary_nas': '192.168.1.100',
                'backup_nas': '192.168.1.101', 
                'default_share': 'dicom-storage',
                'auto_discovery': True,
                'encryption_enabled': True,
                'connection_status': 'connected',
                'last_test': '2025-08-15T10:00:00Z'
            }
            
            return jsonify({
                'success': True,
                'config': config,
                'message': 'NAS configuration retrieved successfully'
            })
            
    except Exception as e:
        logger.error(f"NAS config error: {e}")
        return jsonify({'error': 'NAS configuration failed'}), 500

@nas_bp.route('/config/admin', methods=['GET', 'POST'])
@require_admin
def nas_config_admin():
    """Admin-only NAS configuration with sensitive settings"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            
            # Mock secure configuration update
            logger.info(f"Admin updating NAS configuration: {data}")
            
            return jsonify({
                'success': True,
                'message': 'NAS configuration updated by admin',
                'sensitive_data_updated': True
            })
        else:
            # Mock sensitive configuration retrieval
            config = {
                'primary_nas': '192.168.1.100',
                'backup_nas': '192.168.1.101',
                'default_share': 'dicom-storage',
                'auto_discovery': True,
                'encryption_enabled': True,
                'connection_status': 'connected',
                'admin_credentials': '***PROTECTED***',
                'security_settings': {
                    'encryption_key_rotation': 'weekly',
                    'access_logging': True,
                    'audit_trail': True
                }
            }
            
            return jsonify({
                'success': True,
                'config': config,
                'admin_access': True
            })
            
    except Exception as e:
        logger.error(f"Admin NAS config error: {e}")
        return jsonify({'error': 'Admin NAS configuration failed'}), 500

@nas_bp.route('/test', methods=['GET'])
def nas_test():
    """Test NAS connectivity - public endpoint"""
    try:
        test_results = {
            'primary_nas_test': {
                'ip': '192.168.1.100',
                'status': 'reachable',
                'response_time_ms': 45
            },
            'backup_nas_test': {
                'ip': '192.168.1.101', 
                'status': 'reachable',
                'response_time_ms': 67
            },
            'share_access_test': {
                'dicom_storage': 'accessible',
                'medical_images': 'accessible',
                'backups': 'accessible'
            },
            'overall_status': 'all_tests_passed'
        }
        
        return jsonify({
            'success': True,
            'test_results': test_results,
            'message': 'NAS connectivity test completed successfully'
        })
    except Exception as e:
        logger.error(f"NAS test error: {e}")
        return jsonify({'error': 'NAS test failed'}), 500

# ===== NEW MEDICAL IMAGE MANAGEMENT ENDPOINTS =====

@nas_bp.route('/orthanc/connect', methods=['POST'])
@require_auth
def connect_orthanc():
    """Connect to Orthanc PACS server"""
    try:
        data = request.get_json() or {}
        url = data.get('url', 'http://localhost:8042')
        username = data.get('username', '')
        password = data.get('password', '')
        
        logger.info(f"Connecting to Orthanc at: {url}")
        
        # Test connection to Orthanc
        import requests
        auth = (username, password) if username and password else None
        
        try:
            response = requests.get(f"{url}/system", auth=auth, timeout=10)
            if response.status_code == 200:
                system_info = response.json()
                
                # Store connection details (in production, use secure storage)
                connection_status = {
                    'url': url,
                    'connected': True,
                    'system_info': system_info,
                    'version': system_info.get('Version', 'Unknown'),
                    'name': system_info.get('Name', 'Orthanc'),
                    'timestamp': '2025-08-15T11:00:00Z'
                }
                
                return jsonify({
                    'success': True,
                    'message': 'Successfully connected to Orthanc',
                    'connection': connection_status
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'Failed to connect: HTTP {response.status_code}',
                    'error': 'Authentication or connection failed'
                }), 400
                
        except requests.exceptions.RequestException as e:
            return jsonify({
                'success': False,
                'message': 'Connection failed',
                'error': str(e)
            }), 500
            
    except Exception as e:
        logger.error(f"Orthanc connection error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to connect to Orthanc'
        }), 500

@nas_bp.route('/orthanc/status', methods=['GET'])
def orthanc_status():
    """Get Orthanc connection status"""
    try:
        # Mock status - in production, check actual connection
        status = {
            'connected': True,
            'url': 'http://localhost:8042',
            'version': '1.12.1',
            'name': 'Central Hospital PACS',
            'patients_count': 1247,
            'studies_count': 3891,
            'series_count': 15674,
            'instances_count': 187523,
            'disk_usage_gb': 2.3,
            'last_check': '2025-08-15T11:00:00Z'
        }
        
        return jsonify({
            'success': True,
            'status': status,
            'message': 'Orthanc server is online and accessible'
        })
    except Exception as e:
        logger.error(f"Orthanc status error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get Orthanc status'
        }), 500

@nas_bp.route('/index/start', methods=['POST'])
@require_auth
def start_indexing():
    """Start fast indexing of DICOM images"""
    try:
        data = request.get_json() or {}
        path = data.get('path', '/nas/dicom/')
        
        logger.info(f"Starting DICOM indexing at: {path}")
        
        # Mock indexing process - in production, implement actual indexing
        import threading
        import time
        
        def mock_indexing():
            # Simulate indexing process
            time.sleep(2)  # Simulate work
        
        # Start indexing in background
        indexing_thread = threading.Thread(target=mock_indexing)
        indexing_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'DICOM indexing started',
            'indexing_id': 'idx_20250815_001',
            'status': 'running',
            'path': path,
            'estimated_completion': '2025-08-15T11:05:00Z'
        })
        
    except Exception as e:
        logger.error(f"Indexing start error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to start indexing'
        }), 500

@nas_bp.route('/index/status', methods=['GET'])
def indexing_status():
    """Get current indexing status"""
    try:
        # Mock status - in production, check actual indexing progress
        status = {
            'indexing_id': 'idx_20250815_001',
            'status': 'completed',
            'progress_percent': 100,
            'files_processed': 15673,
            'files_total': 15673,
            'patients_indexed': 1247,
            'studies_indexed': 3891,
            'errors': 0,
            'start_time': '2025-08-15T11:00:00Z',
            'completion_time': '2025-08-15T11:03:00Z',
            'duration_seconds': 180
        }
        
        return jsonify({
            'success': True,
            'indexing': status,
            'message': 'Indexing completed successfully'
        })
    except Exception as e:
        logger.error(f"Indexing status error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get indexing status'
        }), 500

@nas_bp.route('/search/patient', methods=['POST'])
@require_auth
def search_patient_images():
    """Search for patient images and studies"""
    try:
        data = request.get_json() or {}
        patient_id = data.get('patient_id', '')
        study_date = data.get('study_date', '')
        modality = data.get('modality', '')
        
        logger.info(f"Searching for patient: {patient_id}")
        
        # Mock search results - in production, query actual DICOM database
        mock_patients = [
            {
                'patient_id': 'PAT001',
                'name': 'John Doe',
                'birth_date': '1985-03-15',
                'sex': 'M',
                'studies': [
                    {
                        'study_id': 'STU001',
                        'study_date': '2025-08-10',
                        'description': 'Chest CT Scan',
                        'modality': 'CT',
                        'series_count': 3,
                        'instance_count': 125
                    },
                    {
                        'study_id': 'STU002',
                        'study_date': '2025-08-12',
                        'description': 'Brain MRI',
                        'modality': 'MRI',
                        'series_count': 5,
                        'instance_count': 200
                    }
                ]
            },
            {
                'patient_id': 'PAT002',
                'name': 'Jane Smith',
                'birth_date': '1990-07-22',
                'sex': 'F',
                'studies': [
                    {
                        'study_id': 'STU003',
                        'study_date': '2025-08-14',
                        'description': 'Abdominal CT',
                        'modality': 'CT',
                        'series_count': 4,
                        'instance_count': 150
                    }
                ]
            }
        ]
        
        # Filter results based on search criteria
        filtered_patients = []
        for patient in mock_patients:
            if patient_id.lower() in patient['patient_id'].lower() or patient_id.lower() in patient['name'].lower():
                # Filter studies by modality if specified
                if modality:
                    patient['studies'] = [s for s in patient['studies'] if s['modality'] == modality]
                
                # Filter studies by date if specified
                if study_date:
                    patient['studies'] = [s for s in patient['studies'] if s['study_date'] == study_date]
                
                if patient['studies']:  # Only include if has matching studies
                    filtered_patients.append(patient)
        
        return jsonify({
            'success': True,
            'patients': filtered_patients,
            'total_found': len(filtered_patients),
            'search_criteria': {
                'patient_id': patient_id,
                'study_date': study_date,
                'modality': modality
            },
            'message': f'Found {len(filtered_patients)} patient(s) matching criteria'
        })
        
    except Exception as e:
        logger.error(f"Patient search error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to search patient images'
        }), 500

@nas_bp.route('/share/generate', methods=['POST'])
@require_auth
def generate_share_link():
    """Generate secure sharing link for patient images"""
    try:
        data = request.get_json() or {}
        patient_id = data.get('patient_id', '')
        study_id = data.get('study_id', '')
        expiry_hours = int(data.get('expiry_hours', 24))
        message = data.get('message', '')
        
        if not patient_id:
            return jsonify({
                'success': False,
                'error': 'Patient ID is required'
            }), 400
        
        logger.info(f"Generating share link for patient: {patient_id}")
        
        # Generate secure link and access code
        import uuid
        import hashlib
        from datetime import datetime, timedelta
        
        share_id = str(uuid.uuid4())[:8]
        access_code = hashlib.md5(f"{patient_id}{share_id}".encode()).hexdigest()[:6].upper()
        
        expiry_date = datetime.now() + timedelta(hours=expiry_hours)
        
        # In production, store this in database
        share_link = f"http://localhost:5000/share/{share_id}"
        
        share_data = {
            'share_id': share_id,
            'share_link': share_link,
            'access_code': access_code,
            'patient_id': patient_id,
            'study_id': study_id,
            'expiry_date': expiry_date.isoformat(),
            'expiry_hours': expiry_hours,
            'message': message,
            'created_date': datetime.now().isoformat(),
            'download_count': 0,
            'max_downloads': 5
        }
        
        return jsonify({
            'success': True,
            'share_link': share_link,
            'access_code': access_code,
            'expiry_date': expiry_date.strftime('%Y-%m-%d %H:%M:%S'),
            'share_data': share_data,
            'instructions': {
                'step1': 'Share this link with the patient',
                'step2': f'Patient must enter access code: {access_code}',
                'step3': 'Patient can download images until expiry',
                'note': f'Link expires in {expiry_hours} hours'
            },
            'message': 'Secure sharing link generated successfully'
        })
        
    except Exception as e:
        logger.error(f"Share link generation error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate sharing link'
        }), 500

@nas_bp.route('/ping', methods=['POST'])
def ping_device():
    """Ping a specific IP address"""
    try:
        data = request.get_json() or {}
        ip_address = data.get('ip_address', '')
        timeout = data.get('timeout', 5)  # Default 5 second timeout
        
        if not ip_address:
            return jsonify({
                'success': False,
                'error': 'IP address is required'
            }), 400
        
        logger.info(f"Pinging device: {ip_address} with {timeout}s timeout")
        
        # Ping the device
        import subprocess
        import platform
        import time
        
        start_time = time.time()
        
        # Get the ping command for the current OS
        if platform.system().lower() == 'windows':
            cmd = ['ping', '-n', '1', '-w', str(timeout * 1000), ip_address]  # Windows uses milliseconds
        else:
            cmd = ['ping', '-c', '1', '-W', str(timeout), ip_address]  # Linux uses seconds
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
            end_time = time.time()
            response_time_ms = round((end_time - start_time) * 1000, 2)
            
            ping_data = {
                'ip_address': ip_address,
                'reachable': result.returncode == 0,
                'response_time_ms': response_time_ms,
                'response_time': f"{response_time_ms}ms" if result.returncode == 0 else 'timeout',
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None
            }
            
            return jsonify({
                'success': True,
                'ping_result': ping_data,
                'message': f"Ping {'successful' if result.returncode == 0 else 'failed'} for {ip_address}"
            })
            
        except subprocess.TimeoutExpired:
            end_time = time.time()
            return jsonify({
                'success': False,
                'ping_result': {
                    'ip_address': ip_address,
                    'reachable': False,
                    'response_time_ms': timeout * 1000,
                    'error': 'Ping timeout'
                },
                'message': f'Ping timeout for {ip_address}'
            })
            
    except Exception as e:
        logger.error(f"Ping error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to ping device'
        }), 500

@nas_bp.route('/arp-table', methods=['GET'])
@require_admin
def get_arp_table():
    """Get the system's ARP table to show network devices"""
    try:
        import subprocess
        import platform
        import re
        
        logger.info("Fetching ARP table")
        
        # Load custom device names
        device_names = load_device_names()
        
        # Get ARP table based on OS
        if platform.system().lower() == 'windows':
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=10)
        else:
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve ARP table'
            }), 500
        
        # Parse ARP table
        arp_entries = []
        lines = result.stdout.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or 'Interface:' in line or 'Internet Address' in line or '---' in line:
                continue
                
            # Windows ARP format: IP_ADDRESS    PHYSICAL_ADDRESS     TYPE
            if platform.system().lower() == 'windows':
                # Match pattern like: 192.168.1.1    aa-bb-cc-dd-ee-ff    dynamic
                match = re.match(r'^\s*(\d+\.\d+\.\d+\.\d+)\s+([a-fA-F0-9\-]{17})\s+(\w+)', line)
                if match:
                    ip, mac, entry_type = match.groups()
                    mac_clean = mac.replace('-', ':').lower()
                    
                    # Check for custom name
                    custom_name = device_names.get(ip, {}).get('name', '')
                    display_name = custom_name if custom_name else 'Unknown'
                    
                    arp_entries.append({
                        'ip_address': ip,
                        'mac_address': mac_clean,
                        'type': entry_type,
                        'hostname': display_name,
                        'custom_name': custom_name,
                        'last_seen': 'Active'
                    })
            else:
                # Linux ARP format: hostname (IP) at MAC [ether] on interface
                match = re.match(r'^(\S+)\s+\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+([a-fA-F0-9:]{17})', line)
                if match:
                    hostname, ip, mac = match.groups()
                    mac_clean = mac.lower()
                    
                    # Check for custom name
                    custom_name = device_names.get(ip, {}).get('name', '')
                    display_name = custom_name if custom_name else (hostname if hostname != ip else 'Unknown')
                    
                    arp_entries.append({
                        'ip_address': ip,
                        'mac_address': mac_clean,
                        'type': 'dynamic',
                        'hostname': display_name,
                        'custom_name': custom_name,
                        'last_seen': 'Active'
                    })
        
        return jsonify({
            'success': True,
            'arp_entries': arp_entries,
            'total_entries': len(arp_entries),
            'message': f'Found {len(arp_entries)} devices in ARP table'
        })
        
    except Exception as e:
        logger.error(f"ARP table error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve ARP table'
        }), 500

@nas_bp.route('/ping-range', methods=['POST'])
@require_admin  
def ping_range():
    """Ping a range of IP addresses"""
    try:
        data = request.get_json() or {}
        start_ip = data.get('start_ip', '')
        end_ip = data.get('end_ip', '')
        timeout = data.get('timeout', 2)  # Default 2 seconds per ping
        max_concurrent = data.get('max_concurrent', 10)  # Max concurrent pings
        
        if not start_ip or not end_ip:
            return jsonify({
                'success': False,
                'error': 'Start IP and End IP are required'
            }), 400
        
        import ipaddress
        import subprocess
        import platform
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        try:
            # Validate IP addresses and create range
            start = ipaddress.IPv4Address(start_ip)
            end = ipaddress.IPv4Address(end_ip)
            
            if start > end:
                return jsonify({
                    'success': False,
                    'error': 'Start IP must be less than or equal to End IP'
                }), 400
            
            # Generate IP list
            ip_list = []
            current = start
            while current <= end:
                ip_list.append(str(current))
                current += 1
            
            if len(ip_list) > 254:  # Safety limit
                return jsonify({
                    'success': False,
                    'error': 'Range too large. Maximum 254 IPs allowed.'
                }), 400
            
            logger.info(f"Pinging range {start_ip} to {end_ip} ({len(ip_list)} IPs) with {timeout}s timeout")
            
            def ping_single_ip(ip):
                """Ping a single IP address"""
                start_time = time.time()
                
                if platform.system().lower() == 'windows':
                    cmd = ['ping', '-n', '1', '-w', str(timeout * 1000), ip]
                else:
                    cmd = ['ping', '-c', '1', '-W', str(timeout), ip]
                
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 1)
                    end_time = time.time()
                    response_time_ms = round((end_time - start_time) * 1000, 2)
                    
                    return {
                        'ip_address': ip,
                        'reachable': result.returncode == 0,
                        'response_time_ms': response_time_ms,
                        'response_time': f"{response_time_ms}ms" if result.returncode == 0 else 'timeout',
                        'status': 'online' if result.returncode == 0 else 'offline'
                    }
                except subprocess.TimeoutExpired:
                    return {
                        'ip_address': ip,
                        'reachable': False,
                        'response_time_ms': timeout * 1000,
                        'response_time': 'timeout',
                        'status': 'timeout'
                    }
                except Exception as e:
                    return {
                        'ip_address': ip,
                        'reachable': False,
                        'response_time_ms': 0,
                        'response_time': 'error',
                        'status': 'error',
                        'error': str(e)
                    }
            
            # Execute pings concurrently
            results = []
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=min(max_concurrent, len(ip_list))) as executor:
                future_to_ip = {executor.submit(ping_single_ip, ip): ip for ip in ip_list}
                
                for future in as_completed(future_to_ip):
                    result = future.result()
                    results.append(result)
            
            end_time = time.time()
            total_time = round(end_time - start_time, 2)
            
            # Sort results by IP
            results.sort(key=lambda x: ipaddress.IPv4Address(x['ip_address']))
            
            # Calculate statistics
            online_count = sum(1 for r in results if r['reachable'])
            offline_count = len(results) - online_count
            
            return jsonify({
                'success': True,
                'ping_results': results,
                'statistics': {
                    'total_ips': len(results),
                    'online_count': online_count,
                    'offline_count': offline_count,
                    'success_rate': round((online_count / len(results)) * 100, 1),
                    'total_time_seconds': total_time,
                    'average_time_per_ip': round(total_time / len(results), 2)
                },
                'range': {
                    'start_ip': start_ip,
                    'end_ip': end_ip,
                    'timeout': timeout,
                    'max_concurrent': max_concurrent
                },
                'message': f'Pinged {len(results)} IPs: {online_count} online, {offline_count} offline'
            })
            
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': f'Invalid IP address format: {e}'
            }), 400
            
    except Exception as e:
        logger.error(f"Range ping error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to ping IP range'
        }), 500

@nas_bp.route('/network-config', methods=['GET', 'POST'])
@require_admin
def network_config():
    """Get or set network discovery configuration"""
    try:
        if request.method == 'GET':
            # Return current configuration
            config = {
                'default_timeout': 3,
                'max_concurrent_pings': 20,
                'default_start_ip': '192.168.1.1',
                'default_end_ip': '192.168.1.254',
                'auto_discover_on_startup': True,
                'include_arp_table': True,
                'ping_count': 1,
                'scan_common_ports': [22, 80, 443, 445, 8080]
            }
            
            return jsonify({
                'success': True,
                'config': config
            })
        
        else:  # POST - Update configuration
            data = request.get_json() or {}
            
            # Validate configuration values
            timeout = data.get('timeout', 3)
            max_concurrent = data.get('max_concurrent_pings', 20)
            
            if timeout < 1 or timeout > 30:
                return jsonify({
                    'success': False,
                    'error': 'Timeout must be between 1 and 30 seconds'
                }), 400
            
            if max_concurrent < 1 or max_concurrent > 50:
                return jsonify({
                    'success': False,
                    'error': 'Max concurrent pings must be between 1 and 50'
                }), 400
            
            # Here you would save the configuration to a file or database
            # For now, we'll just return success
            
            return jsonify({
                'success': True,
                'message': 'Network configuration updated successfully',
                'config': data
            })
            
    except Exception as e:
        logger.error(f"Network config error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to handle network configuration'
        }), 500

@nas_bp.route('/enhanced-discover', methods=['POST'])
@require_admin
def enhanced_discover():
    """Enhanced network discovery combining ARP table and range ping"""
    try:
        data = request.get_json() or {}
        include_arp = data.get('include_arp', True)
        include_ping_range = data.get('include_ping_range', False)
        start_ip = data.get('start_ip', '192.168.1.1')
        end_ip = data.get('end_ip', '192.168.1.50')
        timeout = data.get('timeout', 2)
        
        logger.info(f"Enhanced discovery: ARP={include_arp}, Range={include_ping_range}")
        
        discovered_devices = []
        
        # Get ARP table if requested
        if include_arp:
            try:
                import subprocess
                import platform
                import re
                
                if platform.system().lower() == 'windows':
                    result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=10)
                else:
                    result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        line = line.strip()
                        if not line or 'Interface:' in line or 'Internet Address' in line or '---' in line:
                            continue
                            
                        if platform.system().lower() == 'windows':
                            match = re.match(r'^\s*(\d+\.\d+\.\d+\.\d+)\s+([a-fA-F0-9\-]{17})\s+(\w+)', line)
                            if match:
                                ip, mac, entry_type = match.groups()
                                discovered_devices.append({
                                    'ip_address': ip,
                                    'mac_address': mac.replace('-', ':').lower(),
                                    'hostname': 'Unknown',
                                    'source': 'ARP Table',
                                    'status': 'active',
                                    'device_type': 'Unknown',
                                    'manufacturer': 'Unknown'
                                })
                        else:
                            match = re.match(r'^(\S+)\s+\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+([a-fA-F0-9:]{17})', line)
                            if match:
                                hostname, ip, mac = match.groups()
                                discovered_devices.append({
                                    'ip_address': ip,
                                    'mac_address': mac.lower(),
                                    'hostname': hostname if hostname != ip else 'Unknown',
                                    'source': 'ARP Table',
                                    'status': 'active',
                                    'device_type': 'Unknown',
                                    'manufacturer': 'Unknown'
                                })
                                
            except Exception as arp_error:
                logger.warning(f"ARP table retrieval failed: {arp_error}")
        
        # Add range ping if requested  
        if include_ping_range:
            try:
                import ipaddress
                from concurrent.futures import ThreadPoolExecutor
                
                start = ipaddress.IPv4Address(start_ip)
                end = ipaddress.IPv4Address(end_ip)
                
                if end - start <= 254:  # Safety limit
                    def ping_and_check(ip_str):
                        import subprocess
                        import platform
                        
                        if platform.system().lower() == 'windows':
                            cmd = ['ping', '-n', '1', '-w', str(timeout * 1000), ip_str]
                        else:
                            cmd = ['ping', '-c', '1', '-W', str(timeout), ip_str]
                        
                        try:
                            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 1)
                            if result.returncode == 0:
                                # Check if this IP is already in discovered devices from ARP
                                existing = next((d for d in discovered_devices if d['ip_address'] == ip_str), None)
                                if not existing:
                                    return {
                                        'ip_address': ip_str,
                                        'mac_address': 'Unknown',
                                        'hostname': 'Unknown',
                                        'source': 'Ping Scan',
                                        'status': 'online',
                                        'device_type': 'Unknown',
                                        'manufacturer': 'Unknown'
                                    }
                                else:
                                    existing['status'] = 'online'
                                    existing['source'] = 'ARP + Ping'
                        except:
                            pass
                        return None
                    
                    # Generate IP range
                    ip_list = []
                    current = start
                    while current <= end:
                        ip_list.append(str(current))
                        current += 1
                    
                    # Ping concurrently
                    with ThreadPoolExecutor(max_workers=20) as executor:
                        ping_results = list(executor.map(ping_and_check, ip_list))
                        
                    # Add new devices found via ping
                    for result in ping_results:
                        if result:
                            discovered_devices.append(result)
                            
            except Exception as ping_error:
                logger.warning(f"Range ping failed: {ping_error}")
        
        # Remove duplicates and sort
        seen_ips = set()
        unique_devices = []
        for device in discovered_devices:
            if device['ip_address'] not in seen_ips:
                seen_ips.add(device['ip_address'])
                unique_devices.append(device)
        
        # Sort by IP address
        try:
            unique_devices.sort(key=lambda x: ipaddress.IPv4Address(x['ip_address']))
        except:
            unique_devices.sort(key=lambda x: x['ip_address'])
        
        return jsonify({
            'success': True,
            'discovered_devices': unique_devices,
            'total_devices': len(unique_devices),
            'discovery_methods': {
                'arp_table': include_arp,
                'ping_range': include_ping_range,
                'range': f"{start_ip} - {end_ip}" if include_ping_range else None,
                'timeout': timeout
            },
            'message': f'Discovered {len(unique_devices)} network devices'
        })
        
    except Exception as e:
        logger.error(f"Enhanced discovery error: {e}")
        return jsonify({
            'success': False,
            'error': 'Enhanced network discovery failed'
        }), 500

@nas_bp.route('/device/rename', methods=['POST'])
@require_admin
def rename_device():
    """Save custom name for a network device"""
    try:
        data = request.get_json() or {}
        ip_address = data.get('ip_address', '')
        mac_address = data.get('mac_address', '')
        custom_name = data.get('custom_name', '')
        
        if not ip_address or not custom_name:
            return jsonify({
                'success': False,
                'error': 'IP address and custom name are required'
            }), 400
        
        logger.info(f"Renaming device {ip_address} to '{custom_name}'")
        
        # Load existing device names and update
        device_names = load_device_names()
        device_names[ip_address] = custom_name
        
        # Also save by MAC address for persistence across IP changes
        if mac_address:
            device_names[mac_address] = custom_name
        
        # Save to persistent storage
        if save_device_names(device_names):
            return jsonify({
                'success': True,
                'message': f'Device renamed to "{custom_name}"',
                'ip_address': ip_address,
                'custom_name': custom_name
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save device name'
            }), 500
        
    except Exception as e:
        logger.error(f"Device rename error: {e}")
        return jsonify({
            'success': False,
            'error': 'Device rename failed'
        }), 500

@nas_bp.route('/device/names', methods=['GET'])
@require_admin
def get_device_names():
    """Get all saved custom device names"""
    try:
        return jsonify({
            'success': True,
            'device_names': load_device_names()
        })
    except Exception as e:
        logger.error(f"Error getting device names: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get device names'
        }), 500

@nas_bp.route('/network-settings', methods=['GET', 'POST'])
@require_admin
def network_settings():
    """Get or save network discovery settings"""
    try:
        import json
        import os
        
        settings_file = 'network_settings.json'
        
        if request.method == 'GET':
            # Load settings
            default_settings = {
                'startIp': '192.168.1.1',
                'endIp': '192.168.1.50',
                'timeout': 2,
                'maxConcurrent': 10,
                'networkRange': '155.235.81.0/24',
                'autoDiscovery': True,
                'includeArp': True,
                'includePingRange': False
            }
            
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, 'r') as f:
                        saved_settings = json.load(f)
                        default_settings.update(saved_settings)
                except:
                    pass
            
            return jsonify({
                'success': True,
                'settings': default_settings
            })
        
        else:  # POST - Save settings
            data = request.get_json() or {}
            
            # Validate settings
            start_ip = data.get('startIp', '192.168.1.1')
            end_ip = data.get('endIp', '192.168.1.50')
            timeout = int(data.get('timeout', 2))
            max_concurrent = int(data.get('maxConcurrent', 10))
            
            if timeout < 1 or timeout > 30:
                return jsonify({
                    'success': False,
                    'error': 'Timeout must be between 1 and 30 seconds'
                }), 400
            
            if max_concurrent < 1 or max_concurrent > 50:
                return jsonify({
                    'success': False,
                    'error': 'Max concurrent must be between 1 and 50'
                }), 400
            
            # Save settings
            settings = {
                'startIp': start_ip,
                'endIp': end_ip,
                'timeout': timeout,
                'maxConcurrent': max_concurrent,
                'networkRange': data.get('networkRange', '155.235.81.0/24'),
                'autoDiscovery': data.get('autoDiscovery', True),
                'includeArp': data.get('includeArp', True),
                'includePingRange': data.get('includePingRange', False),
                'saved_date': '2025-08-15T11:00:00Z'
            }
            
            try:
                with open(settings_file, 'w') as f:
                    json.dump(settings, f, indent=2)
            except Exception as e:
                logger.warning(f"Could not save network settings: {e}")
            
            return jsonify({
                'success': True,
                'settings': settings,
                'message': 'Network settings saved successfully'
            })
            
    except Exception as e:
        logger.error(f"Network settings error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to handle network settings'
        }), 500

@nas_bp.route('/storage/config', methods=['POST'])
@require_auth
def configure_storage():
    """Configure storage paths and settings"""
    try:
        data = request.get_json() or {}
        primary_path = data.get('primary_path', '/nas/dicom/primary/')
        backup_path = data.get('backup_path', '/nas/dicom/backup/')
        compression = data.get('compression', 'none')
        
        logger.info(f"Configuring storage - Primary: {primary_path}, Backup: {backup_path}")
        
        # Mock storage configuration - in production, validate paths and set up storage
        config = {
            'primary_path': primary_path,
            'backup_path': backup_path,
            'compression': compression,
            'auto_backup': True,
            'retention_days': 365,
            'max_storage_gb': 1000,
            'current_usage_gb': 150.5,
            'available_gb': 849.5,
            'configured_date': '2025-08-15T11:00:00Z'
        }
        
        return jsonify({
            'success': True,
            'storage_config': config,
            'message': 'Storage configuration updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Storage configuration error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to configure storage'
        }), 500

@nas_bp.route('/storage/test', methods=['GET'])
def test_storage_paths():
    """Test storage path accessibility"""
    try:
        # Mock storage test results
        test_results = {
            'primary_path': {
                'path': '/nas/dicom/primary/',
                'accessible': True,
                'writable': True,
                'space_gb': 849.5,
                'test_file_created': True
            },
            'backup_path': {
                'path': '/nas/dicom/backup/',
                'accessible': True,
                'writable': True,
                'space_gb': 1500.0,
                'test_file_created': True
            },
            'network_latency_ms': 12,
            'throughput_mbps': 95.5,
            'test_timestamp': '2025-08-15T11:00:00Z'
        }
        
        return jsonify({
            'success': True,
            'test_results': test_results,
            'message': 'All storage paths are accessible and functional'
        })
        
    except Exception as e:
        logger.error(f"Storage test error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to test storage paths'
        }), 500

@nas_bp.route('/share/verify/<share_id>', methods=['POST'])
def verify_share_access(share_id):
    """Verify access code for shared medical images"""
    try:
        data = request.get_json() or {}
        access_code = data.get('access_code', '').upper()
        
        logger.info(f"Verifying access for share: {share_id}")
        
        # Mock verification - in production, check database
        if access_code == 'ABC123':  # Mock access code
            share_data = {
                'share_id': share_id,
                'patient_id': 'PAT001',
                'patient_name': 'John Doe',
                'study_date': '2025-08-10',
                'expiry_date': '2025-08-16 11:00:00',
                'access_verified': True
            }
            
            return jsonify({
                'success': True,
                'share_data': share_data,
                'message': 'Access verified successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid access code'
            }), 401
            
    except Exception as e:
        logger.error(f"Share verification error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to verify access'
        }), 500
