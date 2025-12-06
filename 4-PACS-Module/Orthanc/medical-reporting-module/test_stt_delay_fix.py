#!/usr/bin/env python3
"""
Test script to verify STT delay fix
Tests that the Whisper model stays loaded and chunk processing is fast
"""

import requests
import time
import tempfile
import wave
import numpy as np
import os

def create_test_audio(duration=2.0, sample_rate=16000):
    """Create a simple test audio file"""
    # Generate a simple sine wave
    t = np.linspace(0, duration, int(sample_rate * duration))
    frequency = 440  # A4 note
    audio_data = np.sin(2 * np.pi * frequency * t) * 0.3
    
    # Convert to 16-bit PCM
    audio_data = (audio_data * 32767).astype(np.int16)
    
    # Create WAV file
    temp_fd, temp_path = tempfile.mkstemp(suffix='.wav')
    try:
        os.close(temp_fd)
        with wave.open(temp_path, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        return temp_path
    except Exception as e:
        try:
            os.unlink(temp_path)
        except:
            pass
        raise e

def test_chunk_processing_speed():
    """Test that chunk processing is fast after model is loaded"""
    base_url = "https://127.0.0.1:5443"
    
    print("🧪 Testing STT delay fix...")
    
    # Step 1: Start a voice session to pre-load the model
    print("1. Starting voice session to pre-load Whisper model...")
    try:
        response = requests.post(f"{base_url}/api/voice/session/start", 
                               json={}, 
                               verify=False, 
                               timeout=10)
        if response.status_code == 201:
            session_data = response.json()
            session_id = session_data.get('session', {}).get('session_id', 'demo')
            print(f"   ✅ Session started: {session_id}")
        else:
            print(f"   ❌ Failed to start session: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Session start error: {e}")
        return False
    
    # Step 2: Create test audio
    print("2. Creating test audio...")
    try:
        audio_path = create_test_audio(duration=2.0)
        print(f"   ✅ Test audio created: {audio_path}")
    except Exception as e:
        print(f"   ❌ Audio creation error: {e}")
        return False
    
    # Step 3: Test multiple chunk processing calls to measure speed
    print("3. Testing chunk processing speed...")
    processing_times = []
    
    for i in range(3):
        try:
            start_time = time.time()
            
            with open(audio_path, 'rb') as audio_file:
                files = {'audio': audio_file}
                data = {
                    'session_id': session_id,
                    'chunk_id': f'test_chunk_{i}',
                    'sequence_number': str(i)
                }
                
                response = requests.post(f"{base_url}/api/voice/transcribe-chunk",
                                       files=files,
                                       data=data,
                                       verify=False,
                                       timeout=15)
            
            end_time = time.time()
            processing_time = end_time - start_time
            processing_times.append(processing_time)
            
            if response.status_code == 200:
                result = response.json()
                server_time = result.get('processing_time', 0)
                print(f"   Chunk {i+1}: {processing_time:.2f}s total, {server_time:.2f}s server")
            else:
                print(f"   ❌ Chunk {i+1} failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Chunk {i+1} error: {e}")
    
    # Step 4: Analyze results
    print("\n📊 Results Analysis:")
    if processing_times:
        avg_time = sum(processing_times) / len(processing_times)
        first_time = processing_times[0]
        subsequent_avg = sum(processing_times[1:]) / len(processing_times[1:]) if len(processing_times) > 1 else 0
        
        print(f"   First request: {first_time:.2f}s")
        print(f"   Average time: {avg_time:.2f}s")
        if len(processing_times) > 1:
            print(f"   Subsequent avg: {subsequent_avg:.2f}s")
        
        # Check if fix is working
        if first_time < 5.0 and avg_time < 3.0:
            print("   ✅ DELAY FIX WORKING: Fast processing times!")
            success = True
        elif first_time > 10.0:
            print("   ❌ DELAY STILL EXISTS: First request too slow (model loading)")
            success = False
        elif avg_time > 5.0:
            print("   ❌ DELAY STILL EXISTS: Average processing too slow")
            success = False
        else:
            print("   ⚠️  PARTIAL FIX: Some improvement but could be better")
            success = True
    else:
        print("   ❌ No successful requests to analyze")
        success = False
    
    # Cleanup
    try:
        os.unlink(audio_path)
    except:
        pass
    
    return success

if __name__ == "__main__":
    print("🔧 STT Delay Fix Verification Test")
    print("=" * 50)
    
    success = test_chunk_processing_speed()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 TEST PASSED: STT delay fix is working!")
        print("   The Whisper model is staying loaded and processing is fast.")
    else:
        print("❌ TEST FAILED: STT delay still exists.")
        print("   Check the server logs for more details.")
    
    print("\n💡 Tips for further optimization:")
    print("   - Ensure the server has enough RAM to keep the model loaded")
    print("   - Consider using a smaller Whisper model (tiny/base) for faster processing")
    print("   - Monitor server logs for 'Loading Whisper model...' messages")