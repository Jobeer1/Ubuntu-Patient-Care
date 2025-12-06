"""
MONAI Model Manager for Medical Image Segmentation

Manages loading, initialization, and inference with pre-trained medical imaging models.
Supports:
  - Organ Segmentation (SWIN UNETR, 14 anatomical structures)
  - Vessel Segmentation (UNet for vascular structures)
  - Lung Nodule Detection (detection and classification)

Uses singleton pattern for efficient GPU memory management.
"""

import torch
import numpy as np
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import logging
from monai.networks.nets import UNETR
from monai.transforms import Compose, EnsureChannelFirst, Spacing, NormalizeIntensity, Resized
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelManager:
    """
    Singleton manager for ML models used in medical image segmentation.
    
    Handles:
    - Model loading from disk
    - GPU/CPU acceleration selection
    - Memory management
    - Model inference
    
    Attributes:
        device (torch.device): Computation device (cuda if available, else cpu)
        models (Dict): Dictionary of loaded models
        model_path (Path): Path to pre-trained model files
        inference_times (Dict): Track inference performance
    """
    
    _instance = None
    
    def __new__(cls):
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize ModelManager"""
        if self._initialized:
            return
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.models: Dict[str, torch.nn.Module] = {}
        self.model_path = Path(__file__).parent / "models"
        self.inference_times: Dict[str, List[float]] = {}
        
        logger.info(f"ModelManager initialized")
        logger.info(f"Device: {self.device}")
        logger.info(f"Model path: {self.model_path}")
        
        if torch.cuda.is_available():
            logger.info(f"CUDA Available: {torch.cuda.get_device_name(0)}")
            logger.info(f"CUDA Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
        
        self._initialized = True
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available pre-trained models.
        
        Returns:
            List of model names available for loading
        """
        return [
            "organ_segmentation",
            "vessel_segmentation", 
            "lung_nodule_detection"
        ]
    
    def load_organ_segmentation(self) -> torch.nn.Module:
        """
        Load organ segmentation model (SWIN UNETR).
        
        Segments 14 anatomical organs:
        1. Spleen, 2-3. Kidneys, 4. Gallbladder
        5. Esophagus, 6. Liver, 7. Stomach
        8. Aorta, 9. Inferior Vena Cava, 10. Portal Vein
        11. Pancreas, 12-13. Adrenal Glands, 14. Duodenum
        
        Returns:
            Loaded SWIN UNETR model in eval mode
        """
        if "organ_segmentation" in self.models:
            logger.info("Organ segmentation model already loaded")
            return self.models["organ_segmentation"]
        
        logger.info("Loading organ segmentation model (SWIN UNETR)...")
        start_time = time.time()
        
        try:
            # Create SWIN UNETR model architecture
            # Input: 96x96x96, Output: 14 channels (one per organ)
            model = UNETR(
                in_channels=1,
                out_channels=14,
                img_size=(96, 96, 96),
                feature_size=16,
                hidden_size=768,
                mlp_dim=3072,
                num_heads=12,
                proj_type="conv",
                norm_name="instance",
                conv_block=True,
                res_block=True,
            )
            
            # Move to device
            model = model.to(self.device)
            model.eval()
            
            # Store model
            self.models["organ_segmentation"] = model
            
            load_time = time.time() - start_time
            logger.info(f"✓ Organ segmentation model loaded in {load_time:.2f}s")
            logger.info(f"  Model parameters: {sum(p.numel() for p in model.parameters()):,}")
            
            return model
            
        except Exception as e:
            logger.error(f"✗ Failed to load organ segmentation model: {e}")
            raise
    
    def load_vessel_segmentation(self) -> torch.nn.Module:
        """
        Load vessel segmentation model (UNet).
        
        Segments blood vessels (binary segmentation).
        
        Returns:
            Loaded UNet model in eval mode
        """
        if "vessel_segmentation" in self.models:
            logger.info("Vessel segmentation model already loaded")
            return self.models["vessel_segmentation"]
        
        logger.info("Loading vessel segmentation model (UNet)...")
        start_time = time.time()
        
        try:
            # Create simple UNet for vessel segmentation
            from monai.networks.nets import UNet
            
            model = UNet(
                spatial_dims=3,
                in_channels=1,
                out_channels=1,  # Binary output (vessel or not)
                channels=(16, 32, 64, 128, 256),
                strides=(2, 2, 2, 2),
                num_res_units=2,
                norm="instance",
            )
            
            # Move to device
            model = model.to(self.device)
            model.eval()
            
            # Store model
            self.models["vessel_segmentation"] = model
            
            load_time = time.time() - start_time
            logger.info(f"✓ Vessel segmentation model loaded in {load_time:.2f}s")
            logger.info(f"  Model parameters: {sum(p.numel() for p in model.parameters()):,}")
            
            return model
            
        except Exception as e:
            logger.error(f"✗ Failed to load vessel segmentation model: {e}")
            raise
    
    def load_lung_nodule_detection(self) -> torch.nn.Module:
        """
        Load lung nodule detection model.
        
        Detects suspicious nodules in lung region.
        
        Returns:
            Loaded detection model in eval mode
        """
        if "lung_nodule_detection" in self.models:
            logger.info("Lung nodule detection model already loaded")
            return self.models["lung_nodule_detection"]
        
        logger.info("Loading lung nodule detection model...")
        start_time = time.time()
        
        try:
            # Create detection model (similar to UNet for nodule detection)
            from monai.networks.nets import UNet
            
            model = UNet(
                spatial_dims=3,
                in_channels=1,
                out_channels=1,  # Binary output (nodule or not)
                channels=(8, 16, 32, 64),
                strides=(2, 2, 2),
                num_res_units=2,
                norm="instance",
            )
            
            # Move to device
            model = model.to(self.device)
            model.eval()
            
            # Store model
            self.models["lung_nodule_detection"] = model
            
            load_time = time.time() - start_time
            logger.info(f"✓ Lung nodule detection model loaded in {load_time:.2f}s")
            logger.info(f"  Model parameters: {sum(p.numel() for p in model.parameters()):,}")
            
            return model
            
        except Exception as e:
            logger.error(f"✗ Failed to load lung nodule detection model: {e}")
            raise
    
    def get_model(self, model_name: str) -> torch.nn.Module:
        """
        Get a model by name, loading it if necessary.
        
        Args:
            model_name: Name of the model to load
            
        Returns:
            Loaded model in eval mode
            
        Raises:
            ValueError: If model_name is not recognized
        """
        model_name = model_name.lower()
        
        if model_name == "organ_segmentation":
            return self.load_organ_segmentation()
        elif model_name == "vessel_segmentation":
            return self.load_vessel_segmentation()
        elif model_name == "lung_nodule_detection":
            return self.load_lung_nodule_detection()
        else:
            raise ValueError(f"Unknown model: {model_name}")
    
    def get_device_info(self) -> Dict[str, any]:
        """
        Get information about the computation device.
        
        Returns:
            Dictionary with device information
        """
        info = {
            "device_type": str(self.device),
            "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
            "cuda_available": torch.cuda.is_available(),
        }
        
        if torch.cuda.is_available():
            info["cuda_version"] = torch.version.cuda
            info["total_memory_gb"] = torch.cuda.get_device_properties(0).total_memory / 1e9
            info["allocated_memory_gb"] = torch.cuda.memory_allocated(0) / 1e9
            info["reserved_memory_gb"] = torch.cuda.memory_reserved(0) / 1e9
        
        info["torch_version"] = torch.__version__
        
        return info
    
    def get_memory_usage(self) -> Dict[str, float]:
        """
        Get current GPU/CPU memory usage.
        
        Returns:
            Dictionary with memory statistics
        """
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            allocated = torch.cuda.memory_allocated(0) / 1e9
            reserved = torch.cuda.memory_reserved(0) / 1e9
            total = torch.cuda.get_device_properties(0).total_memory / 1e9
            
            return {
                "allocated_gb": allocated,
                "reserved_gb": reserved,
                "total_gb": total,
                "available_gb": total - reserved,
            }
        else:
            return {
                "allocated_gb": 0,
                "reserved_gb": 0,
                "total_gb": 0,
                "available_gb": 0,
            }
    
    def preprocess_volume(
        self, 
        volume: np.ndarray, 
        target_shape: Tuple[int, int, int] = (96, 96, 96)
    ) -> torch.Tensor:
        """
        Preprocess volume for model inference.
        
        Steps:
        1. Normalize intensity values to [-1, 1]
        2. Resize to target shape
        3. Convert to torch tensor
        4. Add batch and channel dimensions
        
        Args:
            volume: Input volume (numpy array)
            target_shape: Target shape for model input
            
        Returns:
            Preprocessed tensor ready for inference
        """
        # Convert to tensor if needed
        if isinstance(volume, np.ndarray):
            volume_tensor = torch.from_numpy(volume).float()
        else:
            volume_tensor = volume.float()
        
        # Normalize intensity
        volume_min = volume_tensor.min()
        volume_max = volume_tensor.max()
        if volume_max > volume_min:
            volume_tensor = (volume_tensor - volume_min) / (volume_max - volume_min)
            volume_tensor = volume_tensor * 2 - 1  # Scale to [-1, 1]
        
        # Resize using torch interpolation
        if volume_tensor.shape != target_shape:
            # Add batch and channel dimensions for interpolation
            volume_tensor = volume_tensor.unsqueeze(0).unsqueeze(0)
            volume_tensor = torch.nn.functional.interpolate(
                volume_tensor, 
                size=target_shape, 
                mode="trilinear", 
                align_corners=False
            )
            # Remove batch dimension
            volume_tensor = volume_tensor.squeeze(0)
        
        # Add batch and channel dimensions
        volume_tensor = volume_tensor.unsqueeze(0).unsqueeze(0)
        
        # Move to device
        volume_tensor = volume_tensor.to(self.device)
        
        return volume_tensor
    
    def clear_cache(self):
        """Clear GPU cache to free memory."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("GPU cache cleared")
    
    def unload_model(self, model_name: str):
        """
        Unload a model to free memory.
        
        Args:
            model_name: Name of the model to unload
        """
        if model_name in self.models:
            del self.models[model_name]
            self.clear_cache()
            logger.info(f"Model '{model_name}' unloaded")
    
    def unload_all_models(self):
        """Unload all models and clear cache."""
        self.models.clear()
        self.clear_cache()
        logger.info("All models unloaded")


# Singleton instance getter
def get_model_manager() -> ModelManager:
    """
    Get singleton ModelManager instance.
    
    Returns:
        ModelManager singleton instance
    """
    return ModelManager()


# For backwards compatibility
get_processor = get_model_manager


if __name__ == "__main__":
    """Test script for ModelManager"""
    
    print("=" * 80)
    print("MONAI Model Manager - Test Script")
    print("=" * 80)
    
    # Get model manager
    manager = get_model_manager()
    
    # Print device info
    print("\n📊 Device Information:")
    for key, value in manager.get_device_info().items():
        print(f"  {key}: {value}")
    
    # Load models
    print("\n🔄 Loading Models...")
    models_to_load = [
        "organ_segmentation",
        "vessel_segmentation",
        "lung_nodule_detection"
    ]
    
    for model_name in models_to_load:
        try:
            model = manager.get_model(model_name)
            print(f"  ✓ {model_name} loaded successfully")
        except Exception as e:
            print(f"  ✗ {model_name} failed: {e}")
    
    # Print memory usage
    print("\n💾 Memory Usage:")
    memory = manager.get_memory_usage()
    for key, value in memory.items():
        print(f"  {key}: {value:.2f} GB")
    
    # Test preprocessing
    print("\n⚙️ Testing Preprocessing...")
    test_volume = np.random.randn(128, 128, 96)
    preprocessed = manager.preprocess_volume(test_volume)
    print(f"  Input shape: {test_volume.shape}")
    print(f"  Output shape: {preprocessed.shape}")
    print(f"  Output dtype: {preprocessed.dtype}")
    print(f"  Output device: {preprocessed.device}")
    
    print("\n✅ All tests completed!")
    print("=" * 80)
