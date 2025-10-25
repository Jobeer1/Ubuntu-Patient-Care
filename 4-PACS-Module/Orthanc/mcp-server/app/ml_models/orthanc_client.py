"""Orthanc REST API Client for DICOM loading and management"""
import httpx
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
from functools import lru_cache

logger = logging.getLogger(__name__)


class OrthancClient:
    """Client for Orthanc DICOM server REST API"""
    
    def __init__(self, orthanc_url: str = "http://localhost:8042", username: str = "orthanc", password: str = "orthanc"):
        """
        Initialize Orthanc client
        
        Args:
            orthanc_url: Base URL for Orthanc server (default: http://localhost:8042)
            username: Orthanc authentication username (default: orthanc)
            password: Orthanc authentication password (default: orthanc)
        """
        self.orthanc_url = orthanc_url.rstrip("/")
        self.auth = (username, password) if username and password else None
        self.timeout = 30.0
        self._session: Optional[httpx.AsyncClient] = None
        self._local_cache: Dict[str, Any] = {}
        
        logger.info(f"Initialized Orthanc client pointing to {self.orthanc_url}")
    
    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create async HTTP session"""
        if self._session is None:
            self._session = httpx.AsyncClient(auth=self.auth, timeout=self.timeout)
        return self._session
    
    async def close(self):
        """Close HTTP session"""
        if self._session:
            await self._session.aclose()
            self._session = None
    
    async def health_check(self) -> bool:
        """
        Check if Orthanc server is running and accessible
        
        Returns:
            bool: True if server is reachable, False otherwise
        """
        try:
            session = await self._get_session()
            response = await session.get(f"{self.orthanc_url}/system")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Orthanc health check failed: {e}")
            return False
    
    async def get_all_patients(self) -> List[Dict[str, Any]]:
        """
        Get list of all patients in Orthanc
        
        Returns:
            List of patient dictionaries with ID and main dicom tags
        """
        try:
            session = await self._get_session()
            response = await session.get(f"{self.orthanc_url}/patients")
            
            if response.status_code != 200:
                logger.error(f"Failed to get patients: HTTP {response.status_code}")
                return []
            
            patient_ids = response.json()
            patients = []
            
            for patient_id in patient_ids:
                patient_data = await self.get_patient(patient_id)
                if patient_data:
                    patients.append(patient_data)
            
            return patients
        except Exception as e:
            logger.error(f"Error fetching patients from Orthanc: {e}")
            return []
    
    async def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """
        Get patient details including studies
        
        Args:
            patient_id: Orthanc patient ID
            
        Returns:
            Patient dictionary with studies, or None if not found
        """
        try:
            session = await self._get_session()
            response = await session.get(f"{self.orthanc_url}/patients/{patient_id}")
            
            if response.status_code != 200:
                logger.warning(f"Patient {patient_id} not found")
                return None
            
            patient_data = response.json()
            
            # Enrich with human-readable info
            main_dicom = patient_data.get("MainDicomTags", {})
            patient_data["patient_name"] = main_dicom.get("PatientName", "Unknown")
            patient_data["patient_birth_date"] = main_dicom.get("PatientBirthDate", "Unknown")
            patient_data["patient_sex"] = main_dicom.get("PatientSex", "Unknown")
            
            return patient_data
        except Exception as e:
            logger.error(f"Error fetching patient {patient_id}: {e}")
            return None
    
    async def get_all_studies(self) -> List[Dict[str, Any]]:
        """
        Get list of all studies in Orthanc
        
        Returns:
            List of study dictionaries
        """
        try:
            session = await self._get_session()
            response = await session.get(f"{self.orthanc_url}/studies")
            
            if response.status_code != 200:
                logger.error(f"Failed to get studies: HTTP {response.status_code}")
                return []
            
            study_ids = response.json()
            studies = []
            
            for study_id in study_ids:
                study_data = await self.get_study(study_id)
                if study_data:
                    studies.append(study_data)
            
            return studies
        except Exception as e:
            logger.error(f"Error fetching studies from Orthanc: {e}")
            return []
    
    async def get_study(self, study_id: str) -> Optional[Dict[str, Any]]:
        """
        Get study details including series and metadata
        
        Args:
            study_id: Orthanc study ID
            
        Returns:
            Study dictionary with series, or None if not found
        """
        try:
            session = await self._get_session()
            response = await session.get(f"{self.orthanc_url}/studies/{study_id}")
            
            if response.status_code != 200:
                logger.warning(f"Study {study_id} not found")
                return None
            
            study_data = response.json()
            
            # Enrich with human-readable info
            main_dicom = study_data.get("MainDicomTags", {})
            study_data["study_date"] = main_dicom.get("StudyDate", "Unknown")
            study_data["study_time"] = main_dicom.get("StudyTime", "Unknown")
            study_data["study_description"] = main_dicom.get("StudyDescription", "Unnamed Study")
            study_data["modality"] = main_dicom.get("Modality", "UNKNOWN")
            
            return study_data
        except Exception as e:
            logger.error(f"Error fetching study {study_id}: {e}")
            return None
    
    async def get_series(self, series_id: str) -> Optional[Dict[str, Any]]:
        """
        Get series details including instances (DICOM files)
        
        Args:
            series_id: Orthanc series ID
            
        Returns:
            Series dictionary with instances, or None if not found
        """
        try:
            session = await self._get_session()
            response = await session.get(f"{self.orthanc_url}/series/{series_id}")
            
            if response.status_code != 200:
                logger.warning(f"Series {series_id} not found")
                return None
            
            series_data = response.json()
            
            # Enrich with human-readable info
            main_dicom = series_data.get("MainDicomTags", {})
            series_data["series_description"] = main_dicom.get("SeriesDescription", "Unnamed Series")
            series_data["modality"] = main_dicom.get("Modality", "UNKNOWN")
            series_data["series_number"] = main_dicom.get("SeriesNumber", "0")
            
            return series_data
        except Exception as e:
            logger.error(f"Error fetching series {series_id}: {e}")
            return None
    
    async def get_series_dicom_files(self, series_id: str) -> List[bytes]:
        """
        Get all DICOM files in a series
        
        Args:
            series_id: Orthanc series ID
            
        Returns:
            List of DICOM file bytes
        """
        try:
            series_info = await self.get_series(series_id)
            if not series_info:
                return []
            
            instances = series_info.get("Instances", [])
            dicom_files = []
            
            session = await self._get_session()
            
            for instance_id in instances:
                try:
                    response = await session.get(f"{self.orthanc_url}/instances/{instance_id}/file")
                    if response.status_code == 200:
                        dicom_files.append(response.content)
                except Exception as e:
                    logger.warning(f"Failed to download instance {instance_id}: {e}")
                    continue
            
            logger.info(f"Downloaded {len(dicom_files)} DICOM files from series {series_id}")
            return dicom_files
        except Exception as e:
            logger.error(f"Error downloading series {series_id}: {e}")
            return []
    
    async def get_instance_metadata(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """
        Get DICOM metadata for a single instance
        
        Args:
            instance_id: Orthanc instance ID
            
        Returns:
            Dictionary with DICOM tags and metadata, or None if not found
        """
        try:
            session = await self._get_session()
            
            # Get tags
            response = await session.get(f"{self.orthanc_url}/instances/{instance_id}/tags?simplify")
            
            if response.status_code != 200:
                logger.warning(f"Instance {instance_id} not found")
                return None
            
            metadata = response.json()
            
            # Get instance info
            response = await session.get(f"{self.orthanc_url}/instances/{instance_id}")
            if response.status_code == 200:
                instance_info = response.json()
                metadata["file_size"] = instance_info.get("FileSize")
                metadata["slice_location"] = instance_info.get("IndexInSeries", 0)
            
            return metadata
        except Exception as e:
            logger.error(f"Error fetching instance metadata {instance_id}: {e}")
            return None
    
    async def search_studies(self, query: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Search for studies with query parameters
        
        Args:
            query: Dictionary with search parameters
                   Possible keys: PatientName, PatientID, StudyDescription, StudyDate, etc.
                   
        Returns:
            List of matching studies
        """
        try:
            session = await self._get_session()
            
            # Build query string
            params = {
                "case-sensitive": "false",
                "expand": "true"  # Get full study info
            }
            
            # Add DICOM tags to query
            for key, value in query.items():
                params[key] = value
            
            response = await session.post(
                f"{self.orthanc_url}/tools/find",
                json=params
            )
            
            if response.status_code != 200:
                logger.warning(f"Search failed with status {response.status_code}")
                return []
            
            results = response.json()
            return results if isinstance(results, list) else []
        except Exception as e:
            logger.error(f"Error searching studies: {e}")
            return []
    
    async def get_server_info(self) -> Optional[Dict[str, Any]]:
        """
        Get Orthanc server information and statistics
        
        Returns:
            Dictionary with server info, or None if unreachable
        """
        try:
            session = await self._get_session()
            response = await session.get(f"{self.orthanc_url}/system")
            
            if response.status_code != 200:
                return None
            
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching server info: {e}")
            return None


# Singleton instance
_orthanc_client: Optional[OrthancClient] = None


def get_orthanc_client(
    orthanc_url: str = "http://localhost:8042",
    username: str = "orthanc",
    password: str = "orthanc"
) -> OrthancClient:
    """
    Get or create Orthanc client singleton
    
    Args:
        orthanc_url: Base URL for Orthanc server
        username: Orthanc authentication username
        password: Orthanc authentication password
        
    Returns:
        Singleton OrthancClient instance
    """
    global _orthanc_client
    
    if _orthanc_client is None:
        _orthanc_client = OrthancClient(orthanc_url, username, password)
    
    return _orthanc_client
