"""
Credential Manager for Agent 3 - MCP Tools Interface

Exposes vault operations as MCP tools that Granite LLM can call
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from credential_vault import (
    SecureCredentialVault, CredentialType, AccessLevel, CredentialMetadata
)
from credential_embedding import CredentialWeightTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CredentialManager:
    """
    Manages credential vault operations
    
    Used by MCP server to expose credential functions to Granite LLM
    """
    
    def __init__(self, vault_path: str = "./credential_vault.json",
                 master_password: str = "ubuntu_patient_care_vault"):
        """Initialize credential manager"""
        self.vault = SecureCredentialVault(vault_path, master_password)
        self.transformer = CredentialWeightTransformer(embedding_dimension=512)
        self.access_logs = []
    
    def store_database_credential(self, name: str, db_type: str,
                                 host: str, port: int,
                                 database: str, username: str,
                                 password: str, description: str = "") -> Dict[str, Any]:
        """
        Store database credential
        
        Args:
            name: Credential name (e.g., "EHR Database")
            db_type: "mysql", "postgresql", "sqlserver", "mongodb"
            host: Database host/IP
            port: Database port
            database: Database/schema name
            username: Database username
            password: Database password
            description: Human-readable description
        
        Returns: Credential info with ID
        """
        try:
            # Map db_type to CredentialType
            type_map = {
                "mysql": CredentialType.DATABASE_MYSQL,
                "postgresql": CredentialType.DATABASE_POSTGRESQL,
                "sqlserver": CredentialType.DATABASE_SQLSERVER,
                "mongodb": CredentialType.DATABASE_MONGODB
            }
            
            if db_type.lower() not in type_map:
                return {"error": f"Unsupported database type: {db_type}"}
            
            cred_type = type_map[db_type.lower()]
            
            # Store in vault
            cred_id = self.vault.store_credential(
                name=name,
                credential_type=cred_type,
                target_host=host,
                target_port=port,
                target_service=database,
                username=username,
                password=password,
                description=description,
                requires_mfa=False,
                auto_rotate=True
            )
            
            logger.info(f"Stored database credential: {name} ({db_type})")
            
            return {
                "success": True,
                "credential_id": cred_id,
                "name": name,
                "type": db_type,
                "host": host,
                "port": port,
                "message": f"Credential stored successfully"
            }
        
        except Exception as e:
            logger.error(f"Failed to store database credential: {e}")
            return {"error": str(e)}
    
    def store_equipment_credential(self, name: str, equipment_type: str,
                                  host: str, port: int,
                                  service: str, username: str,
                                  password: str, description: str = "") -> Dict[str, Any]:
        """
        Store medical equipment credential
        
        Args:
            name: Credential name (e.g., "PACS Server")
            equipment_type: "medical_device", "nas_smb", "nas_nfs", "vm_hypervisor"
            host: Equipment host/IP
            port: Service port
            service: Service name
            username: Access username
            password: Access password
            description: Description
        
        Returns: Credential info
        """
        try:
            type_map = {
                "medical_device": CredentialType.MEDICAL_DEVICE,
                "nas_smb": CredentialType.NAS_SMB,
                "nas_nfs": CredentialType.NAS_NFS,
                "vm_hypervisor": CredentialType.VM_HYPERVISOR,
                "backup": CredentialType.BACKUP_SYSTEM
            }
            
            if equipment_type.lower() not in type_map:
                return {"error": f"Unsupported equipment type: {equipment_type}"}
            
            cred_type = type_map[equipment_type.lower()]
            
            cred_id = self.vault.store_credential(
                name=name,
                credential_type=cred_type,
                target_host=host,
                target_port=port,
                target_service=service,
                username=username,
                password=password,
                description=description,
                requires_mfa=False,
                auto_rotate=True
            )
            
            logger.info(f"Stored equipment credential: {name} ({equipment_type})")
            
            return {
                "success": True,
                "credential_id": cred_id,
                "name": name,
                "type": equipment_type,
                "host": host,
                "message": f"Equipment credential stored successfully"
            }
        
        except Exception as e:
            logger.error(f"Failed to store equipment credential: {e}")
            return {"error": str(e)}
    
    def retrieve_credential(self, credential_id: str, clinician_id: str,
                           reason: str, access_level: str = "clinician") -> Dict[str, Any]:
        """
        Retrieve credential for use
        
        Args:
            credential_id: ID of credential to retrieve
            clinician_id: ID/name of clinician requesting access
            reason: Reason for access (for audit trail)
            access_level: "clinician", "administrator", "emergency"
        
        Returns: Credential data or error
        """
        try:
            # Map access level
            level_map = {
                "clinician": AccessLevel.CLINICIAN,
                "administrator": AccessLevel.ADMINISTRATOR,
                "emergency": AccessLevel.EMERGENCY,
                "audit": AccessLevel.AUDIT_ONLY
            }
            
            access_level_enum = level_map.get(access_level.lower(), AccessLevel.CLINICIAN)
            
            credential = self.vault.retrieve_credential(
                credential_id,
                accessed_by=clinician_id,
                reason=reason,
                access_level=access_level_enum
            )
            
            if not credential:
                return {"error": "Unable to retrieve credential. Check permissions or expiration."}
            
            logger.info(f"Credential retrieved by {clinician_id}: {reason}")
            
            return {
                "success": True,
                "username": credential.get("username"),
                "password": credential.get("password"),
                "host": credential.get("host"),
                "port": credential.get("port"),
                "retrieved_at": datetime.now().isoformat(),
                "message": "Credential retrieved successfully"
            }
        
        except Exception as e:
            logger.error(f"Failed to retrieve credential: {e}")
            return {"error": str(e)}
    
    def list_credentials(self, access_level: str = "clinician") -> Dict[str, Any]:
        """
        List all available credentials
        
        Returns: List of credential summaries
        """
        try:
            level_map = {
                "clinician": AccessLevel.CLINICIAN,
                "administrator": AccessLevel.ADMINISTRATOR,
                "emergency": AccessLevel.EMERGENCY,
            }
            
            access_level_enum = level_map.get(access_level.lower(), AccessLevel.CLINICIAN)
            
            credentials = self.vault.list_credentials(access_level_enum)
            
            return {
                "success": True,
                "count": len(credentials),
                "credentials": credentials
            }
        
        except Exception as e:
            logger.error(f"Failed to list credentials: {e}")
            return {"error": str(e)}
    
    def rotate_credential(self, credential_id: str, new_username: str,
                         new_password: str, rotated_by: str) -> Dict[str, Any]:
        """
        Rotate credential to new values
        
        Args:
            credential_id: Credential to rotate
            new_username: New username
            new_password: New password
            rotated_by: Admin rotating the credential
        
        Returns: Status
        """
        try:
            success = self.vault.rotate_credential(
                credential_id,
                new_username,
                new_password,
                rotated_by
            )
            
            if success:
                logger.info(f"Credential rotated by {rotated_by}")
                return {
                    "success": True,
                    "message": "Credential rotated successfully"
                }
            else:
                return {"error": "Failed to rotate credential"}
        
        except Exception as e:
            logger.error(f"Failed to rotate credential: {e}")
            return {"error": str(e)}
    
    def get_expiring_credentials(self, days: int = 30) -> Dict[str, Any]:
        """
        Get credentials expiring soon
        
        Args:
            days: Show credentials expiring within this many days
        
        Returns: List of expiring credentials
        """
        try:
            expiring = self.vault.get_expiring_soon(days)
            
            return {
                "success": True,
                "days_threshold": days,
                "count": len(expiring),
                "credentials": expiring
            }
        
        except Exception as e:
            logger.error(f"Failed to get expiring credentials: {e}")
            return {"error": str(e)}
    
    def check_suspicious_activity(self, failed_attempts_threshold: int = 5) -> Dict[str, Any]:
        """
        Check for suspicious credential activity
        
        Args:
            failed_attempts_threshold: How many failed attempts triggers alert
        
        Returns: List of suspicious activities
        """
        try:
            suspicious = self.vault.detect_suspicious_activity(failed_attempts_threshold)
            
            if suspicious:
                logger.warning(f"Detected {len(suspicious)} credentials with suspicious activity")
            
            return {
                "success": True,
                "threshold": failed_attempts_threshold,
                "count": len(suspicious),
                "suspicious_credentials": suspicious
            }
        
        except Exception as e:
            logger.error(f"Failed to check suspicious activity: {e}")
            return {"error": str(e)}
    
    def get_audit_logs(self, credential_id: Optional[str] = None,
                      hours: int = 24) -> Dict[str, Any]:
        """
        Get audit logs for credential access
        
        Args:
            credential_id: Specific credential (optional)
            hours: Look back this many hours
        
        Returns: Audit logs
        """
        try:
            logs = self.vault.get_access_logs(credential_id, hours)
            
            return {
                "success": True,
                "hours_lookback": hours,
                "count": len(logs),
                "logs": logs
            }
        
        except Exception as e:
            logger.error(f"Failed to get audit logs: {e}")
            return {"error": str(e)}
    
    def export_credential_inventory(self) -> Dict[str, Any]:
        """
        Export complete credential inventory
        
        Returns: Full inventory as JSON
        """
        try:
            credentials = self.vault.list_credentials()
            
            # Group by type
            by_type = {}
            for cred in credentials:
                cred_type = cred.get("type", "unknown")
                if cred_type not in by_type:
                    by_type[cred_type] = []
                by_type[cred_type].append(cred)
            
            return {
                "success": True,
                "total_credentials": len(credentials),
                "by_type": by_type,
                "credentials": credentials,
                "exported_at": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to export inventory: {e}")
            return {"error": str(e)}
    
    def get_credential_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored credentials
        
        Returns: Statistics
        """
        try:
            credentials = self.vault.list_credentials()
            expiring = self.vault.get_expiring_soon(30)
            suspicious = self.vault.detect_suspicious_activity()
            
            # Count by type
            by_type = {}
            for cred in credentials:
                cred_type = cred.get("type", "unknown")
                by_type[cred_type] = by_type.get(cred_type, 0) + 1
            
            # Count expired
            expired_count = sum(1 for c in credentials if c.get("is_expired", False))
            
            # Recent access
            recent_logs = self.vault.get_access_logs(hours=24)
            successful_access = sum(1 for log in recent_logs if log.get("success", False))
            failed_access = sum(1 for log in recent_logs if not log.get("success", False))
            
            return {
                "success": True,
                "total_credentials": len(credentials),
                "expired_count": expired_count,
                "expiring_soon": len(expiring),
                "suspicious_activity": len(suspicious),
                "by_type": by_type,
                "recent_access": {
                    "successful": successful_access,
                    "failed": failed_access,
                    "total": successful_access + failed_access
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}


if __name__ == "__main__":
    print("=" * 80)
    print("CREDENTIAL MANAGER - MCP Tools Interface")
    print("=" * 80)
    
    # Initialize manager
    mgr = CredentialManager()
    
    # Store database credential
    print("\n[*] Storing database credentials...")
    result = mgr.store_database_credential(
        name="EHR Database",
        db_type="mysql",
        host="192.168.1.20",
        port=3306,
        database="patient_records",
        username="ehr_admin",
        password="SecurePassword123!",
        description="Main electronic health records database"
    )
    print(f"    {result}")
    ehr_cred_id = result.get("credential_id")
    
    # Store equipment credential
    print("\n[*] Storing equipment credentials...")
    result = mgr.store_equipment_credential(
        name="PACS Server",
        equipment_type="medical_device",
        host="192.168.1.15",
        port=104,
        service="dicom",
        username="pacs_admin",
        password="PACSPassword456!",
        description="Medical imaging DICOM server"
    )
    print(f"    {result}")
    
    # List credentials
    print("\n[+] Available credentials:")
    result = mgr.list_credentials()
    if result.get("success"):
        print(f"    Total: {result['count']}")
        for cred in result["credentials"]:
            print(f"    - {cred['name']} ({cred['type']}) @ {cred['host']}")
    
    # Retrieve credential
    if ehr_cred_id:
        print("\n[*] Retrieving credential...")
        result = mgr.retrieve_credential(
            ehr_cred_id,
            clinician_id="Dr_Smith",
            reason="Patient record lookup",
            access_level="clinician"
        )
        if result.get("success"):
            print(f"    Retrieved: {result['username']}@{result['host']}:{result['port']}")
        else:
            print(f"    Error: {result.get('error')}")
    
    # Get statistics
    print("\n[+] Credential Statistics:")
    result = mgr.get_credential_statistics()
    if result.get("success"):
        print(f"    Total credentials: {result['total_credentials']}")
        print(f"    Expired: {result['expired_count']}")
        print(f"    Expiring soon (30d): {result['expiring_soon']}")
        print(f"    By type: {result['by_type']}")
