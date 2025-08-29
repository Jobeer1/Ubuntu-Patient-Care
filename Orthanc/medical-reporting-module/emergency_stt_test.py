#!/usr/bin/env python3
"""
EMERGENCY STT TEST - Validate Windows file handling fixes
"""

import tempfile
import os
import sys

def test_file_handling():
    """Test the exact file handling approach used in voice_api.py"""
    print("🔧 Testing Emergency STT File Handling...")
    
    try:
        # Test 1: Create temp file with mkstemp (same as voice_api.py)
        temp_fd, temp_audio_path = tempfile.mkstemp(suffix='.wav', prefix='voice_')
        print(f"✅ Temp file created: {temp_audio_path}")
        
        # Test 2: Close file descriptor immediately
        os.close(temp_fd)
        print(f"✅ File descriptor closed immediately")
        
        # Test 3: Write dummy audio data
        dummy_audio = b'RIFF' + b'\x00' * 100  # Minimal WAV-like data
        with open(temp_audio_path, 'wb') as f:
            f.write(dummy_audio)
        print(f"✅ Audio data written: {len(dummy_audio)} bytes")
        
        # Test 4: Verify file accessibility
        if os.path.exists(temp_audio_path):
            file_size = os.path.getsize(temp_audio_path)
            print(f"✅ File accessible: {file_size} bytes")
        else:
            print("❌ File not accessible")
            return False
        
        # Test 5: Read file back
        with open(temp_audio_path, 'rb') as f:
            read_data = f.read()
        print(f"✅ File read successfully: {len(read_data)} bytes")
        
        # Test 6: Clean up
        os.unlink(temp_audio_path)
        print(f"✅ Temp file cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ File handling test failed: {e}")
        return False

def test_whisper_import():
    """Test if Whisper can be imported"""
    print("\n🎤 Testing Whisper Import...")
    
    try:
        import whisper
        print("✅ Whisper imported successfully")
        
        # Try to load tiny model
        print("Loading tiny model...")
        model = whisper.load_model("tiny")
        print("✅ Whisper tiny model loaded successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Whisper import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Whisper model loading failed: {e}")
        return False

def main():
    """Run emergency STT tests"""
    print("=" * 60)
    print("🏥 EMERGENCY STT VALIDATION TEST")
    print("=" * 60)
    
    # Test file handling
    file_test_passed = test_file_handling()
    
    # Test Whisper
    whisper_test_passed = test_whisper_import()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print("=" * 60)
    print(f"File Handling: {'✅ PASS' if file_test_passed else '❌ FAIL'}")
    print(f"Whisper Import: {'✅ PASS' if whisper_test_passed else '❌ FAIL'}")
    
    if file_test_passed and whisper_test_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("💡 STT should now work correctly")
        print("🔄 Restart the app if it's running")
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("🔧 Check the error messages above")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
