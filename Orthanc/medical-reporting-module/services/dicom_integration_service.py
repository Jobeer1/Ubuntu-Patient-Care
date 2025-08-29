#!/usr/bin/env python3
"""
DICOM Integration Service for Medical Reporting Module
Handles Orthanc PACS integration, NAS storage, and DICOM processing
"""

import logging
import requests
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import pydicom
from pathlib import Path

logger = logging.getLogger(__name__)

class DicomIntegrationService:
    """Service for DICOM integration with Orthanc PACS and NAS storage"""
    
    def __init__(self):
        """Initialize DICOM Integration Service"""
        self.orthanc_url = "http://localhost:8042"
        self.orthanc_username = "orthanc"
        self.orthanc_password = "orthanc"
        
        # NAS configuration
        self.nas_mount_point = "/mnt/nas/dicom"
        self.local_dicom_path = "dicom_storage"
        
        # Ensure local DICOM storage exists
        os.makedirs(self.local_dicom_path, exist_ok=True)
        
        logger.info("DICOM Integration Service initialized with Orthanc and NAS support")
    
    def test_orthanc_connection(self) -> Dict[str, Any]:
        """Test connection to Orthanc PACS server"""
        try:
            response = requests.get(
                f"{self.orthanc_url}/system",
                auth=(self.orthanc_username, self.orthanc_password),
                timeout=5
            )
            
            if response.status_code == 200:
                system_info = response.json()
                logger.info("Orthanc connection successful")
                return {
                    'status': 'connected',
                    'version': system_info.get('Version', 'Unknown'),
                    'name': system_info.get('Name', 'Orthanc'),
                    'database_version': system_info.get('DatabaseVersion', 'Unknown')
                }
            else:
                logger.warning(f"Orthanc connection failed: HTTP {response.status_code}")
                return {'status': 'disconnected', 'error': f'HTTP {response.status_code}'}
                
        except requests.exceptions.ConnectionError:
            logger.warning("Orthanc server not reachable")
            return {'status': 'disconnected', 'error': 'Connection refused'}
        except Exception as e:
            logger.error(f"Orthanc connection test failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def get_orthanc_statistics(self) -> Dict[str, Any]:
        """Get Orthanc PACS statistics"""
        try:
            response = requests.get(
                f"{self.orthanc_url}/statistics",
                auth=(self.orthanc_username, self.orthanc_password),
                timeout=5
            )
            
            if response.status_code == 200:
                stats = response.json()
                logger.info("Retrieved Orthanc statistics")
                return {
                    'patients': stats.get('CountPatients', 0),
                    'studies': stats.get('CountStudies', 0),
                    'series': stats.get('CountSeries', 0),
                    'instances': stats.get('CountInstances', 0),
                    'disk_size_mb': round(stats.get('TotalDiskSize', 0) / (1024 * 1024), 2)
                }
            else:
                return {'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            logger.error(f"Failed to get Orthanc statistics: {e}")
            return {'error': str(e)}
    
    def search_studies(self, patient_id: str = None, patient_name: str = None, 
                      study_date: str = None, modality: str = None) -> List[Dict]:
        """Search for studies in Orthanc PACS"""
        try:
            # Build query
            query = {}
            if patient_id:
                query['PatientID'] = patient_id
            if patient_name:
                query['PatientName'] = patient_name
            if study_date:
                query['StudyDate'] = study_date
            if modality:
                query['ModalitiesInStudy'] = modality
            
            response = requests.post(
                f"{self.orthanc_url}/tools/find",
                json={
                    'Level': 'Study',
                    'Query': query,
                    'Expand': True
                },
                auth=(self.orthanc_username, self.orthanc_password),
                timeout=10
            )
            
            if response.status_code == 200:
                studies = response.json()
                logger.info(f"Found {len(studies)} studies")
                
                # Format study information
                formatted_studies = []
                for study in studies:
                    main_tags = study.get('MainDicomTags', {})
                    patient_tags = study.get('PatientMainDicomTags', {})
                    
                    formatted_studies.append({
                        'study_id': study.get('ID', ''),
                        'patient_id': patient_tags.get('PatientID', ''),
                        'patient_name': patient_tags.get('PatientName', ''),
                        'study_date': main_tags.get('StudyDate', ''),
                        'study_time': main_tags.get('StudyTime', ''),
                        'study_description': main_tags.get('StudyDescription', ''),
                        'modalities': study.get('Series', []),
                        'series_count': len(study.get('Series', [])),
                        'instances_count': sum(len(series.get('Instances', [])) for series in study.get('Series', []))
                    })
                
                return formatted_studies
            else:
                logger.error(f"Study search failed: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Study search failed: {e}")
            return []
    
    def get_study_details(self, study_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific study"""
        try:
            response = requests.get(
                f"{self.orthanc_url}/studies/{study_id}",
                auth=(self.orthanc_username, self.orthanc_password),
                timeout=5
            )
            
            if response.status_code == 200:
                study = response.json()
                main_tags = study.get('MainDicomTags', {})
                patient_tags = study.get('PatientMainDicomTags', {})
                
                return {
                    'study_id': study_id,
                    'patient_id': patient_tags.get('PatientID', ''),
                    'patient_name': patient_tags.get('PatientName', ''),
                    'patient_birth_date': patient_tags.get('PatientBirthDate', ''),
                    'patient_sex': patient_tags.get('PatientSex', ''),
                    'study_date': main_tags.get('StudyDate', ''),
                    'study_time': main_tags.get('StudyTime', ''),
                    'study_description': main_tags.get('StudyDescription', ''),
                    'accession_number': main_tags.get('AccessionNumber', ''),
                    'referring_physician': main_tags.get('ReferringPhysicianName', ''),
                    'series': study.get('Series', []),
                    'series_count': len(study.get('Series', [])),
                    'instances_count': sum(len(series.get('Instances', [])) for series in study.get('Series', []))
                }
            else:
                logger.error(f"Failed to get study details: HTTP {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get study details: {e}")
            return {}
    
    def get_study_images(self, study_id: str) -> List[Dict]:
        """Get image URLs for a study"""
        try:
            study_details = self.get_study_details(study_id)
            if not study_details:
                return []
            
            images = []
            for series in study_details.get('series', []):
                series_id = series
                
                # Get series details
                series_response = requests.get(
                    f"{self.orthanc_url}/series/{series_id}",
                    auth=(self.orthanc_username, self.orthanc_password),
                    timeout=5
                )
                
                if series_response.status_code == 200:
                    series_data = series_response.json()
                    series_tags = series_data.get('MainDicomTags', {})
                    
                    for instance in series_data.get('Instances', []):
                        images.append({
                            'instance_id': instance,
                            'series_id': series_id,
                            'series_description': series_tags.get('SeriesDescription', ''),
                            'modality': series_tags.get('Modality', ''),
                            'series_number': series_tags.get('SeriesNumber', ''),
                            'image_url': f"{self.orthanc_url}/instances/{instance}/preview",
                            'dicom_url': f"{self.orthanc_url}/instances/{instance}/file"
                        })
            
            logger.info(f"Retrieved {len(images)} images for study {study_id}")
            return images
            
        except Exception as e:
            logger.error(f"Failed to get study images: {e}")
            return []
    
    def upload_dicom_file(self, file_path: str) -> Dict[str, Any]:
        """Upload DICOM file to Orthanc PACS"""
        try:
            if not os.path.exists(file_path):
                return {'success': False, 'error': 'File not found'}
            
            with open(file_path, 'rb') as f:
                response = requests.post(
                    f"{self.orthanc_url}/instances",
                    data=f.read(),
                    headers={'Content-Type': 'application/dicom'},
                    auth=(self.orthanc_username, self.orthanc_password),
                    timeout=30
                )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"DICOM file uploaded successfully: {file_path}")
                return {
                    'success': True,
                    'instance_id': result.get('ID', ''),
                    'status': result.get('Status', ''),
                    'path': result.get('Path', '')
                }
            else:
                logger.error(f"DICOM upload failed: HTTP {response.status_code}")
                return {'success': False, 'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            logger.error(f"DICOM upload failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_nas_connection(self) -> Dict[str, Any]:
        """Check NAS storage connection"""
        try:
            # Check if NAS mount point exists
            if os.path.exists(self.nas_mount_point):
                # Try to list contents
                contents = os.listdir(self.nas_mount_point)
                
                # Get disk usage
                statvfs = os.statvfs(self.nas_mount_point)
                total_space = statvfs.f_frsize * statvfs.f_blocks
                free_space = statvfs.f_frsize * statvfs.f_available
                
                logger.info("NAS connection successful")
                return {
                    'status': 'connected',
                    'mount_point': self.nas_mount_point,
                    'total_space_gb': round(total_space / (1024**3), 2),
                    'free_space_gb': round(free_space / (1024**3), 2),
                    'files_count': len(contents)
                }
            else:
                logger.warning("NAS mount point not found")
                return {
                    'status': 'disconnected',
                    'error': 'Mount point not found',
                    'mount_point': self.nas_mount_point
                }
                
        except Exception as e:
            logger.error(f"NAS connection check failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def sync_to_nas(self, study_id: str) -> Dict[str, Any]:
        """Sync study to NAS storage"""
        try:
            # Create NAS directory for study
            study_dir = os.path.join(self.nas_mount_point, study_id)
            os.makedirs(study_dir, exist_ok=True)
            
            # Get study details
            study_details = self.get_study_details(study_id)
            if not study_details:
                return {'success': False, 'error': 'Study not found'}
            
            # Download and save DICOM files
            files_synced = 0
            for series in study_details.get('series', []):
                series_response = requests.get(
                    f"{self.orthanc_url}/series/{series}",
                    auth=(self.orthanc_username, self.orthanc_password),
                    timeout=5
                )
                
                if series_response.status_code == 200:
                    series_data = series_response.json()
                    
                    for instance in series_data.get('Instances', []):
                        # Download DICOM file
                        dicom_response = requests.get(
                            f"{self.orthanc_url}/instances/{instance}/file",
                            auth=(self.orthanc_username, self.orthanc_password),
                            timeout=30
                        )
                        
                        if dicom_response.status_code == 200:
                            # Save to NAS
                            file_path = os.path.join(study_dir, f"{instance}.dcm")
                            with open(file_path, 'wb') as f:
                                f.write(dicom_response.content)
                            files_synced += 1
            
            logger.info(f"Synced {files_synced} files to NAS for study {study_id}")
            return {
                'success': True,
                'files_synced': files_synced,
                'nas_path': study_dir
            }
            
        except Exception as e:
            logger.error(f"NAS sync failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_dicom_report(self, study_id: str, report_text: str, 
                           physician_name: str) -> Dict[str, Any]:
        """Create DICOM Structured Report for study"""
        try:
            # Get study details
            study_details = self.get_study_details(study_id)
            if not study_details:
                return {'success': False, 'error': 'Study not found'}
            
            # Create DICOM SR dataset
            from pydicom.dataset import Dataset
            from pydicom.uid import generate_uid
            
            # Create basic DICOM dataset
            ds = Dataset()
            
            # Patient information
            ds.PatientID = study_details.get('patient_id', '')
            ds.PatientName = study_details.get('patient_name', '')
            ds.PatientBirthDate = study_details.get('patient_birth_date', '')
            ds.PatientSex = study_details.get('patient_sex', '')
            
            # Study information
            ds.StudyInstanceUID = generate_uid()
            ds.StudyDate = datetime.now().strftime('%Y%m%d')
            ds.StudyTime = datetime.now().strftime('%H%M%S')
            ds.StudyDescription = "Medical Report"
            ds.AccessionNumber = study_details.get('accession_number', '')
            
            # Series information
            ds.SeriesInstanceUID = generate_uid()
            ds.SeriesNumber = "1"
            ds.SeriesDescription = "Structured Report"
            ds.Modality = "SR"
            
            # Instance information
            ds.SOPInstanceUID = generate_uid()
            ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.88.11"  # Basic Text SR
            ds.InstanceNumber = "1"
            
            # Report content
            ds.ContentDate = datetime.now().strftime('%Y%m%d')
            ds.ContentTime = datetime.now().strftime('%H%M%S')
            ds.ReportingPhysicianName = physician_name
            
            # Save DICOM file
            report_filename = f"report_{study_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dcm"
            report_path = os.path.join(self.local_dicom_path, report_filename)
            
            ds.save_as(report_path)
            
            # Upload to Orthanc
            upload_result = self.upload_dicom_file(report_path)
            
            logger.info(f"Created DICOM report for study {study_id}")
            return {
                'success': True,
                'report_path': report_path,
                'upload_result': upload_result
            }
            
        except Exception as e:
            logger.error(f"DICOM report creation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get overall integration status"""
        orthanc_status = self.test_orthanc_connection()
        nas_status = self.check_nas_connection()
        orthanc_stats = self.get_orthanc_statistics() if orthanc_status['status'] == 'connected' else {}
        
        return {
            'timestamp': datetime.now().isoformat(),
            'orthanc': orthanc_status,
            'nas': nas_status,
            'statistics': orthanc_stats,
            'local_storage': {
                'path': self.local_dicom_path,
                'exists': os.path.exists(self.local_dicom_path)
            }
        }