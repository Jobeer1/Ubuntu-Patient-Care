#!/usr/bin/env python3
"""
Test script to diagnose and fix Whisper model loading issues
"""

import os
import sys
import logging
from pathlib import Path

# Add the medical-reporting-module to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_whisper_installation():
    """Test if Whisper is properly installed"""
    try:
        import whisper
        logger.info("✅ OpenAI Whisper is installed")
        
        # Check available models
        available_models = whisper.available_models()
        logger.info(f"Available Whisper models: {available_models}")
        
        return True
    except ImportError as e:
        logger.error(f"❌ OpenAI Whisper not installed: {e}")
        logger.info("Install with: pip install openai-whisper")
        return False

def test_model_file():
    """Test if the model file exists and is valid"""
    try:
        model_path = Path("models/whisper/base.pt")
        
        if not model_path.exists():
            logger.error(f"❌ Model file does not exist: {model_path}")
            return False
        
        file_size = model_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        logger.info(f"✅ Model file exists: {model_path}")
        logger.info(f"File size: {file_size_mb:.1f} MB")
        
        # Expected size for base model is around 142MB
        if 130 <= file_size_mb <= 160:
            logger.info("✅ File size looks correct for base model")
            return True
        else:
            logger.warning(f"⚠️ File size seems unusual for base model (expected ~142MB)")
            return True  # Still try to load it
            
    except Exception as e:
        logger.error(f"❌ Error checking model file: {e}")
        return False

def test_model_loading():
    """Test loading the Whisper model"""
    try:
        import whisper
        
        model_path = Path("models/whisper/base.pt")
        logger.info(f"Attempting to load model from: {model_path}")
        
        # Try to load the model
        model = whisper.load_model(str(model_path))
        logger.info("✅ Model loaded successfully!")
        
        # Test transcription with a simple audio file (if available)
        logger.info("Model type: " + str(type(model)))
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        return False

def test_whisper_model_manager():
    """Test our custom Whisper model manager"""
    try:
        from services.whisper_model_manager import whisper_model_manager, ModelSize
        
        logger.info("Testing Whisper model manager...")
        
        # Check system specs
        system_specs = whisper_model_manager.get_system_specs()
        logger.info(f"System specs: {system_specs}")
        
        # Check if model exists
        model_exists = whisper_model_manager.check_model_exists(ModelSize.BASE)
        logger.info(f"Model exists check: {model_exists}")
        
        # Validate model integrity
        model_valid = whisper_model_manager.validate_model_integrity(ModelSize.BASE)
        logger.info(f"Model integrity check: {model_valid}")
        
        # Try to set up environment
        success, model_size = whisper_model_manager.setup_whisper_environment(ModelSize.BASE)
        logger.info(f"Environment setup: success={success}, model_size={model_size}")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error testing model manager: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_offline_stt_service():
    """Test the offline STT service"""
    try:
        from services.offline_stt_service import offline_stt_engine
        
        logger.info("Testing offline STT service...")
        
        # Try to initialize
        success = offline_stt_engine.initialize()
        logger.info(f"STT engine initialization: {success}")
        
        if success:
            logger.info("✅ Offline STT service initialized successfully!")
            
            # Get stats
            stats = offline_stt_engine.get_stats()
            logger.info(f"STT stats: {stats}")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ Error testing STT service: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    logger.info("🔍 Starting Whisper diagnostics...")
    
    # Test 1: Whisper installation
    logger.info("\n" + "="*50)
    logger.info("TEST 1: Whisper Installation")
    logger.info("="*50)
    whisper_installed = test_whisper_installation()
    
    if not whisper_installed:
        logger.error("❌ Cannot proceed without Whisper installation")
        return False
    
    # Test 2: Model file
    logger.info("\n" + "="*50)
    logger.info("TEST 2: Model File Check")
    logger.info("="*50)
    model_file_ok = test_model_file()
    
    # Test 3: Model loading
    logger.info("\n" + "="*50)
    logger.info("TEST 3: Model Loading")
    logger.info("="*50)
    model_loading_ok = test_model_loading()
    
    # Test 4: Model manager
    logger.info("\n" + "="*50)
    logger.info("TEST 4: Whisper Model Manager")
    logger.info("="*50)
    model_manager_ok = test_whisper_model_manager()
    
    # Test 5: STT service
    logger.info("\n" + "="*50)
    logger.info("TEST 5: Offline STT Service")
    logger.info("="*50)
    stt_service_ok = test_offline_stt_service()
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("SUMMARY")
    logger.info("="*50)
    logger.info(f"Whisper installed: {'✅' if whisper_installed else '❌'}")
    logger.info(f"Model file OK: {'✅' if model_file_ok else '❌'}")
    logger.info(f"Model loading OK: {'✅' if model_loading_ok else '❌'}")
    logger.info(f"Model manager OK: {'✅' if model_manager_ok else '❌'}")
    logger.info(f"STT service OK: {'✅' if stt_service_ok else '❌'}")
    
    all_ok = all([whisper_installed, model_file_ok, model_loading_ok, model_manager_ok, stt_service_ok])
    
    if all_ok:
        logger.info("🎉 All tests passed! Whisper should be working.")
    else:
        logger.error("❌ Some tests failed. Check the logs above for details.")
    
    return all_ok

if __name__ == "__main__":
    main()