"""
CNN Model Manager for AI Triage Pipeline

Manages lightweight, quantized CNN models for different imaging modalities.
"""

import os
from pathlib import Path
from typing import Dict, Optional
import onnxruntime as ort
import yaml
from loguru import logger


class CNNModelManager:
    """Manages CNN models for medical image triage"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize model manager
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.models: Dict[str, ort.InferenceSession] = {}
        self.model_metadata: Dict[str, dict] = {}
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def select_model(self, study_description: str, modality: str, 
                     body_part: str) -> str:
        """
        Select appropriate CNN model based on study metadata
        
        Args:
            study_description: DICOM study description
            modality: Imaging modality (CT, MR, XR, etc.)
            body_part: Body part examined
            
        Returns:
            Model identifier string
        """
        # Normalize inputs
        study_desc_lower = study_description.lower()
        modality_lower = modality.lower()
        body_part_lower = body_part.lower()
        
        # Selection logic
        if modality_lower == "ct" and "chest" in body_part_lower:
            if any(term in study_desc_lower for term in ["nodule", "lung", "pulmonary"]):
                return "chest_ct_nodule"
                
        elif modality_lower == "mr" and "abdomen" in body_part_lower:
            if any(term in study_desc_lower for term in ["bleed", "hemorrhage"]):
                return "abdomen_mr_bleed"
                
        elif modality_lower == "ct" and "brain" in body_part_lower:
            if any(term in study_desc_lower for term in ["stroke", "cva", "ischemia"]):
                return "brain_ct_stroke"
                
        elif modality_lower == "xr" and "bone" in body_part_lower:
            if any(term in study_desc_lower for term in ["fracture", "trauma"]):
                return "bone_xray_fracture"
        
        # Default fallback
        logger.warning(f"No specific model for {modality}/{body_part}, using generic")
        return "generic_anomaly"
    
    def load_model(self, model_name: str) -> ort.InferenceSession:
        """
        Load ONNX model into memory
        
        Args:
            model_name: Model identifier
            
        Returns:
            ONNX Runtime inference session
        """
        # Check if already loaded
        if model_name in self.models:
            logger.debug(f"Model {model_name} already loaded")
            return self.models[model_name]
        
        # Get model path from config
        model_path = self.config['models'].get(model_name)
        if not model_path:
            raise ValueError(f"Model {model_name} not found in config")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Load model
        logger.info(f"Loading model {model_name} from {model_path}")
        
        # Use CPU execution provider for maximum compatibility
        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        session = ort.InferenceSession(
            model_path,
            sess_options=session_options,
            providers=['CPUExecutionProvider']
        )
        
        # Cache model
        self.models[model_name] = session
        
        # Store metadata
        self.model_metadata[model_name] = {
            'path': model_path,
            'input_shape': session.get_inputs()[0].shape,
            'input_name': session.get_inputs()[0].name,
            'output_name': session.get_outputs()[0].name
        }
        
        logger.info(f"Model {model_name} loaded successfully")
        return session
    
    def get_model_metadata(self, model_name: str) -> dict:
        """Get metadata for a loaded model"""
        if model_name not in self.model_metadata:
            raise ValueError(f"Model {model_name} not loaded")
        return self.model_metadata[model_name]
    
    def unload_model(self, model_name: str):
        """Unload model from memory"""
        if model_name in self.models:
            del self.models[model_name]
            del self.model_metadata[model_name]
            logger.info(f"Model {model_name} unloaded")
    
    def list_available_models(self) -> list:
        """List all available models from config"""
        return list(self.config['models'].keys())
    
    def list_loaded_models(self) -> list:
        """List currently loaded models"""
        return list(self.models.keys())
