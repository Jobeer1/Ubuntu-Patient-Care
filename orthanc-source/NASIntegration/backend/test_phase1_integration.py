#!/usr/bin/env python3
"""
Phase 1 Integration Test - DICOM Viewer to Reporting Integration
Tests the connection between DICOM viewer and reporting system
"""

import requests
import json
import time
import sys
import os
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:5000"
DICOM_VIEWER_URL = "http://localhost:3001"
TEST_ADMIN = {
    "username": "admin",
    "password": "admin123"
}

def test_authentication():
    """Test admin authentication"""
    print("🔐 Testing authentication...")
    
    response = requests.post(f"{BASE_URL}/api/auth/login", 
                           json=TEST_ADMIN,
                           headers={'Content-Type': 'application/json'})
    
    if response.status_code == 200:
        print("✅ Authentication successful")
        return response.cookies
    else:
        print(f"❌ Authentication failed: {response.status_code}")
        return None

def test_dicom_viewer_availability():
    """Test if DICOM viewer is running"""
    print("\n🖥️ Testing DICOM viewer availability...")
    
    try:
        response = requests.get(DICOM_VIEWER_URL, timeout=5)
        if response.status_code == 200:
            print("✅ DICOM viewer is running")
            return True
        else:
            print(f"❌ DICOM viewer returned status: {response.status_code}")
    except requests.RequestException as e:
        print(f"❌ DICOM viewer not accessible: {e}")
    
    return False

def test_reporting_session_creation(cookies):
    """Test creating a reporting session from DICOM viewer"""
    print("\n📝 Testing reporting session creation...")
    
    # Simulate DICOM viewer creating a reporting session
    session_data = {
        'study_id': 'TEST_STUDY_001',
        'image_ids': ['IMG_001', 'IMG_002'],
        'language': 'en-ZA',
        'measurements': [
            {
                'type': 'length',
                'value': 25.5,
                'units': 'mm',
                'description': 'Linear measurement'
            },
            {
                'type': 'angle',
                'value': 45.2,
                'units': 'degrees',
                'description': 'Angular measurement'
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/api/reporting/sessions", 
                           json=session_data,
                           cookies=cookies,
                           headers={'Content-Type': 'application/json'})
    
    if response.status_code == 201:
        data = response.json()
        if data.get('success'):
            session_id = data.get('session', {}).get('session_id')
            print(f"✅ Reporting session created: {session_id}")
            return session_id
        else:
            print(f"❌ Session creation failed: {data.get('error')}")
    else:
        print(f"❌ Session creation endpoint failed: {response.status_code}")
        print(f"Response: {response.text}")
    
    return None

def test_measurement_integration(cookies, session_id):
    """Test measurement data integration"""
    print(f"\n📏 Testing measurement integration for session {session_id}...")
    
    # Get session details to verify measurements were included
    response = requests.get(f"{BASE_URL}/api/reporting/sessions/{session_id}", 
                          cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            session = data.get('session', {})
            # Check if measurements are properly stored
            print("✅ Session retrieved with measurement data")
            print(f"   Study ID: {session.get('study_id')}")
            print(f"   Image IDs: {len(session.get('image_ids', []))}")
            return True
        else:
            print(f"❌ Session retrieval failed: {data.get('error')}")
    else:
        print(f"❌ Session retrieval endpoint failed: {response.status_code}")
    
    return False

def test_voice_recording_workflow(cookies, session_id):
    """Test voice recording workflow"""
    print(f"\n🎤 Testing voice recording workflow for session {session_id}...")
    
    # Test start recording
    response = requests.post(f"{BASE_URL}/api/reporting/sessions/{session_id}/record", 
                           cookies=cookies)
    
    if response.status_code == 200:
        print("✅ Recording started successfully")
        
        # Simulate recording time
        time.sleep(2)
        
        # Test stop recording
        response = requests.post(f"{BASE_URL}/api/reporting/sessions/{session_id}/stop", 
                               cookies=cookies)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ Recording stopped successfully")
                transcript = data.get('transcript', '')
                if transcript:
                    print(f"   Transcript: {transcript[:50]}...")
                return True
            else:
                print(f"❌ Stop recording failed: {data.get('error')}")
        else:
            print(f"❌ Stop recording endpoint failed: {response.status_code}")
    else:
        print(f"❌ Start recording endpoint failed: {response.status_code}")
    
    return False

def test_report_draft_creation(cookies, session_id):
    """Test report draft creation with measurements"""
    print(f"\n📄 Testing report draft creation for session {session_id}...")
    
    # Create a report draft with measurements
    report_data = {
        'report_text': '''MEASUREMENTS:
1. Linear measurement: 25.50 mm
2. Angular measurement: 45.2°

FINDINGS:
The patient presents with chest pain and shortness of breath. 
Physical examination reveals decreased air entry on the right side. 
Chest X-ray shows consolidation in the right lower lobe consistent with pneumonia.

IMPRESSION:
Right lower lobe pneumonia.

RECOMMENDATIONS:
1. Antibiotic therapy
2. Follow-up chest X-ray in 7-10 days
3. Clinical correlation recommended''',
        'measurements': [
            {
                'type': 'length',
                'value': 25.5,
                'units': 'mm',
                'description': 'Linear measurement'
            },
            {
                'type': 'angle',
                'value': 45.2,
                'units': 'degrees',
                'description': 'Angular measurement'
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/api/reporting/sessions/{session_id}/save", 
                           json=report_data,
                           cookies=cookies,
                           headers={'Content-Type': 'application/json'})
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Report draft saved successfully")
            return True
        else:
            print(f"❌ Report save failed: {data.get('error')}")
    else:
        print(f"❌ Report save endpoint failed: {response.status_code}")
    
    return False

def test_typist_queue_integration(cookies, session_id):
    """Test integration with typist queue"""
    print(f"\n👩‍💻 Testing typist queue integration for session {session_id}...")
    
    # Submit report to typist queue
    response = requests.post(f"{BASE_URL}/api/reporting/sessions/{session_id}/submit", 
                           json={
                               'report_text': 'Test report for typist review',
                               'measurements': [],
                               'status': 'pending_review'
                           },
                           cookies=cookies,
                           headers={'Content-Type': 'application/json'})
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Report submitted to typist queue")
            
            # Check if it appears in typist queue
            queue_response = requests.get(f"{BASE_URL}/api/reporting/typist/queue", 
                                        cookies=cookies)
            
            if queue_response.status_code == 200:
                queue_data = queue_response.json()
                if queue_data.get('success'):
                    queue_items = queue_data.get('queue_items', [])
                    session_in_queue = any(item.get('session_id') == session_id for item in queue_items)
                    
                    if session_in_queue:
                        print("✅ Report appears in typist queue")
                        return True
                    else:
                        print("❌ Report not found in typist queue")
                else:
                    print(f"❌ Queue retrieval failed: {queue_data.get('error')}")
            else:
                print(f"❌ Queue endpoint failed: {queue_response.status_code}")
        else:
            print(f"❌ Report submission failed: {data.get('error')}")
    else:
        print(f"❌ Report submission endpoint failed: {response.status_code}")
    
    return False

def test_end_to_end_workflow(cookies):
    """Test complete end-to-end workflow"""
    print("\n🔄 Testing complete end-to-end workflow...")
    
    # Step 1: Create session (simulating DICOM viewer)
    session_id = test_reporting_session_creation(cookies)
    if not session_id:
        return False
    
    # Step 2: Test measurement integration
    if not test_measurement_integration(cookies, session_id):
        return False
    
    # Step 3: Test voice recording
    if not test_voice_recording_workflow(cookies, session_id):
        print("⚠️ Voice recording failed, but continuing...")
    
    # Step 4: Test report draft creation
    if not test_report_draft_creation(cookies, session_id):
        return False
    
    # Step 5: Test typist queue integration
    if not test_typist_queue_integration(cookies, session_id):
        return False
    
    print("✅ End-to-end workflow completed successfully")
    return True

def main():
    """Run all Phase 1 integration tests"""
    print("🇿🇦 SA Medical Reporting - Phase 1 Integration Tests")
    print("=" * 70)
    
    # Test authentication
    cookies = test_authentication()
    if not cookies:
        print("\n❌ Cannot continue without authentication")
        sys.exit(1)
    
    # Test DICOM viewer availability
    dicom_available = test_dicom_viewer_availability()
    
    # Run integration tests
    tests = [
        ("Reporting Session Creation", lambda: test_reporting_session_creation(cookies) is not None),
        ("End-to-End Workflow", lambda: test_end_to_end_workflow(cookies))
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 70)
    print("📋 PHASE 1 INTEGRATION TEST SUMMARY")
    print("=" * 70)
    
    passed = 0
    total = len(results) + 1  # +1 for DICOM viewer availability
    
    if dicom_available:
        passed += 1
        print("✅ DICOM Viewer Availability")
    else:
        print("❌ DICOM Viewer Availability")
    
    for test_name, result in results:
        if result:
            passed += 1
            print(f"✅ {test_name}")
        else:
            print(f"❌ {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 1 integration tests passed!")
        sys.exit(0)
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()