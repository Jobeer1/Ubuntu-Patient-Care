#!/usr/bin/env python3
"""
Test STT Fix - Verify that random text generation is disabled
"""

import sys
import os
import logging
import tempfile
import requests
import json

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_voice_transcription():
    """Test voice transcription endpoint"""
    try:
        # Test the voice transcription endpoint
        url = "https://localhost:5001/api/voice/transcribe"
        
        # Create a dummy audio file for testing
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            # Write minimal WAV header and some dummy audio data
            wav_header = b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x08\x00\x00'
            dummy_audio = b'\x00' * 1000  # 1000 bytes of silence
            temp_file.write(wav_header + dummy_audio)
            temp_audio_path = temp_file.name
        
        try:
            # Test with the dummy audio file
            with open(temp_audio_path, 'rb') as audio_file:
                files = {'audio': audio_file}
                data = {'real_time': 'false'}
                
                response = requests.post(
                    url, 
                    files=files, 
                    data=data,
                    verify=False,  # Skip SSL verification for localhost
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✓ STT Response: {json.dumps(result, indent=2)}")
                    
                    # Check if we're getting random medical words
                    transcription = result.get('transcription', '')
                    if transcription and any(word in transcription.lower() for word in ['breath', 'rate', 'lungs', 'pneumonia', 'neurological']):
                        print("⚠️  WARNING: Still getting random medical words!")
                        return False
                    else:
                        print("✓ No random medical words detected")
                        return True
                else:
                    print(f"✗ HTTP Error: {response.status_code}")
                    print(f"Response: {response.text}")
                    return False
                    
        finally:
            # Clean up
            try:
                os.unlink(temp_audio_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

def test_demo_voice_endpoint():
    """Test demo voice endpoint"""
    try:
        url = "https://localhost:5001/api/demo/voice/start"
        
        response = requests.post(
            url,
            json={},
            verify=False,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Demo Voice Start: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"✗ Demo Voice Start Error: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Demo test failed: {e}")
        return False

def main():
    """Run STT fix tests"""
    print("=" * 60)
    print("STT FIX VERIFICATION TEST")
    print("=" * 60)
    
    print("\n1. Testing Demo Voice Endpoint...")
    demo_success = test_demo_voice_endpoint()
    
    print("\n2. Testing Voice Transcription...")
    transcription_success = test_voice_transcription()
    
    print("\n" + "=" * 60)
    print("TEST RESULTS:")
    print(f"Demo Voice: {'✓ PASS' if demo_success else '✗ FAIL'}")
    print(f"Transcription: {'✓ PASS' if transcription_success else '✗ FAIL'}")
    
    if demo_success and transcription_success:
        print("\n✓ STT FIX SUCCESSFUL - No more random medical words!")
    else:
        print("\n✗ STT FIX INCOMPLETE - Issues remain")
    
    print("=" * 60)

if __name__ == "__main__":
    main()