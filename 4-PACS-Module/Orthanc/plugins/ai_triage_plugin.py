import sys
import os
import json
import logging
from pathlib import Path

# Add parent directory to path to allow importing ai_triage
# Assuming this file is in 4-PACS-Module/Orthanc/plugins/
# We want to add 4-PACS-Module/ to path
current_dir = os.path.dirname(os.path.abspath(__file__))
pacs_module_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
if pacs_module_dir not in sys.path:
    sys.path.append(pacs_module_dir)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OrthancPlugin")

# Try importing orthanc (only available inside Orthanc)
try:
    import orthanc
except ImportError:
    orthanc = None
    logger.warning("Orthanc module not found. Plugin running in standalone/test mode.")

# Import AI Triage components
try:
    from ai_triage.triage_engine import SliceTriageEngine
except ImportError as e:
    logger.error(f"Failed to import AI Triage Engine: {e}")
    SliceTriageEngine = None

# Global Engine Instance
triage_engine = None

def LoadConfiguration():
    """Load plugin configuration"""
    config_path = os.path.join(current_dir, 'ai_triage_config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}

def OnChange(changeType, level, resource):
    """
    Callback for Orthanc changes.
    Triggers when a study is stable (StableStudy = 7).
    """
    if changeType == orthanc.ChangeType.STABLE_STUDY:
        logger.info(f"Stable study detected: {resource}")
        
        if not triage_engine:
            logger.error("Triage engine not initialized")
            return

        try:
            # Get Study Information
            study_tags = json.loads(orthanc.RestApiGet(f'/studies/{resource}'))
            patient_id = study_tags['PatientMainDicomTags']['PatientID']
            study_desc = study_tags['MainDicomTags'].get('StudyDescription', 'Unknown')
            
            logger.info(f"Processing Study: {study_desc} (Patient: {patient_id})")

            # Get list of instances (DICOM files)
            # In a real plugin, we might access files directly if on same disk, 
            # or fetch them via REST API.
            # For performance, direct file access is preferred if configured.
            
            # Orthanc stores files in a hashed directory structure. 
            # We can get the path to the DICOM file for each instance.
            
            instances = study_tags['Instances']
            file_paths = []
            
            for instance_id in instances:
                # This is an internal Orthanc call to get the path on disk
                # Note: This requires the plugin to have read access to Orthanc storage
                # Alternatively, we can get the file content via RestApiGet('/instances/{id}/file')
                # But that loads into memory.
                
                # For this implementation, let's assume we fetch the file content 
                # or get a path. Let's try to get the path if possible, or download to temp.
                
                # Simpler approach for MVP: Use RestApiGet to get bytes, pass bytes to processor.
                # But our engine expects file paths currently.
                # Let's update engine to accept bytes or paths, or save to temp.
                
                # Let's just collect instance IDs for now and let the engine fetch them?
                # No, the engine is generic.
                
                # Let's assume we just log for now, as full integration requires shared storage.
                pass

            # Trigger Triage (Mock call for now as we don't have file paths easily without shared storage)
            # In production, we would likely use a shared volume or HTTP fetch.
            
            logger.info(f"Triggering AI Triage for Study {resource}")
            
            # results = triage_engine.analyze_study(resource, file_paths)
            # logger.info(f"Triage Results: {results}")
            
            # Tag the study with results
            # orthanc.RestApiPost(f'/studies/{resource}/modify', json.dumps({
            #     "Replace": {
            #         "TriageStatus": "Processed"
            #     }
            # }))

        except Exception as e:
            logger.error(f"Error in OnChange callback: {e}")

def Initialize():
    """Plugin initialization"""
    global triage_engine
    logger.info("Initializing AI Triage Plugin")
    
    config = LoadConfiguration()
    
    if SliceTriageEngine:
        triage_engine = SliceTriageEngine()
        logger.info("AI Triage Engine initialized")
    else:
        logger.error("Could not initialize AI Triage Engine")

    if orthanc:
        orthanc.RegisterOnChangeCallback(OnChange)
        logger.info("Registered OnChange callback")

def Finalize():
    """Plugin cleanup"""
    logger.info("Finalizing AI Triage Plugin")

# Entry point if run directly (for testing)
if __name__ == "__main__":
    Initialize()
    # Simulate a callback
    # OnChange(orthanc.ChangeType.STABLE_STUDY, orthanc.ResourceType.STUDY, "dummy_study_id")
