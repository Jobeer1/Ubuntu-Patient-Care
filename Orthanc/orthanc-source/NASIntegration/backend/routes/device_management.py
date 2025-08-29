"""
Device Management Module for South African Medical Imaging System
Handles device configuration, settings, and NAS integration
"""

import json
import os
import logging
import socket
from datetime import datetime
from .nas_utils import set_device_name, get_device_name, ping_device

logger = logging.getLogger(__name__)

class DeviceManager:
    def __init__(self, config_dir=None):
        """Initialize Device Manager with configuration directory"""
        if config_dir is None:
            config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
        
        self.config_dir = config_dir
        self.device_config_file = os.path.join(config_dir, 'device_configs.json')
        self.nas_config_file = os.path.join(config_dir, 'nas_configs.json')
        
        # Ensure config directory exists
        os.makedirs(config_dir, exist_ok=True)
        
        # Initialize config files if they don't exist
        self._initialize_config_files()
    
    def _initialize_config_files(self):
        """Initialize configuration files with default structure"""
        if not os.path.exists(self.device_config_file):
            default_device_config = {
                "device_configurations": {},
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }
            with open(self.device_config_file, 'w') as f:
                json.dump(default_device_config, f, indent=2)
        
        if not os.path.exists(self.nas_config_file):
            default_nas_config = {
                "nas_devices": {},
                "default_settings": {
                    "dicom_port": 4242,
                    "web_port": 8042,
                    "storage_path": "/var/lib/orthanc/db",
                    "auto_routing": False,
                    "compression": True
                },
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }
            with open(self.nas_config_file, 'w') as f:
                json.dump(default_nas_config, f, indent=2)
    
    def get_device_configuration(self, device_id):
        """Get configuration for a specific device"""
        try:
            with open(self.device_config_file, 'r') as f:
                config = json.load(f)
            
            return config['device_configurations'].get(device_id, {})
        
        except Exception as e:
            logger.error(f"Error getting device configuration: {e}")
            return {}
    
    def save_device_configuration(self, device_id, configuration):
        """Save configuration for a specific device"""
        try:
            # Load existing config
            with open(self.device_config_file, 'r') as f:
                config = json.load(f)
            
            # Update device configuration
            config['device_configurations'][device_id] = {
                **configuration,
                'last_updated': datetime.now().isoformat()
            }
            config['last_updated'] = datetime.now().isoformat()
            
            # Save updated config
            with open(self.device_config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Device configuration saved for {device_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving device configuration: {e}")
            return False
    
    def configure_nas_device(self, ip_address, mac_address, nas_config):
        """Configure a device as a NAS server"""
        try:
            device_id = f"{ip_address}_{mac_address.replace(':', '_')}"
            
            # Validate required NAS configuration
            required_fields = ['dicom_port', 'web_port', 'storage_path']
            for field in required_fields:
                if field not in nas_config:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }
            
            # Load existing NAS config
            with open(self.nas_config_file, 'r') as f:
                config = json.load(f)
            
            # Prepare NAS device configuration
            nas_device_config = {
                'ip_address': ip_address,
                'mac_address': mac_address,
                'dicom_port': nas_config.get('dicom_port', 4242),
                'web_port': nas_config.get('web_port', 8042),
                'storage_path': nas_config.get('storage_path', '/var/lib/orthanc/db'),
                'auto_routing': nas_config.get('auto_routing', False),
                'compression': nas_config.get('compression', True),
                'enabled': nas_config.get('enabled', True),
                'priority': nas_config.get('priority', 1),
                'backup_location': nas_config.get('backup_location', False),
                'created_date': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
            
            # Add device to NAS config
            config['nas_devices'][device_id] = nas_device_config
            config['last_updated'] = datetime.now().isoformat()
            
            # Save updated NAS config
            with open(self.nas_config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"NAS device configured: {ip_address}")
            
            return {
                'success': True,
                'message': f'NAS device configured successfully at {ip_address}',
                'device_id': device_id,
                'configuration': nas_device_config
            }
        
        except Exception as e:
            logger.error(f"Error configuring NAS device: {e}")
            return {
                'success': False,
                'error': f'Failed to configure NAS device: {str(e)}'
            }
    
    def get_nas_devices(self):
        """Get all configured NAS devices"""
        try:
            with open(self.nas_config_file, 'r') as f:
                config = json.load(f)
            
            return config.get('nas_devices', {})
        
        except Exception as e:
            logger.error(f"Error getting NAS devices: {e}")
            return {}
    
    def update_device_name(self, mac_address, ip_address, new_name):
        """Update device name using utility function"""
        try:
            result = set_device_name(mac_address, ip_address, new_name)
            if result:
                logger.info(f"Device name updated: {new_name} for {ip_address}")
                return {
                    'success': True,
                    'message': f'Device name updated to "{new_name}"'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to save device name'
                }
        
        except Exception as e:
            logger.error(f"Error updating device name: {e}")
            return {
                'success': False,
                'error': f'Failed to update device name: {str(e)}'
            }
    
    def test_device_connectivity(self, ip_address, test_type='ping'):
        """Test connectivity to a device"""
        try:
            if test_type == 'ping':
                result = ping_device(ip_address)
                return {
                    'success': True,
                    'test_type': 'ping',
                    'reachable': result['reachable'],
                    'response_time': result['response_time'],
                    'details': result
                }
            
            elif test_type == 'dicom_port':
                # Test DICOM port (4242) connectivity
                port = 4242
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                
                start_time = datetime.now()
                result = sock.connect_ex((ip_address, port))
                end_time = datetime.now()
                
                sock.close()
                
                response_time = (end_time - start_time).total_seconds() * 1000
                
                return {
                    'success': True,
                    'test_type': 'dicom_port',
                    'reachable': result == 0,
                    'port': port,
                    'response_time': f"{response_time:.1f}ms" if result == 0 else "Timeout"
                }
            
            elif test_type == 'web_port':
                # Test Web interface port (8042) connectivity
                port = 8042
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                
                start_time = datetime.now()
                result = sock.connect_ex((ip_address, port))
                end_time = datetime.now()
                
                sock.close()
                
                response_time = (end_time - start_time).total_seconds() * 1000
                
                return {
                    'success': True,
                    'test_type': 'web_port',
                    'reachable': result == 0,
                    'port': port,
                    'response_time': f"{response_time:.1f}ms" if result == 0 else "Timeout"
                }
            
            else:
                return {
                    'success': False,
                    'error': f'Unknown test type: {test_type}'
                }
        
        except Exception as e:
            logger.error(f"Device connectivity test failed: {e}")
            return {
                'success': False,
                'error': f'Connectivity test failed: {str(e)}',
                'test_type': test_type
            }
    
    def get_device_details(self, ip_address, mac_address):
        """Get comprehensive device details"""
        try:
            device_id = f"{ip_address}_{mac_address.replace(':', '_')}"
            
            # Get device configuration
            device_config = self.get_device_configuration(device_id)
            
            # Get NAS configuration if device is configured as NAS
            nas_devices = self.get_nas_devices()
            nas_config = nas_devices.get(device_id, {})
            
            # Get custom name
            custom_name = get_device_name(mac_address, ip_address)
            
            # Test connectivity
            ping_result = self.test_device_connectivity(ip_address, 'ping')
            
            device_details = {
                'device_id': device_id,
                'ip_address': ip_address,
                'mac_address': mac_address,
                'custom_name': custom_name,
                'is_nas_configured': bool(nas_config),
                'device_configuration': device_config,
                'nas_configuration': nas_config,
                'connectivity': {
                    'ping': ping_result
                },
                'last_updated': datetime.now().isoformat()
            }
            
            # Add additional connectivity tests if NAS configured
            if nas_config:
                dicom_test = self.test_device_connectivity(ip_address, 'dicom_port')
                web_test = self.test_device_connectivity(ip_address, 'web_port')
                
                device_details['connectivity']['dicom_port'] = dicom_test
                device_details['connectivity']['web_port'] = web_test
            
            return {
                'success': True,
                'device_details': device_details
            }
        
        except Exception as e:
            logger.error(f"Error getting device details: {e}")
            return {
                'success': False,
                'error': f'Failed to get device details: {str(e)}'
            }

    def get_device_name(self, mac_address, ip_address=None):
        """Return custom device name (wrapper around nas_utils.get_device_name).

        This method exists so higher-level modules can call
        device_manager.get_device_name(...) without importing nas_utils.
        """
        try:
            # get_device_name from nas_utils is imported at module level
            return get_device_name(mac_address, ip_address)
        except Exception as e:
            logger.error(f"Error fetching device name for {mac_address}/{ip_address}: {e}")
            return 'Unknown'
    
    def remove_nas_configuration(self, ip_address, mac_address):
        """Remove NAS configuration for a device"""
        try:
            device_id = f"{ip_address}_{mac_address.replace(':', '_')}"
            
            # Load NAS config
            with open(self.nas_config_file, 'r') as f:
                config = json.load(f)
            
            # Remove device from NAS config
            if device_id in config['nas_devices']:
                del config['nas_devices'][device_id]
                config['last_updated'] = datetime.now().isoformat()
                
                # Save updated config
                with open(self.nas_config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                
                logger.info(f"NAS configuration removed for {ip_address}")
                
                return {
                    'success': True,
                    'message': f'NAS configuration removed for {ip_address}'
                }
            else:
                return {
                    'success': False,
                    'error': 'Device is not configured as NAS'
                }
        
        except Exception as e:
            logger.error(f"Error removing NAS configuration: {e}")
            return {
                'success': False,
                'error': f'Failed to remove NAS configuration: {str(e)}'
            }
