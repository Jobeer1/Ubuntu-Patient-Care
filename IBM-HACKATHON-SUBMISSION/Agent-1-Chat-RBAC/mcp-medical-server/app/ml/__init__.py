"""Machine Learning Module for Medical Document Processing

This module provides lightweight, offline-capable ML models for:
- Speech recognition (Whisper)
- Face recognition (facial identification)
- Optical character recognition (Tesseract)
- Document processing pipeline (combines all three)
"""

from app.ml.speech_recognition import SpeechRecognitionService
from app.ml.face_recognition_service import FaceRecognitionService
from app.ml.ocr_service import OCRService
from app.ml.document_processing import DocumentProcessingPipeline

__all__ = [
    "SpeechRecognitionService",
    "FaceRecognitionService",
    "OCRService",
    "DocumentProcessingPipeline"
]

# Initialize services
speech_service = SpeechRecognitionService()
face_service = FaceRecognitionService()
ocr_service = OCRService()
pipeline = DocumentProcessingPipeline()
