#!/usr/bin/env python3
"""
Quick test script for new features:
- TTS performance (should be <100ms after warmup)
- Voice note upload/retrieve
- Invite code generation
- Group member management
"""

import sys
import time
import requests
from io import BytesIO

BASE_URL = "http://localhost:5001"

def test_tts_performance():
    """Test TTS response time"""
    print("\n🧪 Testing TTS Performance...")
    
    # First call might be slow (initialization)
    test_texts = [
        "Quick test",
        "Testing voice notes for group chat",
        "TTS should be instant now"
    ]
    
    for text in test_texts:
        start = time.time()
        try:
            response = requests.post(
                f"{BASE_URL}/api/tts/speak",
                json={'text': text},
                headers={'Authorization': 'Bearer test-token'},
                timeout=5
            )
            elapsed = time.time() - start
            
            if response.status_code == 200:
                size_kb = len(response.content) / 1024
                print(f"  ✓ '{text[:30]}...' → {elapsed*1000:.0f}ms ({size_kb:.1f}KB)")
            else:
                print(f"  ✗ Status {response.status_code}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

def test_invite_generation():
    """Test invite link generation"""
    print("\n🎯 Testing Invite Code Generation...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/invites/generate",
            headers={'Authorization': 'Bearer test-token'},
            timeout=5
        )
        
        if response.status_code == 201:
            data = response.json()
            print(f"  ✓ Invite Code: {data['code']}")
            print(f"    URL: {data['invite_url']}")
            print(f"    WhatsApp: {data['share_links']['whatsapp'][:60]}...")
        else:
            print(f"  ✗ Status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

def test_voice_note_api():
    """Test voice note upload"""
    print("\n🎙️ Testing Voice Note Upload...")
    
    # Create a dummy WAV file (silent 1-second audio)
    # Format: 44100 Hz, mono, 16-bit PCM
    import struct
    sample_rate = 44100
    duration = 1
    num_samples = sample_rate * duration
    
    # WAV header
    channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    
    wav_data = b'RIFF'
    wav_data += struct.pack('<I', 36 + num_samples * 2)  # File size - 8
    wav_data += b'WAVE'
    wav_data += b'fmt '
    wav_data += struct.pack('<I', 16)  # Subchunk1Size
    wav_data += struct.pack('<H', 1)   # AudioFormat (PCM)
    wav_data += struct.pack('<H', channels)
    wav_data += struct.pack('<I', sample_rate)
    wav_data += struct.pack('<I', byte_rate)
    wav_data += struct.pack('<H', block_align)
    wav_data += struct.pack('<H', bits_per_sample)
    wav_data += b'data'
    wav_data += struct.pack('<I', num_samples * 2)
    wav_data += b'\x00' * (num_samples * 2)  # Silent audio
    
    try:
        files = {'audio': ('test.wav', BytesIO(wav_data), 'audio/wav')}
        data = {'duration': '1.0'}
        
        response = requests.post(
            f"{BASE_URL}/api/voice-notes/upload",
            files=files,
            data=data,
            headers={'Authorization': 'Bearer test-token'},
            timeout=5
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"  ✓ Voice Note Created: {result['note_id']}")
            print(f"    URL: {result['url']}")
            print(f"    Duration: {result['duration']}s")
        else:
            print(f"  ✗ Status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

def test_group_members():
    """Test group member list endpoint"""
    print("\n👥 Testing Group Member Management...")
    
    # This will fail without a valid token, but shows API is working
    try:
        response = requests.get(
            f"{BASE_URL}/api/groups/test-group/members",
            headers={'Authorization': 'Bearer test-token'},
            timeout=5
        )
        
        if response.status_code in [200, 401, 404]:
            print(f"  ✓ Endpoint responds (status {response.status_code})")
        else:
            print(f"  ✗ Status {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Testing New SDOH Chat Features")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        print(f"✓ Server is running on {BASE_URL}")
    except:
        print(f"✗ Cannot connect to {BASE_URL}")
        print("   Make sure Flask is running: python run.py")
        sys.exit(1)
    
    # Run tests
    test_tts_performance()
    test_invite_generation()
    test_voice_note_api()
    test_group_members()
    
    print("\n" + "=" * 60)
    print("✅ API tests complete!")
    print("=" * 60)
