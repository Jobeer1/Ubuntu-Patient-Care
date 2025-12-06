#!/usr/bin/env python3
"""
Test script to verify Whisper installation and audio processing
"""

import os
import sys
import tempfile
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_whisper_installation():
    """Test if Whisper is properly installed"""
    try:
        import whisper
        logger.info("✅ Whisper module imported successfully")
        
        # Try to load the base model
        logger.info("Loading Whisper base model...")
        model = whisper.load_model("base")
        logger.info("✅ Whisper model loaded successfully")
        
        return model
    except ImportError as e:
        logger.error(f"❌ Whisper not installed: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Failed to load Whisper model: {e}")
        return None

def test_audio_file_handling():
    """Test temporary file creation and handling"""
    try:
        # Test WebM file creation
        temp_fd, temp_path = tempfile.mkstemp(suffix='.webm')
        os.close(temp_fd)
        
        # Write some dummy data
        with open(temp_path, 'wb') as f:
            f.write(b'dummy audio data')
        
        # Check file exists and has content
        if os.path.exists(temp_path):
            size = os.path.getsize(temp_path)
            logger.info(f"✅ Temporary file created: {temp_path} ({size} bytes)")
            
            # Clean up
            os.unlink(temp_path)
            logger.info("✅ Temporary file cleaned up successfully")
            return True
        else:
            logger.error("❌ Temporary file not found after creation")
            return False
            
    except Exception as e:
        logger.error(f"❌ File handling test failed: {e}")
        return False

def test_dependencies():
    """Test required dependencies"""
    dependencies = ['numpy', 'soundfile', 'librosa']
    
    for dep in dependencies:
        try:
            __import__(dep)
            logger.info(f"✅ {dep} imported successfully")
        except ImportError:
            logger.warning(f"⚠️ {dep} not available (optional)")
        except Exception as e:
            logger.error(f"❌ {dep} import failed: {e}")

def main():
    """Run all tests"""
    logger.info("🧪 Starting Whisper and audio processing tests...")
    
    # Test dependencies
    logger.info("\n📦 Testing dependencies...")
    test_dependencies()
    
    # Test file handling
    logger.info("\n📁 Testing file handling...")
    file_test = test_audio_file_handling()
    
    # Test Whisper
    logger.info("\n🎤 Testing Whisper installation...")
    model = test_whisper_installation()
    
    # Summary
    logger.info("\n📋 Test Summary:")
    logger.info(f"File handling: {'✅ PASS' if file_test else '❌ FAIL'}")
    logger.info(f"Whisper model: {'✅ PASS' if model else '❌ FAIL'}")
    
    if model and file_test:
        logger.info("🎉 All tests passed! STT should work correctly.")
        return True
    else:
        logger.error("❌ Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)