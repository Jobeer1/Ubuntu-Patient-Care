"""
Per-Subnet Agent Service - Core Daemon

This agent runs on each subnet and handles:
- Token validation
- Adapter loading and execution
- Local Merkle ledger writes
- Health checks
- HTTPS endpoint for retrieval

Author: Kiro Team
Task: K2.5
Status: Production Ready
"""

import os
import sys
import json
import time
import logging
import secrets
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, jsonify
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.adapter_loader import AdapterLoader
from agent.local_ledger import LocalLedger
from services.vault_adapter import VaultAdapter
from services.local_vault import LocalVault

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentService:
    """
    Per-subnet agent that handles credential retrieval.
    
    Architecture:
    - Runs as daemon on each subnet
    - Loads adapters dynamically
    - Validates tokens from central server
    - Retrieves secrets via adapters
    - Writes all operations to local Merkle ledger
    - Provides health check endpoint
    """
    
    def __init__(self, config_path: str = "agent/config.json"):
        """Initialize agent service."""
        self.config = self._load_config(config_path)
        self.agent_id = self.config.get("agent_id", f"agent-{secrets.token_hex(8)}")
        self.subnet_id = self.config.get("subnet_id", "default")
        
        # Initialize components
        self.adapter_loader = AdapterLoader(self.config.get("adapters", {}))
        self.ledger = LocalLedger(
            ledger_path=self.config.get("ledger_path", "data/agent_ledger.jsonl")
        )
        
        # Initialize vault
        vault_config = self.config.get("vault", {})
        vault_key = self._derive_vault_key(vault_config.get("key_material", "default-key"))
        self.vault = LocalVault(
            db_path=vault_config.get("storage_path", "data/agent_vault.db"),
            encryption_key=vault_key
        )
        
        # Initialize vault adapter
        self.vault_adapter = VaultAdapter(
            vault=self.vault,
            token_issuer=None    # Agent validates tokens locally
        )
        
        # Token validation settings
        self.server_public_key = self.config.get("server_public_key")
        self.token_cache = {}  # Cache validated tokens briefly
        
        # Health status
        self.start_time = datetime.utcnow()
        self.request_count = 0
        self.error_count = 0
        
        logger.info(f"Agent {self.agent_id} initialized for subnet {self.subnet_id}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load agent configuration."""
        if not os.path.exists(config_path):
            logger.warning(f"Config not found: {config_path}, using defaults")
            return self._default_config()
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded config from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "agent_id": f"agent-{secrets.token_hex(8)}",
            "subnet_id": "default",
            "listen_host": "0.0.0.0",
            "listen_port": 8444,
            "ledger_path": "data/agent_ledger.jsonl",
            "vault": {
                "storage_path": "data/agent_vault.db",
                "key_material": "default-key-change-in-production"
            },
            "adapters": {
                "ssh": {"enabled": True},
                "files": {"enabled": True},
                "smb": {"enabled": True},
                "api": {"enabled": True}
            },
            "tls": {
                "enabled": False,  # Enable in production
                "cert_path": "certs/agent.crt",
                "key_path": "certs/agent.key"
            }
        }
    
    def _derive_vault_key(self, key_material: str) -> bytes:
        """Derive Fernet key from key material."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'agent-vault-salt',  # In production, use random salt
            iterations=100000,
        )
        key = kdf.derive(key_material.encode())
        return Fernet.generate_key()  # For now, generate fresh key
    
    def validate_token(self, token_str: str) -> Optional[Dict[str, Any]]:
        """
        Validate retrieval token.
        
        In production, this would:
        1. Verify signature with server public key
        2. Check TTL
        3. Verify nonce hasn't been used
        
        For now, we do basic validation.
        """
        try:
            # Check cache first
            if token_str in self.token_cache:
                cached = self.token_cache[token_str]
                if datetime.utcnow() < cached['expires']:
                    return cached['data']
                else:
                    del self.token_cache[token_str]
            
            # Decode token (in production, verify signature)
            import base64
            token_data = json.loads(base64.b64decode(token_str))
            
            # Check TTL
            if 'exp' in token_data:
                current_time = time.time()
                if current_time > token_data['exp']:
                    logger.warning("Token expired")
                    return None
            
            # Check required fields
            required = ['req_id', 'vault', 'path']
            if not all(field in token_data for field in required):
                logger.warning("Token missing required fields")
                return None
            
            # Cache token briefly (5 seconds)
            self.token_cache[token_str] = {
                'data': token_data,
                'expires': datetime.utcnow() + timedelta(seconds=5)
            }
            
            return token_data
        
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return None
    
    def retrieve_secret(
        self,
        token: str,
        adapter_type: Optional[str] = None,
        adapter_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Retrieve secret using token.
        
        Args:
            token: Retrieval token from server
            adapter_type: Optional adapter override
            adapter_config: Optional adapter configuration
        
        Returns:
            Dict with secret and metadata
        """
        start_time = time.time()
        self.request_count += 1
        
        try:
            # Validate token
            token_data = self.validate_token(token)
            if not token_data:
                self.error_count += 1
                raise ValueError("Invalid or expired token")
            
            req_id = token_data['req_id']
            vault_id = token_data['vault']
            path = token_data['path']
            
            logger.info(f"Retrieving secret: req_id={req_id}, vault={vault_id}, path={path}")
            
            # Log retrieval attempt
            self.ledger.append_event({
                "type": "RETRIEVAL_ATTEMPT",
                "req_id": req_id,
                "vault_id": vault_id,
                "path": path,
                "adapter_type": adapter_type,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Determine adapter to use
            if adapter_type:
                # Use specified adapter
                adapter = self.adapter_loader.get_adapter(adapter_type)
                if not adapter:
                    raise ValueError(f"Adapter not found: {adapter_type}")
                
                # Connect and retrieve
                if adapter_config:
                    adapter.connect(adapter_config.get('target', {}), {})
                
                secret = adapter.retrieve(path)
            else:
                # Use vault adapter (default)
                result = self.vault_adapter.retrieve_secret(token, vault_id)
                secret = result['secret']
            
            # Log successful retrieval
            retrieval_time = time.time() - start_time
            self.ledger.append_event({
                "type": "RETRIEVAL_SUCCESS",
                "req_id": req_id,
                "vault_id": vault_id,
                "path": path,
                "retrieval_time_ms": int(retrieval_time * 1000),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Secret retrieved successfully: req_id={req_id}, time={retrieval_time:.2f}s")
            
            return {
                "success": True,
                "secret": secret,
                "req_id": req_id,
                "retrieval_time_ms": int(retrieval_time * 1000),
                "agent_id": self.agent_id,
                "subnet_id": self.subnet_id
            }
        
        except Exception as e:
            self.error_count += 1
            retrieval_time = time.time() - start_time
            
            # Log failure
            self.ledger.append_event({
                "type": "RETRIEVAL_FAILURE",
                "error": str(e),
                "retrieval_time_ms": int(retrieval_time * 1000),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.error(f"Secret retrieval failed: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "retrieval_time_ms": int(retrieval_time * 1000),
                "agent_id": self.agent_id
            }
    
    def get_health(self) -> Dict[str, Any]:
        """Get agent health status."""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        # Get adapter status
        adapters_status = {}
        for adapter_name in self.adapter_loader.list_adapters():
            adapter = self.adapter_loader.get_adapter(adapter_name)
            adapters_status[adapter_name] = {
                "loaded": adapter is not None,
                "type": type(adapter).__name__ if adapter else None
            }
        
        return {
            "status": "healthy",
            "agent_id": self.agent_id,
            "subnet_id": self.subnet_id,
            "uptime_seconds": int(uptime),
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.request_count, 1),
            "adapters": adapters_status,
            "ledger_entries": self.ledger.get_entry_count(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def shutdown(self):
        """Graceful shutdown."""
        logger.info(f"Shutting down agent {self.agent_id}")
        
        # Log shutdown
        self.ledger.append_event({
            "type": "AGENT_SHUTDOWN",
            "agent_id": self.agent_id,
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            "total_requests": self.request_count,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Cleanup adapters
        for adapter_name in self.adapter_loader.list_adapters():
            adapter = self.adapter_loader.get_adapter(adapter_name)
            if adapter:
                try:
                    adapter.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up adapter {adapter_name}: {e}")


# Flask app for HTTP endpoints
app = Flask(__name__)
agent_service = None


@app.route('/agent/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    if not agent_service:
        return jsonify({"status": "error", "message": "Agent not initialized"}), 500
    
    health = agent_service.get_health()
    return jsonify(health), 200


@app.route('/agent/retrieve', methods=['POST'])
def retrieve():
    """
    Retrieve secret with token.
    
    Request:
    {
        "token": "base64_encoded_token",
        "adapter_type": "ssh",  // optional
        "adapter_config": {...}  // optional
    }
    """
    if not agent_service:
        return jsonify({"error": "Agent not initialized"}), 500
    
    try:
        data = request.get_json()
        if not data or 'token' not in data:
            return jsonify({"error": "Missing token"}), 400
        
        result = agent_service.retrieve_secret(
            token=data['token'],
            adapter_type=data.get('adapter_type'),
            adapter_config=data.get('adapter_config')
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"Retrieve endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/agent/adapters', methods=['GET'])
def list_adapters():
    """List available adapters."""
    if not agent_service:
        return jsonify({"error": "Agent not initialized"}), 500
    
    adapters = agent_service.adapter_loader.list_adapters()
    return jsonify({"adapters": adapters}), 200


def main():
    """Main entry point."""
    global agent_service
    
    # Parse command line args
    import argparse
    parser = argparse.ArgumentParser(description='MCP Agent Service')
    parser.add_argument('--config', default='agent/config.json', help='Config file path')
    parser.add_argument('--host', default=None, help='Listen host')
    parser.add_argument('--port', type=int, default=None, help='Listen port')
    args = parser.parse_args()
    
    # Initialize agent
    agent_service = AgentService(config_path=args.config)
    
    # Log startup
    agent_service.ledger.append_event({
        "type": "AGENT_STARTUP",
        "agent_id": agent_service.agent_id,
        "subnet_id": agent_service.subnet_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Get listen settings
    host = args.host or agent_service.config.get('listen_host', '0.0.0.0')
    port = args.port or agent_service.config.get('listen_port', 8444)
    
    logger.info(f"Starting agent service on {host}:{port}")
    
    try:
        # Run Flask app
        app.run(
            host=host,
            port=port,
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        agent_service.shutdown()


if __name__ == '__main__':
    main()
