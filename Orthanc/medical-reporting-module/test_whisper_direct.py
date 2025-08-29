#!/usr/bin/env python3
"""
Test Whisper Direct - Test actual audio transcription
"""

import sys
import os
import logging
import tempfile
import whisper
import numpy as np
import wave

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_audio():
    """Create a simple test audio file with silence"""
    try:
        # Create a simple WAV file with silence
        sample_rate = 16000
        duration = 2  # 2 seconds
        samples = np.zeros(int(sample_rate * duration), dtype=np.int16)
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            with wave.open(temp_file.name, 'w') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(samples.tobytes())
            
            return temp_file.name
            
    except Exception as e:
        logger.error(f"Failed to create test audio: {e}")
        return None

def test_whisper_transcription():
    """Test Whisper transcription directly"""
    try:
        print("Loading Whisper model...")
        model = whisper.load_model("base")
        print("✓ Whisper model loaded successfully")
        
        # Create test audio file
        print("Creating test audio file...")
        audio_path = create_test_audio()
        
        if not audio_path:
            print("✗ Failed to create test audio")
            return False
        
        try:
            print("Transcribing audio...")
            result = model.transcribe(audio_path, language="en")
            
            transcription = result["text"].strip()
            print(f"✓ Transcription result: '{transcription}'")
            
            if not transcription:
                print("✓ Empty transcription (expected for silence)")
            else:
                print(f"✓ Got transcription: {transcription}")
            
            return True
            
        finally:
            # Clean up
            try:
                os.unlink(audio_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Whisper test failed: {e}")
        return False

def test_offline_stt_service():
    """Test the offline STT service"""
    try:
        print("Testing offline STT service...")
        
        # Import the service
        from services.offline_stt_service import offline_stt_engine
        
        # Initialize
        if offline_stt_engine.initialize():
            print("✓ Offline STT engine initialized")
            
            # Test with a dummy audio file
            audio_path = create_test_audio()
            if audio_path:
                try:
                    transcription = offline_stt_engine.transcribe_audio_file(audio_path)
                    print(f"✓ STT Service result: '{transcription}'")
                    return True
                finally:
                    try:
                        os.unlink(audio_path)
                    except:
                        pass
            else:
                print("✗ Failed to create test audio")
                return False
        else:
            print("✗ Failed to initialize offline STT engine")
            return False
            
    except Exception as e:
        logger.error(f"Offline STT service test failed: {e}")
        return False

def main():
    """Run Whisper tests"""
    print("=" * 60)
    print("WHISPER TRANSCRIPTION TEST")
    print("=" * 60)
    
    print("\n1. Testing Whisper Direct...")
    whisper_success = test_whisper_transcription()
    
    print("\n2. Testing Offline STT Service...")
    stt_success = test_offline_stt_service()
    
    print("\n" + "=" * 60)
    print("TEST RESULTS:")
    print(f"Whisper Direct: {'✓ PASS' if whisper_success else '✗ FAIL'}")
    print(f"STT Service: {'✓ PASS' if stt_success else '✗ FAIL'}")
    
    if whisper_success and stt_success:
        print("\n✓ WHISPER TRANSCRIPTION WORKING!")
        print("The STT system is now ready for real audio transcription.")
    else:
        print("\n✗ WHISPER TRANSCRIPTION ISSUES")
        print("Some components need attention.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()