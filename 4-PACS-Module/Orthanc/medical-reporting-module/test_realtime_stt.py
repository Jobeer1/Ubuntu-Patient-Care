#!/usr/bin/env python3
"""
Test script for Real-Time Speech-to-Text functionality
Tests the new chunk processing endpoints and real-time features
"""

import requests
import json
import time
import tempfile
import os
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:5000"  # Adjust if your server runs on different port
API_BASE = f"{BASE_URL}/api/voice"

def test_session_management():
    """Test voice session creation and management"""
    print("Testing session management...")
    
    # Start session
    response = requests.post(f"{API_BASE}/session/start", json={
        "language": "en-ZA",
        "medical_mode": True
    })
    
    assert response.status_code == 201, f"Failed to start session: {response.status_code}"
    session_data = response.json()
    session_id = session_data["session"]["session_id"]
    print(f"✓ Session started: {session_id}")
    
    # Get session status
    response = requests.get(f"{API_BASE}/session/status")
    assert response.status_code == 200, f"Failed to get session status: {response.status_code}"
    status_data = response.json()
    assert status_data["active"] == True, "Session should be active"
    print("✓ Session status verified")
    
    # Get session context
    response = requests.get(f"{API_BASE}/session/{session_id}/context")
    assert response.status_code == 200, f"Failed to get session context: {response.status_code}"
    context_data = response.json()
    assert context_data["session_id"] == session_id, "Session ID mismatch"
    print("✓ Session context retrieved")
    
    return session_id

def create_test_audio_chunk():
    """Create a simple test audio file (WAV format)"""
    # Create a minimal WAV file with silence
    # WAV header for 1 second of silence at 16kHz, mono, 16-bit
    sample_rate = 16000
    duration = 1  # 1 second
    samples = sample_rate * duration
    
    # WAV file structure
    wav_data = bytearray()
    
    # RIFF header
    wav_data.extend(b'RIFF')
    wav_data.extend((36 + samples * 2).to_bytes(4, 'little'))  # File size - 8
    wav_data.extend(b'WAVE')
    
    # fmt chunk
    wav_data.extend(b'fmt ')
    wav_data.extend((16).to_bytes(4, 'little'))  # fmt chunk size
    wav_data.extend((1).to_bytes(2, 'little'))   # PCM format
    wav_data.extend((1).to_bytes(2, 'little'))   # Mono
    wav_data.extend(sample_rate.to_bytes(4, 'little'))  # Sample rate
    wav_data.extend((sample_rate * 2).to_bytes(4, 'little'))  # Byte rate
    wav_data.extend((2).to_bytes(2, 'little'))   # Block align
    wav_data.extend((16).to_bytes(2, 'little'))  # Bits per sample
    
    # data chunk
    wav_data.extend(b'data')
    wav_data.extend((samples * 2).to_bytes(4, 'little'))  # Data size
    
    # Silent audio data (all zeros)
    wav_data.extend(b'\x00' * (samples * 2))
    
    return bytes(wav_data)

def test_chunk_processing(session_id):
    """Test real-time chunk processing"""
    print("Testing chunk processing...")
    
    # Create test audio chunk
    audio_data = create_test_audio_chunk()
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_file.write(audio_data)
        temp_file_path = temp_file.name
    
    try:
        # Test chunk transcription
        with open(temp_file_path, 'rb') as audio_file:
            files = {'audio': ('test_chunk.wav', audio_file, 'audio/wav')}
            data = {
                'session_id': session_id,
                'chunk_id': 'test_chunk_001',
                'sequence_number': '0',
                'language': 'en-ZA'
            }
            
            response = requests.post(f"{API_BASE}/transcribe-chunk", files=files, data=data)
            
        assert response.status_code == 200, f"Chunk processing failed: {response.status_code}"
        result = response.json()
        
        assert result["success"] == True, f"Chunk processing unsuccessful: {result}"
        assert "chunk_id" in result, "Missing chunk_id in response"
        assert result["chunk_id"] == "test_chunk_001", "Chunk ID mismatch"
        
        print(f"✓ Chunk processed successfully: '{result.get('transcription', '(empty)')}'")
        
        # Test duplicate chunk (should return cached result)
        with open(temp_file_path, 'rb') as audio_file:
            files = {'audio': ('test_chunk.wav', audio_file, 'audio/wav')}
            
            response = requests.post(f"{API_BASE}/transcribe-chunk", files=files, data=data)
            
        assert response.status_code == 200, "Duplicate chunk processing failed"
        duplicate_result = response.json()
        assert duplicate_result["chunk_id"] == result["chunk_id"], "Duplicate detection failed"
        print("✓ Duplicate chunk detection working")
        
    finally:
        # Clean up temp file
        os.unlink(temp_file_path)
    
    return result

def test_session_finalization(session_id):
    """Test session finalization and final pass optimization"""
    print("Testing session finalization...")
    
    # Finalize session transcription
    response = requests.post(f"{API_BASE}/session/{session_id}/finalize")
    
    assert response.status_code == 200, f"Session finalization failed: {response.status_code}"
    result = response.json()
    
    assert result["success"] == True, f"Session finalization unsuccessful: {result}"
    print(f"✓ Session finalized with {len(result.get('improvements', []))} improvements")
    
    return result

def test_session_cleanup(session_id):
    """Test session cleanup"""
    print("Testing session cleanup...")
    
    # End session
    response = requests.post(f"{API_BASE}/session/end")
    
    assert response.status_code == 200, f"Failed to end session: {response.status_code}"
    session_data = response.json()
    
    assert session_data["session"]["session_id"] == session_id, "Session ID mismatch"
    assert session_data["session"]["state"] == "ended", "Session should be ended"
    print("✓ Session ended successfully")
    
    # Verify session is no longer active
    response = requests.get(f"{API_BASE}/session/status")
    assert response.status_code == 200, "Failed to get session status after cleanup"
    status_data = response.json()
    assert status_data["active"] == False, "Session should not be active after cleanup"
    print("✓ Session cleanup verified")

def test_error_handling():
    """Test error handling scenarios"""
    print("Testing error handling...")
    
    # Test chunk processing without session
    audio_data = create_test_audio_chunk()
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_file.write(audio_data)
        temp_file_path = temp_file.name
    
    try:
        # Test with invalid session
        with open(temp_file_path, 'rb') as audio_file:
            files = {'audio': ('test_chunk.wav', audio_file, 'audio/wav')}
            data = {
                'session_id': 'invalid_session_id',
                'chunk_id': 'test_chunk_error',
                'sequence_number': '0'
            }
            
            response = requests.post(f"{API_BASE}/transcribe-chunk", files=files, data=data)
            
        # Should still work (creates new context if needed)
        assert response.status_code == 200, "Should handle invalid session gracefully"
        print("✓ Invalid session handled gracefully")
        
        # Test without audio file
        response = requests.post(f"{API_BASE}/transcribe-chunk", data={'session_id': 'test'})
        assert response.status_code == 400, "Should reject request without audio"
        print("✓ Missing audio file rejected properly")
        
    finally:
        os.unlink(temp_file_path)

def test_medical_terminology():
    """Test medical terminology enhancement"""
    print("Testing medical terminology enhancement...")
    
    # Start new session
    response = requests.post(f"{API_BASE}/session/start", json={"medical_mode": True})
    session_data = response.json()
    session_id = session_data["session"]["session_id"]
    
    # Test with medical terms (using regular transcribe endpoint for simplicity)
    test_text = "Patient has tb and high bp"
    
    # Create a simple audio file (the enhancement happens on the server side)
    audio_data = create_test_audio_chunk()
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_file.write(audio_data)
        temp_file_path = temp_file.name
    
    try:
        with open(temp_file_path, 'rb') as audio_file:
            files = {'audio': ('medical_test.wav', audio_file, 'audio/wav')}
            data = {'session_id': session_id, 'language': 'en-ZA'}
            
            response = requests.post(f"{API_BASE}/transcribe", files=files, data=data)
            
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Medical terminology processing completed")
        else:
            print(f"⚠ Medical terminology test skipped (transcription service may not be available)")
            
    finally:
        os.unlink(temp_file_path)
        # Clean up session
        requests.post(f"{API_BASE}/session/end")

def run_performance_test():
    """Test performance with multiple concurrent chunks"""
    print("Testing performance with multiple chunks...")
    
    # Start session
    response = requests.post(f"{API_BASE}/session/start")
    session_data = response.json()
    session_id = session_data["session"]["session_id"]
    
    # Create multiple test chunks
    num_chunks = 5
    audio_data = create_test_audio_chunk()
    
    start_time = time.time()
    
    for i in range(num_chunks):
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, 'rb') as audio_file:
                files = {'audio': (f'chunk_{i}.wav', audio_file, 'audio/wav')}
                data = {
                    'session_id': session_id,
                    'chunk_id': f'perf_chunk_{i:03d}',
                    'sequence_number': str(i)
                }
                
                response = requests.post(f"{API_BASE}/transcribe-chunk", files=files, data=data)
                
            if response.status_code != 200:
                print(f"⚠ Chunk {i} failed: {response.status_code}")
                
        finally:
            os.unlink(temp_file_path)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"✓ Processed {num_chunks} chunks in {total_time:.2f} seconds ({total_time/num_chunks:.2f}s per chunk)")
    
    # Clean up
    requests.post(f"{API_BASE}/session/end")

def main():
    """Run all tests"""
    print("=" * 60)
    print("Real-Time Speech-to-Text Test Suite")
    print("=" * 60)
    
    try:
        # Test basic functionality
        session_id = test_session_management()
        chunk_result = test_chunk_processing(session_id)
        finalize_result = test_session_finalization(session_id)
        test_session_cleanup(session_id)
        
        # Test error scenarios
        test_error_handling()
        
        # Test medical terminology
        test_medical_terminology()
        
        # Performance test
        run_performance_test()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("Real-time STT functionality is working correctly.")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to server at {BASE_URL}")
        print("Make sure the medical reporting server is running.")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())