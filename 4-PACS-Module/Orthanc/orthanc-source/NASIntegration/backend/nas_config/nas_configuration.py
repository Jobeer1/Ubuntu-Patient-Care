#!/usr/bin/env python3
"""
NAS Configuration Management
Centralized configuration for NAS paths used in indexing and search operations
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Configuration file location
CONFIG_DIR = os.path.dirname(__file__)
NAS_CONFIG_FILE = os.path.join(CONFIG_DIR, 'nas_settings.json')

# Environment variable override
NAS_PATH_ENV = os.environ.get('NAS_PATH')
NAS_ALIAS_ENV = os.environ.get('NAS_ALIAS')

# Default NAS configurations
DEFAULT_NAS_CONFIGS = {
    'ct_archiving': {
        'path': r'\\155.235.81.155\Image Archiving',
        'description': 'CT scans only (Legacy)',
        'modalities': ['CT'],
        'enabled': False
    },
    'all_modalities': {
        'path': r'\\155.235.81.49\DICOM_Storage',
        'description': 'All modalities (Primary)',
        'modalities': ['CT', 'MR', 'US', 'XC', 'OT', 'PR', 'KO', 'SR', 'SEG'],
        'enabled': True
    }
}


class NASConfiguration:
    """Manages NAS path configuration"""
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load NAS configuration from file or defaults"""
        # Priority: Environment variable > Config file > Defaults
        
        if NAS_PATH_ENV:
            logger.info(f"📍 Using NAS_PATH from environment: {NAS_PATH_ENV}")
            return {'active_path': NAS_PATH_ENV, 'source': 'environment'}
        
        if os.path.exists(NAS_CONFIG_FILE):
            try:
                with open(NAS_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                logger.info(f"📍 Loaded NAS configuration from {NAS_CONFIG_FILE}")
                return config
            except Exception as e:
                logger.warning(f"Failed to load {NAS_CONFIG_FILE}: {e}")
        
        # Use defaults
        logger.info("📍 Using default NAS configurations")
        return {
            'configs': DEFAULT_NAS_CONFIGS,
            'active_alias': 'all_modalities',
            'source': 'defaults'
        }
    
    def get_active_nas_path(self) -> str:
        """
        Get the currently active NAS path
        
        Returns:
            str: UNC path to the active NAS
        """
        if 'active_path' in self.config:
            return self.config['active_path']
        
        # Look up by alias
        alias = self.config.get('active_alias', 'all_modalities')
        configs = self.config.get('configs', DEFAULT_NAS_CONFIGS)
        
        if alias in configs and configs[alias].get('enabled'):
            nas_config = configs[alias]
            logger.info(f"✅ Active NAS: {alias} -> {nas_config['path']}")
            return nas_config['path']
        
        # Fallback to first enabled config
        for key, cfg in configs.items():
            if cfg.get('enabled'):
                logger.info(f"✅ Active NAS: {key} -> {cfg['path']}")
                return cfg['path']
        
        # Last resort: use defaults all_modalities
        return DEFAULT_NAS_CONFIGS['all_modalities']['path']
    
    def set_active_nas(self, alias: str) -> bool:
        """
        Set the active NAS by alias
        
        Args:
            alias: Configuration alias (e.g., 'all_modalities', 'ct_archiving')
        
        Returns:
            bool: True if successful
        """
        configs = self.config.get('configs', DEFAULT_NAS_CONFIGS)
        
        if alias not in configs:
            logger.error(f"❌ Unknown NAS alias: {alias}")
            return False
        
        # Update config
        self.config['active_alias'] = alias
        
        # Save to file
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(NAS_CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"✅ NAS configuration updated: {alias}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save NAS configuration: {e}")
            return False
    
    def get_nas_configs(self) -> Dict:
        """
        Get all available NAS configurations
        
        Returns:
            dict: All NAS configurations
        """
        return self.config.get('configs', DEFAULT_NAS_CONFIGS)
    
    def get_active_nas_config(self) -> Dict:
        """
        Get the active NAS configuration details
        
        Returns:
            dict: Configuration for the active NAS
        """
        alias = self.config.get('active_alias', 'all_modalities')
        configs = self.config.get('configs', DEFAULT_NAS_CONFIGS)
        
        for key, cfg in configs.items():
            if key == alias and cfg.get('enabled'):
                return cfg
        
        # Fallback
        return DEFAULT_NAS_CONFIGS['all_modalities']
    
    def get_nas_path_for_alias(self, alias: str) -> Optional[str]:
        """
        Get NAS path for a specific alias
        
        Args:
            alias: Configuration alias
        
        Returns:
            str or None: NAS path if found
        """
        configs = self.config.get('configs', DEFAULT_NAS_CONFIGS)
        if alias in configs:
            return configs[alias].get('path')
        return None


# Singleton instance
_nas_config_instance: Optional[NASConfiguration] = None


def get_nas_config() -> NASConfiguration:
    """Get or create the NAS configuration singleton"""
    global _nas_config_instance
    if _nas_config_instance is None:
        _nas_config_instance = NASConfiguration()
    return _nas_config_instance


def get_active_nas_path() -> str:
    """Convenience function to get the active NAS path"""
    return get_nas_config().get_active_nas_path()


def set_active_nas_by_alias(alias: str) -> bool:
    """Convenience function to set active NAS by alias"""
    return get_nas_config().set_active_nas(alias)


def reload_nas_config():
    """Reload NAS configuration (useful for testing or dynamic updates)"""
    global _nas_config_instance
    _nas_config_instance = None


if __name__ == '__main__':
    # Test the configuration
    config = get_nas_config()
    print(f"Active NAS: {config.get_active_nas_path()}")
    print(f"All configs: {config.get_nas_configs()}")
    print(f"Active config: {config.get_active_nas_config()}")
