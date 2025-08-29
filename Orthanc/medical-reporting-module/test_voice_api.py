#!/usr/bin/env python3
"""
Test script for voice API endpoints
"""

import requests
import json
import time

def test_voice_endpoints():
    """Test voice API endpoints"""
    base_url = "http://127.0.0.1:5001"
    
    print("🧪 Testing Voice API Endpoints...")
    
    # Test 1: Start voice session
    print("\n1. Testing voice session start...")
    try:
        response = requests.post(f"{base_url}/api/voice/demo/start", 
                               json={"doctor_id": "test_doctor"})
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Session started: {data.get('session_id')}")
            session_id = data.get('session_id')
        else:
            print(f"❌ Session start failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Session start error: {e}")
        return
    
    # Test 2: Simulate transcription
    print("\n2. Testing simulation endpoint...")
    try:
        response = requests.post(f"{base_url}/api/voice/demo/simulate",
                               json={"text": "The patient has tb and numonia"})
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Original: {data.get('original_text')}")
            print(f"✅ Processed: {data.get('processed_text')}")
        else:
            print(f"❌ Simulation failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Simulation error: {e}")
    
    # Test 3: Test medical processing
    print("\n3. Testing medical vocabulary processing...")
    test_phrases = [
        "tb in the lung",
        "numonia and consolidation", 
        "no acute abnormality",
        "bilateral lung fields are clear"
    ]
    
    for phrase in test_phrases:
        try:
            response = requests.post(f"{base_url}/api/voice/demo/simulate",
                                   json={"text": phrase})
            
            if response.status_code == 200:
                data = response.json()
                original = data.get('original_text', '')
                processed = data.get('processed_text', '')
                
                if original != processed:
                    print(f"✅ '{original}' → '{processed}'")
                else:
                    print(f"ℹ️  '{original}' (no changes)")
            else:
                print(f"❌ Failed to process: {phrase}")
        except Exception as e:
            print(f"❌ Error processing '{phrase}': {e}")
    
    print("\n🏁 Voice API test completed!")

if __name__ == "__main__":
    test_voice_endpoints()