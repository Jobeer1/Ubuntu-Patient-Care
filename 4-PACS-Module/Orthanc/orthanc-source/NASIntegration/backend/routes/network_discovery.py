"""
Network Discovery Module for South African Medical Imaging System
Handles ARP table scanning, range ping, and enhanced network discovery
"""

import subprocess
import platform
import ipaddress
import concurrent.futures
import logging
import re
import json
import os
from datetime import datetime
import socket
from contextlib import closing

def scan_device_ports(ip_address, ports=None, timeout=2):
    """Enhanced device port scanning with comprehensive information collection"""
    if ports is None:
        ports = [21, 22, 23, 25, 53, 80, 104, 110, 111, 139, 143, 443, 445, 993, 995, 2049, 3306, 5432, 8042, 8080, 8104, 11112]

    open_ports = []
    device_info = {
        'ip_address': ip_address,
        'scan_timestamp': datetime.now().isoformat(),
        'os_fingerprint': 'Unknown',
        'device_type': 'Unknown',
        'services': [],
        'vulnerabilities': [],
        'network_interfaces': []
    }

    for port in ports:
        try:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((ip_address, port))
                if result == 0:
                    # Port is open - collect detailed service information
                    service_info = get_detailed_service_info(ip_address, port, timeout)
                    open_ports.append({
                        'port': port,
                        'protocol': 'tcp',
                        'service': service_info.get('service', get_service_name(port)),
                        'status': 'open',
                        'version': service_info.get('version', 'Unknown'),
                        'banner': service_info.get('banner', ''),
                        'ssl_info': service_info.get('ssl_info', {}),
                        'last_seen': datetime.now().isoformat()
                    })

                    # Update device info based on service
                    if port == 22:
                        device_info['os_fingerprint'] = 'Linux/Unix'
                        device_info['device_type'] = 'Server'
                    elif port == 445:
                        device_info['os_fingerprint'] = 'Windows'
                        device_info['device_type'] = 'Windows Server'
                    elif port == 548:
                        device_info['device_type'] = 'Apple Device'
                    elif port in [104, 11112, 8042, 8104]:
                        device_info['device_type'] = 'Medical Imaging Device'
                        device_info['services'].append('DICOM')

        except Exception as e:
            logger.debug(f"Port scan error for {ip_address}:{port} - {e}")
            continue

    device_info['open_ports'] = open_ports
    device_info['total_ports_scanned'] = len(ports)
    device_info['port_scan_completed'] = True

    # Store comprehensive device information in database
    device_db.store_device_info(ip_address, device_info)

    return device_info

def get_detailed_service_info(ip_address, port, timeout=2):
    """Get detailed service information for a specific port"""
    try:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(timeout)
            sock.connect((ip_address, port))

            service_info = {
                'service': get_service_name(port),
                'version': 'Unknown',
                'banner': '',
                'ssl_info': {}
            }

            # Try to get service banner
            try:
                if port == 80 or port == 8080:
                    sock.send(b"GET / HTTP/1.0\r\n\r\n")
                    banner = sock.recv(1024).decode('utf-8', errors='ignore')
                    service_info['banner'] = banner.split('\n')[0] if banner else ''
                    if 'Server:' in banner:
                        server_line = [line for line in banner.split('\n') if line.startswith('Server:')][0]
                        service_info['version'] = server_line.replace('Server:', '').strip()

                elif port == 443:
                    # For HTTPS, try to get certificate info
                    import ssl
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE

                    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as ssl_sock:
                        ssl_sock.settimeout(timeout)
                        ssl_conn = context.wrap_socket(ssl_sock, server_hostname=ip_address)
                        ssl_conn.connect((ip_address, port))

                        cert = ssl_conn.getpeercert()
                        if cert:
                            service_info['ssl_info'] = {
                                'issuer': dict(cert.get('issuer', [])),
                                'subject': dict(cert.get('subject', [])),
                                'notBefore': cert.get('notBefore', ''),
                                'notAfter': cert.get('notAfter', '')
                            }

                elif port == 22:
                    # SSH banner
                    banner = sock.recv(256).decode('utf-8', errors='ignore')
                    service_info['banner'] = banner.strip()
                    if 'SSH-' in banner:
                        service_info['version'] = banner.split('SSH-')[1].split()[0]

                elif port == 25:
                    # SMTP banner
                    banner = sock.recv(256).decode('utf-8', errors='ignore')
                    service_info['banner'] = banner.strip()

                elif port in [104, 11112, 8042, 8104]:
                    # DICOM related services
                    service_info['service'] = 'DICOM'
                    if port == 104:
                        service_info['version'] = 'DICOM Standard'
                    elif port == 11112:
                        service_info['version'] = 'DICOM Web Services'
                    elif port == 8042:
                        service_info['version'] = 'Orthanc PACS'
                    elif port == 8104:
                        service_info['version'] = 'DICOM TLS'

            except Exception as e:
                logger.debug(f"Banner grab failed for {ip_address}:{port} - {e}")

            return service_info

    except Exception as e:
        logger.debug(f"Service info collection failed for {ip_address}:{port} - {e}")
        return {
            'service': get_service_name(port),
            'version': 'Unknown',
            'banner': '',
            'ssl_info': {}
        }

def get_service_name(port):
    """Get service name for common ports"""
    port_services = {
        21: 'FTP',
        22: 'SSH',
        23: 'Telnet',
        25: 'SMTP',
        53: 'DNS',
        80: 'HTTP',
        110: 'POP3',
        143: 'IMAP',
        443: 'HTTPS',
        993: 'IMAPS',
        995: 'POP3S',
        104: 'DICOM',
        111: 'RPC',
        139: 'NetBIOS',
        445: 'SMB',
        993: 'IMAPS',
        2049: 'NFS',
        3306: 'MySQL',
        5432: 'PostgreSQL',
        8080: 'HTTP-Alt',
        8042: 'Orthanc',
        8104: 'DICOM-TLS',
        11112: 'DICOM-Web'
    }
    return port_services.get(port, 'Unknown')

def get_device_name(mac_address, ip_address):
    """Get custom device name"""
    try:
        # Try to resolve hostname
        hostname = socket.gethostbyaddr(ip_address)[0]
        return hostname
    except:
        return f"Device-{ip_address}"

def get_device_manufacturer(mac_address):
    """Enhanced device manufacturer lookup from MAC address"""
    if not mac_address or mac_address == 'Unknown':
        return 'Unknown'

    # Normalize MAC address format
    mac = mac_address.replace('-', ':').replace('.', ':').upper()
    if len(mac) < 8:
        return 'Unknown'

    mac_prefix = mac[:8]

    # Comprehensive MAC vendor database
    vendors = {
        # Medical Device Manufacturers
        '00:11:22': 'Siemens Healthcare',
        '00:13:37': 'GE Healthcare',
        '00:14:2D': 'Philips Healthcare',
        '00:15:17': 'Carestream Health',
        '00:16:35': 'Agfa Healthcare',
        '00:17:3F': 'McKesson Medical',
        '00:18:8B': 'Philips Medical',
        '00:19:7E': 'Philips Healthcare',
        '00:1A:4D': 'Gendex Dental',
        '00:1B:21': 'Intel (Medical)',
        '00:1C:23': 'Siemens Medical',
        '00:1D:7E': 'Cisco (Medical)',
        '00:1E:13': 'Cisco Systems',
        '00:1F:5B': 'Apple (Medical)',
        '00:21:5A': 'Hewlett Packard (Medical)',
        '00:22:64': 'Thomson Medical',
        '00:23:5E': 'Cisco SPVTG',
        '00:24:81': 'Hewlett Packard',
        '00:25:84': 'Cisco SPVTG',
        '00:26:73': 'Cisco Systems',
        '00:27:0C': 'Cisco Systems',
        '00:50:56': 'VMware',
        '00:0C:29': 'VMware',
        '00:05:69': 'VMware',
        '00:1C:14': 'VMware',
        '00:1C:42': 'Parallels',
        '02:42:AC': 'Docker',
        '0A:00:27': 'VirtualBox',
        '52:54:00': 'QEMU',
        'B8:27:EB': 'Raspberry Pi Foundation',
        'DC:A6:32': 'Raspberry Pi Foundation',
        'E4:5F:01': 'Raspberry Pi Foundation',
        '28:CD:C1': 'Apple',
        '8C:85:90': 'Apple',
        'AC:BC:32': 'Apple',
        '00:11:24': 'Apple',
        '00:14:51': 'Apple',
        '00:16:CB': 'Apple',
        '00:17:F2': 'Apple',
        '00:19:E3': 'Apple',
        '00:1B:63': 'Apple',
        '00:1C:B3': 'Apple',
        '00:1D:4F': 'Apple',
        '00:1E:52': 'Apple',
        '00:1E:C2': 'Apple',
        '00:1F:5B': 'Apple',
        '00:1F:F3': 'Apple',
        '00:21:E9': 'Apple',
        '00:22:41': 'Apple',
        '00:23:12': 'Apple',
        '00:23:32': 'Apple',
        '00:23:6C': 'Apple',
        '00:24:36': 'Apple',
        '00:25:00': 'Apple',
        '00:25:4B': 'Apple',
        '00:26:08': 'Apple',
        '00:26:4A': 'Apple',
        '00:26:B0': 'Apple',
        '00:26:BB': 'Apple',
        '00:27:22': 'Apple',
        '00:30:65': 'Apple',
        '00:50:E4': 'Apple',
        '00:61:71': 'Apple',
        '00:6D:52': 'Apple',
        '00:88:65': 'Apple',
        '00:A0:40': 'Apple',
        '00:C6:10': 'Apple',
        '00:CD:FE': 'Apple',
        '00:F4:B9': 'Apple',
        '04:0C:CE': 'Apple',
        '04:1E:64': 'Apple',
        '04:26:65': 'Apple',
        '04:48:9A': 'Apple',
        '04:54:53': 'Apple',
        '04:D3:CF': 'Apple',
        '04:E5:36': 'Apple',
        '04:F1:3E': 'Apple',
        '04:F7:E4': 'Apple',
        '08:00:07': 'Apple',
        '08:66:98': 'Apple',
        '08:74:02': 'Apple',
        '0C:30:21': 'Apple',
        '0C:3E:9F': 'Apple',
        '0C:4D:E9': 'Apple',
        '0C:77:1A': 'Apple',
        '0C:84:DC': 'Apple',
        '10:1C:0C': 'Apple',
        '10:40:F3': 'Apple',
        '10:93:E9': 'Apple',
        '10:9A:DD': 'Apple',
        '10:DD:B1': 'Apple',
        '14:10:9F': 'Apple',
        '14:5A:05': 'Apple',
        '14:8F:C6': 'Apple',
        '14:99:E2': 'Apple',
        '14:DA:E9': 'Apple',
        '18:20:32': 'Apple',
        '18:34:51': 'Apple',
        '18:65:90': 'Apple',
        '18:9E:FC': 'Apple',
        '18:E7:F4': 'Apple',
        '1C:1A:C0': 'Apple',
        '1C:5C:F2': 'Apple',
        '1C:AB:A7': 'Apple',
        '1C:E6:2B': 'Apple',
        '20:7D:74': 'Apple',
        '20:A2:E4': 'Apple',
        '20:C9:D0': 'Apple',
        '24:1F:2C': 'Apple',
        '24:5B:A7': 'Apple',
        '24:A0:74': 'Apple',
        '24:A2:E1': 'Apple',
        '24:AB:81': 'Apple',
        '24:E3:14': 'Apple',
        '28:0B:5C': 'Apple',
        '28:0D:FC': 'Apple',
        '28:37:37': 'Apple',
        '28:5A:EB': 'Apple',
        '28:6A:B8': 'Apple',
        '28:CF:DA': 'Apple',
        '28:CF:E9': 'Apple',
        '28:E0:2C': 'Apple',
        '28:E1:4C': 'Apple',
        '28:E7:CF': 'Apple',
        '28:ED:6A': 'Apple',
        '28:F0:76': 'Apple',
        '2C:1F:23': 'Apple',
        '2C:20:0B': 'Apple',
        '2C:B4:3A': 'Apple',
        '2C:BE:08': 'Apple',
        '2C:F0:EE': 'Apple',
        '2C:F5:D3': 'Apple',
        '30:10:E4': 'Apple',
        '30:35:AD': 'Apple',
        '30:57:14': 'Apple',
        '30:63:6B': 'Apple',
        '30:90:AB': 'Apple',
        '30:F7:C5': 'Apple',
        '34:08:04': 'Apple',
        '34:12:98': 'Apple',
        '34:15:9E': 'Apple',
        '34:36:3B': 'Apple',
        '34:51:C9': 'Apple',
        '34:8B:75': 'Apple',
        '34:A3:95': 'Apple',
        '34:C0:59': 'Apple',
        '34:E2:FD': 'Apple',
        '38:0F:4A': 'Apple',
        '38:48:4C': 'Apple',
        '38:71:DE': 'Apple',
        '38:B5:4D': 'Apple',
        '38:C9:86': 'Apple',
        '3C:07:54': 'Apple',
        '3C:15:C2': 'Apple',
        '3C:22:FB': 'Apple',
        '3C:2E:F9': 'Apple',
        '3C:43:8E': 'Apple',
        '3C:AB:8E': 'Apple',
        '3C:D0:F8': 'Apple',
        '40:30:04': 'Apple',
        '40:33:1A': 'Apple',
        '40:3C:FC': 'Apple',
        '40:4D:7F': 'Apple',
        '40:6C:8F': 'Apple',
        '40:A6:D9': 'Apple',
        '40:B3:95': 'Apple',
        '40:D3:2D': 'Apple',
        '44:00:10': 'Apple',
        '44:2A:60': 'Apple',
        '44:4D:50': 'Apple',
        '44:FB:42': 'Apple',
        '48:3B:38': 'Apple',
        '48:60:BC': 'Apple',
        '48:74:12': 'Apple',
        '48:89:E7': 'Apple',
        '48:A1:95': 'Apple',
        '48:BF:6B': 'Apple',
        '48:D7:05': 'Apple',
        '48:E9:F1': 'Apple',
        '4C:32:75': 'Apple',
        '4C:57:CA': 'Apple',
        '4C:7C:5F': 'Apple',
        '4C:B1:99': 'Apple',
        '50:32:37': 'Apple',
        '50:7A:55': 'Apple',
        '50:EA:D6': 'Apple',
        '54:26:96': 'Apple',
        '54:4E:90': 'Apple',
        '54:72:4F': 'Apple',
        '54:9F:13': 'Apple',
        '54:AE:27': 'Apple',
        '54:E4:3A': 'Apple',
        '58:1F:AA': 'Apple',
        '58:40:4E': 'Apple',
        '58:55:CA': 'Apple',
        '58:7F:57': 'Apple',
        '58:B0:35': 'Apple',
        '5C:59:48': 'Apple',
        '5C:8D:4E': 'Apple',
        '5C:95:AE': 'Apple',
        '5C:97:F3': 'Apple',
        '5C:AD:CF': 'Apple',
        '5C:F5:DA': 'Apple',
        '5C:F7:E6': 'Apple',
        '60:03:08': 'Apple',
        '60:33:4B': 'Apple',
        '60:69:44': 'Apple',
        '60:7E:CD': 'Apple',
        '60:92:17': 'Apple',
        '60:A3:7D': 'Apple',
        '60:C5:47': 'Apple',
        '60:D9:C7': 'Apple',
        '60:F1:3D': 'Apple',
        '60:F4:45': 'Apple',
        '60:F8:1D': 'Apple',
        '60:FA:CD': 'Apple',
        '64:20:0F': 'Apple',
        '64:5A:04': 'Apple',
        '64:9A:BE': 'Apple',
        '64:A3:CB': 'Apple',
        '64:B0:A6': 'Apple',
        '64:B9:E8': 'Apple',
        '64:E6:82': 'Apple',
        '68:09:27': 'Apple',
        '68:5B:35': 'Apple',
        '68:64:4B': 'Apple',
        '68:96:7B': 'Apple',
        '68:9C:70': 'Apple',
        '68:A8:6D': 'Apple',
        '68:AE:20': 'Apple',
        '68:D9:3C': 'Apple',
        '68:FB:7E': 'Apple',
        '6C:19:C0': 'Apple',
        '6C:3E:6D': 'Apple',
        '6C:40:08': 'Apple',
        '6C:70:9F': 'Apple',
        '6C:72:E7': 'Apple',
        '6C:94:F8': 'Apple',
        '6C:96:CF': 'Apple',
        '6C:C2:6B': 'Apple',
        '70:11:24': 'Apple',
        '70:3E:AC': 'Apple',
        '70:48:0F': 'Apple',
        '70:56:81': 'Apple',
        '70:70:0D': 'Apple',
        '70:73:CB': 'Apple',
        '70:7D:B9': 'Apple',
        '70:CD:60': 'Apple',
        '70:DE:E2': 'Apple',
        '70:E2:84': 'Apple',
        '74:1B:B2': 'Apple',
        '74:81:14': 'Apple',
        '74:8D:08': 'Apple',
        '74:C2:46': 'Apple',
        '74:E1:B6': 'Apple',
        '74:E2:F5': 'Apple',
        '78:31:2B': 'Apple',
        '78:4F:43': 'Apple',
        '78:6C:1C': 'Apple',
        '78:7E:61': 'Apple',
        '78:9F:70': 'Apple',
        '78:A3:E4': 'Apple',
        '78:CA:39': 'Apple',
        '78:D7:5F': 'Apple',
        '7C:04:D0': 'Apple',
        '7C:11:BE': 'Apple',
        '7C:50:49': 'Apple',
        '7C:6D:62': 'Apple',
        '7C:C3:A1': 'Apple',
        '7C:D1:C3': 'Apple',
        '7C:F0:5F': 'Apple',
        '7C:FB:FB': 'Apple',
        '7E:3B:D8': 'Apple',
        '80:00:6E': 'Apple',
        '80:49:71': 'Apple',
        '80:92:9F': 'Apple',
        '80:BE:05': 'Apple',
        '80:D6:05': 'Apple',
        '80:E6:50': 'Apple',
        '80:EA:96': 'Apple',
        '84:29:99': 'Apple',
        '84:38:35': 'Apple',
        '84:78:8B': 'Apple',
        '84:89:87': 'Apple',
        '84:B1:53': 'Apple',
        '84:FC:FE': 'Apple',
        '86:00:1D': 'Apple',
        '88:1F:A1': 'Apple',
        '88:66:5A': 'Apple',
        '88:6B:6E': 'Apple',
        '88:C6:63': 'Apple',
        '8C:00:6D': 'Apple',
        '8C:29:37': 'Apple',
        '8C:58:77': 'Apple',
        '8C:7B:9D': 'Apple',
        '8C:7C:92': 'Apple',
        '8C:85:90': 'Apple',
        '8C:8E:F2': 'Apple',
        '8C:BE:BE': 'Apple',
        '90:27:E4': 'Apple',
        '90:3C:92': 'Apple',
        '90:72:40': 'Apple',
        '90:84:0D': 'Apple',
        '90:8D:6C': 'Apple',
        '90:A3:65': 'Apple',
        '90:B2:1F': 'Apple',
        '90:B9:31': 'Apple',
        '90:FD:61': 'Apple',
        '94:94:26': 'Apple',
        '94:B0:1F': 'Apple',
        '98:01:A7': 'Apple',
        '98:03:D8': 'Apple',
        '98:10:E8': 'Apple',
        '98:5A:EB': 'Apple',
        '98:9E:63': 'Apple',
        '98:B8:E3': 'Apple',
        '98:D6:BB': 'Apple',
        '98:D6:F7': 'Apple',
        '98:E0:D9': 'Apple',
        '9C:04:EB': 'Apple',
        '9C:20:7B': 'Apple',
        '9C:29:3F': 'Apple',
        '9C:35:EB': 'Apple',
        '9C:4E:36': 'Apple',
        '9C:8B:A0': 'Apple',
        '9C:F3:87': 'Apple',
        '9C:F4:8E': 'Apple',
        '9C:F6:1A': 'Apple',
        '9C:F8:DB': 'Apple',
        'A0:18:28': 'Apple',
        'A0:99:9B': 'Apple',
        'A0:D7:95': 'Apple',
        'A4:31:35': 'Apple',
        'A4:5E:60': 'Apple',
        'A4:67:06': 'Apple',
        'A4:B1:97': 'Apple',
        'A4:C3:61': 'Apple',
        'A4:D1:8C': 'Apple',
        'A4:F1:E8': 'Apple',
        'A8:20:66': 'Apple',
        'A8:5B:78': 'Apple',
        'A8:66:7F': 'Apple',
        'A8:87:4C': 'Apple',
        'A8:8E:24': 'Apple',
        'A8:96:8A': 'Apple',
        'A8:BB:CF': 'Apple',
        'A8:CB:95': 'Apple',
        'A8:DD:5F': 'Apple',
        'A8:FA:D8': 'Apple',
        'A8:FF:0A': 'Apple',
        'AC:29:3A': 'Apple',
        'AC:3C:0B': 'Apple',
        'AC:61:75': 'Apple',
        'AC:7F:3E': 'Apple',
        'AC:87:A3': 'Apple',
        'AC:BC:32': 'Apple',
        'AC:CF:5C': 'Apple',
        'AC:E4:B5': 'Apple',
        'B0:34:95': 'Apple',
        'B0:65:BD': 'Apple',
        'B0:98:2E': 'Apple',
        'B4:18:D1': 'Apple',
        'B4:8B:19': 'Apple',
        'B4:F0:AB': 'Apple',
        'B8:09:8A': 'Apple',
        'B8:17:C2': 'Apple',
        'B8:41:5F': 'Apple',
        'B8:44:D9': 'Apple',
        'B8:53:AC': 'Apple',
        'B8:78:2E': 'Apple',
        'B8:8D:12': 'Apple',
        'B8:C1:11': 'Apple',
        'B8:C7:5D': 'Apple',
        'B8:E8:56': 'Apple',
        'B8:F6:B1': 'Apple',
        'B8:FF:61': 'Apple',
        'BC:4C:C4': 'Apple',
        'BC:52:B7': 'Apple',
        'BC:6C:21': 'Apple',
        'BC:92:6B': 'Apple',
        'BC:9F:EF': 'Apple',
        'BC:A9:20': 'Apple',
        'BC:D0:74': 'Apple',
        'C0:63:94': 'Apple',
        'C0:84:7D': 'Apple',
        'C0:9F:42': 'Apple',
        'C0:CC:F8': 'Apple',
        'C4:2C:03': 'Apple',
        'C8:1E:E7': 'Apple',
        'C8:2A:14': 'Apple',
        'C8:33:4B': 'Apple',
        'C8:69:CD': 'Apple',
        'C8:B5:B7': 'Apple',
        'C8:BC:C8': 'Apple',
        'C8:D0:83': 'Apple',
        'C8:E0:EB': 'Apple',
        'CC:08:8D': 'Apple',
        'CC:20:E8': 'Apple',
        'CC:25:EF': 'Apple',
        'CC:44:63': 'Apple',
        'CC:78:5F': 'Apple',
        'D0:03:4B': 'Apple',
        'D0:23:DB': 'Apple',
        'D0:25:98': 'Apple',
        'D0:33:11': 'Apple',
        'D0:4F:7E': 'Apple',
        'D0:81:7A': 'Apple',
        'D0:A6:37': 'Apple',
        'D0:E1:40': 'Apple',
        'D4:61:2E': 'Apple',
        'D4:61:9D': 'Apple',
        'D4:90:9C': 'Apple',
        'D4:9A:20': 'Apple',
        'D4:F4:6F': 'Apple',
        'D6:31:6A': 'Apple',
        'D8:00:4D': 'Apple',
        'D8:30:62': 'Apple',
        'D8:96:95': 'Apple',
        'D8:A2:5E': 'Apple',
        'D8:BB:2C': 'Apple',
        'D8:CF:9C': 'Apple',
        'D8:D1:CB': 'Apple',
        'D8:FF:0C': 'Apple',
        'DC:0C:5C': 'Apple',
        'DC:2B:2A': 'Apple',
        'DC:2B:61': 'Apple',
        'DC:37:52': 'Apple',
        'DC:41:5F': 'Apple',
        'DC:4A:3E': 'Apple',
        'DC:86:D8': 'Apple',
        'DC:9B:9C': 'Apple',
        'DC:A9:04': 'Apple',
        'DC:F0:5D': 'Apple',
        'E0:AC:CB': 'Apple',
        'E0:B5:2D': 'Apple',
        'E0:B9:BA': 'Apple',
        'E0:C9:7A': 'Apple',
        'E0:F5:C6': 'Apple',
        'E0:F8:47': 'Apple',
        'E4:25:E7': 'Apple',
        'E4:8B:7F': 'Apple',
        'E4:98:D6': 'Apple',
        'E4:CE:8F': 'Apple',
        'E4:E4:AB': 'Apple',
        'E8:06:88': 'Apple',
        'E8:8D:28': 'Apple',
        'E8:B2:AC': 'Apple',
        'EC:2A:E0': 'Apple',
        'EC:35:86': 'Apple',
        'EC:85:2F': 'Apple',
        'F0:18:98': 'Apple',
        'F0:24:75': 'Apple',
        'F0:79:59': 'Apple',
        'F0:7F:06': 'Apple',
        'F0:7F:0C': 'Apple',
        'F0:99:BF': 'Apple',
        'F0:B4:79': 'Apple',
        'F0:CB:A1': 'Apple',
        'F0:D1:A9': 'Apple',
        'F0:DB:E2': 'Apple',
        'F0:DB:F8': 'Apple',
        'F0:DC:E2': 'Apple',
        'F0:F6:1C': 'Apple',
        'F4:0F:24': 'Apple',
        'F4:1B:A1': 'Apple',
        'F4:37:B7': 'Apple',
        'F4:5C:89': 'Apple',
        'F4:5E:AB': 'Apple',
        'F4:5F:69': 'Apple',
        'F4:81:EA': 'Apple',
        'F4:F1:5A': 'Apple',
        'F4:F9:51': 'Apple',
        'F6:0E:DD': 'Apple',
        'F6:1E:89': 'Apple',
        'F6:27:93': 'Apple',
        'F6:2F:20': 'Apple',
        'F6:31:3B': 'Apple',
        'F6:8C:E6': 'Apple',
        'F6:D4:67': 'Apple',
        'F6:FB:C8': 'Apple',
        'F8:27:93': 'Apple',
        'F8:38:80': 'Apple',
        'F8:62:14': 'Apple',
        'F8:6F:C1': 'Apple',
        'F8:7A:EF': 'Apple',
        'F8:95:C7': 'Apple',
        'F8:9F:C5': 'Apple',
        'F8:A0:97': 'Apple',
        'F8:FF:0B': 'Apple',
        'FC:25:3F': 'Apple',
        'FC:E9:98': 'Apple',
        'FC:FC:48': 'Apple'
    }

    return vendors.get(mac_prefix, 'Unknown')

def determine_device_type(ip_address, mac_address, manufacturer=None):
    """Determine device type based on IP, MAC, and manufacturer"""
    if not manufacturer:
        manufacturer = get_device_manufacturer(mac_address) if mac_address else 'Unknown'
    
    # Simple device type detection
    if manufacturer == 'Apple':
        return 'Apple Device'
    elif manufacturer == 'VMware':
        return 'Virtual Machine'
    elif manufacturer == 'Oracle VirtualBox':
        return 'Virtual Machine'
    elif 'Raspberry Pi' in manufacturer:
        return 'Raspberry Pi'
    elif manufacturer != 'Unknown':
        return f'{manufacturer} Device'
    else:
        return 'Unknown Device'

def ping_device(ip_address, timeout=2):
    """Ping a single device"""
    try:
        # Use system ping command
        system = platform.system().lower()
        
        if system == 'windows':
            cmd = ['ping', '-n', '1', '-w', str(int(timeout * 1000)), ip_address]
        else:
            cmd = ['ping', '-c', '1', '-W', str(timeout), ip_address]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 1)
        
        if result.returncode == 0:
            # Extract response time if possible
            response_time = None
            if system == 'windows':
                # Windows ping output: "Reply from 192.168.1.1: bytes=32 time=1ms TTL=64"
                import re
                match = re.search(r'time[=<](\d+)ms', result.stdout)
                if match:
                    response_time = f"{match.group(1)}ms"
            else:
                # Linux ping output: "64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=1.23 ms"
                import re
                match = re.search(r'time[=<](\d+\.?\d*)', result.stdout)
                if match:
                    response_time = f"{match.group(1)}ms"
            
            return {
                'success': True,
                'reachable': True,
                'response_time': response_time or 'OK',
                'ip_address': ip_address
            }
        else:
            return {
                'success': True,
                'reachable': False,
                'response_time': 'Timeout',
                'ip_address': ip_address
            }
    except subprocess.TimeoutExpired:
        return {
            'success': True,
            'reachable': False,
            'response_time': 'Timeout',
            'ip_address': ip_address
        }
    except Exception as e:
        logger.error(f"Ping error for {ip_address}: {e}")
        return {
            'success': False,
            'reachable': False,
            'response_time': 'Error',
            'ip_address': ip_address,
            'error': str(e)
        }

logger = logging.getLogger(__name__)

def get_arp_table():
    """Get ARP table entries from system"""
    try:
        logger.info("Fetching ARP table")

        system = platform.system().lower()

        # Try a sequence of commands with increasing timeouts and fallbacks
        commands = []
        if system == 'windows':
            commands = [(['arp', '-a'], 10), (['netsh', 'interface', 'ip', 'show', 'neighbors'], 12), (['ipconfig', '/all'], 8)]
        else:
            commands = [(['arp', '-a'], 10), (['ip', 'neigh', 'show'], 8), (['cat', '/proc/net/arp'], 5)]

        output = None
        last_err = None

        for cmd, to in commands:
            try:
                logger.debug(f"Trying ARP command: {' '.join(cmd)} (timeout={to}s)")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=to)
                if result.returncode == 0 and result.stdout and result.stdout.strip():
                    output = result.stdout
                    logger.debug(f"ARP command succeeded: {' '.join(cmd)}")
                    break
                else:
                    # Keep stderr for logging and try next
                    last_err = result.stderr or result.stdout
                    logger.debug(f"ARP command returned no output or non-zero code: {' '.join(cmd)} - rc={result.returncode}")
            except subprocess.TimeoutExpired:
                logger.warning(f"ARP command timed out for: {' '.join(cmd)}")
                last_err = 'timeout'
                continue
            except Exception as e:
                logger.debug(f"ARP command error for {' '.join(cmd)}: {e}")
                last_err = str(e)
                continue

        if not output:
            logger.error(f"ARP discovery failed; last error: {last_err}")
            return []

        arp_entries = []
        lines = output.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Skip common header lines
            if 'interface:' in line.lower() or 'internet address' in line.lower() or '---' in line or 'arp:' in line.lower():
                continue

            # Windows typical:  10.0.0.1           00-11-22-33-44-55     dynamic
            if system == 'windows':
                parts = re.split(r'\s+', line)
                # Find a part that looks like an IP and one that looks like a MAC
                ip_candidate = None
                mac_candidate = None
                for p in parts:
                    if re.match(r'\d+\.\d+\.\d+\.\d+', p):
                        ip_candidate = p
                    if re.match(r'([0-9a-fA-F]{2}[-:]){5}[0-9a-fA-F]{2}', p):
                        mac_candidate = p

                if not ip_candidate or not mac_candidate:
                    # Some commands (ipconfig) have MAC without mapping; skip
                    continue

                ip_address = ip_candidate
                mac_address = mac_candidate.replace('-', ':').lower()

                # Skip broadcast entries often represented as ff:ff:ff:ff:ff:ff
                if mac_address == 'ff:ff:ff:ff:ff:ff':
                    continue

                # Skip multicast or link-local addresses (not useful as devices)
                try:
                    ip_obj = ipaddress.IPv4Address(ip_address)
                    if ip_obj.is_multicast or ip_obj.is_link_local:
                        continue
                except Exception:
                    pass

                manufacturer = get_device_manufacturer(mac_address)
                device_type = determine_device_type(ip_address, mac_address, manufacturer)
                custom_name = get_device_name(mac_address, ip_address)

                arp_entries.append({
                    'ip_address': ip_address,
                    'mac_address': mac_address,
                    'hostname': custom_name,
                    'manufacturer': manufacturer,
                    'type': device_type,
                    'last_seen': 'Active',
                    'source': 'ARP Table',
                    'via_arp': True
                })
            else:
                # Linux/Unix formats
                match = re.search(r'(\d+\.\d+\.\d+\.\d+).*?([0-9a-f:]{17})', line.lower())
                if match:
                    ip_address = match.group(1)
                    mac_address = match.group(2)
                    mac_address = mac_address.lower()

                    # Skip broadcast MAC and multicast/link-local IP addresses
                    if mac_address == 'ff:ff:ff:ff:ff:ff':
                        continue
                    try:
                        ip_obj = ipaddress.IPv4Address(ip_address)
                        if ip_obj.is_multicast or ip_obj.is_link_local:
                            continue
                    except Exception:
                        pass

                    manufacturer = get_device_manufacturer(mac_address)
                    device_type = determine_device_type(ip_address, mac_address, manufacturer)
                    custom_name = get_device_name(mac_address, ip_address)

                    arp_entries.append({
                        'ip_address': ip_address,
                        'mac_address': mac_address,
                        'hostname': custom_name,
                        'manufacturer': manufacturer,
                        'type': device_type,
                        'last_seen': 'Active',
                        'source': 'ARP Table',
                        'via_arp': True
                    })

        logger.info(f"Found {len(arp_entries)} devices in ARP table")
        return arp_entries

    except Exception as e:
        logger.error(f"Error getting ARP table: {e}")
        return []

def ping_range(start_ip, end_ip, timeout=2, max_concurrent=10, max_hosts=None):
    """Ping a range of IP addresses concurrently"""
    try:
        logger.info(f"Pinging range {start_ip} to {end_ip}")

        # Generate IP list
        start = ipaddress.IPv4Address(start_ip)
        end = ipaddress.IPv4Address(end_ip)

        ip_list = []
        current = start
        while current <= end:
            ip_list.append(str(current))
            current += 1

        # Apply a safe cap to the number of hosts scanned at once. Default cap 254
        cap = 254
        if isinstance(max_hosts, int) and max_hosts > 0:
            cap = min(cap, max_hosts)

        if len(ip_list) > cap:
            logger.warning(f"Large IP range ({len(ip_list)} IPs), limiting to first {cap}")
            ip_list = ip_list[:cap]

        results = []
        start_time = datetime.now()

        # Ping IPs concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            future_to_ip = {
                executor.submit(ping_device, ip, timeout): ip
                for ip in ip_list
            }

            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Ping failed for {ip}: {e}")
                    results.append({
                        'success': False,
                        'reachable': False,
                        'response_time': "Error",
                        'ip_address': ip,
                        'error': str(e)
                    })

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        # Calculate statistics
        # If ARP table contains entries, use that as a fallback to mark hosts reachable
        try:
            arp_entries = get_arp_table()
            arp_ips = set(e.get('ip_address') for e in arp_entries if e.get('ip_address'))
        except Exception:
            arp_ips = set()

        # If ping failed but IP present in ARP, mark reachable by ARP
        for r in results:
            if not r.get('reachable') and r.get('ip_address') in arp_ips:
                r['reachable'] = True
                # Indicate ARP-based reachability
                r['response_time'] = r.get('response_time', 'ARP')
                r['success'] = True

        online_count = sum(1 for r in results if r.get('reachable'))
        offline_count = len(results) - online_count
        success_rate = (online_count / len(results) * 100) if results else 0

        statistics = {
            'total_pinged': len(results),
            'online_count': online_count,
            'offline_count': offline_count,
            'success_rate': round(success_rate, 1),
            'total_time_seconds': round(total_time, 2),
            'average_time_per_ip': round(total_time / len(results), 3) if results else 0
        }

        logger.info(f"Ping range completed: {online_count}/{len(results)} online ({success_rate:.1f}%)")

        return {
            'results': results,
            'statistics': statistics,
            'range': {
                'start_ip': start_ip,
                'end_ip': end_ip,
                'timeout': timeout,
                'max_concurrent': max_concurrent
            }
        }
    except Exception as e:
        logger.error(f"Error in ping range: {e}")
        return {
            'results': [],
            'statistics': {'error': str(e)},
            'range': {'start_ip': start_ip, 'end_ip': end_ip}
        }

def enhanced_network_discovery(include_arp=True, include_ping_range=False, 
                             start_ip=None, end_ip=None, timeout=2, include_port_scan=False, max_hosts=None):
    """Enhanced network discovery combining ARP and ping range"""
    try:
        logger.info("Starting enhanced network discovery")
        
        discovered_devices = []
        methods_used = []
        
        # ARP Table Discovery
        if include_arp:
            logger.info("Including ARP table discovery")
            arp_devices = get_arp_table()
            discovered_devices.extend(arp_devices)
            methods_used.append("ARP Table")
        
        # Range Ping Discovery
        if include_ping_range and start_ip and end_ip:
            logger.info(f"Including ping range discovery: {start_ip} to {end_ip}")
            ping_results = ping_range(start_ip, end_ip, timeout, max_concurrent=10, max_hosts=max_hosts)
            
            # Convert ping results to device format
            for result in ping_results['results']:
                if result['reachable']:
                    # Check if device already exists in ARP results
                    existing = next((d for d in discovered_devices 
                                   if d['ip_address'] == result['ip_address']), None)
                    
                    if not existing:
                        # Add new device from ping
                        custom_name = get_device_name(None, result['ip_address'])
                        device_type = determine_device_type(result['ip_address'], None)
                        
                        discovered_devices.append({
                            'ip_address': result['ip_address'],
                            'mac_address': 'Unknown',
                            'hostname': custom_name,
                            'manufacturer': 'Unknown',
                            'via_arp': False,
                            'type': device_type,
                            'last_seen': 'Active',
                            'source': 'Range Ping',
                            'ping_result': result
                        })
                    else:
                        # Update existing device with ping info
                        existing['ping_result'] = result
                    # Optionally perform a light port scan to fingerprint services
                    if include_port_scan:
                        try:
                            port_info = scan_device_ports(result['ip_address'], timeout=1)
                            # attach scan summary into device entry or existing
                            target = existing if existing else next((d for d in discovered_devices if d['ip_address'] == result['ip_address']), None)
                            if target is not None:
                                target['port_scan'] = port_info
                        except Exception as e:
                            logger.debug(f"Port scan failed for {result['ip_address']}: {e}")
            
            methods_used.append("Range Ping")
        
        # Remove duplicates based on IP address
        unique_devices = {}
        for device in discovered_devices:
            ip = device['ip_address']
            if ip not in unique_devices:
                unique_devices[ip] = device
            else:
                # Merge information, preferring ARP data
                existing = unique_devices[ip]
                if device.get('source') == 'ARP Table' and existing.get('source') != 'ARP Table':
                    unique_devices[ip] = device
                elif 'ping_result' in device and 'ping_result' not in existing:
                    existing['ping_result'] = device['ping_result']
        
        final_devices = list(unique_devices.values())
        
        logger.info(f"Enhanced discovery completed: {len(final_devices)} unique devices found")
        
        return {
            'success': True,
            'discovered_devices': final_devices,
            'total_devices': len(final_devices),
            'methods_used': methods_used,
            'message': f'Enhanced discovery found {len(final_devices)} devices using {", ".join(methods_used)}'
        }
        
    except Exception as e:
        logger.error(f"Enhanced discovery error: {e}")
        return {
            'success': False,
            'error': f'Enhanced discovery failed: {str(e)}',
            'discovered_devices': [],
            'total_devices': 0
        }

def validate_network_range(network_range, current_network="155.235.81.0/24"):
    """Validate network range and check for security warnings"""
    try:
        if not network_range or '/' not in network_range:
            return {
                'valid': False,
                'error': 'Invalid network range format. Use CIDR notation (e.g., 192.168.1.0/24)'
            }
        
        # Parse network
        try:
            network = ipaddress.IPv4Network(network_range, strict=False)
        except ValueError as e:
            return {
                'valid': False,
                'error': f'Invalid network format: {str(e)}'
            }
        
        # Security check for scanning outside current network
        current_net = ipaddress.IPv4Network(current_network, strict=False)
        
        if network.network_address != current_net.network_address:
            return {
                'valid': True,
                'warning': True,
                'warning_type': 'network_security',
                'message': f'You are trying to scan outside your current network domain ({current_network}). This could trigger security alerts.',
                'current_network': current_network,
                'requested_network': network_range
            }
        
        return {
            'valid': True,
            'warning': False,
            'network': network_range
        }
        
    except Exception as e:
        return {
            'valid': False,
            'error': f'Network validation error: {str(e)}'
        }

class DeviceDatabase:
    """Shared JSON database for storing comprehensive device information"""

    def __init__(self, db_path=None):
        if db_path is None:
            # Store in the backend directory
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(backend_dir, 'device_database.json')
        else:
            self.db_path = db_path

        self._ensure_database()

    def _ensure_database(self):
        """Ensure the database file exists with proper structure"""
        if not os.path.exists(self.db_path):
            initial_structure = {
                "database_info": {
                    "version": "1.0",
                    "created": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                },
                "devices": {},
                "networks": {},
                "statistics": {
                    "total_devices": 0,
                    "medical_devices": 0,
                    "last_scan": None
                }
            }
            with open(self.db_path, 'w') as f:
                json.dump(initial_structure, f, indent=2)

    def store_device_info(self, ip_address, device_info):
        """Store comprehensive device information"""
        try:
            with open(self.db_path, 'r') as f:
                data = json.load(f)

            device_key = ip_address

            # Merge new information with existing data
            if device_key in data['devices']:
                existing = data['devices'][device_key]
                # Update existing device info
                for key, value in device_info.items():
                    if key == 'open_ports' and key in existing:
                        # Merge port information
                        existing_ports = {p.get('port', p.get('port_number', 0)): p for p in existing['open_ports']}
                        new_ports = {p.get('port', p.get('port_number', 0)): p for p in value}

                        # Update existing ports and add new ones
                        for port_num, port_info in new_ports.items():
                            existing_ports[port_num] = port_info

                        existing['open_ports'] = list(existing_ports.values())
                    else:
                        existing[key] = value

                existing['last_updated'] = datetime.now().isoformat()
                existing['scan_count'] = existing.get('scan_count', 0) + 1
            else:
                # New device
                device_info['first_seen'] = datetime.now().isoformat()
                device_info['last_updated'] = datetime.now().isoformat()
                device_info['scan_count'] = 1
                data['devices'][device_key] = device_info
                data['statistics']['total_devices'] += 1

                # Check if it's a medical device
                if device_info.get('device_type') == 'Medical Imaging Device' or \
                   any(p.get('port') in [104, 11112, 8042, 8104] for p in device_info.get('open_ports', [])):
                    data['statistics']['medical_devices'] += 1

            # Update network information
            network = self._get_network_from_ip(ip_address)
            if network not in data['networks']:
                data['networks'][network] = {
                    'devices': [],
                    'last_scan': datetime.now().isoformat()
                }

            if device_key not in data['networks'][network]['devices']:
                data['networks'][network]['devices'].append(device_key)

            data['networks'][network]['last_scan'] = datetime.now().isoformat()
            data['database_info']['last_updated'] = datetime.now().isoformat()
            data['statistics']['last_scan'] = datetime.now().isoformat()

            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)

            return True

        except Exception as e:
            logger.error(f"Error storing device info: {e}")
            return False

    def get_device_info(self, ip_address):
        """Retrieve device information"""
        try:
            with open(self.db_path, 'r') as f:
                data = json.load(f)

            return data['devices'].get(ip_address, {})
        except Exception as e:
            logger.error(f"Error retrieving device info: {e}")
            return {}

    def get_network_devices(self, network=None):
        """Get all devices on a specific network"""
        try:
            with open(self.db_path, 'r') as f:
                data = json.load(f)

            if network:
                device_keys = data['networks'].get(network, {}).get('devices', [])
                return {key: data['devices'][key] for key in device_keys if key in data['devices']}
            else:
                return data['devices']

        except Exception as e:
            logger.error(f"Error retrieving network devices: {e}")
            return {}

    def get_statistics(self):
        """Get database statistics"""
        try:
            with open(self.db_path, 'r') as f:
                data = json.load(f)

            return data['statistics']
        except Exception as e:
            logger.error(f"Error retrieving statistics: {e}")
            return {}

    def _get_network_from_ip(self, ip_address):
        """Extract network from IP address (assuming /24 subnet)"""
        parts = ip_address.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        return "Unknown"

# Global device database instance
device_db = DeviceDatabase()

# API Endpoints for device database
def get_device_database_info():
    """Get comprehensive device database information"""
    try:
        devices = device_db.get_network_devices()
        statistics = device_db.get_statistics()

        # Convert devices dict to list for frontend
        device_list = []
        for ip, info in devices.items():
            device_list.append({
                'ip_address': ip,
                'ip': ip,
                'hostname': info.get('hostname', 'Unknown'),
                'mac_address': info.get('mac_address', 'Unknown'),
                'manufacturer': info.get('manufacturer', 'Unknown'),
                'device_type': info.get('device_type', 'Unknown'),
                'os_fingerprint': info.get('os_fingerprint', 'Unknown'),
                'reachable': info.get('reachable', False),
                'response_time': info.get('response_time', 'N/A'),
                'open_ports': info.get('open_ports', []),
                'services': info.get('services', []),
                'last_updated': info.get('last_updated', ''),
                'scan_count': info.get('scan_count', 0),
                'first_seen': info.get('first_seen', ''),
                'confidence_score': info.get('confidence_score', 0)
            })

        return {
            'success': True,
            'devices': device_list,
            'statistics': statistics,
            'total_entries': len(device_list)
        }

    except Exception as e:
        logger.error(f"Error retrieving device database info: {e}")
        return {
            'success': False,
            'error': str(e),
            'devices': [],
            'statistics': {},
            'total_entries': 0
        }

def get_device_details(ip_address):
    """Get detailed information for a specific device"""
    try:
        device_info = device_db.get_device_info(ip_address)

        if device_info:
            return {
                'success': True,
                'device': {
                    'ip_address': ip_address,
                    'hostname': device_info.get('hostname', 'Unknown'),
                    'mac_address': device_info.get('mac_address', 'Unknown'),
                    'manufacturer': device_info.get('manufacturer', 'Unknown'),
                    'device_type': device_info.get('device_type', 'Unknown'),
                    'os_fingerprint': device_info.get('os_fingerprint', 'Unknown'),
                    'reachable': device_info.get('reachable', False),
                    'response_time': device_info.get('response_time', 'N/A'),
                    'open_ports': device_info.get('open_ports', []),
                    'services': device_info.get('services', []),
                    'vulnerabilities': device_info.get('vulnerabilities', []),
                    'last_updated': device_info.get('last_updated', ''),
                    'first_seen': device_info.get('first_seen', ''),
                    'scan_count': device_info.get('scan_count', 0),
                    'network_interfaces': device_info.get('network_interfaces', [])
                }
            }
        else:
            return {
                'success': False,
                'error': f'Device {ip_address} not found in database'
            }

    except Exception as e:
        logger.error(f"Error retrieving device details: {e}")
        return {
            'success': False,
            'error': str(e)
        }
