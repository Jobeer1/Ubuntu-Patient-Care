#!/usr/bin/env python3
"""
Test actual voice transcription functionality
"""

import sys
import os
import numpy as np
import wave
import tempfile
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.offline_stt_service import OfflineSTTEngine, STTConfig, STTMode

def create_test_audio():
    """Create a simple test audio file (silence for testing)"""
    # Create 2 seconds of silence at 16kHz
    sample_rate = 16000
    duration = 2.0
    samples = int(sample_rate * duration)
    
    # Generate some simple audio (sine wave for testing)
    t = np.linspace(0, duration, samples, False)
    audio_data = np.sin(2 * np.pi * 440 * t) * 0.1  # 440Hz tone, low volume
    
    # Convert to 16-bit PCM
    audio_data = (audio_data * 32767).astype(np.int16)
    
    # Save to temporary WAV file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    with wave.open(temp_file.name, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    return temp_file.name

def test_voice_transcription():
    """Test actual voice transcription"""
    print("Testing voice transcription with Whisper...")
    
    config = STTConfig(
        mode=STTMode.OFFLINE_ONLY,
        model_size="base",
        enable_medical_terminology=True
    )
    
    engine = OfflineSTTEngine(config)
    
    # Initialize engine
    if not engine.initialize():
        print("✗ Failed to initialize engine")
        return False
    
    print("✓ Engine initialized")
    
    # Create test audio
    audio_file = create_test_audio()
    print(f"✓ Created test audio: {audio_file}")
    
    try:
        # Read audio file
        with open(audio_file, 'rb') as f:
            audio_data = f.read()
        
        print("✓ Audio file read successfully")
        
        # Transcribe audio
        result = engine.transcribe_audio(audio_data, "test_user")
        
        if result:
            print(f"✓ Transcription successful!")
            print(f"  Text: '{result.text}'")
            print(f"  Confidence: {result.confidence}")
            print(f"  Quality: {result.audio_quality}")
            print(f"  Processing time: {result.processing_time_ms}ms")
            return True
        else:
            print("✗ Transcription failed")
            return False
            
    except Exception as e:
        print(f"✗ Error during transcription: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists(audio_file):
            os.unlink(audio_file)

if __name__ == "__main__":
    success = test_voice_transcription()
    if success:
        print("\n🎉 Voice transcription test PASSED!")
    else:
        print("\n❌ Voice transcription test FAILED!")