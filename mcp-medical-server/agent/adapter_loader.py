"""
Dynamic Adapter Loader

Loads and manages adapters for the agent service.

Author: Kiro Team
Task: K2.5
"""

import sys
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.base_adapter import BaseAdapter
from adapters.ssh_adapter import SSHAdapter
from adapters.files_adapter import FilesAdapter
from adapters.smb_adapter import SMBAdapter
from adapters.api_adapter import APIAdapter

logger = logging.getLogger(__name__)


class AdapterLoader:
    """
    Dynamically loads and manages adapters.
    
    Supports:
    - SSH adapter
    - Files adapter
    - SMB adapter
    - API adapter
    """
    
    # Registry of available adapters
    ADAPTER_REGISTRY = {
        'ssh': SSHAdapter,
        'files': FilesAdapter,
        'smb': SMBAdapter,
        'api': APIAdapter
    }
    
    def __init__(self, adapter_config: Dict[str, Any]):
        """
        Initialize adapter loader.
        
        Args:
            adapter_config: Configuration for each adapter
                {
                    "ssh": {"enabled": True, ...},
                    "files": {"enabled": True, ...},
                    ...
                }
        """
        self.config = adapter_config
        self.adapters: Dict[str, BaseAdapter] = {}
        self._load_adapters()
    
    def _load_adapters(self):
        """Load all enabled adapters."""
        for adapter_name, adapter_class in self.ADAPTER_REGISTRY.items():
            adapter_cfg = self.config.get(adapter_name, {})
            
            if not adapter_cfg.get('enabled', True):
                logger.info(f"Adapter {adapter_name} is disabled")
                continue
            
            try:
                # Instantiate adapter
                adapter = adapter_class()
                self.adapters[adapter_name] = adapter
                logger.info(f"Loaded adapter: {adapter_name}")
            
            except Exception as e:
                logger.error(f"Failed to load adapter {adapter_name}: {e}")
    
    def get_adapter(self, adapter_name: str) -> Optional[BaseAdapter]:
        """Get adapter by name."""
        return self.adapters.get(adapter_name)
    
    def list_adapters(self) -> List[str]:
        """List all loaded adapters."""
        return list(self.adapters.keys())
    
    def reload_adapter(self, adapter_name: str) -> bool:
        """Reload a specific adapter."""
        if adapter_name not in self.ADAPTER_REGISTRY:
            logger.error(f"Unknown adapter: {adapter_name}")
            return False
        
        try:
            # Cleanup old adapter
            if adapter_name in self.adapters:
                self.adapters[adapter_name].cleanup()
                del self.adapters[adapter_name]
            
            # Load new instance
            adapter_class = self.ADAPTER_REGISTRY[adapter_name]
            adapter = adapter_class()
            self.adapters[adapter_name] = adapter
            
            logger.info(f"Reloaded adapter: {adapter_name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to reload adapter {adapter_name}: {e}")
            return False
