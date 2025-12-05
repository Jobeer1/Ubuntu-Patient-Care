"""
AI Triage Control MCP Tool

This module provides Model Context Protocol (MCP) tools for controlling
the AI-driven triage system. Enables LLM agents to:
- Select and configure triage models
- Trigger triage pipeline on studies
- Monitor triage status and results
- Handle errors and fallbacks

Author: AI Teleradiology Team
Date: 2025-11-27
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import asyncio
from dataclasses import dataclass, asdict, field


# ============================================================================
# Enums and Data Classes
# ============================================================================

class ModelType(str, Enum):
    """Available model types for triage"""
    CHEST_CT_NODULE = "chest_ct_squeezenet"
    ABDOMEN_MR_BLEED = "abdomen_mr_shufflenet"
    BRAIN_CT_STROKE = "brain_ct_mobilenet"
    BONE_XRAY_FRACTURE = "bone_xray_efficientnet"


class TriageStatus(str, Enum):
    """Status of triage pipeline"""
    PENDING = "pending"
    PROCESSING = "processing"
    CRITICAL = "critical"
    ABNORMAL = "abnormal"
    NORMAL = "normal"
    FAILED = "failed"
    COMPLETED = "completed"


class Severity(str, Enum):
    """Severity level of findings"""
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    NORMAL = "normal"


@dataclass
class TriageResult:
    """Result of triage operation"""
    study_id: str
    model: ModelType
    status: TriageStatus
    severity: Severity
    confidence: float
    message: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    critical_slices: List[int] = field(default_factory=list)
    roi_coordinates: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['model'] = self.model.value
        data['status'] = self.status.value
        data['severity'] = self.severity.value
        return data


@dataclass
class ModelConfig:
    """Configuration for a triage model"""
    model_type: ModelType
    version: str
    threshold: float = 0.7
    enabled: bool = True
    batch_size: int = 8
    device: str = "cpu"
    quantized: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TriageRequest:
    """Request to triage a study"""
    study_id: str
    modality: str
    body_part: str
    model_type: Optional[ModelType] = None
    force_full_study: bool = False
    callback_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# AI Triage Engine
# ============================================================================

class AITriageEngine:
    """Core AI triage engine - manages models and triage pipeline"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the AI Triage Engine
        
        Args:
            config_path: Path to configuration file
        """
        self.logger = logging.getLogger(__name__)
        self.models: Dict[str, ModelConfig] = {}
        self.triage_queue: Dict[str, TriageStatus] = {}
        self.results_cache: Dict[str, TriageResult] = {}
        self._load_config(config_path)

    def _load_config(self, config_path: Optional[str] = None):
        """Load configuration from file or use defaults"""
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self._initialize_models(config.get('models', {}))
            except Exception as e:
                self.logger.error(f"Failed to load config: {e}")
                self._initialize_default_models()
        else:
            self._initialize_default_models()

    def _initialize_default_models(self):
        """Initialize with default model configurations"""
        models_config = [
            ModelConfig(
                model_type=ModelType.CHEST_CT_NODULE,
                version="1.0",
                threshold=0.75,
                metadata={
                    "modality": "CT",
                    "body_part": "Chest",
                    "target": "Pulmonary Nodules",
                    "sensitivity": 0.90,
                    "specificity": 0.85,
                    "model_size_mb": 45
                }
            ),
            ModelConfig(
                model_type=ModelType.ABDOMEN_MR_BLEED,
                version="1.0",
                threshold=0.70,
                metadata={
                    "modality": "MR",
                    "body_part": "Abdomen",
                    "target": "Bleeding",
                    "sensitivity": 0.88,
                    "specificity": 0.82,
                    "model_size_mb": 42
                }
            ),
            ModelConfig(
                model_type=ModelType.BRAIN_CT_STROKE,
                version="1.0",
                threshold=0.72,
                metadata={
                    "modality": "CT",
                    "body_part": "Brain",
                    "target": "Acute Stroke",
                    "sensitivity": 0.92,
                    "specificity": 0.88,
                    "model_size_mb": 38
                }
            ),
            ModelConfig(
                model_type=ModelType.BONE_XRAY_FRACTURE,
                version="1.0",
                threshold=0.68,
                metadata={
                    "modality": "XR",
                    "body_part": "Bone",
                    "target": "Fractures",
                    "sensitivity": 0.85,
                    "specificity": 0.80,
                    "model_size_mb": 35
                }
            ),
        ]

        for model_config in models_config:
            self.models[model_config.model_type.value] = model_config
            self.logger.info(f"Initialized model: {model_config.model_type.value}")

    def _initialize_models(self, models_config: Dict):
        """Initialize models from config dictionary"""
        for model_type, config in models_config.items():
            try:
                mtype = ModelType(model_type)
                model_config = ModelConfig(
                    model_type=mtype,
                    version=config.get('version', '1.0'),
                    threshold=config.get('threshold', 0.7),
                    enabled=config.get('enabled', True),
                    batch_size=config.get('batch_size', 8),
                    device=config.get('device', 'cpu'),
                    quantized=config.get('quantized', True),
                    metadata=config.get('metadata', {})
                )
                self.models[model_type] = model_config
            except ValueError as e:
                self.logger.error(f"Invalid model type {model_type}: {e}")

    def list_models(self) -> Dict[str, Dict[str, Any]]:
        """
        List all available triage models
        
        Returns:
            Dictionary of available models with their configurations
        """
        self.logger.info("Listing available models")
        return {
            key: {
                'type': config.model_type.value,
                'version': config.version,
                'threshold': config.threshold,
                'enabled': config.enabled,
                'metadata': config.metadata
            }
            for key, config in self.models.items()
        }

    def select_model(self, modality: str, body_part: str) -> Tuple[bool, str, Optional[ModelType]]:
        """
        Select appropriate model based on modality and body part
        
        Args:
            modality: Imaging modality (CT, MR, XR, US)
            body_part: Body part being imaged
            
        Returns:
            Tuple of (success, message, model_type)
        """
        self.logger.info(f"Selecting model for {modality} {body_part}")

        # Map modality/body_part combinations to models
        model_map = {
            ('CT', 'Chest'): ModelType.CHEST_CT_NODULE,
            ('MR', 'Abdomen'): ModelType.ABDOMEN_MR_BLEED,
            ('CT', 'Brain'): ModelType.BRAIN_CT_STROKE,
            ('XR', 'Bone'): ModelType.BONE_XRAY_FRACTURE,
        }

        key = (modality.upper(), body_part.title())
        
        if key not in model_map:
            msg = f"No model available for {modality} {body_part}"
            self.logger.warning(msg)
            return False, msg, None

        model_type = model_map[key]
        
        if model_type.value not in self.models:
            msg = f"Model {model_type.value} not loaded"
            self.logger.error(msg)
            return False, msg, None

        config = self.models[model_type.value]
        if not config.enabled:
            msg = f"Model {model_type.value} is disabled"
            self.logger.warning(msg)
            return False, msg, None

        msg = f"Selected model: {model_type.value} (v{config.version})"
        self.logger.info(msg)
        return True, msg, model_type

    def trigger_triage(self, request: TriageRequest) -> TriageResult:
        """
        Trigger triage pipeline for a study
        
        Args:
            request: TriageRequest object
            
        Returns:
            TriageResult with status and findings
        """
        self.logger.info(f"Triggering triage for study {request.study_id}")
        
        # Select model if not specified
        model_type = request.model_type
        if not model_type:
            success, msg, selected = self.select_model(request.modality, request.body_part)
            if not success:
                return TriageResult(
                    study_id=request.study_id,
                    model=ModelType.CHEST_CT_NODULE,  # Default fallback
                    status=TriageStatus.FAILED,
                    severity=Severity.NORMAL,
                    confidence=0.0,
                    message=f"Model selection failed: {msg}",
                    error=msg
                )
            model_type = selected

        # Update queue status
        self.triage_queue[request.study_id] = TriageStatus.PROCESSING

        try:
            # Simulate triage processing (in production, call actual model inference)
            result = self._simulate_triage_inference(request, model_type)
            
            # Cache result
            self.results_cache[request.study_id] = result
            self.triage_queue[request.study_id] = result.status
            
            self.logger.info(f"Triage completed for {request.study_id}: {result.status.value}")
            return result

        except Exception as e:
            error_msg = f"Triage failed: {str(e)}"
            self.logger.error(error_msg)
            
            result = TriageResult(
                study_id=request.study_id,
                model=model_type,
                status=TriageStatus.FAILED,
                severity=Severity.NORMAL,
                confidence=0.0,
                message=error_msg,
                error=error_msg
            )
            
            self.triage_queue[request.study_id] = TriageStatus.FAILED
            return result

    def _simulate_triage_inference(self, request: TriageRequest, model_type: ModelType) -> TriageResult:
        """
        Simulate triage inference (placeholder for actual model)
        
        Args:
            request: TriageRequest
            model_type: Selected model type
            
        Returns:
            TriageResult
        """
        # Simulate inference - in production, replace with actual model call
        import random
        
        confidence = random.uniform(0.6, 0.99)
        is_critical = random.random() < 0.1  # 10% of cases are critical
        
        if is_critical:
            severity = Severity.CRITICAL
            status = TriageStatus.CRITICAL
            confidence = max(0.85, confidence)
            critical_slices = list(range(10, 50, 5))
        else:
            severity = Severity.NORMAL
            status = TriageStatus.NORMAL
            critical_slices = []

        return TriageResult(
            study_id=request.study_id,
            model=model_type,
            status=status,
            severity=severity,
            confidence=confidence,
            message=f"Triage completed. Severity: {severity.value}",
            critical_slices=critical_slices,
            roi_coordinates={
                "region": "primary_finding",
                "x": random.randint(100, 400),
                "y": random.randint(100, 400),
                "width": random.randint(50, 200),
                "height": random.randint(50, 200)
            }
        )

    def get_triage_status(self, study_id: str) -> Dict[str, Any]:
        """
        Get current triage status for a study
        
        Args:
            study_id: Study identifier
            
        Returns:
            Dictionary with status information
        """
        self.logger.info(f"Getting triage status for {study_id}")
        
        status = self.triage_queue.get(study_id, TriageStatus.PENDING)
        result = self.results_cache.get(study_id)

        return {
            "study_id": study_id,
            "status": status.value,
            "result": result.to_dict() if result else None
        }

    def get_model_config(self, model_type: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific model
        
        Args:
            model_type: Model type identifier
            
        Returns:
            Model configuration dictionary or None
        """
        self.logger.info(f"Getting config for model {model_type}")
        
        if model_type not in self.models:
            self.logger.error(f"Model {model_type} not found")
            return None

        config = self.models[model_type]
        return {
            'type': config.model_type.value,
            'version': config.version,
            'threshold': config.threshold,
            'enabled': config.enabled,
            'batch_size': config.batch_size,
            'device': config.device,
            'quantized': config.quantized,
            'metadata': config.metadata
        }

    def update_model_threshold(self, model_type: str, threshold: float) -> Tuple[bool, str]:
        """
        Update threshold for a model
        
        Args:
            model_type: Model type identifier
            threshold: New threshold value (0.0-1.0)
            
        Returns:
            Tuple of (success, message)
        """
        if model_type not in self.models:
            msg = f"Model {model_type} not found"
            self.logger.error(msg)
            return False, msg

        if not (0.0 <= threshold <= 1.0):
            msg = "Threshold must be between 0.0 and 1.0"
            self.logger.error(msg)
            return False, msg

        self.models[model_type].threshold = threshold
        msg = f"Updated {model_type} threshold to {threshold}"
        self.logger.info(msg)
        return True, msg

    def toggle_model(self, model_type: str, enabled: bool) -> Tuple[bool, str]:
        """
        Enable or disable a model
        
        Args:
            model_type: Model type identifier
            enabled: True to enable, False to disable
            
        Returns:
            Tuple of (success, message)
        """
        if model_type not in self.models:
            msg = f"Model {model_type} not found"
            self.logger.error(msg)
            return False, msg

        self.models[model_type].enabled = enabled
        state = "enabled" if enabled else "disabled"
        msg = f"Model {model_type} {state}"
        self.logger.info(msg)
        return True, msg


# ============================================================================
# MCP Tool Functions
# ============================================================================

# Global engine instance
_engine: Optional[AITriageEngine] = None


def initialize_engine(config_path: Optional[str] = None):
    """Initialize the global AI triage engine"""
    global _engine
    _engine = AITriageEngine(config_path)
    return _engine


def get_engine() -> AITriageEngine:
    """Get the global engine instance, initializing if needed"""
    global _engine
    if _engine is None:
        _engine = AITriageEngine()
    return _engine


def mcp_list_models() -> Dict[str, Any]:
    """
    MCP Tool: List available triage models
    
    Returns available AI models for triage
    """
    engine = get_engine()
    return {
        "success": True,
        "models": engine.list_models()
    }


def mcp_select_model(modality: str, body_part: str) -> Dict[str, Any]:
    """
    MCP Tool: Select model based on imaging characteristics
    
    Args:
        modality: Imaging modality (CT, MR, XR, US)
        body_part: Body part being imaged
        
    Returns selected model information
    """
    engine = get_engine()
    success, message, model_type = engine.select_model(modality, body_part)
    
    return {
        "success": success,
        "message": message,
        "model": model_type.value if model_type else None,
        "config": engine.get_model_config(model_type.value) if model_type else None
    }


def mcp_trigger_triage(
    study_id: str,
    modality: str,
    body_part: str,
    model_type: Optional[str] = None,
    force_full_study: bool = False,
    callback_url: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    MCP Tool: Trigger AI triage on a study
    
    Args:
        study_id: Study identifier
        modality: Imaging modality
        body_part: Body part
        model_type: Optional model override
        force_full_study: Force transfer of full study
        callback_url: Callback URL for async notification
        metadata: Additional metadata
        
    Returns triage result
    """
    engine = get_engine()
    
    # Convert model_type string if provided
    model_enum = None
    if model_type:
        try:
            model_enum = ModelType(model_type)
        except ValueError:
            return {
                "success": False,
                "message": f"Invalid model type: {model_type}"
            }

    request = TriageRequest(
        study_id=study_id,
        modality=modality,
        body_part=body_part,
        model_type=model_enum,
        force_full_study=force_full_study,
        callback_url=callback_url,
        metadata=metadata or {}
    )

    result = engine.trigger_triage(request)
    
    return {
        "success": result.error is None,
        "result": result.to_dict()
    }


def mcp_get_triage_status(study_id: str) -> Dict[str, Any]:
    """
    MCP Tool: Get triage status for a study
    
    Args:
        study_id: Study identifier
        
    Returns current triage status
    """
    engine = get_engine()
    status_info = engine.get_triage_status(study_id)
    
    return {
        "success": True,
        "status_info": status_info
    }


def mcp_get_model_config(model_type: str) -> Dict[str, Any]:
    """
    MCP Tool: Get model configuration
    
    Args:
        model_type: Model type identifier
        
    Returns model configuration details
    """
    engine = get_engine()
    config = engine.get_model_config(model_type)
    
    return {
        "success": config is not None,
        "config": config
    }


def mcp_update_model_threshold(model_type: str, threshold: float) -> Dict[str, Any]:
    """
    MCP Tool: Update model detection threshold
    
    Args:
        model_type: Model type identifier
        threshold: New threshold value (0.0-1.0)
        
    Returns update result
    """
    engine = get_engine()
    success, message = engine.update_model_threshold(model_type, threshold)
    
    return {
        "success": success,
        "message": message
    }


def mcp_toggle_model(model_type: str, enabled: bool) -> Dict[str, Any]:
    """
    MCP Tool: Enable or disable a model
    
    Args:
        model_type: Model type identifier
        enabled: True to enable, False to disable
        
    Returns toggle result
    """
    engine = get_engine()
    success, message = engine.toggle_model(model_type, enabled)
    
    return {
        "success": success,
        "message": message
    }


# ============================================================================
# Tool Registry (for MCP server integration)
# ============================================================================

MCP_TOOLS = {
    "list_models": {
        "function": mcp_list_models,
        "description": "List all available AI triage models",
        "parameters": {}
    },
    "select_model": {
        "function": mcp_select_model,
        "description": "Select appropriate triage model based on imaging characteristics",
        "parameters": {
            "modality": {"type": "string", "description": "Imaging modality (CT, MR, XR, US)"},
            "body_part": {"type": "string", "description": "Body part being imaged"}
        }
    },
    "trigger_triage": {
        "function": mcp_trigger_triage,
        "description": "Trigger AI triage pipeline on a study",
        "parameters": {
            "study_id": {"type": "string", "description": "Study identifier"},
            "modality": {"type": "string", "description": "Imaging modality"},
            "body_part": {"type": "string", "description": "Body part"},
            "model_type": {"type": "string", "description": "Optional model override"},
            "force_full_study": {"type": "boolean", "description": "Force full study transfer"},
            "callback_url": {"type": "string", "description": "Optional callback URL"},
            "metadata": {"type": "object", "description": "Additional metadata"}
        }
    },
    "get_triage_status": {
        "function": mcp_get_triage_status,
        "description": "Get triage status for a study",
        "parameters": {
            "study_id": {"type": "string", "description": "Study identifier"}
        }
    },
    "get_model_config": {
        "function": mcp_get_model_config,
        "description": "Get configuration for a specific model",
        "parameters": {
            "model_type": {"type": "string", "description": "Model type identifier"}
        }
    },
    "update_model_threshold": {
        "function": mcp_update_model_threshold,
        "description": "Update detection threshold for a model",
        "parameters": {
            "model_type": {"type": "string", "description": "Model type identifier"},
            "threshold": {"type": "number", "description": "New threshold (0.0-1.0)"}
        }
    },
    "toggle_model": {
        "function": mcp_toggle_model,
        "description": "Enable or disable a model",
        "parameters": {
            "model_type": {"type": "string", "description": "Model type identifier"},
            "enabled": {"type": "boolean", "description": "True to enable, False to disable"}
        }
    }
}


if __name__ == "__main__":
    # Test the engine
    logging.basicConfig(level=logging.INFO)
    
    engine = initialize_engine()
    print("\n=== Available Models ===")
    models = engine.list_models()
    for name, config in models.items():
        print(f"  {name}: {config['version']}")
    
    print("\n=== Model Selection Test ===")
    success, msg, model = engine.select_model("CT", "Chest")
    print(f"  {msg}")
    
    print("\n=== Trigger Triage Test ===")
    request = TriageRequest(
        study_id="STUDY-001",
        modality="CT",
        body_part="Chest"
    )
    result = engine.trigger_triage(request)
    print(f"  Status: {result.status.value}")
    print(f"  Severity: {result.severity.value}")
    print(f"  Confidence: {result.confidence:.2%}")
