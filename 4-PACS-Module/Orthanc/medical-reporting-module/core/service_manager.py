#!/usr/bin/env python3
"""
Service Manager for Medical Reporting Module
Manages and monitors system services and their status
"""

import logging
import requests
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ServiceManager:
    """Manages system services and their health status"""
    
    def __init__(self):
        self.services = {
            'voice_engine': self._check_voice_engine,
            'dicom_service': self._check_dicom_service,
            'orthanc_pacs': self._check_orthanc_pacs,
            'nas_storage': self._check_nas_storage
        }
    
    def get_all_service_status(self) -> Dict[str, str]:
        """Get status of all registered services"""
        status = {}
        
        for service_name, check_function in self.services.items():
            try:
                status[service_name] = check_function()
            except Exception as e:
                logger.error(f"Error checking {service_name}: {e}")
                status[service_name] = 'error'
        
        return status
    
    def get_service_status(self, service_name: str) -> str:
        """Get status of a specific service"""
        if service_name not in self.services:
            return 'unknown'
        
        try:
            return self.services[service_name]()
        except Exception as e:
            logger.error(f"Error checking {service_name}: {e}")
            return 'error'
    
    def _check_voice_engine(self) -> str:
        """Check if voice engine is available"""
        try:
            # Check if we can import the voice API
            from ..api import voice_api
            return 'ready'
        except ImportError:
            logger.warning("Voice API not available")
            return 'unavailable'
        except Exception as e:
            logger.error(f"Voice engine check failed: {e}")
            return 'error'
    
    def _check_dicom_service(self) -> str:
        """Check DICOM service status"""
        try:
            # Check if DICOM libraries are available
            import pydicom
            return 'ready'
        except ImportError:
            logger.warning("DICOM libraries not available")
            return 'unavailable'
        except Exception as e:
            logger.error(f"DICOM service check failed: {e}")
            return 'error'
    
    def _check_orthanc_pacs(self) -> str:
        """Check Orthanc PACS connectivity"""
        try:
            # Try to connect to local Orthanc instance
            orthanc_url = os.getenv('ORTHANC_URL', 'http://localhost:8042')
            
            response = requests.get(f"{orthanc_url}/system", timeout=5)
            if response.status_code == 200:
                return 'online'
            else:
                return 'offline'
        except requests.exceptions.ConnectionError:
            logger.debug("Orthanc PACS not reachable")
            return 'offline'
        except requests.exceptions.Timeout:
            logger.warning("Orthanc PACS timeout")
            return 'timeout'
        except Exception as e:
            logger.error(f"Orthanc PACS check failed: {e}")
            return 'error'
    
    def _check_nas_storage(self) -> str:
        """Check NAS storage availability"""
        try:
            # Check if NAS mount point exists and is accessible
            nas_path = os.getenv('NAS_MOUNT_PATH', '/mnt/nas')
            
            if os.path.exists(nas_path) and os.path.ismount(nas_path):
                # Try to write a test file
                test_file = os.path.join(nas_path, '.health_check')
                try:
                    with open(test_file, 'w') as f:
                        f.write('health_check')
                    os.remove(test_file)
                    return 'mounted'
                except (OSError, IOError):
                    return 'read_only'
            else:
                return 'unmounted'
        except Exception as e:
            logger.error(f"NAS storage check failed: {e}")
            return 'error'
    
    def restart_service(self, service_name: str) -> bool:
        """Restart a specific service (if supported)"""
        logger.info(f"Restart requested for service: {service_name}")
        
        # For now, just return True as we don't have actual service restart logic
        # In a real implementation, this would restart the actual services
        return True
    
    def get_service_info(self, service_name: str) -> Dict[str, Any]:
        """Get detailed information about a service"""
        info = {
            'name': service_name,
            'status': self.get_service_status(service_name),
            'last_checked': None,
            'details': {}
        }
        
        # Add service-specific details
        if service_name == 'voice_engine':
            info['details'] = {
                'description': 'AI Voice Recognition Engine',
                'capabilities': ['Speech-to-Text', 'Medical Terminology', 'SA English']
            }
        elif service_name == 'dicom_service':
            info['details'] = {
                'description': 'DICOM Image Processing Service',
                'capabilities': ['Image Viewing', 'Metadata Extraction', 'Format Conversion']
            }
        elif service_name == 'orthanc_pacs':
            info['details'] = {
                'description': 'Orthanc PACS Server',
                'capabilities': ['DICOM Storage', 'Query/Retrieve', 'Web Viewer']
            }
        elif service_name == 'nas_storage':
            info['details'] = {
                'description': 'Network Attached Storage',
                'capabilities': ['File Storage', 'Backup', 'Archive']
            }
        
        return info