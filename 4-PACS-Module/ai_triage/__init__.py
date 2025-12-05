"""
AI Triage Pipeline for Ultra-Low Bandwidth Teleradiology

This module implements an AI-driven data economy solution that reduces
medical imaging data transfer by >90% while maintaining diagnostic quality.
"""

__version__ = "0.1.0"
__author__ = "Ubuntu Patient Care Community"
__license__ = "MIT"

try:
    from .model_manager import CNNModelManager
    __all__ = ["CNNModelManager"]
except ImportError:
    # Allow importing the package even if dependencies (like onnxruntime) are missing
    # This is useful for testing independent components like DicomProcessor
    CNNModelManager = None
    __all__ = []
