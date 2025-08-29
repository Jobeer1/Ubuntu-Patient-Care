#!/usr/bin/env python3
"""
WHISPER DIRECT TEST - Test Whisper functionality directly
"""

def test_whisper_directly():
    """Test Whisper import and basic functionality"""
    print("🎤 Testing Whisper Direct Import...")
    
    try:
        import whisper
        print("✅ Whisper imported successfully")
        
        # Test loading tiny model
        print("Loading tiny model...")
        model = whisper.load_model("tiny")
        print("✅ Tiny model loaded successfully")
        
        # Create a simple test audio file
        import tempfile
        import os
        import numpy as np
        import wave
        
        # Create a simple sine wave as test audio
        sample_rate = 16000
        duration = 1  # 1 second
        frequency = 440  # A4 note
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave_data = np.sin(frequency * 2 * np.pi * t) * 0.3
        
        # Convert to 16-bit PCM
        wave_data_int = (wave_data * 32767).astype(np.int16)
        
        # Create temp WAV file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.wav', prefix='whisper_test_')
        os.close(temp_fd)
        
        # Write WAV file
        with wave.open(temp_path, 'w') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 2 bytes per sample
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(wave_data_int.tobytes())
        
        print(f"✅ Test audio file created: {temp_path}")
        print(f"File size: {os.path.getsize(temp_path)} bytes")
        
        # Test Whisper transcription
        print("Testing Whisper transcription...")
        result = model.transcribe(temp_path, language="en", fp16=False)
        
        print(f"✅ Whisper transcription completed")
        print(f"Result: '{result['text']}'")
        
        # Clean up
        os.unlink(temp_path)
        print("✅ Test file cleaned up")
        
        return True
        
    except ImportError as e:
        print(f"❌ Whisper import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Whisper test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🔧 WHISPER DIRECT TEST")
    print("=" * 50)
    
    success = test_whisper_directly()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 WHISPER WORKING CORRECTLY!")
    else:
        print("❌ WHISPER ISSUES DETECTED")
    print("=" * 50)
