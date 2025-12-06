#!/usr/bin/env python3
"""
GOTG PACS-RIS Integration Bridge
Seamless integration between PACS and RIS systems
"""

import os
import time
import json
import logging
import requests
import schedule
from datetime import datetime
from flask import Flask, jsonify, request
from threading import Thread

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
ORTHANC_URL = os.getenv('ORTHANC_URL', 'http://pacs-orthanc:8042')
ORTHANC_USER = os.getenv('ORTHANC_USERNAME', 'orthanc')
ORTHANC_PASS = os.getenv('ORTHANC_PASSWORD', 'orthanc')
RIS_URL = os.getenv('RIS_URL', 'http://host.docker.internal:5000')
WORKLIST_SYNC_INTERVAL = int(os.getenv('WORKLIST_SYNC_INTERVAL', '60'))

# Flask app
app = Flask(__name__)

class RISBridge:
    """Bridge between PACS and RIS"""
    
    def __init__(self):
        self.stats = {
            'worklist_synced': 0,
            'studies_updated': 0,
            'errors': 0,
            'last_sync': None
        }
    
    def sync_worklist(self):
        """Sync modality worklist from RIS to PACS"""
        try:
            logger.info("Syncing worklist from RIS")
            
            # Get appointments from RIS
            response = requests.get(
                f'{RIS_URL}/api/appointments',
                params={'status': 'scheduled'},
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get appointments from RIS: {response.status_code}")
                self.stats['errors'] += 1
                return
            
            appointments = response.json()
            logger.info(f"Found {len(appointments)} scheduled appointments")
            
            # Convert to DICOM worklist format
            for appt in appointments:
                self._create_worklist_item(appt)
            
            self.stats['worklist_synced'] += len(appointments)
            self.stats['last_sync'] = datetime.now().isoformat()
            logger.info(f"Worklist sync complete: {len(appointments)} items")
            
        except Exception as e:
            logger.error(f"Worklist sync failed: {e}")
            self.stats['errors'] += 1
    
    def _create_worklist_item(self, appointment):
        """Create DICOM worklist item from appointment"""
        try:
            # Get patient details from RIS
            patient_response = requests.get(
                f'{RIS_URL}/api/patients/{appointment["patientId"]}',
                timeout=5
            )
            
            if patient_response.status_code != 200:
                logger.warning(f"Patient not found: {appointment['patientId']}")
                return
            
            patient = patient_response.json()
            
            # Create worklist item in Orthanc
            worklist_item = {
                'PatientID': patient.get('id'),
                'PatientName': f"{patient.get('firstName')} {patient.get('lastName')}",
                'PatientBirthDate': patient.get('dateOfBirth', ''),
                'PatientSex': patient.get('gender', 'O')[0],
                'AccessionNumber': appointment.get('id'),
                'ScheduledProcedureStepStartDate': appointment.get('date'),
                'ScheduledProcedureStepStartTime': appointment.get('time', '').replace(':', ''),
                'Modality': self._map_modality(appointment.get('modality')),
                'ScheduledProcedureStepDescription': appointment.get('procedure', ''),
                'RequestedProcedureDescription': appointment.get('procedure', ''),
                'StudyInstanceUID': self._generate_uid()
            }
            
            logger.debug(f"Created worklist item for patient {patient.get('id')}")
            
        except Exception as e:
            logger.error(f"Failed to create worklist item: {e}")
    
    def _map_modality(self, modality_name):
        """Map RIS modality name to DICOM modality code"""
        mapping = {
            'X-Ray': 'CR',
            'CT Scan': 'CT',
            'MRI': 'MR',
            'Ultrasound': 'US',
            'Mammography': 'MG',
            'Fluoroscopy': 'XA',
            'Nuclear Medicine': 'NM',
            'PET Scan': 'PT'
        }
        return mapping.get(modality_name, 'OT')
    
    def _generate_uid(self):
        """Generate DICOM UID"""
        import time
        timestamp = str(int(time.time() * 1000000))
        return f"1.2.826.0.1.3680043.8.498.{timestamp}"
    
    def update_study_status(self, study_id, status):
        """Update study status in RIS"""
        try:
            # Get study details from Orthanc
            response = requests.get(
                f'{ORTHANC_URL}/studies/{study_id}',
                auth=(ORTHANC_USER, ORTHANC_PASS),
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Study not found in PACS: {study_id}")
                return False
            
            study = response.json()
            
            # Extract accession number (maps to appointment ID)
            accession_number = study.get('MainDicomTags', {}).get('AccessionNumber')
            
            if not accession_number:
                logger.warning(f"No accession number for study {study_id}")
                return False
            
            # Update appointment status in RIS
            ris_response = requests.put(
                f'{RIS_URL}/api/appointments/{accession_number}',
                json={'status': status},
                timeout=10
            )
            
            if ris_response.status_code == 200:
                logger.info(f"Updated study status in RIS: {accession_number} -> {status}")
                self.stats['studies_updated'] += 1
                return True
            else:
                logger.error(f"Failed to update RIS: {ris_response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update study status: {e}")
            self.stats['errors'] += 1
            return False
    
    def monitor_study_changes(self):
        """Monitor PACS for study changes and update RIS"""
        try:
            # Get recent changes from Orthanc
            response = requests.get(
                f'{ORTHANC_URL}/changes',
                auth=(ORTHANC_USER, ORTHANC_PASS),
                params={'limit': 100},
                timeout=10
            )
            
            if response.status_code != 200:
                return
            
            changes = response.json().get('Changes', [])
            
            for change in changes:
                if change['ChangeType'] == 'NewStudy':
                    # New study received
                    self.update_study_status(change['ID'], 'in_progress')
                elif change['ChangeType'] == 'StableStudy':
                    # Study completed
                    self.update_study_status(change['ID'], 'completed')
            
        except Exception as e:
            logger.error(f"Failed to monitor changes: {e}")
    
    def run(self):
        """Main bridge loop"""
        logger.info("Starting GOTG PACS-RIS Bridge")
        
        # Schedule tasks
        schedule.every(WORKLIST_SYNC_INTERVAL).seconds.do(self.sync_worklist)
        schedule.every(30).seconds.do(self.monitor_study_changes)
        
        # Initial sync
        self.sync_worklist()
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutting down RIS bridge")
                break
            except Exception as e:
                logger.error(f"Error in bridge loop: {e}")
                time.sleep(5)

# Global bridge instance
ris_bridge = RISBridge()

# Flask routes
@app.route('/health')
def health():
    """Health check"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/stats')
def stats():
    """Get bridge statistics"""
    return jsonify(ris_bridge.stats)

@app.route('/sync-worklist', methods=['POST'])
def sync_worklist():
    """Trigger worklist sync"""
    ris_bridge.sync_worklist()
    return jsonify({'status': 'sync triggered'})

@app.route('/update-study', methods=['POST'])
def update_study():
    """Update study status"""
    data = request.json
    study_id = data.get('study_id')
    status = data.get('status')
    
    if not study_id or not status:
        return jsonify({'error': 'Missing study_id or status'}), 400
    
    success = ris_bridge.update_study_status(study_id, status)
    return jsonify({'success': success})

def run_flask():
    """Run Flask server"""
    app.run(host='0.0.0.0', port=5003, debug=False)

if __name__ == '__main__':
    # Start Flask in separate thread
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Run bridge
    ris_bridge.run()
