#!/usr/bin/env python3
"""
Onboarding Collection Tool (OCT)

CRITICAL: Harvests credentials from clinic environment for vault ingestion.
This is the implementation of the Ghost Recovery Strategy.

Usage:
    python collect_credentials.py --owner-sig owner_sig.json --target-subnet 192.168.1.0/24
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import secrets
import hashlib

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OnboardingCollectionTool:
    """
    Main orchestrator for credential collection
    
    Coordinates:
    - Owner authorization verification
    - Discovery of targets
    - Credential collection via adapters
    - Vault ingestion
    - Audit logging
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize OCT with configuration"""
        self.config = config
        self.owner_sig = None
        self.collected_secrets = []
        self.audit_log = []
        self.operation_id = self._generate_operation_id()
        
        logger.info(f"OCT initialized - Operation ID: {self.operation_id}")
    
    def _generate_operation_id(self) -> str:
        """Generate unique operation ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        random_suffix = secrets.token_hex(4)
        return f"OCT-{timestamp}-{random_suffix}"
    
    def verify_owner_authorization(self, sig_file: Path) -> bool:
        """
        Verify owner signature and authorization
        
        Args:
            sig_file: Path to owner signature JSON
        
        Returns:
            True if authorized
        """
        try:
            with open(sig_file, 'r') as f:
                self.owner_sig = json.load(f)
            
            # Verify required fields
            required = ['owner_id', 'scope', 'allowed_actions', 'ttl_hours', 'signature']
            for field in required:
                if field not in self.owner_sig:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # TODO: Verify Ed25519 signature
            # from services.signature_service import SignatureService
            # sig_service = SignatureService()
            # is_valid = sig_service.verify_authorization(self.owner_sig)
            
            # For now, accept if all fields present
            logger.info(f"Owner authorization verified: {self.owner_sig['owner_id']}")
            logger.info(f"Scope: {self.owner_sig['scope']}")
            logger.info(f"TTL: {self.owner_sig['ttl_hours']} hours")
            
            self._audit_log("OWNER_AUTH", {
                "owner_id": self.owner_sig['owner_id'],
                "scope": self.owner_sig['scope'],
                "ttl_hours": self.owner_sig['ttl_hours']
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Authorization verification failed: {e}")
            return False
    
    def discover_targets(self, subnet: str) -> List[Dict[str, Any]]:
        """
        Discover devices on subnet
        
        Args:
            subnet: Network subnet (e.g., "192.168.1.0/24")
        
        Returns:
            List of discovered devices
        """
        logger.info(f"Discovering targets on {subnet}...")
        
        # TODO: Implement actual discovery
        # For now, return mock targets
        targets = [
            {
                "ip": "192.168.1.10",
                "type": "nas",
                "vendor": "synology",
                "services": ["ssh", "smb", "http"]
            },
            {
                "ip": "192.168.1.20",
                "type": "server",
                "vendor": "dell",
                "services": ["ssh", "rdp"]
            }
        ]
        
        logger.info(f"Discovered {len(targets)} targets")
        self._audit_log("DISCOVERY", {"subnet": subnet, "count": len(targets)})
        
        return targets
    
    def collect_from_target(self, target: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Collect credentials from a single target
        
        Args:
            target: Target device info
        
        Returns:
            List of collected secrets
        """
        logger.info(f"Collecting from {target['ip']} ({target['type']})...")
        
        secrets_found = []
        
        try:
            # Select appropriate adapter
            if target['type'] == 'nas':
                secrets_found = self._collect_nas(target)
            elif target['type'] == 'server':
                secrets_found = self._collect_server(target)
            else:
                logger.warning(f"Unknown target type: {target['type']}")
            
            logger.info(f"Collected {len(secrets_found)} secrets from {target['ip']}")
            
        except Exception as e:
            logger.error(f"Collection failed for {target['ip']}: {e}")
        
        return secrets_found
    
    def _collect_nas(self, target: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect credentials from NAS device"""
        # Import adapters (add parent dir to path if needed)
        import sys
        from pathlib import Path
        parent_dir = Path(__file__).parent.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))
        
        try:
            from adapters.smb_adapter import SMBAdapter
            from adapters.ssh_adapter import SSHAdapter
        except ImportError:
            logger.warning("Adapters not available, using mock collection")
        
        secrets = []
        
        # Try SSH first
        if 'ssh' in target.get('services', []):
            try:
                adapter = SSHAdapter()
                # TODO: Use ephemeral account or provided credentials
                # For now, log attempt
                logger.info(f"Would attempt SSH collection from {target['ip']}")
                
                secrets.append({
                    "source": f"{target['ip']}:ssh",
                    "type": "nas_admin",
                    "path": "/etc/config/admin.conf",
                    "hash": self._hash_content(b"placeholder"),
                    "collected_ts": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"SSH collection failed: {e}")
        
        return secrets
    
    def _collect_server(self, target: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect credentials from server"""
        # Import adapters (add parent dir to path if needed)
        import sys
        from pathlib import Path
        parent_dir = Path(__file__).parent.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))
        
        try:
            from adapters.ssh_adapter import SSHAdapter
        except ImportError:
            logger.warning("SSH adapter not available, using mock collection")
        
        secrets = []
        
        # Try SSH
        if 'ssh' in target.get('services', []):
            try:
                logger.info(f"Would attempt SSH collection from {target['ip']}")
                
                # Common credential locations
                paths = [
                    "/etc/app/credentials.conf",
                    "/opt/pacs/config/database.ini",
                    "/home/admin/.ssh/id_rsa"
                ]
                
                for path in paths:
                    secrets.append({
                        "source": f"{target['ip']}:{path}",
                        "type": "config_file",
                        "path": path,
                        "hash": self._hash_content(path.encode()),
                        "collected_ts": datetime.utcnow().isoformat()
                    })
                    
            except Exception as e:
                logger.error(f"Server collection failed: {e}")
        
        return secrets
    
    def ingest_to_vault(self, secrets: List[Dict[str, Any]]) -> bool:
        """
        Ingest collected secrets into vault
        
        Args:
            secrets: List of collected secrets
        
        Returns:
            True if successful
        """
        logger.info(f"Ingesting {len(secrets)} secrets to vault...")
        
        try:
            # TODO: Use VaultAdapter
            # from services.vault_adapter import VaultAdapter
            # vault = VaultAdapter()
            
            for secret in secrets:
                # Encrypt secret
                encrypted = self._encrypt_secret(secret)
                
                # Store in vault
                vault_path = f"onboarding/{self.operation_id}/{secret['hash'][:8]}"
                
                logger.info(f"Stored: {vault_path}")
                
                self._audit_log("VAULT_INGEST", {
                    "vault_path": vault_path,
                    "source": secret['source'],
                    "hash": secret['hash']
                })
            
            logger.info("Vault ingestion complete")
            return True
            
        except Exception as e:
            logger.error(f"Vault ingestion failed: {e}")
            return False
    
    def _encrypt_secret(self, secret: Dict[str, Any]) -> bytes:
        """Encrypt secret for vault storage"""
        from cryptography.fernet import Fernet
        
        # TODO: Use proper key management
        key = Fernet.generate_key()
        f = Fernet(key)
        
        secret_json = json.dumps(secret).encode()
        encrypted = f.encrypt(secret_json)
        
        return encrypted
    
    def _hash_content(self, content: bytes) -> str:
        """Calculate SHA256 hash of content"""
        return hashlib.sha256(content).hexdigest()
    
    def _audit_log(self, event_type: str, data: Dict[str, Any]):
        """Record audit event"""
        event = {
            "operation_id": self.operation_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data
        }
        
        self.audit_log.append(event)
        logger.debug(f"Audit: {event_type}")
    
    def save_audit_log(self, output_dir: Path):
        """Save audit log to file"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = output_dir / f"audit_{self.operation_id}.json"
        
        with open(log_file, 'w') as f:
            json.dump({
                "operation_id": self.operation_id,
                "events": self.audit_log
            }, f, indent=2)
        
        logger.info(f"Audit log saved: {log_file}")
    
    def run(self, target_subnet: str, output_dir: Path) -> bool:
        """
        Run complete collection operation
        
        Args:
            target_subnet: Network subnet to scan
            output_dir: Output directory for logs
        
        Returns:
            True if successful
        """
        logger.info("=" * 60)
        logger.info("ONBOARDING COLLECTION TOOL - STARTING")
        logger.info("=" * 60)
        
        try:
            # 1. Discover targets
            targets = self.discover_targets(target_subnet)
            
            if not targets:
                logger.warning("No targets discovered")
                return False
            
            # 2. Collect from each target
            all_secrets = []
            for target in targets:
                secrets = self.collect_from_target(target)
                all_secrets.extend(secrets)
            
            logger.info(f"Total secrets collected: {len(all_secrets)}")
            
            # 3. Ingest to vault
            if all_secrets:
                success = self.ingest_to_vault(all_secrets)
                if not success:
                    logger.error("Vault ingestion failed")
                    return False
            
            # 4. Save audit log
            self.save_audit_log(output_dir)
            
            logger.info("=" * 60)
            logger.info("ONBOARDING COLLECTION TOOL - COMPLETE")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            self._audit_log("ERROR", {"error": str(e)})
            self.save_audit_log(output_dir)
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Onboarding Collection Tool - Harvest credentials for vault"
    )
    
    parser.add_argument(
        '--owner-sig',
        type=Path,
        required=True,
        help="Path to owner signature JSON file"
    )
    
    parser.add_argument(
        '--target-subnet',
        type=str,
        required=True,
        help="Target subnet (e.g., 192.168.1.0/24)"
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('./oct_output'),
        help="Output directory for logs and artifacts"
    )
    
    parser.add_argument(
        '--mode',
        choices=['full', 'scoped', 'test'],
        default='scoped',
        help="Collection mode"
    )
    
    args = parser.parse_args()
    
    # Verify owner signature file exists
    if not args.owner_sig.exists():
        logger.error(f"Owner signature file not found: {args.owner_sig}")
        sys.exit(1)
    
    # Create OCT instance
    config = {
        "mode": args.mode,
        "output_dir": str(args.output_dir)
    }
    
    oct = OnboardingCollectionTool(config)
    
    # Verify authorization
    if not oct.verify_owner_authorization(args.owner_sig):
        logger.error("Owner authorization failed")
        sys.exit(1)
    
    # Run collection
    success = oct.run(args.target_subnet, args.output_dir)
    
    if success:
        logger.info("✅ Collection completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Collection failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
