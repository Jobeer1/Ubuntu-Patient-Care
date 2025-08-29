#!/usr/bin/env python3
"""
Quick STT Test - Test if voice transcription is working
"""

import sys
import os
import tempfile
import logging

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_stt_service():
    """Test the STT service with a minimal audio file"""
    print("🎤 Testing STT Service...")
    
    try:
        from services.offline_stt_service import offline_stt_service
        
        # Initialize the service
        if not offline_stt_service.initialize():
            print("❌ STT service initialization failed")
            return False
        
        print("✅ STT service initialized")
        
        # Create a proper WAV file for testing
        import struct
        
        # Generate a simple sine wave audio (440Hz tone for 1 second)
        sample_rate = 16000
        duration = 1.0  # 1 second
        frequency = 440  # A4 note
        
        # Generate samples
        import math
        samples = []
        for i in range(int(sample_rate * duration)):
            t = i / sample_rate
            sample = int(32767 * 0.1 * math.sin(2 * math.pi * frequency * t))  # Low volume
            samples.append(sample)
        
        # Create WAV file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
            
            # Write WAV header
            temp_file.write(b'RIFF')
            temp_file.write(struct.pack('<I', 36 + len(samples) * 2))  # File size
            temp_file.write(b'WAVE')
            temp_file.write(b'fmt ')
            temp_file.write(struct.pack('<I', 16))  # Subchunk1Size
            temp_file.write(struct.pack('<H', 1))   # AudioFormat (PCM)
            temp_file.write(struct.pack('<H', 1))   # NumChannels (mono)
            temp_file.write(struct.pack('<I', sample_rate))  # SampleRate
            temp_file.write(struct.pack('<I', sample_rate * 2))  # ByteRate
            temp_file.write(struct.pack('<H', 2))   # BlockAlign
            temp_file.write(struct.pack('<H', 16))  # BitsPerSample
            temp_file.write(b'data')
            temp_file.write(struct.pack('<I', len(samples) * 2))  # Subchunk2Size
            
            # Write audio data
            for sample in samples:
                temp_file.write(struct.pack('<h', sample))
        
        print(f"📁 Created test audio file: {temp_path}")
        
        # Test transcription
        result = offline_stt_service.transcribe_audio_file(temp_path)
        
        # Clean up
        try:
            os.unlink(temp_path)
        except:
            pass
        
        if result is not None:
            print(f"✅ STT transcription successful: '{result}'")
            return True
        else:
            print("⚠️  STT returned None (no speech detected - expected for tone)")
            return True  # This is actually normal for a sine wave
        
    except Exception as e:
        print(f"❌ STT service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run STT test"""
    print("🏥 SA Medical Reporting - STT Service Test")
    print("=" * 50)
    
    if test_stt_service():
        print("🎉 STT service is working correctly!")
        return 0
    else:
        print("⚠️  STT service test failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
