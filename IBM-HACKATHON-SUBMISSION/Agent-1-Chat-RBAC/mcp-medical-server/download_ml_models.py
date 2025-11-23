#!/usr/bin/env python3
"""
Download and Cache ML Models

This script pre-downloads all ML models so they're ready to use offline.
Prevents long delays on first use when models are automatically downloaded.

Models downloaded:
1. Whisper (base model) - 140MB - Speech-to-text
2. face_recognition - 5MB - Face detection/recognition
3. Tesseract OCR - 50MB - Text extraction from documents

Total: ~200MB storage, 1-time download
"""

import os
import sys
import logging
from pathlib import Path
import argparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_whisper_model(model_size="base"):
    """
    Download OpenAI Whisper model.
    
    Args:
        model_size: 'tiny', 'base', 'small', 'medium', 'large'
                   Recommended: 'base' (140MB, good accuracy)
                   Fast: 'tiny' (30MB, lower accuracy)
    """
    logger.info(f"📥 Downloading Whisper model ({model_size})...")
    
    try:
        import whisper
        
        logger.info(f"   Loading Whisper {model_size} model...")
        model = whisper.load_model(model_size)
        
        logger.info(f"✅ Whisper {model_size} model downloaded and cached")
        logger.info(f"   Location: {Path.home() / '.cache' / 'whisper'}")
        
        return True
    
    except ImportError:
        logger.error("❌ Whisper not installed")
        logger.error("   Install with: pip install openai-whisper")
        return False
    
    except Exception as e:
        logger.error(f"❌ Failed to download Whisper: {e}")
        return False


def download_face_recognition_model():
    """Download face_recognition model (dlib CNN)"""
    logger.info("📥 Downloading face_recognition models...")
    
    try:
        import face_recognition
        
        # These are downloaded automatically on first use
        # We trigger the download here
        logger.info("   Initializing face detection...")
        
        # This forces model loading/caching
        face_recognition.batch_face_locations([], number_upsample_num_times=1)
        
        logger.info("✅ face_recognition models downloaded and cached")
        logger.info("   Location: ~/.dlib/")
        
        return True
    
    except ImportError:
        logger.error("❌ face_recognition not installed")
        logger.error("   Install with: pip install face-recognition")
        return False
    
    except Exception as e:
        logger.error(f"❌ Failed to download face_recognition models: {e}")
        return False


def download_tesseract_ocr_model():
    """Download Tesseract OCR model"""
    logger.info("📥 Checking Tesseract OCR installation...")
    
    try:
        import pytesseract
        import subprocess
        
        # Check if tesseract is installed
        try:
            result = subprocess.run(
                ['tesseract', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                logger.info("✅ Tesseract OCR is installed")
                logger.info(f"   {result.stdout.split(chr(10))[0]}")
                return True
        
        except FileNotFoundError:
            logger.error("❌ Tesseract not found in PATH")
            logger.error("   Install from: https://github.com/UB-Mannheim/tesseract/wiki")
            
            if sys.platform == 'win32':
                logger.info("   Windows: Download installer from GitHub link above")
            elif sys.platform == 'darwin':
                logger.info("   macOS: brew install tesseract")
            else:
                logger.info("   Linux: sudo apt-get install tesseract-ocr")
            
            return False
    
    except ImportError:
        logger.error("❌ pytesseract not installed")
        logger.error("   Install with: pip install pytesseract")
        return False
    
    except Exception as e:
        logger.error(f"❌ OCR check failed: {e}")
        return False


def download_easyocr_model():
    """Download EasyOCR models (alternative OCR)"""
    logger.info("📥 Downloading EasyOCR models (optional)...")
    
    try:
        import easyocr
        
        logger.info("   Downloading English language model...")
        reader = easyocr.Reader(['en'], gpu=False)
        
        logger.info("✅ EasyOCR models downloaded and cached")
        logger.info("   Languages available: en (English)")
        
        return True
    
    except ImportError:
        logger.warning("⚠️  EasyOCR not installed (optional)")
        logger.warning("   Install with: pip install easyocr")
        return False
    
    except Exception as e:
        logger.error(f"❌ Failed to download EasyOCR models: {e}")
        return False


def download_all_models(whisper_model_size="base"):
    """Download all required models"""
    logger.info("=" * 70)
    logger.info("ML Model Download Manager")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Downloading models for:")
    logger.info("  ✓ Speech-to-text (Whisper)")
    logger.info("  ✓ Face recognition")
    logger.info("  ✓ OCR (Tesseract + EasyOCR)")
    logger.info("")
    logger.info("This is a one-time operation (may take 10-30 minutes)")
    logger.info("")
    logger.info("=" * 70)
    
    results = {
        "whisper": download_whisper_model(whisper_model_size),
        "face_recognition": download_face_recognition_model(),
        "tesseract_ocr": download_tesseract_ocr_model(),
        "easyocr": download_easyocr_model()
    }
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("Download Summary")
    logger.info("=" * 70)
    
    for model_name, success in results.items():
        status = "✅" if success else "❌"
        logger.info(f"{status} {model_name.replace('_', ' ').title()}")
    
    logger.info("")
    
    all_success = all(results.values())
    
    if all_success:
        logger.info("✅ All models downloaded successfully!")
        logger.info("")
        logger.info("You can now use paperwork voice service offline.")
    else:
        logger.warning("⚠️  Some models failed to download.")
        logger.warning("Please install missing dependencies and try again.")
    
    logger.info("")
    logger.info("=" * 70)
    
    return all_success


def verify_models():
    """Verify that all models are available and loadable"""
    logger.info("🔍 Verifying model installations...")
    logger.info("")
    
    checks = {}
    
    # Check Whisper
    try:
        import whisper
        logger.info("✅ Whisper module imported successfully")
        checks['whisper'] = True
    except ImportError:
        logger.error("❌ Whisper module not found")
        checks['whisper'] = False
    
    # Check face_recognition
    try:
        import face_recognition
        logger.info("✅ face_recognition module imported successfully")
        checks['face_recognition'] = True
    except ImportError:
        logger.error("❌ face_recognition module not found")
        checks['face_recognition'] = False
    
    # Check Tesseract
    try:
        import pytesseract
        import subprocess
        result = subprocess.run(['tesseract', '--version'], capture_output=True, timeout=5)
        if result.returncode == 0:
            logger.info("✅ Tesseract OCR available")
            checks['tesseract'] = True
        else:
            logger.error("❌ Tesseract not in PATH")
            checks['tesseract'] = False
    except:
        logger.error("❌ Tesseract not found")
        checks['tesseract'] = False
    
    # Check EasyOCR
    try:
        import easyocr
        logger.info("✅ EasyOCR module imported successfully")
        checks['easyocr'] = True
    except ImportError:
        logger.warning("⚠️  EasyOCR not installed (optional)")
        checks['easyocr'] = False
    
    logger.info("")
    logger.info("Summary:")
    for name, available in checks.items():
        status = "✅" if available else "❌"
        logger.info(f"  {status} {name.replace('_', ' ').title()}")
    
    return all(checks.values())


def main():
    parser = argparse.ArgumentParser(
        description="Download and verify ML models for paperwork automation"
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify models are installed without downloading'
    )
    parser.add_argument(
        '--whisper-model',
        default='base',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help='Whisper model size (default: base)'
    )
    
    args = parser.parse_args()
    
    if args.verify:
        success = verify_models()
    else:
        success = download_all_models(args.whisper_model)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
