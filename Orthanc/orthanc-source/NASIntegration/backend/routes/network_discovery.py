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
from datetime import datetime
from .nas_utils import get_device_name, get_device_manufacturer, determine_device_type, ping_device, scan_device_ports

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
