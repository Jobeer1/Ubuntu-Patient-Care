#!/usr/bin/env python3
"""
Test WebM audio processing without FFmpeg
"""

import os
import sys
import tempfile
import logging
import numpy as np
import soundfile as sf

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_webm():
    """Create a test WebM-like audio file (actually WAV for testing)"""
    try:
        # Generate a simple sine wave
        sample_rate = 16000
        duration = 2.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = 0.3 * np.sin(2 * np.pi * frequency * t)
        
        # Save as WAV file (simulating WebM for testing)
        temp_fd, temp_path = tempfile.mkstemp(suffix='.wav')
        os.close(temp_fd)
        
        sf.write(temp_path, audio_data, sample_rate)
        
        logger.info(f"✅ Created test audio file: {temp_path}")
        return temp_path
        
    except Exception as e:
        logger.error(f"❌ Failed to create test audio: {e}")
        return None

def test_webm_conversion(audio_file_path):
    """Test the WebM conversion function"""
    try:
        # Import the conversion function from voice_api
        sys.path.append('.')
        from api.voice_api import convert_webm_to_numpy
        
        logger.info(f"🔄 Testing WebM conversion on: {audio_file_path}")
        
        # Test the conversion
        audio_data = convert_webm_to_numpy(audio_file_path)
        
        if len(audio_data) > 0:
            logger.info(f"✅ Conversion successful: {len(audio_data)} samples, dtype: {audio_data.dtype}")
            return True
        else:
            logger.error("❌ Conversion returned empty array")
            return False
            
    except Exception as e:
        logger.error(f"❌ Conversion test failed: {e}")
        return False

def test_whisper_with_numpy():
    """Test Whisper with numpy array input"""
    try:
        import whisper
        
        # Load Whisper model
        logger.info("🎤 Loading Whisper model...")
        model = whisper.load_model("base")
        
        # Create test audio data
        sample_rate = 16000
        duration = 1.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = 0.1 * np.sin(2 * np.pi * frequency * t).astype(np.float32)
        
        logger.info(f"🔄 Testing Whisper with numpy array: {len(audio_data)} samples")
        
        # Test transcription
        result = model.transcribe(audio_data, language="en")
        transcription = result["text"].strip()
        
        logger.info(f"✅ Whisper transcription successful: '{transcription}'")
        return True
        
    except Exception as e:
        logger.error(f"❌ Whisper numpy test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🧪 Testing WebM processing fix...")
    
    # Create test audio
    audio_file = create_test_webm()
    if not audio_file:
        return False
    
    try:
        # Test conversion
        conversion_success = test_webm_conversion(audio_file)
        
        # Test Whisper with numpy
        whisper_success = test_whisper_with_numpy()
        
        # Summary
        logger.info("\n📋 Test Summary:")
        logger.info(f"WebM conversion: {'✅ PASS' if conversion_success else '❌ FAIL'}")
        logger.info(f"Whisper numpy: {'✅ PASS' if whisper_success else '❌ FAIL'}")
        
        if conversion_success and whisper_success:
            logger.info("🎉 All tests passed! WebM processing should work without FFmpeg.")
            return True
        else:
            logger.error("❌ Some tests failed. Check the errors above.")
            return False
            
    finally:
        # Clean up
        if audio_file and os.path.exists(audio_file):
            os.unlink(audio_file)
            logger.info("🧹 Cleaned up test audio file")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)