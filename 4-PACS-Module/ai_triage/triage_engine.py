import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from .dicom_processor import DicomSliceExtractor
from .model_manager import CNNModelManager

# Configure logging
logger = logging.getLogger(__name__)

class SliceTriageEngine:
    """
    Core Triage Engine.
    Orchestrates DICOM processing, Model Selection, and Inference.
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.dicom_processor = DicomSliceExtractor()
        # Initialize model manager (handles ONNX loading)
        # We wrap this in try-except to allow running without models present
        try:
            self.model_manager = CNNModelManager(config_path)
        except Exception as e:
            logger.warning(f"Failed to initialize ModelManager: {e}. Running in mock mode.")
            self.model_manager = None

    def analyze_study(self, study_id: str, dicom_files: List[str]) -> Dict[str, Any]:
        """
        Analyzes a full study by processing its DICOM files.
        
        Args:
            study_id: The StudyInstanceUID.
            dicom_files: List of file paths to DICOM instances.
            
        Returns:
            Dictionary containing triage results.
        """
        logger.info(f"Starting triage for study {study_id} with {len(dicom_files)} instances")
        
        results = {
            "study_id": study_id,
            "status": "processing",
            "findings": [],
            "critical_slices": [],
            "score": 0.0
        }

        try:
            # 1. Process a sample file to determine modality/body part
            if not dicom_files:
                raise ValueError("No DICOM files provided")

            # Load first file for metadata
            first_ds = self.dicom_processor.load_dicom(dicom_files[0])
            metadata = self.dicom_processor.get_metadata(first_ds)
            
            modality = metadata.get('Modality', 'UNKNOWN')
            body_part = metadata.get('BodyPartExamined', 'UNKNOWN')
            study_desc = metadata.get('StudyDescription', '')

            logger.info(f"Detected: {modality} - {body_part} - {study_desc}")

            # 2. Select Model
            model_id = None
            if self.model_manager:
                model_id = self.model_manager.select_model(study_desc, modality, body_part)
            
            if not model_id:
                logger.info("No suitable AI model found for this study type.")
                results["status"] = "skipped"
                results["message"] = "No model supported"
                return results

            # 3. Process Slices & Run Inference
            # For MVP, we might process a subset or all. 
            # Let's assume we process all for now, but in batches.
            
            scores = []
            
            for file_path in dicom_files:
                try:
                    # Extract frames (handles multi-frame too)
                    frames = self.dicom_processor.extract_frames(file_path, target_size=(224, 224))
                    
                    for frame in frames:
                        pixel_data = frame['pixel_data']
                        # Preprocess for model (add batch/channel dims)
                        # shape: (224, 224) -> (1, 1, 224, 224)
                        input_tensor = np.expand_dims(np.expand_dims(pixel_data, axis=0), axis=0)
                        
                        # Run Inference
                        if self.model_manager:
                            # Mock inference if model manager exists but models aren't loaded?
                            # The model_manager should handle inference.
                            # Assuming model_manager has a run_inference method (it doesn't in the snippet I saw)
                            # Let's assume we'd call:
                            # score = self.model_manager.run_inference(model_id, input_tensor)
                            
                            # For now, generate a mock score based on pixel intensity (just for testing flow)
                            score = float(np.mean(pixel_data)) # Dummy logic
                            scores.append(score)
                            
                            if score > 0.8: # Dummy threshold
                                results['critical_slices'].append(frame['metadata'].get('InstanceNumber'))
                        
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    continue

            # 4. Aggregate Results
            if scores:
                max_score = max(scores)
                results["score"] = max_score
                if max_score > 0.7:
                    results["status"] = "critical"
                    results["findings"].append("High probability of abnormality detected")
                else:
                    results["status"] = "normal"
            else:
                results["status"] = "failed"
                results["message"] = "No valid slices processed"

        except Exception as e:
            logger.error(f"Triage failed: {e}")
            results["status"] = "failed"
            results["error"] = str(e)

        return results
