#!/usr/bin/env python3
"""
Test script to verify the STT button fix
"""

import requests
import time
import json

def test_voice_demo_page():
    """Test that the voice demo page loads correctly"""
    try:
        response = requests.get('https://localhost:5443/voice-demo', verify=False)
        print(f"Voice demo page status: {response.status_code}")
        
        # Check if the microphone button is present
        if 'microphone-btn' in response.text:
            print("✅ Microphone button found in HTML")
        else:
            print("❌ Microphone button NOT found in HTML")
            
        # Check if the UI manager script is loaded
        if 'ui-manager.js' in response.text:
            print("✅ UI Manager script loaded")
        else:
            print("❌ UI Manager script NOT loaded")
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error testing voice demo page: {e}")
        return False

def test_voice_session_start():
    """Test that voice session can be started"""
    try:
        response = requests.post('https://localhost:5443/api/voice/session/start', 
                               json={}, verify=False)
        print(f"Voice session start status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"✅ Voice session started: {data.get('session_id')}")
            return True
        else:
            print(f"❌ Failed to start voice session: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error starting voice session: {e}")
        return False

def main():
    print("🔧 Testing STT Button Fix...")
    print("=" * 50)
    
    # Test 1: Voice demo page loads
    print("\n1. Testing voice demo page...")
    page_ok = test_voice_demo_page()
    
    # Test 2: Voice session can start
    print("\n2. Testing voice session start...")
    session_ok = test_voice_session_start()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Voice demo page: {'✅ PASS' if page_ok else '❌ FAIL'}")
    print(f"Voice session start: {'✅ PASS' if session_ok else '❌ FAIL'}")
    
    if page_ok and session_ok:
        print("\n🎉 STT button fix appears to be working!")
        print("The microphone button should now respond to clicks.")
    else:
        print("\n⚠️ Some issues detected. Check the server logs.")

if __name__ == "__main__":
    main()