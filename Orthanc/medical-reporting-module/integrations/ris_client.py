"""
RIS (Radiology Information System) integration client
"""

import requests
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from config.integration_config import IntegrationConfig

logger = logging.getLogger(__name__)

class RISClient:
    """Client for RIS system integration"""
    
    def __init__(self):
        self.config = IntegrationConfig.RIS_CONFIG
        self.base_url = self.config['url']
        self.username = self.config['username']
        self.password = self.config['password']
        self.enabled = self.config['enabled']
        self.timeout = self.config['timeout']
        self.hl7_enabled = self.config['hl7_enabled']
        
        if not self.enabled:
            logger.info("RIS integration is disabled")
    
    def check_connectivity(self) -> bool:
        """Check if RIS system is accessible"""
        if not self.enabled:
            return False
        
        try:
            # Try to connect to RIS system
            response = requests.get(
                f"{self.base_url}/api/health",
                auth=(self.username, self.password) if self.username else None,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.info("RIS connectivity check successful")
                return True
            else:
                logger.warning(f"RIS connectivity check failed: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"RIS connectivity check failed: {e}")
            return False
    
    def get_patient_info(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient information from RIS"""
        if not self.enabled:
            return None
        
        try:
            response = requests.get(
                f"{self.base_url}/api/patients/{patient_id}",
                auth=(self.username, self.password) if self.username else None,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"Patient {patient_id} not found in RIS")
                return None
            else:
                logger.error(f"Failed to get patient info: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get patient info from RIS: {e}")
            return None
    
    def get_study_order(self, accession_number: str) -> Optional[Dict[str, Any]]:
        """Get study order information from RIS"""
        if not self.enabled:
            return None
        
        try:
            response = requests.get(
                f"{self.base_url}/api/orders/accession/{accession_number}",
                auth=(self.username, self.password) if self.username else None,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"Study order {accession_number} not found in RIS")
                return None
            else:
                logger.error(f"Failed to get study order: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get study order from RIS: {e}")
            return None
    
    def update_study_status(self, accession_number: str, status: str, notes: str = None) -> bool:
        """Update study status in RIS"""
        if not self.enabled:
            return True  # Return success if RIS is disabled
        
        try:
            data = {
                'status': status,
                'updated_at': datetime.utcnow().isoformat(),
                'notes': notes
            }
            
            response = requests.put(
                f"{self.base_url}/api/orders/accession/{accession_number}/status",
                json=data,
                auth=(self.username, self.password) if self.username else None,
                timeout=self.timeout
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"Study status updated in RIS: {accession_number} -> {status}")
                return True
            else:
                logger.error(f"Failed to update study status: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update study status in RIS: {e}")
            return False
    
    def submit_report(self, accession_number: str, report_data: Dict[str, Any]) -> bool:
        """Submit report to RIS"""
        if not self.enabled:
            return True
        
        try:
            # Format report for RIS
            ris_report = {
                'accession_number': accession_number,
                'report_text': report_data.get('content', {}).get('findings', ''),
                'impression': report_data.get('content', {}).get('impression', ''),
                'recommendations': report_data.get('content', {}).get('recommendations', ''),
                'radiologist_id': report_data.get('doctor_id'),
                'report_date': datetime.utcnow().isoformat(),
                'status': 'final' if report_data.get('status') == 'final' else 'preliminary'
            }
            
            response = requests.post(
                f"{self.base_url}/api/reports",
                json=ris_report,
                auth=(self.username, self.password) if self.username else None,
                timeout=self.timeout
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Report submitted to RIS: {accession_number}")
                return True
            else:
                logger.error(f"Failed to submit report to RIS: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to submit report to RIS: {e}")
            return False
    
    def get_referring_physician(self, physician_id: str) -> Optional[Dict[str, Any]]:
        """Get referring physician information"""
        if not self.enabled:
            return None
        
        try:
            response = requests.get(
                f"{self.base_url}/api/physicians/{physician_id}",
                auth=(self.username, self.password) if self.username else None,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Referring physician {physician_id} not found")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get referring physician info: {e}")
            return None
    
    def get_worklist(self, modality: str = None, date_range: tuple = None) -> List[Dict[str, Any]]:
        """Get worklist from RIS"""
        if not self.enabled:
            return []
        
        try:
            params = {}
            if modality:
                params['modality'] = modality
            if date_range:
                params['start_date'] = date_range[0]
                params['end_date'] = date_range[1]
            
            response = requests.get(
                f"{self.base_url}/api/worklist",
                params=params,
                auth=(self.username, self.password) if self.username else None,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get worklist: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get worklist from RIS: {e}")
            return []
    
    def send_hl7_message(self, message_type: str, data: Dict[str, Any]) -> bool:
        """Send HL7 message to RIS"""
        if not self.enabled or not self.hl7_enabled:
            return True
        
        try:
            # This is a simplified HL7 implementation
            # In production, you would use a proper HL7 library
            hl7_message = self._create_hl7_message(message_type, data)
            
            response = requests.post(
                f"{self.base_url}/api/hl7",
                data=hl7_message,
                headers={'Content-Type': 'text/plain'},
                auth=(self.username, self.password) if self.username else None,
                timeout=self.timeout
            )
            
            if response.status_code in [200, 202]:
                logger.info(f"HL7 message sent: {message_type}")
                return True
            else:
                logger.error(f"Failed to send HL7 message: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send HL7 message: {e}")
            return False
    
    def _create_hl7_message(self, message_type: str, data: Dict[str, Any]) -> str:
        """Create HL7 message (simplified implementation)"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        
        if message_type == 'ORU':  # Observation Result
            # Simplified ORU message for report results
            message = f"""MSH|^~\\&|REPORTING|HOSPITAL|RIS|HOSPITAL|{timestamp}||ORU^R01|{timestamp}|P|2.5
PID|1||{data.get('patient_id', '')}||{data.get('patient_name', '')}
OBR|1||{data.get('accession_number', '')}|{data.get('procedure_code', '')}|{data.get('procedure_name', '')}
OBX|1|TX|FINDINGS||{data.get('findings', '')}
OBX|2|TX|IMPRESSION||{data.get('impression', '')}"""
        else:
            # Generic message
            message = f"""MSH|^~\\&|REPORTING|HOSPITAL|RIS|HOSPITAL|{timestamp}||{message_type}|{timestamp}|P|2.5"""
        
        return message
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get RIS integration status"""
        return {
            'enabled': self.enabled,
            'hl7_enabled': self.hl7_enabled,
            'base_url': self.base_url,
            'connected': self.check_connectivity() if self.enabled else False,
            'last_check': datetime.utcnow().isoformat()
        }

# Global RIS client instance
ris_client = RISClient()

def get_study_context(accession_number: str) -> Dict[str, Any]:
    """Get complete study context from RIS"""
    context = {
        'accession_number': accession_number,
        'patient_info': None,
        'study_order': None,
        'referring_physician': None,
        'ris_available': ris_client.enabled
    }
    
    if not ris_client.enabled:
        return context
    
    try:
        # Get study order
        study_order = ris_client.get_study_order(accession_number)
        if study_order:
            context['study_order'] = study_order
            
            # Get patient info
            patient_id = study_order.get('patient_id')
            if patient_id:
                patient_info = ris_client.get_patient_info(patient_id)
                context['patient_info'] = patient_info
            
            # Get referring physician
            physician_id = study_order.get('referring_physician_id')
            if physician_id:
                physician_info = ris_client.get_referring_physician(physician_id)
                context['referring_physician'] = physician_info
        
        return context
        
    except Exception as e:
        logger.error(f"Failed to get study context: {e}")
        return context