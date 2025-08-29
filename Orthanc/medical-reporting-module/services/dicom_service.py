#!/usr/bin/env python3
"""
DICOM Service for Medical Reporting Module
DICOM 3.0 compliant image handling and metadata processing
"""

import logging
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import generate_uid
import requests
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

class DICOMService:
    """DICOM 3.0 compliant service for medical image handling"""
    
    def __init__(self, orthanc_url: str = "http://localhost:8042"):
        self.orthanc_url = orthanc_url.rstrip('/')
        self.temp_dir = Path(tempfile.gettempdir()) / "dicom_temp"
        self.temp_dir.mkdir(exist_ok=True)
        
        # DICOM configuration
        self.ae_title = "SA_MEDICAL_REPORTING"
        self.institution_name = "SA Medical Reporting Module"
        self.manufacturer = "SA Medical Systems"
        
        logger.info(f"DICOM Service initialized with Orthanc URL: {self.orthanc_url}")
    
    def validate_dicom_file(self, file_path: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate DICOM file and extract metadata"""
        try:
            # Read DICOM file
            ds = pydicom.dcmread(file_path, force=True)
            
            # Basic validation
            validation_result = {
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'metadata': {}
            }
            
            # Check required DICOM tags
            required_tags = [
                ('PatientID', 'Patient ID'),
                ('StudyInstanceUID', 'Study Instance UID'),
                ('SeriesInstanceUID', 'Series Instance UID'),
                ('SOPInstanceUID', 'SOP Instance UID'),
                ('Modality', 'Modality')
            ]
            
            for tag, description in required_tags:
                if not hasattr(ds, tag) or not getattr(ds, tag):
                    validation_result['errors'].append(f"Missing required tag: {description}")
                    validation_result['is_valid'] = False
                else:
                    validation_result['metadata'][tag] = str(getattr(ds, tag))
            
            # Extract additional metadata
            optional_tags = [
                'PatientName', 'PatientBirthDate', 'PatientSex',
                'StudyDate', 'StudyTime', 'StudyDescription',
                'SeriesDate', 'SeriesTime', 'SeriesDescription',
                'InstitutionName', 'Manufacturer', 'ManufacturerModelName'
            ]
            
            for tag in optional_tags:
                if hasattr(ds, tag):
                    value = getattr(ds, tag)
                    if value:
                        validation_result['metadata'][tag] = str(value)
            
            # Check image data
            if hasattr(ds, 'pixel_array'):
                try:
                    pixel_data = ds.pixel_array
                    validation_result['metadata']['ImageDimensions'] = f"{pixel_data.shape}"
                    validation_result['metadata']['HasPixelData'] = True
                except Exception as e:
                    validation_result['warnings'].append(f"Could not read pixel data: {e}")
                    validation_result['metadata']['HasPixelData'] = False
            else:
                validation_result['metadata']['HasPixelData'] = False
            
            # Validate UIDs format
            uid_tags = ['StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID']
            for tag in uid_tags:
                if tag in validation_result['metadata']:
                    uid = validation_result['metadata'][tag]
                    if not self._is_valid_uid(uid):
                        validation_result['errors'].append(f"Invalid UID format for {tag}: {uid}")
                        validation_result['is_valid'] = False
            
            return validation_result['is_valid'], validation_result
            
        except Exception as e:
            logger.error(f"DICOM validation error: {e}")
            return False, {
                'is_valid': False,
                'errors': [f"Failed to read DICOM file: {e}"],
                'warnings': [],
                'metadata': {}
            }
    
    def _is_valid_uid(self, uid: str) -> bool:
        """Validate DICOM UID format"""
        if not uid:
            return False
        
        # UID should contain only digits and dots
        if not all(c.isdigit() or c == '.' for c in uid):
            return False
        
        # Should not start or end with dot
        if uid.startswith('.') or uid.endswith('.'):
            return False
        
        # Should not have consecutive dots
        if '..' in uid:
            return False
        
        # Length should be reasonable (max 64 characters)
        if len(uid) > 64:
            return False
        
        return True
    
    def create_dicom_sr(self, report_data: Dict[str, Any]) -> Optional[str]:
        """Create DICOM Structured Report (SR) for medical reports"""
        try:
            # Create new DICOM dataset
            ds = Dataset()
            
            # Set required DICOM tags
            ds.PatientID = report_data.get('patient_id', 'UNKNOWN')
            ds.PatientName = report_data.get('patient_name', 'UNKNOWN^PATIENT')
            ds.PatientBirthDate = report_data.get('patient_birth_date', '')
            ds.PatientSex = report_data.get('patient_sex', 'O')
            
            # Study information
            ds.StudyInstanceUID = report_data.get('study_uid', generate_uid())
            ds.StudyDate = datetime.now().strftime('%Y%m%d')
            ds.StudyTime = datetime.now().strftime('%H%M%S')
            ds.StudyDescription = report_data.get('study_description', 'Medical Report')
            
            # Series information
            ds.SeriesInstanceUID = generate_uid()
            ds.SeriesDate = ds.StudyDate
            ds.SeriesTime = ds.StudyTime
            ds.SeriesDescription = 'Structured Report'
            ds.SeriesNumber = '1'
            
            # SOP information
            ds.SOPInstanceUID = generate_uid()
            ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.88.11'  # Basic Text SR
            
            # Modality and other required fields
            ds.Modality = 'SR'
            ds.InstitutionName = self.institution_name
            ds.Manufacturer = self.manufacturer
            ds.ManufacturerModelName = 'SA Medical Reporting v1.0'
            
            # Content information
            ds.ContentDate = ds.StudyDate
            ds.ContentTime = ds.StudyTime
            ds.InstanceNumber = '1'
            
            # Structured Report specific tags
            ds.ValueType = 'CONTAINER'
            ds.ConceptNameCodeSequence = []
            ds.ContentSequence = []
            
            # Add report content
            report_content = report_data.get('content', '')
            if report_content:
                content_item = Dataset()
                content_item.ValueType = 'TEXT'
                content_item.TextValue = report_content[:1024]  # Limit text length
                ds.ContentSequence.append(content_item)
            
            # Save to temporary file
            temp_file = self.temp_dir / f"sr_{ds.SOPInstanceUID}.dcm"
            
            # Create file dataset
            file_meta = Dataset()
            file_meta.MediaStorageSOPClassUID = ds.SOPClassUID
            file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
            file_meta.ImplementationClassUID = generate_uid()
            file_meta.ImplementationVersionName = 'SA_MEDICAL_1.0'
            
            file_ds = FileDataset(str(temp_file), ds, file_meta=file_meta, preamble=b"\0" * 128)
            file_ds.save_as(str(temp_file))
            
            logger.info(f"Created DICOM SR: {temp_file}")
            return str(temp_file)
            
        except Exception as e:
            logger.error(f"Failed to create DICOM SR: {e}")
            return None
    
    def send_to_orthanc(self, dicom_file_path: str) -> Tuple[bool, Dict[str, Any]]:
        """Send DICOM file to Orthanc PACS"""
        try:
            # Read DICOM file
            with open(dicom_file_path, 'rb') as f:
                dicom_data = f.read()
            
            # Send to Orthanc
            response = requests.post(
                f"{self.orthanc_url}/instances",
                data=dicom_data,
                headers={'Content-Type': 'application/dicom'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully sent DICOM to Orthanc: {result.get('ID')}")
                return True, {
                    'success': True,
                    'orthanc_id': result.get('ID'),
                    'status': result.get('Status'),
                    'path': result.get('Path')
                }
            else:
                logger.error(f"Failed to send DICOM to Orthanc: {response.status_code} - {response.text}")
                return False, {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error sending DICOM to Orthanc: {e}")
            return False, {
                'success': False,
                'error': str(e)
            }
    
    def query_orthanc_studies(self, query_params: Dict[str, str]) -> List[Dict[str, Any]]:
        """Query Orthanc for studies using DICOM C-FIND"""
        try:
            # Build query
            query = {}
            
            # Map common query parameters
            param_mapping = {
                'patient_id': 'PatientID',
                'patient_name': 'PatientName',
                'study_date': 'StudyDate',
                'study_description': 'StudyDescription',
                'modality': 'ModalitiesInStudy'
            }
            
            for param, dicom_tag in param_mapping.items():
                if param in query_params and query_params[param]:
                    query[dicom_tag] = query_params[param]
            
            # Query Orthanc
            response = requests.post(
                f"{self.orthanc_url}/tools/find",
                json={
                    'Level': 'Study',
                    'Query': query,
                    'Expand': True
                },
                timeout=30
            )
            
            if response.status_code == 200:
                studies = response.json()
                
                # Process results
                processed_studies = []
                for study in studies:
                    main_tags = study.get('MainDicomTags', {})
                    patient_tags = study.get('PatientMainDicomTags', {})
                    
                    processed_study = {
                        'orthanc_id': study.get('ID'),
                        'patient_id': patient_tags.get('PatientID', ''),
                        'patient_name': patient_tags.get('PatientName', ''),
                        'patient_birth_date': patient_tags.get('PatientBirthDate', ''),
                        'patient_sex': patient_tags.get('PatientSex', ''),
                        'study_instance_uid': main_tags.get('StudyInstanceUID', ''),
                        'study_date': main_tags.get('StudyDate', ''),
                        'study_time': main_tags.get('StudyTime', ''),
                        'study_description': main_tags.get('StudyDescription', ''),
                        'accession_number': main_tags.get('AccessionNumber', ''),
                        'series_count': len(study.get('Series', [])),
                        'instances_count': study.get('CountInstances', 0)
                    }
                    processed_studies.append(processed_study)
                
                logger.info(f"Found {len(processed_studies)} studies")
                return processed_studies
            else:
                logger.error(f"Orthanc query failed: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error querying Orthanc: {e}")
            return []
    
    def get_study_details(self, orthanc_study_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a study from Orthanc"""
        try:
            response = requests.get(
                f"{self.orthanc_url}/studies/{orthanc_study_id}",
                timeout=30
            )
            
            if response.status_code == 200:
                study_data = response.json()
                
                # Get series information
                series_list = []
                for series_id in study_data.get('Series', []):
                    series_response = requests.get(
                        f"{self.orthanc_url}/series/{series_id}",
                        timeout=30
                    )
                    
                    if series_response.status_code == 200:
                        series_data = series_response.json()
                        series_tags = series_data.get('MainDicomTags', {})
                        
                        series_info = {
                            'orthanc_id': series_id,
                            'series_instance_uid': series_tags.get('SeriesInstanceUID', ''),
                            'series_description': series_tags.get('SeriesDescription', ''),
                            'modality': series_tags.get('Modality', ''),
                            'series_number': series_tags.get('SeriesNumber', ''),
                            'instances_count': len(series_data.get('Instances', []))
                        }
                        series_list.append(series_info)
                
                # Compile study details
                main_tags = study_data.get('MainDicomTags', {})
                patient_tags = study_data.get('PatientMainDicomTags', {})
                
                study_details = {
                    'orthanc_id': orthanc_study_id,
                    'study_instance_uid': main_tags.get('StudyInstanceUID', ''),
                    'study_date': main_tags.get('StudyDate', ''),
                    'study_time': main_tags.get('StudyTime', ''),
                    'study_description': main_tags.get('StudyDescription', ''),
                    'accession_number': main_tags.get('AccessionNumber', ''),
                    'patient_id': patient_tags.get('PatientID', ''),
                    'patient_name': patient_tags.get('PatientName', ''),
                    'patient_birth_date': patient_tags.get('PatientBirthDate', ''),
                    'patient_sex': patient_tags.get('PatientSex', ''),
                    'series': series_list,
                    'total_instances': study_data.get('CountInstances', 0)
                }
                
                return study_details
            else:
                logger.error(f"Failed to get study details: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting study details: {e}")
            return None
    
    def get_instance_preview(self, orthanc_instance_id: str) -> Optional[bytes]:
        """Get preview image for DICOM instance"""
        try:
            response = requests.get(
                f"{self.orthanc_url}/instances/{orthanc_instance_id}/preview",
                timeout=30
            )
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Failed to get instance preview: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting instance preview: {e}")
            return None
    
    def check_orthanc_connection(self) -> Tuple[bool, Dict[str, Any]]:
        """Check connection to Orthanc PACS"""
        try:
            response = requests.get(f"{self.orthanc_url}/system", timeout=10)
            
            if response.status_code == 200:
                system_info = response.json()
                return True, {
                    'connected': True,
                    'version': system_info.get('Version', 'Unknown'),
                    'name': system_info.get('Name', 'Orthanc'),
                    'api_version': system_info.get('ApiVersion', 'Unknown')
                }
            else:
                return False, {
                    'connected': False,
                    'error': f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Orthanc connection check failed: {e}")
            return False, {
                'connected': False,
                'error': str(e)
            }
    
    def cleanup_temp_files(self):
        """Clean up temporary DICOM files"""
        try:
            for file_path in self.temp_dir.glob("*.dcm"):
                if file_path.stat().st_mtime < (datetime.now().timestamp() - 3600):  # 1 hour old
                    file_path.unlink()
                    logger.debug(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")

# Global DICOM service instance
dicom_service = DICOMService()