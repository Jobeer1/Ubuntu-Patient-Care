"""
Medical Sharing Service
Handles secure medical image sharing with doctors and patients
"""

import logging
import uuid
import hashlib
from datetime import datetime, timedelta
from .database_operations import create_medical_share, get_medical_share, update_share_access
from .patient_search import find_patient_by_id_or_name
from .dicom_integration import upload_patient_to_orthanc

logger = logging.getLogger(__name__)

def generate_secure_share_link(share_request):
    """Generate a secure sharing link for patient images"""
    try:
        patient_id = share_request.get('patient_id', '')
        patient_name = share_request.get('patient_name', '')
        doctor_name = share_request.get('doctor_name', 'Unknown Doctor')
        doctor_email = share_request.get('doctor_email', '')
        recipient_type = share_request.get('recipient_type', 'doctor')
        expiry_hours = int(share_request.get('expiry_hours', 72))
        message = share_request.get('message', '')
        allow_download = share_request.get('allow_download', True)
        
        if not patient_id and not patient_name:
            raise ValueError('Patient ID or name is required')
        
        identifier = patient_id or patient_name
        logger.info(f"🔗 Generating share link for patient: {identifier} by {doctor_name}")
        
        # Find the patient data
        patient_data = find_patient_by_id_or_name(identifier)
        
        if not patient_data:
            raise ValueError(f'Patient {identifier} not found in system')
        
        # Generate secure link and access code
        share_id = str(uuid.uuid4())[:12]
        access_code = hashlib.sha256(f"{identifier}{share_id}{datetime.now().isoformat()}".encode()).hexdigest()[:8].upper()
        
        expiry_date = datetime.now() + timedelta(hours=expiry_hours)
        
        # Create shareable link
        share_link = f"http://localhost:5000/medical-share/{share_id}"
        
        # Upload patient files to Orthanc and get Study UID
        orthanc_study_uid = None
        try:
            orthanc_study_uid = upload_patient_to_orthanc(patient_data)
            logger.info(f"✅ Patient uploaded to Orthanc with Study UID: {orthanc_study_uid}")
        except Exception as e:
            logger.error(f"Failed to upload to Orthanc: {e}")
        
        # Store in database for security
        share_data = {
            'share_id': share_id,
            'patient_id': patient_data.get('patient_id', identifier),
            'patient_name': patient_data.get('name', 'Unknown'),
            'access_code': access_code,
            'doctor_name': doctor_name,
            'doctor_email': doctor_email,
            'recipient_type': recipient_type,
            'created_date': datetime.now().isoformat(),
            'expiry_date': expiry_date.isoformat(),
            'message': message,
            'allow_download': allow_download,
            'max_downloads': 10 if recipient_type == 'doctor' else 3,
            'orthanc_study_uid': orthanc_study_uid
        }
        
        create_medical_share(share_data)
        
        # Generate response
        instructions = generate_sharing_instructions(recipient_type, access_code, expiry_hours, expiry_date)
        
        return {
            'success': True,
            'share_link': share_link,
            'access_code': access_code,
            'expiry_date': expiry_date.strftime('%Y-%m-%d %H:%M:%S'),
            'share_data': {
                'share_id': share_id,
                'share_link': share_link,
                'access_code': access_code,
                'patient_id': patient_data.get('patient_id', identifier),
                'patient_name': patient_data.get('name', 'Unknown'),
                'patient_birth_date': patient_data.get('birth_date', ''),
                'patient_sex': patient_data.get('sex', ''),
                'doctor_name': doctor_name,
                'recipient_type': recipient_type,
                'expiry_date': expiry_date.isoformat(),
                'expiry_hours': expiry_hours,
                'message': message,
                'created_date': datetime.now().isoformat(),
                'download_count': 0,
                'allow_download': allow_download,
                'studies_count': patient_data.get('total_studies', 0)
            },
            'instructions': instructions,
            'patient_info': {
                'name': patient_data.get('name', 'Unknown'),
                'id': patient_data.get('patient_id', identifier),
                'birth_date': patient_data.get('birth_date', ''),
                'studies_available': patient_data.get('total_studies', 0)
            },
            'orthanc_study_uid': orthanc_study_uid,
            'ohif_viewer_url': f"http://localhost:8042/ohif/viewer/{orthanc_study_uid}" if orthanc_study_uid else None,
            'dicom_viewer_url': f"http://localhost:5000/api/nas/dicom-viewer?studyUID={orthanc_study_uid}&shareId={share_id}" if orthanc_study_uid else None,
            'message': f'✅ Secure sharing link generated for {recipient_type}: {patient_data.get("name", identifier)}'
        }
        
    except Exception as e:
        logger.error(f"Share link generation error: {e}")
        raise

def generate_sharing_instructions(recipient_type, access_code, expiry_hours, expiry_date):
    """Generate appropriate instructions based on recipient type"""
    if recipient_type == 'doctor':
        return {
            'step1': f'Share this secure link with the receiving doctor',
            'step2': f'Doctor access code: {access_code}',
            'step3': 'Doctor can view and download medical images',
            'step4': f'Link expires in {expiry_hours} hours ({expiry_date.strftime("%Y-%m-%d %H:%M")})',
            'security': 'HIPAA-compliant secure sharing with audit trail'
        }
    else:
        return {
            'step1': f'Share this secure link with the patient',
            'step2': f'Patient access code: {access_code}',
            'step3': 'Patient can view their medical images',
            'step4': f'Link expires in {expiry_hours} hours',
            'note': 'Limited downloads for patient safety'
        }

def verify_share_access(share_id, access_code):
    """Verify share access and return share information"""
    try:
        logger.info(f"🔐 Verifying access for medical share: {share_id}")
        
        share_record = get_medical_share(share_id)
        
        if not share_record:
            return {
                'success': False,
                'message': '❌ Invalid share ID or expired link'
            }
        
        if share_record['access_code'] != access_code.upper():
            return {
                'success': False,
                'message': '❌ Invalid access code'
            }
        
        # Check expiry
        expiry_date = datetime.fromisoformat(share_record['expiry_date'])
        if datetime.now() > expiry_date:
            return {
                'success': False,
                'message': '❌ This sharing link has expired'
            }
        
        # Check download limits
        if share_record['download_count'] >= share_record['max_downloads']:
            return {
                'success': False,
                'message': '❌ Download limit exceeded for this link'
            }
        
        # Update access log
        update_share_access(share_id)
        
        return {
            'success': True,
            'share_data': share_record,
            'message': '✅ Access granted'
        }
        
    except Exception as e:
        logger.error(f"Share verification error: {e}")
        return {
            'success': False,
            'message': f'Verification error: {str(e)}'
        }