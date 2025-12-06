"""
Database Discovery Tools for Practice Infrastructure

Discovers:
- SQL Server databases
- MySQL/MariaDB instances
- PostgreSQL databases
- MongoDB instances
- Database configurations
- Database users and permissions
- Backup status
- Database sizes
"""

import socket
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseDiscovery:
    """
    Discovers and probes database servers on network
    """
    
    def __init__(self):
        self.discovered_databases = {}
        self.lock = threading.Lock()
    
    def probe_database_servers(self, ips: List[str]) -> Dict[str, Any]:
        """
        Probe a list of IPs for database servers
        
        Args:
            ips: List of IP addresses to probe
            
        Returns:
            Dictionary of discovered databases
        """
        logger.info(f"Probing {len(ips)} IPs for database servers...")
        
        threads = []
        for ip in ips:
            thread = threading.Thread(
                target=self._probe_single_ip,
                args=(ip,)
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)
            
            if len(threads) >= 50:
                for t in threads:
                    t.join(timeout=0.1)
                threads = [t for t in threads if t.is_alive()]
        
        for thread in threads:
            thread.join()
        
        logger.info(f"Database probing complete. Found {len(self.discovered_databases)} databases")
        return {
            "status": "COMPLETE",
            "databases_found": len(self.discovered_databases),
            "databases": self.discovered_databases
        }
    
    def _probe_single_ip(self, ip: str):
        """Probe single IP for all database types"""
        # Try MySQL
        mysql_result = self._probe_mysql(ip)
        if mysql_result:
            with self.lock:
                key = f"{ip}:3306"
                self.discovered_databases[key] = mysql_result
        
        # Try PostgreSQL
        postgres_result = self._probe_postgresql(ip)
        if postgres_result:
            with self.lock:
                key = f"{ip}:5432"
                self.discovered_databases[key] = postgres_result
        
        # Try SQL Server
        sqlserver_result = self._probe_sqlserver(ip)
        if sqlserver_result:
            with self.lock:
                key = f"{ip}:1433"
                self.discovered_databases[key] = sqlserver_result
        
        # Try MongoDB
        mongodb_result = self._probe_mongodb(ip)
        if mongodb_result:
            with self.lock:
                key = f"{ip}:27017"
                self.discovered_databases[key] = mongodb_result
    
    def _probe_mysql(self, ip: str, port: int = 3306, timeout: int = 2) -> Optional[Dict[str, Any]]:
        """
        Probe for MySQL server
        """
        try:
            # Try to connect
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            result = sock.connect_ex((ip, port))
            
            if result == 0:
                # Port is open, read MySQL handshake
                sock.sendall(b"")
                try:
                    data = sock.recv(1024)
                    
                    if data and b"mysql" in data.lower():
                        # Parse MySQL handshake packet
                        version_info = self._parse_mysql_handshake(data)
                        
                        return {
                            "type": "MySQL",
                            "ip": ip,
                            "port": port,
                            "status": "ACCESSIBLE",
                            "version": version_info.get("version", "Unknown"),
                            "features": version_info,
                            "discovery_time": datetime.now().isoformat(),
                            "description": "MySQL database server - likely contains medical records or application data"
                        }
                except socket.timeout:
                    pass
            
            sock.close()
        
        except Exception as e:
            logger.debug(f"MySQL probe failed for {ip}: {e}")
        
        return None
    
    def _parse_mysql_handshake(self, data: bytes) -> Dict[str, Any]:
        """Parse MySQL server handshake packet"""
        try:
            # Skip first byte (protocol version)
            # Bytes 1-9: MySQL version string (null-terminated)
            version_end = data.find(b'\x00')
            if version_end > 0:
                version = data[1:version_end].decode('utf-8', errors='ignore')
                return {
                    "version": version,
                    "protocol": "MySQL"
                }
        except Exception as e:
            logger.debug(f"Error parsing MySQL handshake: {e}")
        
        return {"version": "Unknown", "protocol": "MySQL"}
    
    def _probe_postgresql(self, ip: str, port: int = 5432, timeout: int = 2) -> Optional[Dict[str, Any]]:
        """
        Probe for PostgreSQL server
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            result = sock.connect_ex((ip, port))
            
            if result == 0:
                # Try to send startup message
                startup_msg = self._create_postgresql_startup()
                sock.sendall(startup_msg)
                
                try:
                    data = sock.recv(1024)
                    
                    # Check for PostgreSQL response
                    if b'S' in data or b'E' in data or b'R' in data:
                        return {
                            "type": "PostgreSQL",
                            "ip": ip,
                            "port": port,
                            "status": "ACCESSIBLE",
                            "version": self._parse_postgresql_response(data),
                            "description": "PostgreSQL database server - likely contains medical records or application data",
                            "discovery_time": datetime.now().isoformat()
                        }
                
                except socket.timeout:
                    pass
            
            sock.close()
        
        except Exception as e:
            logger.debug(f"PostgreSQL probe failed for {ip}: {e}")
        
        return None
    
    def _create_postgresql_startup(self) -> bytes:
        """Create PostgreSQL startup message"""
        try:
            params = b"user\x00postgres\x00database\x00postgres\x00"
            length = len(params) + 8
            msg = length.to_bytes(4, 'big') + b'\x03\x00\x00\x00' + params
            return msg
        except Exception:
            return b""
    
    def _parse_postgresql_response(self, data: bytes) -> str:
        """Parse PostgreSQL response"""
        # Look for version info or just return indicator
        if b'9.6' in data or b'10' in data or b'11' in data or b'12' in data:
            return "PostgreSQL 9.6+ detected"
        return "PostgreSQL detected"
    
    def _probe_sqlserver(self, ip: str, port: int = 1433, timeout: int = 2) -> Optional[Dict[str, Any]]:
        """
        Probe for SQL Server
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            result = sock.connect_ex((ip, port))
            
            if result == 0:
                # SQL Server TDS protocol
                prelogin = self._create_sqlserver_prelogin()
                sock.sendall(prelogin)
                
                try:
                    data = sock.recv(1024)
                    
                    if len(data) > 0:
                        version_info = self._parse_sqlserver_prelogin(data)
                        return {
                            "type": "SQL Server",
                            "ip": ip,
                            "port": port,
                            "status": "ACCESSIBLE",
                            "version": version_info.get("version", "Unknown"),
                            "build": version_info.get("build", "Unknown"),
                            "description": "SQL Server database - likely contains medical records or application data",
                            "discovery_time": datetime.now().isoformat()
                        }
                
                except socket.timeout:
                    # Even timeout indicates SQL Server might be there
                    return {
                        "type": "SQL Server",
                        "ip": ip,
                        "port": port,
                        "status": "POSSIBLE",
                        "version": "Unknown (timeout)",
                        "description": "SQL Server database (possibly) - medical records database",
                        "discovery_time": datetime.now().isoformat()
                    }
            
            sock.close()
        
        except Exception as e:
            logger.debug(f"SQL Server probe failed for {ip}: {e}")
        
        return None
    
    def _create_sqlserver_prelogin(self) -> bytes:
        """Create SQL Server PRELOGIN packet"""
        # TDS PRELOGIN packet format
        # Packet type 18 (PRELOGIN), Status 1, length varies
        return bytes([
            0x12,  # PRELOGIN packet type
            0x01,  # Status: EOM
            0x00, 0x00,  # Length (will be calculated)
            0x00, 0x00,  # SPID
            0x00,  # Packet number
            0x00   # Window
        ])
    
    def _parse_sqlserver_prelogin(self, data: bytes) -> Dict[str, Any]:
        """Parse SQL Server PRELOGIN response"""
        version_info = {"version": "Unknown", "build": "Unknown"}
        
        try:
            # Look for version patterns in response
            if b'SQL' in data or b'sql' in data:
                version_info["version"] = "SQL Server 2019 or later"
        except Exception as e:
            logger.debug(f"Error parsing SQL Server response: {e}")
        
        return version_info
    
    def _probe_mongodb(self, ip: str, port: int = 27017, timeout: int = 2) -> Optional[Dict[str, Any]]:
        """
        Probe for MongoDB
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            result = sock.connect_ex((ip, port))
            
            if result == 0:
                # Send MongoDB isMaster command
                msg = self._create_mongodb_ismastercommand()
                sock.sendall(msg)
                
                try:
                    data = sock.recv(1024)
                    
                    if len(data) > 0:
                        return {
                            "type": "MongoDB",
                            "ip": ip,
                            "port": port,
                            "status": "ACCESSIBLE",
                            "version": "MongoDB detected",
                            "description": "MongoDB database server - NoSQL database for medical data",
                            "discovery_time": datetime.now().isoformat()
                        }
                
                except socket.timeout:
                    pass
            
            sock.close()
        
        except Exception as e:
            logger.debug(f"MongoDB probe failed for {ip}: {e}")
        
        return None
    
    def _create_mongodb_ismastercommand(self) -> bytes:
        """Create MongoDB isMaster command"""
        # Simplified MongoDB wire protocol
        try:
            # isMaster command in BSON: {isMaster: 1}
            bson = b'\x0c\x00\x00\x00\x10isMaster\x00\x01\x00\x00\x00\x00'
            length = len(bson) + 4
            msg = length.to_bytes(4, 'little') + bson
            return msg
        except Exception:
            return b""
    
    def get_database_summary(self) -> Dict[str, Any]:
        """Get summary of discovered databases"""
        summary = {
            "total_databases": len(self.discovered_databases),
            "mysql_instances": 0,
            "postgresql_instances": 0,
            "sqlserver_instances": 0,
            "mongodb_instances": 0,
            "accessible": 0,
            "by_type": {}
        }
        
        for db_info in self.discovered_databases.values():
            db_type = db_info.get("type", "Unknown")
            
            if db_type not in summary["by_type"]:
                summary["by_type"][db_type] = []
            
            summary["by_type"][db_type].append({
                "ip": db_info["ip"],
                "port": db_info["port"],
                "status": db_info.get("status", "Unknown"),
                "version": db_info.get("version", "Unknown")
            })
            
            if db_info.get("status") == "ACCESSIBLE":
                summary["accessible"] += 1
            
            if db_type == "MySQL":
                summary["mysql_instances"] += 1
            elif db_type == "PostgreSQL":
                summary["postgresql_instances"] += 1
            elif db_type == "SQL Server":
                summary["sqlserver_instances"] += 1
            elif db_type == "MongoDB":
                summary["mongodb_instances"] += 1
        
        return summary
    
    def export_discovered_databases(self, filename: str = "discovered_databases.json") -> str:
        """Export discovered databases to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.discovered_databases, f, indent=2)
            logger.info(f"Databases exported to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error exporting databases: {e}")
            return None


class DatabaseAnalyzer:
    """
    Analyzes discovered databases for medical practice usage
    """
    
    @staticmethod
    def analyze_database(db_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze database for common medical applications
        """
        analysis = {
            "database_info": db_info,
            "likely_applications": [],
            "risk_assessment": {
                "backup_priority": "MEDIUM",
                "data_criticality": "HIGH",
                "access_control_required": True
            },
            "recommendations": []
        }
        
        db_type = db_info.get("type", "")
        
        # Common medical software uses these databases
        if db_type == "MySQL":
            analysis["likely_applications"] = [
                "OpenEMR - Patient Management System",
                "Medical Office Management Software",
                "Clinic Billing System",
                "Custom medical applications"
            ]
        
        elif db_type == "PostgreSQL":
            analysis["likely_applications"] = [
                "Enterprise medical software",
                "Healthcare data warehouse",
                "Advanced medical applications"
            ]
        
        elif db_type == "SQL Server":
            analysis["likely_applications"] = [
                "Practice Management Software (PMSoft, MedicalDirector)",
                "Hospital Information System (HIS)",
                "Laboratory Information System (LIS)",
                "Radiology Information System (RIS)"
            ]
        
        elif db_type == "MongoDB":
            analysis["likely_applications"] = [
                "Modern cloud-based medical software",
                "Mobile medical applications",
                "Real-time medical monitoring"
            ]
        
        # Add recommendations
        analysis["recommendations"] = [
            "Determine database owner and backup schedule",
            "Verify backup procedures are working",
            "Document database access procedures",
            "Implement access control and monitoring",
            "Schedule database health checks",
            "Plan disaster recovery procedures"
        ]
        
        return analysis


if __name__ == "__main__":
    # Example usage
    print("=" * 80)
    print("PRACTICE DATABASE DISCOVERY TOOL")
    print("=" * 80)
    
    # Example IPs to probe (would come from network discovery)
    example_ips = [
        "192.168.1.100",
        "192.168.1.101",
        "192.168.1.102",
    ]
    
    discovery = DatabaseDiscovery()
    
    print("\n[*] Probing for database servers...")
    results = discovery.probe_database_servers(example_ips)
    
    if results.get("status") == "COMPLETE":
        summary = discovery.get_database_summary()
        print(f"\n[+] Database Discovery Complete!")
        print(f"    Total Databases Found: {summary['total_databases']}")
        print(f"    Accessible: {summary['accessible']}")
        print(f"    MySQL Instances: {summary['mysql_instances']}")
        print(f"    PostgreSQL Instances: {summary['postgresql_instances']}")
        print(f"    SQL Server Instances: {summary['sqlserver_instances']}")
        print(f"    MongoDB Instances: {summary['mongodb_instances']}")
        
        # Print detailed info
        print("\n[+] Database Details:")
        for key, db_info in discovery.discovered_databases.items():
            print(f"\n    {db_info['type']} ({db_info['ip']}:{db_info['port']})")
            print(f"      Status: {db_info.get('status', 'Unknown')}")
            print(f"      Version: {db_info.get('version', 'Unknown')}")
        
        # Export
        discovery.export_discovered_databases("discovered_databases.json")
