#!/usr/bin/env python3
"""
Test the STT endpoint with a simple audio file
"""

import os
import sys
import tempfile
import logging
import requests
import numpy as np
import soundfile as sf

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_audio():
    """Create a simple test audio file"""
    try:
        # Generate a simple sine wave (440 Hz for 2 seconds)
        sample_rate = 16000
        duration = 2.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = 0.3 * np.sin(2 * np.pi * frequency * t)
        
        # Save as WAV file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.wav')
        os.close(temp_fd)
        
        sf.write(temp_path, audio_data, sample_rate)
        
        logger.info(f"✅ Created test audio file: {temp_path}")
        return temp_path
        
    except Exception as e:
        logger.error(f"❌ Failed to create test audio: {e}")
        return None

def test_transcription_endpoint(audio_file_path):
    """Test the transcription endpoint"""
    try:
        # Test the chunk transcription endpoint
        url = 'http://localhost:5443/api/voice/transcribe-chunk'
        
        with open(audio_file_path, 'rb') as f:
            files = {'audio': (os.path.basename(audio_file_path), f, 'audio/wav')}
            data = {
                'session_id': 'test_session',
                'chunk_id': 'test_chunk_1',
                'sequence_number': '0'
            }
            
            logger.info(f"🚀 Testing transcription endpoint: {url}")
            response = requests.post(url, files=files, data=data, verify=False, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Transcription successful: {result}")
                return True
            else:
                logger.error(f"❌ Transcription failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Endpoint test failed: {e}")
        return False

def main():
    """Run the endpoint test"""
    logger.info("🧪 Testing STT endpoint...")
    
    # Create test audio
    audio_file = create_test_audio()
    if not audio_file:
        return False
    
    try:
        # Test the endpoint
        success = test_transcription_endpoint(audio_file)
        
        if success:
            logger.info("🎉 STT endpoint test passed!")
        else:
            logger.error("❌ STT endpoint test failed!")
            
        return success
        
    finally:
        # Clean up
        if audio_file and os.path.exists(audio_file):
            os.unlink(audio_file)
            logger.info("🧹 Cleaned up test audio file")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)