"""
Orthanc DICOM server integration client
"""

import requests
import logging
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
import base64
import json
from config.integration_config import IntegrationConfig

logger = logging.getLogger(__name__)

class OrthancClient:
    """Client for Orthanc DICOM server integration"""
    
    def __init__(self):
        self.config = IntegrationConfig.ORTHANC_CONFIG
        self.base_url = self.config['url']
        self.username = self.config['username']
        self.password = self.config['password']
        self.timeout = self.config['timeout']
        self.retry_attempts = self.config['retry_attempts']
        self.retry_delay = self.config['retry_delay']
        
        # Create authentication header
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {encoded_credentials}"
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[requests.Response]:
        """Make authenticated request to Orthanc server"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = kwargs.get('headers', {})
        headers['Authorization'] = self.auth_header
        kwargs['headers'] = headers
        kwargs['timeout'] = self.timeout
        
        for attempt in range(self.retry_attempts):
            try:
                response = requests.request(method, url, **kwargs)
                return response
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt == self.retry_attempts - 1:
                    logger.error(f"All {self.retry_attempts} attempts failed for {method} {endpoint}")
                    return None
                
                import time
                time.sleep(self.retry_delay)
        
        return None
    
    def get_system_info(self) -> Optional[Dict[str, Any]]:
        """Get Orthanc system information"""
        response = self._make_request('GET', '/system')
        if response and response.status_code == 200:
            return response.json()
        return None
    
    def search_studies(self, query: Dict[str, str]) -> List[Dict[str, Any]]:
        """Search for studies using DICOM tags"""
        try:
            response = self._make_request('POST', '/tools/find', json={
                'Level': 'Study',
                'Query': query,
                'Expand': True
            })
            
            if response and response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Study search failed: {response.status_code if response else 'No response'}")
                return []
                
        except Exception as e:
            logger.error(f"Study search error: {e}")
            return []
    
    def get_study_details(self, study_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a study"""
        response = self._make_request('GET', f'/studies/{study_id}')
        if response and response.status_code == 200:
            return response.json()
        return None
    
    def get_study_series(self, study_id: str) -> List[Dict[str, Any]]:
        """Get all series in a study"""
        try:
            response = self._make_request('GET', f'/studies/{study_id}/series')
            if response and response.status_code == 200:
                series_ids = response.json()
                
                # Get detailed info for each series
                series_details = []
                for series_id in series_ids:
                    series_response = self._make_request('GET', f'/series/{series_id}')
                    if series_response and series_response.status_code == 200:
                        series_details.append(series_response.json())
                
                return series_details
            return []
            
        except Exception as e:
            logger.error(f"Error getting study series: {e}")
            return []
    
    def get_series_instances(self, series_id: str) -> List[Dict[str, Any]]:
        """Get all instances in a series"""
        try:
            response = self._make_request('GET', f'/series/{series_id}/instances')
            if response and response.status_code == 200:
                instance_ids = response.json()
                
                # Get detailed info for each instance
                instance_details = []
                for instance_id in instance_ids:
                    instance_response = self._make_request('GET', f'/instances/{instance_id}')
                    if instance_response and instance_response.status_code == 200:
                        instance_details.append(instance_response.json())
                
                return instance_details
            return []
            
        except Exception as e:
            logger.error(f"Error getting series instances: {e}")
            return []
    
    def get_instance_image(self, instance_id: str, frame: int = 0) -> Optional[bytes]:
        """Get image data for a DICOM instance"""
        try:
            endpoint = f'/instances/{instance_id}/frames/{frame}/image-uint8'
            response = self._make_request('GET', endpoint)
            
            if response and response.status_code == 200:
                return response.content
            return None
            
        except Exception as e:
            logger.error(f"Error getting instance image: {e}")
            return None
    
    def get_instance_tags(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get DICOM tags for an instance"""
        response = self._make_request('GET', f'/instances/{instance_id}/tags')
        if response and response.status_code == 200:
            return response.json()
        return None
    
    def get_patient_studies(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all studies for a patient"""
        return self.search_studies({'PatientID': patient_id})
    
    def get_study_by_accession(self, accession_number: str) -> Optional[Dict[str, Any]]:
        """Get study by accession number"""
        studies = self.search_studies({'AccessionNumber': accession_number})
        return studies[0] if studies else None
    
    def download_study_zip(self, study_id: str) -> Optional[bytes]:
        """Download entire study as ZIP file"""
        try:
            response = self._make_request('GET', f'/studies/{study_id}/archive')
            if response and response.status_code == 200:
                return response.content
            return None
            
        except Exception as e:
            logger.error(f"Error downloading study ZIP: {e}")
            return None
    
    def get_study_statistics(self, study_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a study"""
        response = self._make_request('GET', f'/studies/{study_id}/statistics')
        if response and response.status_code == 200:
            return response.json()
        return None
    
    def check_connectivity(self) -> bool:
        """Check if Orthanc server is accessible"""
        try:
            system_info = self.get_system_info()
            if system_info:
                logger.info(f"Connected to Orthanc server version: {system_info.get('Version', 'unknown')}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Orthanc connectivity check failed: {e}")
            return False
    
    def get_dicom_web_url(self, study_id: str) -> str:
        """Get DICOMweb URL for study viewing"""
        return f"{self.base_url}/dicom-web/studies/{study_id}"
    
    def get_ohif_viewer_url(self, study_id: str) -> str:
        """Get OHIF viewer URL for study"""
        return f"{self.base_url}/ohif/viewer/{study_id}"
    
    def create_study_link(self, study_id: str, expiry_hours: int = 24) -> Optional[str]:
        """Create a shareable link for a study"""
        try:
            # This would typically create a temporary access token
            # For now, return a direct link (in production, implement proper token-based sharing)
            return f"{self.base_url}/app/explorer.html#study?uuid={study_id}"
            
        except Exception as e:
            logger.error(f"Error creating study link: {e}")
            return None

# Global Orthanc client instance
orthanc_client = OrthancClient()

def get_study_for_reporting(study_id: str) -> Optional[Dict[str, Any]]:
    """Get study data formatted for reporting module"""
    try:
        study_details = orthanc_client.get_study_details(study_id)
        if not study_details:
            return None
        
        series_list = orthanc_client.get_study_series(study_id)
        statistics = orthanc_client.get_study_statistics(study_id)
        
        # Format for reporting module
        formatted_study = {
            'study_id': study_id,
            'patient_id': study_details.get('PatientMainDicomTags', {}).get('PatientID'),
            'patient_name': study_details.get('PatientMainDicomTags', {}).get('PatientName'),
            'study_date': study_details.get('MainDicomTags', {}).get('StudyDate'),
            'study_time': study_details.get('MainDicomTags', {}).get('StudyTime'),
            'study_description': study_details.get('MainDicomTags', {}).get('StudyDescription'),
            'accession_number': study_details.get('MainDicomTags', {}).get('AccessionNumber'),
            'modality': study_details.get('MainDicomTags', {}).get('ModalitiesInStudy'),
            'series_count': len(series_list),
            'instance_count': statistics.get('CountInstances', 0) if statistics else 0,
            'series': series_list,
            'viewer_url': orthanc_client.get_ohif_viewer_url(study_id),
            'dicom_web_url': orthanc_client.get_dicom_web_url(study_id)
        }
        
        return formatted_study
        
    except Exception as e:
        logger.error(f"Error formatting study for reporting: {e}")
        return None