"""
Whisper Model Manager for Medical Reporting Module
Handles automatic download, validation, and management of OpenAI Whisper models
"""

import os
import logging
import requests
import hashlib
import json
import shutil
import psutil
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from urllib.parse import urlparse
import tempfile
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ModelSize(Enum):
    """Available Whisper model sizes"""
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

@dataclass
class ModelInfo:
    """Information about a Whisper model"""
    size: ModelSize
    file_size_mb: int
    download_url: str
    checksum: str
    description: str
    min_ram_gb: float
    recommended_ram_gb: float

@dataclass
class SystemSpecs:
    """System specifications for model selection"""
    total_ram_gb: float
    available_ram_gb: float
    cpu_cores: int
    has_gpu: bool
    available_disk_gb: float

class WhisperModelManager:
    """Manages Whisper model downloads and validation"""
    
    # Model information with download URLs and checksums
    MODEL_INFO = {
        ModelSize.TINY: ModelInfo(
            size=ModelSize.TINY,
            file_size_mb=39,
            download_url="https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9f/tiny.pt",
            checksum="65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9f",
            description="Fastest, lowest accuracy. Good for testing.",
            min_ram_gb=1.0,
            recommended_ram_gb=2.0
        ),
        ModelSize.BASE: ModelInfo(
            size=ModelSize.BASE,
            file_size_mb=142,
            download_url="https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt",
            checksum="ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e",
            description="Good balance of speed and accuracy. Recommended for most users.",
            min_ram_gb=2.0,
            recommended_ram_gb=4.0
        ),
        ModelSize.SMALL: ModelInfo(
            size=ModelSize.SMALL,
            file_size_mb=466,
            download_url="https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt",
            checksum="9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794",
            description="Better accuracy, slower processing. Good for production use.",
            min_ram_gb=4.0,
            recommended_ram_gb=8.0
        ),
        ModelSize.MEDIUM: ModelInfo(
            size=ModelSize.MEDIUM,
            file_size_mb=1542,
            download_url="https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt",
            checksum="345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1",
            description="High accuracy, slower processing. For high-quality transcription.",
            min_ram_gb=8.0,
            recommended_ram_gb=16.0
        ),
        ModelSize.LARGE: ModelInfo(
            size=ModelSize.LARGE,
            file_size_mb=3094,
            download_url="https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a/large-v3.pt",
            checksum="e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a",
            description="Highest accuracy, slowest processing. For maximum quality.",
            min_ram_gb=16.0,
            recommended_ram_gb=32.0
        )
    }
    
    def __init__(self, models_directory: str = None):
        """Initialize the Whisper model manager"""
        if models_directory is None:
            # Default to models directory in the application root
            app_root = Path(__file__).parent.parent
            models_directory = app_root / "models" / "whisper"
        
        self.models_directory = Path(models_directory)
        self.models_directory.mkdir(parents=True, exist_ok=True)
        
        # Cache directory for downloads
        self.cache_directory = self.models_directory / "cache"
        self.cache_directory.mkdir(exist_ok=True)
        
        logger.info(f"Whisper model manager initialized. Models directory: {self.models_directory}")
    
    def get_system_specs(self) -> SystemSpecs:
        """Get current system specifications"""
        try:
            # Get memory info
            memory = psutil.virtual_memory()
            total_ram_gb = memory.total / (1024**3)
            available_ram_gb = memory.available / (1024**3)
            
            # Get CPU info
            cpu_cores = psutil.cpu_count(logical=False) or psutil.cpu_count()
            
            # Check for GPU (simplified check)
            has_gpu = False
            try:
                import torch
                has_gpu = torch.cuda.is_available()
            except ImportError:
                pass
            
            # Get disk space
            disk_usage = psutil.disk_usage(str(self.models_directory))
            available_disk_gb = disk_usage.free / (1024**3)
            
            return SystemSpecs(
                total_ram_gb=total_ram_gb,
                available_ram_gb=available_ram_gb,
                cpu_cores=cpu_cores,
                has_gpu=has_gpu,
                available_disk_gb=available_disk_gb
            )
            
        except Exception as e:
            logger.error(f"Failed to get system specs: {e}")
            # Return conservative defaults
            return SystemSpecs(
                total_ram_gb=4.0,
                available_ram_gb=2.0,
                cpu_cores=2,
                has_gpu=False,
                available_disk_gb=10.0
            )
    
    def get_optimal_model_size(self, system_specs: SystemSpecs = None) -> ModelSize:
        """Determine optimal model size based on system specifications"""
        if system_specs is None:
            system_specs = self.get_system_specs()
        
        logger.info(f"System specs: RAM={system_specs.total_ram_gb:.1f}GB, "
                   f"Available={system_specs.available_ram_gb:.1f}GB, "
                   f"CPU cores={system_specs.cpu_cores}, GPU={system_specs.has_gpu}")
        
        # Check available disk space first
        required_space_gb = 5.0  # Minimum space needed including model + temp files
        if system_specs.available_disk_gb < required_space_gb:
            logger.warning(f"Low disk space: {system_specs.available_disk_gb:.1f}GB available")
            return ModelSize.TINY
        
        # FORCE BASE MODEL FOR FAST STARTUP - Medical reporting doesn't need huge models
        # Base model (74MB) is sufficient for medical terminology and much faster to load
        logger.info("Using BASE model for fast startup and medical reporting efficiency")
        return ModelSize.BASE
    
    def check_model_exists(self, model_size: ModelSize) -> bool:
        """Check if a model exists and is valid"""
        try:
            model_path = self.get_model_path(model_size)
            
            if not model_path.exists():
                return False
            
            # Check file size
            file_size_mb = model_path.stat().st_size / (1024 * 1024)
            expected_size_mb = self.MODEL_INFO[model_size].file_size_mb
            
            # Allow 5% variance in file size
            if abs(file_size_mb - expected_size_mb) > (expected_size_mb * 0.05):
                logger.warning(f"Model {model_size.value} has unexpected size: {file_size_mb:.1f}MB "
                             f"(expected {expected_size_mb}MB)")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to check model existence: {e}")
            return False
    
    def get_model_path(self, model_size: ModelSize) -> Path:
        """Get the path where a model should be stored"""
        return self.models_directory / f"{model_size.value}.pt"
    
    def validate_model_integrity(self, model_size: ModelSize) -> bool:
        """Validate model file integrity using checksum"""
        try:
            model_path = self.get_model_path(model_size)
            
            if not model_path.exists():
                return False
            
            # Calculate SHA256 checksum
            sha256_hash = hashlib.sha256()
            with open(model_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            
            calculated_checksum = sha256_hash.hexdigest()
            expected_checksum = self.MODEL_INFO[model_size].checksum
            
            if calculated_checksum == expected_checksum:
                logger.info(f"Model {model_size.value} integrity validated successfully")
                return True
            else:
                logger.error(f"Model {model_size.value} integrity check failed. "
                           f"Expected: {expected_checksum}, Got: {calculated_checksum}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to validate model integrity: {e}")
            return False
    
    def download_model(self, model_size: ModelSize, progress_callback=None) -> bool:
        """Download a Whisper model with progress tracking"""
        try:
            model_info = self.MODEL_INFO[model_size]
            model_path = self.get_model_path(model_size)
            temp_path = self.cache_directory / f"{model_size.value}_temp.pt"
            
            logger.info(f"Starting download of {model_size.value} model ({model_info.file_size_mb}MB)")
            
            # Check available disk space
            system_specs = self.get_system_specs()
            required_space_gb = (model_info.file_size_mb * 2) / 1024  # 2x for temp file
            
            if system_specs.available_disk_gb < required_space_gb:
                logger.error(f"Insufficient disk space. Required: {required_space_gb:.1f}GB, "
                           f"Available: {system_specs.available_disk_gb:.1f}GB")
                return False
            
            # Download with progress tracking
            response = requests.get(model_info.download_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            progress_callback(progress, downloaded_size, total_size)
            
            logger.info(f"Download completed: {downloaded_size / (1024*1024):.1f}MB")
            
            # Validate downloaded file
            if not self._validate_downloaded_file(temp_path, model_info):
                logger.error("Downloaded file validation failed")
                temp_path.unlink(missing_ok=True)
                return False
            
            # Move to final location
            if model_path.exists():
                model_path.unlink()
            
            shutil.move(str(temp_path), str(model_path))
            
            logger.info(f"Model {model_size.value} downloaded and installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download model {model_size.value}: {e}")
            # Clean up temp file
            if 'temp_path' in locals():
                temp_path.unlink(missing_ok=True)
            return False
    
    def _validate_downloaded_file(self, file_path: Path, model_info: ModelInfo) -> bool:
        """Validate downloaded file size and checksum"""
        try:
            # Check file size
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            expected_size_mb = model_info.file_size_mb
            
            if abs(file_size_mb - expected_size_mb) > (expected_size_mb * 0.05):
                logger.error(f"Downloaded file size mismatch: {file_size_mb:.1f}MB "
                           f"(expected {expected_size_mb}MB)")
                return False
            
            # Validate checksum
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            
            calculated_checksum = sha256_hash.hexdigest()
            
            if calculated_checksum != model_info.checksum:
                logger.error(f"Downloaded file checksum mismatch")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate downloaded file: {e}")
            return False
    
    def setup_whisper_environment(self, preferred_model_size: ModelSize = None) -> Tuple[bool, ModelSize]:
        """Set up Whisper environment with automatic model selection and download"""
        try:
            # Get system specifications
            system_specs = self.get_system_specs()
            
            # Determine optimal model size
            if preferred_model_size is None:
                optimal_size = self.get_optimal_model_size(system_specs)
            else:
                optimal_size = preferred_model_size
            
            logger.info(f"Setting up Whisper environment with {optimal_size.value} model")
            
            # Check if model exists and is valid
            if self.check_model_exists(optimal_size):
                if self.validate_model_integrity(optimal_size):
                    logger.info(f"Model {optimal_size.value} already exists and is valid")
                    return True, optimal_size
                else:
                    logger.warning(f"Model {optimal_size.value} exists but is corrupted, re-downloading")
            
            # Download the model
            def progress_callback(progress, downloaded, total):
                if progress % 10 == 0:  # Log every 10%
                    logger.info(f"Download progress: {progress:.1f}% "
                               f"({downloaded/(1024*1024):.1f}/{total/(1024*1024):.1f} MB)")
            
            success = self.download_model(optimal_size, progress_callback)
            
            if success:
                logger.info(f"Whisper environment setup completed with {optimal_size.value} model")
                return True, optimal_size
            else:
                # Try fallback to smaller model
                if optimal_size != ModelSize.TINY:
                    logger.warning(f"Failed to download {optimal_size.value}, trying TINY model as fallback")
                    fallback_success = self.download_model(ModelSize.TINY, progress_callback)
                    if fallback_success:
                        return True, ModelSize.TINY
                
                logger.error("Failed to set up Whisper environment")
                return False, optimal_size
            
        except Exception as e:
            logger.error(f"Failed to setup Whisper environment: {e}")
            return False, ModelSize.BASE
    
    def list_available_models(self) -> List[Dict]:
        """List all available models with their status"""
        models = []
        
        for model_size in ModelSize:
            model_info = self.MODEL_INFO[model_size]
            exists = self.check_model_exists(model_size)
            valid = self.validate_model_integrity(model_size) if exists else False
            
            models.append({
                "size": model_size.value,
                "file_size_mb": model_info.file_size_mb,
                "description": model_info.description,
                "min_ram_gb": model_info.min_ram_gb,
                "recommended_ram_gb": model_info.recommended_ram_gb,
                "exists": exists,
                "valid": valid,
                "path": str(self.get_model_path(model_size))
            })
        
        return models
    
    def cleanup_cache(self) -> bool:
        """Clean up temporary download files"""
        try:
            if self.cache_directory.exists():
                for file_path in self.cache_directory.glob("*_temp.pt"):
                    file_path.unlink()
                    logger.info(f"Cleaned up temp file: {file_path.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup cache: {e}")
            return False
    
    def get_model_status(self) -> Dict:
        """Get comprehensive status of all models"""
        try:
            system_specs = self.get_system_specs()
            optimal_size = self.get_optimal_model_size(system_specs)
            
            return {
                "system_specs": {
                    "total_ram_gb": system_specs.total_ram_gb,
                    "available_ram_gb": system_specs.available_ram_gb,
                    "cpu_cores": system_specs.cpu_cores,
                    "has_gpu": system_specs.has_gpu,
                    "available_disk_gb": system_specs.available_disk_gb
                },
                "optimal_model_size": optimal_size.value,
                "models_directory": str(self.models_directory),
                "models": self.list_available_models()
            }
            
        except Exception as e:
            logger.error(f"Failed to get model status: {e}")
            return {}

# Global instance
whisper_model_manager = WhisperModelManager()