#!/usr/bin/env python3
"""
Test script to verify our Phase 1 API fixes work correctly
Run this after restarting the Flask server
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_endpoints():
    """Test the newly added API endpoints"""
    print("🔧 Testing Phase 1 API Fixes")
    print("=" * 50)
    
    # Test authentication first
    print("🔐 Testing authentication...")
    auth_response = requests.post(f"{BASE_URL}/api/auth/login", 
                                 json={"username": "admin", "password": "admin123"},
                                 headers={'Content-Type': 'application/json'})
    
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return
    
    cookies = auth_response.cookies
    print("✅ Authentication successful")
    
    # Test session creation
    print("\n📝 Testing session creation...")
    session_data = {
        'study_id': 'TEST_STUDY_001',
        'image_ids': ['IMG_001', 'IMG_002'],
        'language': 'en-ZA',
        'measurements': [
            {'type': 'length', 'value': 25.5, 'units': 'mm', 'description': 'Linear measurement'}
        ]
    }
    
    session_response = requests.post(f"{BASE_URL}/api/reporting/sessions", 
                                   json=session_data,
                                   cookies=cookies,
                                   headers={'Content-Type': 'application/json'})
    
    if session_response.status_code != 201:
        print(f"❌ Session creation failed: {session_response.status_code}")
        print(f"Response: {session_response.text}")
        return
    
    session_id = session_response.json().get('session', {}).get('session_id')
    print(f"✅ Session created: {session_id}")
    
    # Test new audio start endpoint
    print(f"\n🎤 Testing audio/start endpoint...")
    start_response = requests.post(f"{BASE_URL}/api/reporting/sessions/{session_id}/audio/start",
                                 cookies=cookies,
                                 headers={'Content-Type': 'application/json'})
    
    print(f"Status: {start_response.status_code}")
    if start_response.status_code == 200:
        print("✅ Audio start endpoint working!")
    else:
        print(f"❌ Audio start failed: {start_response.text}")
    
    # Test new audio stop endpoint  
    print(f"\n🎤 Testing audio/stop endpoint...")
    stop_response = requests.post(f"{BASE_URL}/api/reporting/sessions/{session_id}/audio/stop",
                                cookies=cookies,
                                headers={'Content-Type': 'application/json'})
    
    print(f"Status: {stop_response.status_code}")
    if stop_response.status_code == 200:
        print("✅ Audio stop endpoint working!")
    else:
        print(f"❌ Audio stop failed: {stop_response.text}")
    
    # Test new save endpoint
    print(f"\n📄 Testing save report endpoint...")
    report_data = {
        'report_text': 'Test report with measurements',
        'measurements': [
            {'type': 'length', 'value': 25.5, 'units': 'mm', 'description': 'Test measurement'}
        ]
    }
    
    save_response = requests.post(f"{BASE_URL}/api/reporting/sessions/{session_id}/save",
                                json=report_data,
                                cookies=cookies,
                                headers={'Content-Type': 'application/json'})
    
    print(f"Status: {save_response.status_code}")
    if save_response.status_code == 200:
        print("✅ Save report endpoint working!")
    else:
        print(f"❌ Save report failed: {save_response.text}")
    
    print("\n" + "=" * 50)
    print("🎯 API Fixes Test Complete!")

if __name__ == "__main__":
    test_endpoints()
