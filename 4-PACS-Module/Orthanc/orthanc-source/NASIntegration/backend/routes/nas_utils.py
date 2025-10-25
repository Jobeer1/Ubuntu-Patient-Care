"""
NAS Utility Functions for South African Medical Imaging System
Handles device naming, JSON storage, and common utilities
"""

import json
import os
import logging
import subprocess
import platform
import socket
from datetime import datetime
from datetime import datetime

logger = logging.getLogger(__name__)

# Device names storage file
DEVICE_NAMES_FILE = 'device_names.json'
DISCOVERED_DEVICES_FILE = 'discovered_devices.json'

def load_discovered_devices():
    """Load discovered devices from JSON database"""
    try:
        if os.path.exists(DISCOVERED_DEVICES_FILE):
            with open(DISCOVERED_DEVICES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'devices': [],
            'last_discovery': None,
            'discovery_count': 0
        }
    except Exception as e:
        logger.error(f"Error loading discovered devices: {e}")
        return {
            'devices': [],
            'last_discovery': None,
            'discovery_count': 0
        }

def save_discovered_devices(devices, discovery_method='ARP Table'):
    """Save discovered devices to JSON database"""
    try:
        # Load existing data
        existing_data = load_discovered_devices()
        
        # Update with new devices
        device_data = {
            'devices': devices,
            'last_discovery': datetime.now().isoformat(),
            'discovery_method': discovery_method,
            'discovery_count': existing_data.get('discovery_count', 0) + 1,
            'total_devices': len(devices)
        }
        
        with open(DISCOVERED_DEVICES_FILE, 'w', encoding='utf-8') as f:
            json.dump(device_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(devices)} discovered devices to database")
        return True
    except Exception as e:
        logger.error(f"Error saving discovered devices: {e}")
        return False

def get_cached_discovered_devices():
    """Get cached discovered devices from database"""
    try:
        data = load_discovered_devices()
        return data.get('devices', [])
    except Exception as e:
        logger.error(f"Error getting cached devices: {e}")
        return []

def load_device_names():
    """Load device custom names from JSON file"""
    try:
        if os.path.exists(DEVICE_NAMES_FILE):
            with open(DEVICE_NAMES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading device names: {e}")
        return {}

def save_device_names(device_names):
    """Save device custom names to JSON file"""
    try:
        with open(DEVICE_NAMES_FILE, 'w', encoding='utf-8') as f:
            json.dump(device_names, f, indent=2, ensure_ascii=False)
        logger.info(f"Device names saved to {DEVICE_NAMES_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error saving device names: {e}")
        return False

# Configuration flags
ENABLE_DNS_RESOLUTION = False  # Temporarily disabled to prevent hanging

def resolve_hostname(ip_address):
    """Resolve hostname from IP address using DNS"""
    try:
        if not ip_address or ip_address == 'Unknown':
            return 'Unknown'
            
        # Check if DNS resolution is enabled
        if not ENABLE_DNS_RESOLUTION:
            return 'Unknown'
        
        # Skip multicast addresses
        if ip_address.startswith('224.') or ip_address.startswith('239.') or ip_address.startswith('226.') or ip_address.startswith('234.'):
            return 'Multicast'
        
        # Set socket timeout to prevent hanging
        original_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(2.0)  # 2 second timeout
        
        try:
            hostname = socket.gethostbyaddr(ip_address)[0]
            return hostname if hostname else 'Unknown'
        finally:
            socket.setdefaulttimeout(original_timeout)
            
    except (socket.herror, socket.gaierror, OSError):
        return 'Unknown'
    except Exception as e:
        logger.debug(f"Hostname resolution failed for {ip_address}: {e}")
        return 'Unknown'

def get_device_name(mac_address, ip_address=None):
    """Get custom name for a device by MAC address, with fallback to DNS resolution"""
    device_names = load_device_names()
    
    # Try custom name first (MAC address)
    if mac_address and mac_address in device_names:
        return device_names[mac_address].get('name', 'Unknown')
    
    # Fallback to IP custom name if MAC not found
    if ip_address and ip_address in device_names:
        return device_names[ip_address].get('name', 'Unknown')
    
    # If no custom name, try DNS resolution
    if ip_address:
        hostname = resolve_hostname(ip_address)
        if hostname and hostname != 'Unknown' and hostname != 'Multicast':
            return hostname
    
    return 'Unknown'

def update_device_ping_result(ip_address, ping_result):
    """Update device with ping result and store it"""
    try:
        # Load discovered devices
        data = load_discovered_devices()
        devices = data.get('devices', [])
        
        # Find and update the device
        updated = False
        for device in devices:
            if device.get('ip_address') == ip_address:
                device['last_ping'] = datetime.now().isoformat()
                device['reachable'] = ping_result.get('reachable', False)
                device['response_time'] = ping_result.get('response_time', 'N/A')
                device['ping_status'] = 'Online' if ping_result.get('reachable') else 'Offline'
                updated = True
                break
        
        # If device not found, create a new entry
        if not updated:
            devices.append({
                'ip_address': ip_address,
                'hostname': resolve_hostname(ip_address),
                'mac_address': 'Unknown',
                'manufacturer': 'Unknown',
                'last_ping': datetime.now().isoformat(),
                'reachable': ping_result.get('reachable', False),
                'response_time': ping_result.get('response_time', 'N/A'),
                'ping_status': 'Online' if ping_result.get('reachable') else 'Offline',
                'source': 'Ping Test'
            })
        
        # Save updated data
        data['devices'] = devices
        save_discovered_devices(devices, 'Ping Update')
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating ping result for {ip_address}: {e}")
        return False

def set_device_name(mac_address, ip_address, new_name):
    """Set custom name for a device and update discovered devices"""
    device_names = load_device_names()
    
    # Use MAC address as primary key
    device_names[mac_address] = {
        'name': new_name,
        'ip_address': ip_address,
        'last_updated': datetime.now().isoformat(),
        'mac_address': mac_address
    }
    
    # Also update the discovered devices data
    try:
        data = load_discovered_devices()
        devices = data.get('devices', [])
        
        # Update device in discovered devices list
        for device in devices:
            if (device.get('mac_address') == mac_address or 
                device.get('ip_address') == ip_address):
                device['hostname'] = new_name
                device['custom_name'] = new_name
                device['last_updated'] = datetime.now().isoformat()
        
        save_discovered_devices(devices, 'Name Update')
        
    except Exception as e:
        logger.error(f"Error updating discovered devices with new name: {e}")
    
    return save_device_names(device_names)

def ping_device(ip_address, timeout=5):
    """Ping a device and return status with response time"""
    try:
        if platform.system().lower() == 'windows':
            # Windows ping command
            result = subprocess.run(
                ['ping', '-n', '1', '-w', str(timeout * 1000), ip_address],
                capture_output=True,
                text=True,
                timeout=timeout + 2
            )
        else:
            # Linux/Unix ping command
            result = subprocess.run(
                ['ping', '-c', '1', '-W', str(timeout), ip_address],
                capture_output=True,
                text=True,
                timeout=timeout + 2
            )
        
        success = result.returncode == 0
        response_time = None
        
        if success:
            # Extract response time from ping output
            output = result.stdout.lower()
            if 'time=' in output:
                try:
                    time_part = output.split('time=')[1].split()[0]
                    response_time = float(time_part.replace('ms', ''))
                except:
                    response_time = 0.0
        
        return {
            'success': success,
            'reachable': success,
            'response_time': f"{response_time:.2f}ms" if response_time else "N/A",
            'ip_address': ip_address
        }
        
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'reachable': False,
            'response_time': "Timeout",
            'ip_address': ip_address,
            'error': 'Ping timeout'
        }
    except Exception as e:
        logger.error(f"Ping error for {ip_address}: {e}")
        return {
            'success': False,
            'reachable': False,
            'response_time': "Error",
            'ip_address': ip_address,
            'error': str(e)
        }

def get_network_settings():
    """Load network settings from JSON file"""
    try:
        settings_file = 'network_settings.json'
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                raw = json.load(f)
                # Normalize keys to camelCase for frontend compatibility
                return {
                    'startIp': raw.get('startIp') or raw.get('start_ip') or raw.get('startIP') or raw.get('start', ''),
                    'endIp': raw.get('endIp') or raw.get('end_ip') or raw.get('endIP') or raw.get('end', ''),
                    'timeout': raw.get('timeout', 2000),
                    'maxConcurrent': raw.get('maxConcurrent') or raw.get('max_concurrent') or raw.get('max_threads', 10),
                    'networkRange': raw.get('networkRange') or raw.get('network_range') or raw.get('network', '')
                }
        
        # Default settings (camelCase keys expected by frontend)
        return {
            'startIp': '192.168.1.1',
            'endIp': '192.168.1.50',
            'timeout': 2000,
            'maxConcurrent': 10,
            'networkRange': '192.168.1.0/24'
        }
    except Exception as e:
        logger.error(f"Error loading network settings: {e}")
        return {}

def save_network_settings(settings):
    """Save network settings to JSON file"""
    try:
        settings_file = 'network_settings.json'
        # Canonicalize incoming settings to a stable schema used by the UI
        canonical = {}

        # Accept multiple key names and normalize
        canonical['startIp'] = settings.get('startIp') or settings.get('start_ip') or settings.get('start') or ''
        canonical['endIp'] = settings.get('endIp') or settings.get('end_ip') or settings.get('end') or ''

        # Timeout: frontend historically sent milliseconds, some server calls send seconds.
        # Normalize to milliseconds. If value looks small (<= 10) assume seconds.
        raw_timeout = settings.get('timeout') or settings.get('timeoutMs') or settings.get('pingTimeout') or 2000
        try:
            t = int(raw_timeout)
        except Exception:
            # try floats
            try:
                t = int(float(raw_timeout))
            except Exception:
                t = 2000

        if t <= 10:
            # treat as seconds
            t = t * 1000

        canonical['timeout'] = t

        canonical['maxConcurrent'] = settings.get('maxConcurrent') or settings.get('max_concurrent') or settings.get('maxThreads') or settings.get('max_threads') or 10
        canonical['networkRange'] = settings.get('networkRange') or settings.get('network_range') or settings.get('network') or ''

        with open(settings_file, 'w') as f:
            json.dump(canonical, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving network settings: {e}")
        return False

def validate_ip_address(ip):
    """Validate IP address format"""
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        for part in parts:
            if not 0 <= int(part) <= 255:
                return False
        return True
    except:
        return False

def validate_network_range(network_range):
    """Validate CIDR network range"""
    try:
        if '/' not in network_range:
            return False
        ip, prefix = network_range.split('/')
        if not validate_ip_address(ip):
            return False
        if not 0 <= int(prefix) <= 32:
            return False
        return True
    except:
        return False

def format_mac_address(mac):
    """Format MAC address consistently"""
    if not mac:
        return "Unknown"
    
    # Remove common separators and convert to lowercase
    mac_clean = mac.replace(':', '').replace('-', '').replace('.', '').lower()
    
    # Add colons every 2 characters
    if len(mac_clean) == 12:
        return ':'.join(mac_clean[i:i+2] for i in range(0, 12, 2))
    
    return mac

def get_device_manufacturer(mac_address):
    """Get device manufacturer from MAC address OUI"""
    if not mac_address or mac_address == "Unknown":
        return "Unknown"
    
    # Simple OUI lookup (first 3 octets)
    oui_map = {
        '00:0c:29': 'VMware',
        '00:50:56': 'VMware',
        '08:00:27': 'VirtualBox',
        '00:1a:a0': 'Dell',
        '00:24:21': 'Dell',
        '74:46:a0': 'HP Enterprise',
        '08:2e:5f': 'HP Enterprise',
        'b8:ca:3a': 'Dell',
        '90:b1:1c': 'Dell',
        'f4:8e:38': 'Cisco',
        '3c:ec:ef': 'Cisco',
        '74:f8:db': 'Ubiquiti',
        'f0:9f:c2': 'Ubiquiti',
        '00:04:a3': 'Microchip',
        '00:e0:4c': 'Realtek',
        '00:c0:ee': 'Unknown OEM',
        'ff:ff:ff': 'Broadcast'
    }
    
    try:
        oui = mac_address[:8].lower()
        return oui_map.get(oui, "Unknown")
    except:
        return "Unknown"

def determine_device_type(ip_address, mac_address, manufacturer=None):
    """Determine device type based on IP, MAC, and manufacturer"""
    if not manufacturer:
        manufacturer = get_device_manufacturer(mac_address)
    
    # Broadcast/Multicast addresses
    if mac_address and (mac_address.startswith('ff:ff:') or mac_address.startswith('01:00:')):
        return "Broadcast/Multicast"
    
    # Virtual machines
    if manufacturer in ['VMware', 'VirtualBox']:
        return "Virtual Machine"
    
    # Network infrastructure
    if manufacturer in ['HP Enterprise', 'Cisco']:
        if ip_address and (ip_address.endswith('.1') or ip_address.endswith('.254')):
            return "Network Gateway"
        return "Network Infrastructure"
    
    # Computers/Servers
    if manufacturer in ['Dell', 'HP']:
        return "Computer/Server"
    
    # Network devices
    if manufacturer == 'Ubiquiti':
        return "Network Device"
    
    # Special IP ranges
    if ip_address:
        if ip_address.startswith('224.') or ip_address.startswith('239.'):
            return "Multicast"
        elif ip_address.endswith('.1') or ip_address.endswith('.254'):
            return "Gateway/Router"
    
    return "Network Device"

def scan_device_ports(ip_address, common_ports=None, timeout=1):
    """Scan common ports on a device to identify services and calculate NAS confidence"""
    if not common_ports:
        # Enhanced port list with MEDICAL DEVICE and PACS-specific services
        # Prioritize medical imaging and DICOM ports for faster identification
        common_ports = [
            104,      # DICOM (primary medical imaging protocol)
            11112,    # DICOM C-MOVE (image transfer)
            8104,     # DICOM C-FIND (query/retrieve)
            2762,     # DICOM TLS (secure DICOM)
            4006,     # DICOM over TLS
            2575,     # DICOM Web Services
            4242,     # DICOM TLS alternative
            2761,     # DICOM TLS alternative
            11113,    # DICOM C-STORE (storage)
            11114,    # DICOM C-GET (retrieve)
            
            # Medical device management and web interfaces
            80,       # HTTP (web interface)
            443,      # HTTPS (secure web interface)
            8080,     # HTTP Alt (alternative web management)
            8443,     # HTTPS Alt
            9000,     # Common medical device management
            9090,     # Common medical device management
            
            # Remote management
            22,       # SSH
            23,       # Telnet
            161,      # SNMP
            
            # Storage and file sharing for medical images
            445,      # SMB/CIFS
            139,      # NetBIOS/SMB
            2049,     # NFS
            21,       # FTP
            
            # Database systems common in medical information systems
            3306,     # MySQL
            1433,     # SQL Server
            1521,     # Oracle
            5432,     # PostgreSQL
            
            # Network services
            53,       # DNS
            67,       # DHCP
            68,       # DHCP
            123,      # NTP
            514       # Syslog
        ]
    
    open_ports = []
    services = []
    nas_indicators = []
    
    for port in common_ports:
        try:
            # Set socket timeout
            # Use a per-call timeout; avoid changing global default in tight loops
            # socket.setdefaulttimeout(timeout)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            result = sock.connect_ex((ip_address, port))
            
            if result == 0:
                open_ports.append(port)
                
                # Identify service by port
                service_name = get_service_name(port)
                if service_name:
                    services.append(f"{service_name} ({port})")
                    
                    # Check for NAS indicators
                    nas_indicator = get_nas_indicator(port, service_name)
                    if nas_indicator:
                        nas_indicators.append(nas_indicator)
                else:
                    services.append(f"Port {port}")
                    
            sock.close()
            
        except Exception as e:
            logger.debug(f"Error scanning port {port} on {ip_address}: {e}")
            continue
    
    # Calculate MEDICAL DEVICE confidence score
    nas_confidence = calculate_nas_confidence(open_ports, nas_indicators)
    
    return {
        'ip_address': ip_address,
        'open_ports': open_ports,
        'services': services,
        'nas_indicators': nas_indicators,
        'nas_confidence_score': nas_confidence['score'],
        'nas_confidence_reason': nas_confidence['reason'],
        'nas_confidence_level': nas_confidence['level'],
        'medical_device_assessment': nas_confidence['assessment'],
        'total_ports_scanned': len(common_ports),
        'open_port_count': len(open_ports),
        'scan_timestamp': datetime.now().isoformat()
    }

def get_service_name(port):
    """Get common service name for a port number"""
    services = {
        21: 'FTP',
        22: 'SSH',
        23: 'Telnet',
        25: 'SMTP',
        53: 'DNS',
        80: 'HTTP',
        110: 'POP3',
        135: 'RPC',
        139: 'NetBIOS/SMB',
        143: 'IMAP',
        161: 'SNMP',
        443: 'HTTPS',
        445: 'SMB/CIFS',
        993: 'IMAPS',
        995: 'POP3S',
        1433: 'SQL Server',
        1521: 'Oracle',
        2049: 'NFS',
        3306: 'MySQL',
        3389: 'RDP',
        4444: 'DICOM',
        5000: 'Synology HTTP',
        5001: 'Synology HTTPS',
        8080: 'HTTP Alt',
        8081: 'NAS Web Interface',
        8104: 'DICOM C-FIND',
        8443: 'HTTPS Alt',
        9000: 'NAS Management',
        11112: 'DICOM C-MOVE',
        50001: 'QNAP Management',
        51413: 'Transmission',
    }
    return services.get(port)

def get_service_name(port):
    """Get common service name for a port number (medical device focused)"""
    services = {
        # Medical Imaging and DICOM
        104: 'DICOM',
        11112: 'DICOM C-MOVE',
        8104: 'DICOM C-FIND',
        2762: 'DICOM TLS',
        4006: 'DICOM TLS',
        2575: 'DICOM Web Services',
        4242: 'DICOM TLS Alt',
        2761: 'DICOM TLS Alt',
        11113: 'DICOM C-STORE',
        11114: 'DICOM C-GET',
        
        # Web Services
        80: 'HTTP',
        443: 'HTTPS',
        8080: 'HTTP Alt',
        8443: 'HTTPS Alt',
        9000: 'Medical Mgmt',
        9090: 'Medical Mgmt',
        
        # Remote Management
        22: 'SSH',
        23: 'Telnet',
        161: 'SNMP',
        
        # File Sharing and Storage
        21: 'FTP',
        139: 'NetBIOS/SMB',
        445: 'SMB/CIFS',
        2049: 'NFS',
        
        # Database Systems
        3306: 'MySQL',
        1433: 'SQL Server',
        1521: 'Oracle',
        5432: 'PostgreSQL',
        
        # Network Services
        53: 'DNS',
        67: 'DHCP Server',
        68: 'DHCP Client',
        123: 'NTP',
        514: 'Syslog',
        
        # Legacy services
        25: 'SMTP',
        110: 'POP3',
        143: 'IMAP',
        993: 'IMAPS',
        995: 'POP3S',
        3389: 'RDP',
        5900: 'VNC'
    }
    return services.get(port)

def get_nas_indicator(port, service_name):
    """Identify medical device indicators for scoring"""
    medical_indicators = {
        # Primary Medical Imaging Ports
        104: {'type': 'DICOM Protocol', 'score': 50, 'description': 'Primary DICOM communication port'},
        11112: {'type': 'DICOM C-MOVE', 'score': 45, 'description': 'DICOM image transfer protocol'},
        8104: {'type': 'DICOM C-FIND', 'score': 40, 'description': 'DICOM query/retrieve protocol'},
        2762: {'type': 'DICOM TLS', 'score': 35, 'description': 'Secure DICOM over TLS'},
        4006: {'type': 'DICOM TLS Alt', 'score': 35, 'description': 'Alternative DICOM TLS port'},
        2575: {'type': 'DICOM Web Services', 'score': 30, 'description': 'DICOM web services'},
        
        # Medical System Management
        80: {'type': 'HTTP Web Interface', 'score': 25, 'description': 'Medical device web management'},
        443: {'type': 'HTTPS Web Interface', 'score': 30, 'description': 'Secure medical device web management'},
        8080: {'type': 'HTTP Alt Management', 'score': 20, 'description': 'Alternative web management'},
        8443: {'type': 'HTTPS Alt Management', 'score': 25, 'description': 'Alternative secure web management'},
        9000: {'type': 'Medical Device Mgmt', 'score': 20, 'description': 'Medical device management interface'},
        
        # Remote Management
        22: {'type': 'SSH Management', 'score': 15, 'description': 'Secure remote management'},
        23: {'type': 'Telnet Management', 'score': 10, 'description': 'Legacy remote management'},
        161: {'type': 'SNMP Monitoring', 'score': 20, 'description': 'Network monitoring and management'},
        
        # Storage and File Sharing
        445: {'type': 'SMB/CIFS Storage', 'score': 20, 'description': 'Medical image storage sharing'},
        139: {'type': 'NetBIOS/SMB', 'score': 15, 'description': 'Legacy file sharing'},
        2049: {'type': 'NFS Storage', 'score': 20, 'description': 'Network file system for images'},
        21: {'type': 'FTP Transfer', 'score': 15, 'description': 'File transfer for medical images'},
        
        # Database Systems
        3306: {'type': 'MySQL Database', 'score': 15, 'description': 'Common in medical information systems'},
        1433: {'type': 'SQL Server', 'score': 15, 'description': 'Common in medical information systems'},
        1521: {'type': 'Oracle Database', 'score': 15, 'description': 'Common in medical information systems'},
        5432: {'type': 'PostgreSQL', 'score': 15, 'description': 'Common in medical information systems'},
        
        # Specialized Medical Ports
        4242: {'type': 'DICOM TLS Alt', 'score': 30, 'description': 'Alternative DICOM TLS'},
        2761: {'type': 'DICOM TLS Alt', 'score': 30, 'description': 'Alternative DICOM TLS'},
        11113: {'type': 'DICOM C-STORE', 'score': 35, 'description': 'DICOM storage protocol'},
        11114: {'type': 'DICOM C-GET', 'score': 35, 'description': 'DICOM retrieval protocol'}
    }
    return medical_indicators.get(port)

def calculate_nas_confidence(open_ports, nas_indicators):
    """Calculate confidence score that device is a MEDICAL IMAGING device"""
    score = 0
    reasons = []
    
    # Base scoring from medical device indicators
    for indicator in nas_indicators:
        if indicator:
            score += indicator['score']
            reasons.append(f"{indicator['type']}: +{indicator['score']} ({indicator['description']})")
    
    # Bonus scoring for medical device combinations
    port_set = set(open_ports)
    
    # DICOM protocol suite bonus (most important)
    if 104 in port_set and (11112 in port_set or 8104 in port_set):
        score += 25
        reasons.append("DICOM Protocol Suite: +25 (Complete DICOM implementation)")
    
    # PACS system indicators
    if (80 in port_set or 443 in port_set) and (3306 in port_set or 1433 in port_set or 1521 in port_set):
        score += 20
        reasons.append("Web + Database: +20 (PACS system pattern)")
    
    # Medical imaging device bonus
    medical_ports = [104, 11112, 8104, 2762, 4006, 2575, 4242, 2761, 11113, 11114]
    medical_port_count = len([p for p in medical_ports if p in port_set])
    if medical_port_count >= 2:
        bonus = medical_port_count * 10
        score += bonus
        reasons.append(f"Multiple Medical Ports: +{bonus} ({medical_port_count} medical ports)")
    
    # Storage + medical protocols
    if (445 in port_set or 2049 in port_set) and 104 in port_set:
        score += 15
        reasons.append("Storage + DICOM: +15 (Image storage with DICOM)")
    
    # Management interface bonus
    if (22 in port_set or 161 in port_set) and (80 in port_set or 443 in port_set):
        score += 12
        reasons.append("Management Combo: +12 (Remote + web management)")
    
    # Multiple file protocols bonus
    file_protocols = [21, 139, 445, 2049]
    file_protocol_count = len([p for p in file_protocols if p in port_set])
    if file_protocol_count >= 2:
        bonus = file_protocol_count * 8
        score += bonus
        reasons.append(f"Multiple File Protocols: +{bonus} ({file_protocol_count} protocols)")
    
    # Web services bonus
    web_ports = [80, 443, 8080, 8443, 9000]
    web_port_count = len([p for p in web_ports if p in port_set])
    if web_port_count >= 2:
        bonus = web_port_count * 5
        score += bonus
        reasons.append(f"Multiple Web Services: +{bonus} ({web_port_count} web ports)")
    
    # Cap score at 100 and floor at 0
    score = max(0, min(score, 100))

    # Map to confidence percent (0-100)
    confidence_percent = score

    # Determine confidence level
    if confidence_percent >= 70:
        level = "VERY HIGH"
        color = "success"
        assessment = "Medical Imaging Device"
    elif confidence_percent >= 50:
        level = "HIGH"
        color = "success"
        assessment = "Likely Medical Device"
    elif confidence_percent >= 30:
        level = "MEDIUM"
        color = "warning"
        assessment = "Possible Medical Device"
    elif confidence_percent >= 15:
        level = "LOW"
        color = "secondary"
        assessment = "Unlikely Medical Device"
    else:
        level = "VERY LOW"
        color = "secondary"
        assessment = "Not a Medical Device"

    return {
        'score': confidence_percent,
        'level': level,
        'color': color,
        'assessment': assessment,
        'reason': reasons
    }
