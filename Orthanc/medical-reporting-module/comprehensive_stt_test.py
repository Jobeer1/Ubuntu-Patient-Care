#!/usr/bin/env python3
"""
COMPREHENSIVE STT FIX TEST - All-in-one validation
"""

import tempfile
import os
import sys
import time

def test_complete_pipeline():
    """Test the complete audio processing pipeline"""
    print("🔧 Testing Complete STT Pipeline...")
    
    try:
        # Step 1: Test file creation (same as voice_api.py)
        temp_fd, temp_audio_path = tempfile.mkstemp(suffix='.wav', prefix='voice_')
        os.close(temp_fd)
        
        # Create stable directory and path
        stable_dir = os.path.join(os.path.dirname(temp_audio_path), 'whisper_audio')
        os.makedirs(stable_dir, exist_ok=True)
        stable_audio_path = os.path.join(stable_dir, f"audio_{os.getpid()}_{int(time.time())}.wav")
        
        print(f"✅ Temp path: {temp_audio_path}")
        print(f"✅ Stable path: {stable_audio_path}")
        
        # Step 2: Create dummy audio data
        dummy_audio = b'RIFF\x24\x08\x00\x00WAVE' + b'\x00' * 100
        
        # Write to both locations
        with open(temp_audio_path, 'wb') as f:
            f.write(dummy_audio)
        
        import shutil
        shutil.copy2(temp_audio_path, stable_audio_path)
        
        print(f"✅ Audio written to both paths: {len(dummy_audio)} bytes")
        
        # Step 3: Test Whisper import
        try:
            import whisper
            print("✅ Whisper imported successfully")
        except ImportError as e:
            print(f"❌ Whisper not available: {e}")
            return False
        
        # Step 4: Load model
        try:
            model = whisper.load_model("tiny")
            print("✅ Whisper tiny model loaded")
        except Exception as e:
            print(f"❌ Model loading failed: {e}")
            return False
        
        # Step 5: Test file access
        active_path = stable_audio_path if os.path.exists(stable_audio_path) else temp_audio_path
        
        try:
            with open(active_path, 'rb') as test_file:
                test_data = test_file.read(10)
            print(f"✅ File access verified: {len(test_data)} bytes read")
        except Exception as e:
            print(f"❌ File access failed: {e}")
            return False
        
        # Step 6: Test Whisper transcription (this is where it usually fails)
        try:
            print(f"🎤 Testing Whisper transcription with: {active_path}")
            result = model.transcribe(active_path, language="en", fp16=False)
            print("✅ Whisper transcription completed!")
            print(f"Result: '{result.get('text', 'No text')}'")
        except Exception as e:
            print(f"❌ Whisper transcription failed: {e}")
            print(f"Error type: {type(e).__name__}")
            
            # Try to understand the error better
            if "cannot find the file" in str(e).lower():
                print("🔍 File not found error - checking file status:")
                print(f"  Temp path exists: {os.path.exists(temp_audio_path)}")
                print(f"  Stable path exists: {os.path.exists(stable_audio_path)}")
                print(f"  Active path: {active_path}")
                print(f"  Working directory: {os.getcwd()}")
            
            return False
        
        # Step 7: Cleanup
        try:
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
            if os.path.exists(stable_audio_path):
                os.unlink(stable_audio_path)
            if os.path.exists(stable_dir):
                os.rmdir(stable_dir)
            print("✅ Cleanup completed")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        return False

def test_whisper_alternative():
    """Test if there's an alternative Whisper issue"""
    print("\n🔄 Testing Whisper Alternative Approach...")
    
    try:
        import whisper
        
        # Try with a simple string path
        simple_path = "C:\\temp\\test_audio.wav"
        
        # Create a minimal WAV file
        wav_header = (
            b'RIFF' +
            (36).to_bytes(4, 'little') +  # Chunk size
            b'WAVE' +
            b'fmt ' +
            (16).to_bytes(4, 'little') +  # Subchunk1 size
            (1).to_bytes(2, 'little') +   # Audio format (PCM)
            (1).to_bytes(2, 'little') +   # Number of channels
            (16000).to_bytes(4, 'little') + # Sample rate
            (32000).to_bytes(4, 'little') + # Byte rate
            (2).to_bytes(2, 'little') +   # Block align
            (16).to_bytes(2, 'little') +  # Bits per sample
            b'data' +
            (0).to_bytes(4, 'little')     # Subchunk2 size (empty data)
        )
        
        # Ensure temp directory exists
        os.makedirs("C:\\temp", exist_ok=True)
        
        with open(simple_path, 'wb') as f:
            f.write(wav_header)
        
        print(f"✅ Created simple test file: {simple_path}")
        
        # Test Whisper
        model = whisper.load_model("tiny")
        result = model.transcribe(simple_path, language="en", fp16=False)
        
        print("✅ Alternative approach worked!")
        print(f"Result: '{result.get('text', 'No text')}'")
        
        # Cleanup
        os.unlink(simple_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Alternative approach failed: {e}")
        return False

def main():
    """Run comprehensive STT tests"""
    print("=" * 60)
    print("🏥 COMPREHENSIVE STT FIX VALIDATION")
    print("=" * 60)
    
    # Test 1: Complete pipeline
    pipeline_success = test_complete_pipeline()
    
    # Test 2: Alternative approach
    alternative_success = test_whisper_alternative()
    
    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS:")
    print("=" * 60)
    print(f"Complete Pipeline: {'✅ PASS' if pipeline_success else '❌ FAIL'}")
    print(f"Alternative Method: {'✅ PASS' if alternative_success else '❌ FAIL'}")
    
    if pipeline_success or alternative_success:
        print("\n🎉 AT LEAST ONE METHOD WORKS!")
        print("💡 STT functionality should be available")
    else:
        print("\n⚠️  ALL METHODS FAILED")
        print("🔧 Whisper installation or environment issue")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
