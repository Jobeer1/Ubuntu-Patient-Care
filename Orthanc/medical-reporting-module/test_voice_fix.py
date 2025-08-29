#!/usr/bin/env python3
"""
Test the voice transcription fix
"""

import requests
import json
import time

def test_voice_transcription():
    """Test voice transcription API"""
    print("🎤 Testing Voice Transcription Fix...")
    
    base_url = "https://localhost:5001"
    
    try:
        # Test the voice transcribe endpoint
        print("Testing real-time transcription...")
        
        # Create a dummy audio file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            # Write some dummy audio data
            temp_file.write(b'dummy audio data')
            temp_audio_path = temp_file.name
        
        try:
            # Test real-time transcription
            with open(temp_audio_path, 'rb') as audio_file:
                files = {'audio': audio_file}
                data = {
                    'session_id': 'test_session',
                    'language': 'en-ZA',
                    'real_time': 'true'
                }
                
                response = requests.post(
                    f"{base_url}/api/voice/transcribe",
                    files=files,
                    data=data,
                    verify=False  # Skip SSL verification for testing
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Real-time transcription successful: {result.get('transcription', 'No text')}")
                    return True
                else:
                    print(f"❌ Real-time transcription failed: {response.status_code}")
                    print(f"Response: {response.text}")
                    return False
                    
        finally:
            # Clean up
            try:
                os.unlink(temp_audio_path)
            except:
                pass
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_voice_transcription()
    if success:
        print("\n🎉 Voice transcription fix is working!")
        print("✅ Real-time transcription should now work properly")
        print("✅ Text should appear as you speak")
    else:
        print("\n❌ Voice transcription fix needs more work")