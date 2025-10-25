#!/usr/bin/env python3
"""
Test script to verify STT system is working properly
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

def test_ffmpeg():
    """Test FFmpeg availability"""
    print("🔧 Testing FFmpeg...")
    
    # Add local ffmpeg to PATH
    local_ffmpeg = Path("ffmpeg")
    if local_ffmpeg.exists():
        ffmpeg_dir = str(local_ffmpeg.absolute())
        current_path = os.environ.get('PATH', '')
        if ffmpeg_dir not in current_path:
            os.environ['PATH'] = ffmpeg_dir + os.pathsep + current_path
            print(f"✅ Added FFmpeg to PATH: {ffmpeg_dir}")
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ FFmpeg is working correctly")
            return True
        else:
            print(f"❌ FFmpeg failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ FFmpeg test failed: {e}")
        return False

def test_whisper():
    """Test Whisper availability"""
    print("🎤 Testing Whisper...")
    
    try:
        import whisper
        print("✅ Whisper module imported successfully")
        
        # Try to load model
        model = whisper.load_model("base")
        print("✅ Whisper model loaded successfully")
        
        return True
    except ImportError:
        print("❌ Whisper not installed - run: pip install openai-whisper")
        return False
    except Exception as e:
        print(f"❌ Whisper test failed: {e}")
        return False

def test_audio_conversion():
    """Test audio conversion functionality"""
    print("🔄 Testing audio conversion...")
    
    try:
        # Create a simple test WAV file
        import numpy as np
        import wave
        
        # Generate 1 second of sine wave at 440Hz
        sample_rate = 16000
        duration = 1.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t)
        
        # Convert to 16-bit integers
        audio_data = (audio_data * 32767).astype(np.int16)
        
        # Create temporary WAV file
        temp_fd, temp_wav = tempfile.mkstemp(suffix='.wav')
        os.close(temp_fd)
        
        try:
            with wave.open(temp_wav, 'w') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.tobytes())
            
            print(f"✅ Created test WAV file: {temp_wav}")
            
            # Test if Whisper can process it
            if test_whisper_processing(temp_wav):
                print("✅ Audio conversion test passed")
                return True
            else:
                print("❌ Audio conversion test failed")
                return False
                
        finally:
            try:
                os.unlink(temp_wav)
            except:
                pass
                
    except Exception as e:
        print(f"❌ Audio conversion test failed: {e}")
        return False

def test_whisper_processing(wav_file):
    """Test Whisper processing of WAV file"""
    try:
        import whisper
        
        model = whisper.load_model("base")
        result = model.transcribe(wav_file)
        
        print(f"✅ Whisper processed audio successfully")
        print(f"   Transcription: '{result['text']}'")
        return True
        
    except Exception as e:
        print(f"❌ Whisper processing failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 STT System Test Suite")
    print("=" * 40)
    
    tests = [
        ("FFmpeg", test_ffmpeg),
        ("Whisper", test_whisper),
        ("Audio Conversion", test_audio_conversion)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 40)
    print("📊 Test Results:")
    
    all_passed = True
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if not success:
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 All tests passed! STT system should work correctly.")
    else:
        print("⚠️  Some tests failed. STT system may not work properly.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)