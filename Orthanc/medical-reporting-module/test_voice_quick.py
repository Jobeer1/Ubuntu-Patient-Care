#!/usr/bin/env python3
"""
Quick Test - Test voice transcription functionality
"""

import sys
import os
import requests
import json

def test_voice_api():
    """Test the voice API endpoints"""
    base_url = "https://localhost:5001"
    
    print("🎤 Testing Voice API...")
    
    try:
        # Test session start
        print("📞 Testing session start...")
        session_response = requests.post(
            f"{base_url}/api/voice/session/start",
            verify=False,  # Skip SSL verification for local testing
            timeout=10
        )
        
        if session_response.status_code in [200, 201]:
            print("✅ Voice session start: SUCCESS")
            session_data = session_response.json()
            print(f"   Session ID: {session_data.get('session', {}).get('session_id', 'N/A')}")
        else:
            print(f"❌ Voice session start failed: {session_response.status_code}")
            return False
        
        # Test transcribe endpoint (without audio - should handle gracefully)
        print("🎙️  Testing transcribe endpoint...")
        transcribe_response = requests.post(
            f"{base_url}/api/voice/transcribe",
            verify=False,
            timeout=30
        )
        
        if transcribe_response.status_code in [400, 422]:
            print("✅ Voice transcribe endpoint: Correctly handles missing audio")
        else:
            print(f"⚠️  Voice transcribe endpoint: {transcribe_response.status_code}")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure the app is running on https://localhost:5001")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Run voice API tests"""
    print("🏥 SA Medical Reporting - Voice API Test")
    print("=" * 50)
    print("Make sure the app is running first: python app.py")
    print()
    
    if test_voice_api():
        print("\n🎉 Voice API tests completed!")
        print("💡 Try the live demo at: https://localhost:5001/voice-demo")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
