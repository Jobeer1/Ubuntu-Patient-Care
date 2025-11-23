"""
Network Discovery Tools for Practice Infrastructure

Discovers:
- NAS devices and storage systems
- Medical imaging servers (DICOM, PACS)
- Database servers
- Application servers
- Virtual machines
- PCs and workstations
- Network equipment (switches, firewalls, routers)
- Network printers
- Medical devices (ultrasound, monitors, etc.)
"""

import socket
import threading
import time
from datetime import datetime
import subprocess
import ipaddress
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
import json
import platform
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NetworkDiscovery:
    """
    Discovers devices on the network using multiple methods
    """
    
    def __init__(self):
        self.discovered_devices = {}
        self.threads = []
        self.lock = threading.Lock()
        self.os_type = platform.system()
        
    def discover_network_range(self, network_cidr: str, timeout: int = 5) -> Dict[str, Any]:
        """
        Discover all active devices on a network range
        
        Args:
            network_cidr: Network in CIDR notation (e.g., "192.168.1.0/24")
            timeout: Timeout for each ping in seconds
            
        Returns:
            Dictionary of discovered devices
        """
        logger.info(f"Starting network discovery on {network_cidr}")
        
        try:
            network = ipaddress.ip_network(network_cidr, strict=False)
        except ValueError as e:
            logger.error(f"Invalid network CIDR: {network_cidr}")
            return {"error": str(e), "status": "FAILED"}
        
        # Get local IP to avoid scanning self
        local_ip = self._get_local_ip()
        
        # Discover hosts using ping
        hosts = self._discover_hosts_ping(network, timeout, local_ip)
        
        # For each host, get detailed information
        for host in hosts:
            self._identify_device(str(host))
        
        logger.info(f"Discovery complete. Found {len(self.discovered_devices)} devices")
        return {
            "status": "COMPLETE",
            "network": network_cidr,
            "devices_found": len(self.discovered_devices),
            "devices": self.discovered_devices
        }
    
    def _get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            logger.warning(f"Could not determine local IP: {e}")
            return "127.0.0.1"
    
    def _discover_hosts_ping(self, network: ipaddress.IPv4Network, timeout: int, 
                             skip_ip: str) -> List[ipaddress.IPv4Address]:
        """
        Discover active hosts using ping
        """
        active_hosts = []
        
        # Determine ping command based on OS
        ping_cmd = self._get_ping_command(timeout)
        
        logger.info(f"Pinging {network.num_addresses} hosts (this may take a while)...")
        
        threads = []
        for ip in network.hosts():
            if str(ip) != skip_ip:
                thread = threading.Thread(
                    target=self._ping_host,
                    args=(str(ip), ping_cmd, active_hosts)
                )
                thread.daemon = True
                thread.start()
                threads.append(thread)
                
                # Limit concurrent threads
                if len(threads) >= 100:
                    for t in threads:
                        t.join(timeout=0.1)
                    threads = [t for t in threads if t.is_alive()]
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        return sorted(active_hosts)
    
    def _get_ping_command(self, timeout: int) -> List[str]:
        """Get ping command for OS"""
        if self.os_type == "Windows":
            return ["ping", "-n", "1", "-w", str(timeout * 1000)]
        else:  # Linux, macOS
            return ["ping", "-c", "1", "-W", str(timeout)]
    
    def _ping_host(self, ip: str, ping_cmd: List[str], active_hosts: List):
        """Ping a single host"""
        try:
            cmd = ping_cmd + [ip]
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=10,
                text=True
            )
            if result.returncode == 0:
                with self.lock:
                    active_hosts.append(ipaddress.ip_address(ip))
                logger.debug(f"Found: {ip}")
        except Exception as e:
            logger.debug(f"Ping failed for {ip}: {e}")
    
    def _identify_device(self, ip: str):
        """
        Identify device type and characteristics
        """
        device_info = {
            "ip": ip,
            "hostname": None,
            "mac_address": None,
            "device_type": "Unknown",
            "open_ports": [],
            "services": [],
            "os_info": None,
            "is_nas": False,
            "is_database": False,
            "is_medical": False,
            "is_vm": False,
            "is_server": False,
            "is_printer": False,
            "description": "",
            "discovery_time": datetime.now().isoformat()
        }
        
        try:
            # Get hostname
            try:
                hostname = socket.gethostbyaddr(ip)[0]
                device_info["hostname"] = hostname
            except (socket.herror, socket.gaierror):
                device_info["hostname"] = "Unknown"
            
            # Scan common ports
            common_ports = {
                21: "FTP",
                22: "SSH",
                25: "SMTP",
                53: "DNS",
                80: "HTTP",
                111: "RPC",
                139: "NetBIOS",
                445: "SMB/CIFS",
                389: "LDAP",
                443: "HTTPS",
                465: "SMTP-SSL",
                514: "Syslog",
                587: "SMTP-TLS",
                636: "LDAPS",
                3306: "MySQL",
                3389: "RDP",
                5432: "PostgreSQL",
                5900: "VNC",
                6379: "Redis",
                8080: "HTTP-Alt",
                8443: "HTTPS-Alt",
                27017: "MongoDB",
                1433: "SQL-Server",
                5984: "CouchDB",
                9200: "Elasticsearch",
                50389: "DICOM",
                104: "DICOM",
                11112: "DICOM-ALT"
            }
            
            for port, service in common_ports.items():
                if self._port_open(ip, port, timeout=1):
                    device_info["open_ports"].append(port)
                    device_info["services"].append(service)
            
            # Identify device type based on services and hostname
            device_info = self._classify_device(device_info)
            
        except Exception as e:
            logger.warning(f"Error identifying device {ip}: {e}")
        
        with self.lock:
            self.discovered_devices[ip] = device_info
    
    def _port_open(self, ip: str, port: int, timeout: int = 1) -> bool:
        """Check if port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def _classify_device(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify device based on hostname, open ports, and services
        """
        hostname = device_info.get("hostname", "").lower()
        services = device_info.get("services", [])
        ports = device_info.get("open_ports", [])
        
        # Check for NAS
        if any(keyword in hostname for keyword in ["nas", "storage", "backup", "synology", "qnap"]):
            device_info["is_nas"] = True
            device_info["device_type"] = "Network Storage (NAS)"
            device_info["description"] = "Network Attached Storage - likely contains backups or shared files"
        
        # Check for Database Server
        elif 3306 in ports or 5432 in ports or 1433 in ports or 27017 in ports:
            device_info["is_database"] = True
            if 3306 in ports:
                device_info["device_type"] = "Database Server (MySQL)"
            elif 5432 in ports:
                device_info["device_type"] = "Database Server (PostgreSQL)"
            elif 1433 in ports:
                device_info["device_type"] = "Database Server (SQL Server)"
            elif 27017 in ports:
                device_info["device_type"] = "Database Server (MongoDB)"
            device_info["description"] = "Database server - stores patient data, medical records, or application data"
        
        # Check for Medical Imaging (DICOM/PACS)
        elif 50389 in ports or 104 in ports or 11112 in ports:
            device_info["is_medical"] = True
            device_info["device_type"] = "DICOM/PACS Server"
            device_info["description"] = "Medical imaging server - stores and manages medical images (X-ray, CT, MRI, etc.)"
        
        # Check for VM Host
        elif any(keyword in hostname for keyword in ["esxi", "hyperv", "kvm", "vmware", "hyper-v"]):
            device_info["is_vm"] = True
            device_info["device_type"] = "Virtual Machine Host"
            device_info["description"] = "Hypervisor - runs virtual machines hosting medical applications"
        
        # Check for Web/App Server
        elif 80 in ports or 443 in ports:
            if "server" in hostname or "app" in hostname or "web" in hostname:
                device_info["is_server"] = True
                device_info["device_type"] = "Web/Application Server"
                device_info["description"] = "Application server - hosts web interfaces for medical software"
            elif 22 in ports or 3389 in ports:  # SSH or RDP
                device_info["is_server"] = True
                device_info["device_type"] = "Server"
                device_info["description"] = "Server - provides services to medical practice"
        
        # Check for Printer
        elif any(keyword in hostname for keyword in ["printer", "hp", "canon", "xerox"]):
            device_info["is_printer"] = True
            device_info["device_type"] = "Network Printer"
            device_info["description"] = "Network printer - prints patient documents and reports"
        
        # Check for Workstation/PC
        elif 3389 in ports and len(ports) > 1:  # RDP + other services
            device_info["device_type"] = "PC/Workstation"
            device_info["description"] = "Medical workstation - staff uses for patient care"
        
        # Check for Switch/Router
        elif 53 in ports or 161 in ports:  # DNS or SNMP
            device_info["device_type"] = "Network Equipment"
            device_info["description"] = "Network device - switch, router, or firewall"
        
        # Default for servers with SSH
        elif 22 in ports:
            device_info["is_server"] = True
            device_info["device_type"] = "Server (Linux/Unix)"
            device_info["description"] = "Linux/Unix server - provides services to medical practice"
        
        return device_info
    
    def discover_specific_network(self, network_interface: Optional[str] = None) -> Dict[str, Any]:
        """
        Discover devices on the current network (auto-detect network range)
        """
        try:
            # Get local IP and subnet
            local_ip = self._get_local_ip()
            network_range = self._get_network_range(local_ip)
            
            logger.info(f"Auto-detected network: {network_range} (local IP: {local_ip})")
            
            return self.discover_network_range(network_range)
        
        except Exception as e:
            logger.error(f"Error discovering network: {e}")
            return {"error": str(e), "status": "FAILED"}
    
    def _get_network_range(self, ip: str) -> str:
        """Get network range from IP (assumes /24 subnet)"""
        parts = ip.split(".")
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    
    def get_device_summary(self) -> Dict[str, Any]:
        """Get summary of discovered devices by type"""
        summary = {
            "total_devices": len(self.discovered_devices),
            "nas_devices": 0,
            "database_servers": 0,
            "medical_devices": 0,
            "vm_hosts": 0,
            "web_servers": 0,
            "workstations": 0,
            "printers": 0,
            "network_equipment": 0,
            "unknown": 0,
            "devices_by_type": {}
        }
        
        for device_info in self.discovered_devices.values():
            device_type = device_info.get("device_type", "Unknown")
            
            if device_type not in summary["devices_by_type"]:
                summary["devices_by_type"][device_type] = []
            
            summary["devices_by_type"][device_type].append({
                "ip": device_info["ip"],
                "hostname": device_info["hostname"],
                "description": device_info["description"]
            })
            
            if device_info["is_nas"]:
                summary["nas_devices"] += 1
            elif device_info["is_database"]:
                summary["database_servers"] += 1
            elif device_info["is_medical"]:
                summary["medical_devices"] += 1
            elif device_info["is_vm"]:
                summary["vm_hosts"] += 1
            elif device_info["is_server"]:
                summary["web_servers"] += 1
            elif device_info["is_printer"]:
                summary["printers"] += 1
            elif device_info.get("device_type") == "Network Equipment":
                summary["network_equipment"] += 1
            else:
                summary["unknown"] += 1
        
        return summary
    
    def export_discovered_devices(self, filename: str = "discovered_devices.json") -> str:
        """Export discovered devices to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.discovered_devices, f, indent=2)
            logger.info(f"Devices exported to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error exporting devices: {e}")
            return None


class ServiceDiscovery:
    """
    Discovers services running on discovered devices
    """
    
    @staticmethod
    def probe_device_services(ip: str, hostname: Optional[str] = None) -> Dict[str, Any]:
        """
        Probe a device for running services
        """
        services_info = {
            "ip": ip,
            "hostname": hostname,
            "services_detected": [],
            "open_ports": [],
            "identified_applications": []
        }
        
        # Common service ports
        service_ports = {
            21: {"name": "FTP", "type": "file_transfer"},
            22: {"name": "SSH", "type": "remote_access"},
            53: {"name": "DNS", "type": "network"},
            80: {"name": "HTTP", "type": "web"},
            110: {"name": "POP3", "type": "email"},
            143: {"name": "IMAP", "type": "email"},
            389: {"name": "LDAP", "type": "directory"},
            443: {"name": "HTTPS", "type": "web"},
            445: {"name": "SMB/CIFS", "type": "file_share"},
            3306: {"name": "MySQL", "type": "database"},
            3389: {"name": "RDP", "type": "remote_access"},
            5432: {"name": "PostgreSQL", "type": "database"},
            5900: {"name": "VNC", "type": "remote_access"},
            8080: {"name": "HTTP-ALT", "type": "web"},
            8443: {"name": "HTTPS-ALT", "type": "web"},
            1433: {"name": "SQL Server", "type": "database"},
            50389: {"name": "DICOM", "type": "medical"},
            104: {"name": "DICOM-ALT", "type": "medical"},
        }
        
        for port, service_info in service_ports.items():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            try:
                result = sock.connect_ex((ip, port))
                if result == 0:
                    services_info["open_ports"].append(port)
                    services_info["services_detected"].append(service_info)
            except Exception:
                pass
            finally:
                sock.close()
        
        return services_info


if __name__ == "__main__":
    # Example usage
    print("=" * 80)
    print("PRACTICE NETWORK DISCOVERY TOOL")
    print("=" * 80)
    
    discovery = NetworkDiscovery()
    
    # Discover devices on current network
    print("\n[*] Discovering devices on network...")
    results = discovery.discover_specific_network()
    
    # Print summary
    if results.get("status") == "COMPLETE":
        summary = discovery.get_device_summary()
        print(f"\n[+] Discovery Complete!")
        print(f"    Total Devices: {summary['total_devices']}")
        print(f"    NAS Devices: {summary['nas_devices']}")
        print(f"    Database Servers: {summary['database_servers']}")
        print(f"    Medical Devices: {summary['medical_devices']}")
        print(f"    VM Hosts: {summary['vm_hosts']}")
        print(f"    Servers: {summary['web_servers']}")
        print(f"    Printers: {summary['printers']}")
        print(f"    Unknown: {summary['unknown']}")
        
        # Print detailed device list
        print("\n[+] Devices by Type:")
        for device_type, devices in summary["devices_by_type"].items():
            print(f"\n    {device_type}:")
            for device in devices:
                print(f"      - {device['ip']:20} {device['hostname']:30} {device['description']}")
        
        # Export
        discovery.export_discovered_devices("discovered_devices.json")
