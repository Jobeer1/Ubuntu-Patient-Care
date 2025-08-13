#!/usr/bin/env python3
"""
Test script for Simple Orthanc Management System
Verifies that the new practical system works correctly
"""

import requests
import json
import time
import sys
import os

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_USER = {
    "username": "admin",
    "password": "admin123"
}

def test_authentication():
    """Test admin authentication"""
    print("🔐 Testing authentication...")
    
    # Login
    response = requests.post(f"{BASE_URL}/api/auth/login", 
                           json=TEST_USER,
                           headers={'Content-Type': 'application/json'})
    
    if response.status_code == 200:
        print("✅ Authentication successful")
        return response.cookies
    else:
        print(f"❌ Authentication failed: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def test_server_status(cookies):
    """Test server status endpoint"""
    print("\n📊 Testing server status...")
    
    response = requests.get(f"{BASE_URL}/api/orthanc/status", cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            status = data.get('status', {})
            print(f"✅ Server status: {status.get('status', 'unknown')}")
            print(f"   Last check: {status.get('last_check', 'unknown')}")
            return True
        else:
            print(f"❌ Status check failed: {data.get('error', 'unknown error')}")
    else:
        print(f"❌ Status endpoint failed: {response.status_code}")
    
    return False

def test_quick_stats(cookies):
    """Test quick stats endpoint"""
    print("\n📈 Testing quick stats...")
    
    response = requests.get(f"{BASE_URL}/api/orthanc/quick-stats", cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            stats = data.get('stats', {})
            print(f"✅ Quick stats retrieved:")
            print(f"   Server status: {stats.get('server_status', 'unknown')}")
            print(f"   Studies count: {stats.get('studies_count', 0)}")
            print(f"   Storage used: {stats.get('storage_used_mb', 0)} MB")
            print(f"   Active shares: {stats.get('active_shares', 0)}")
            print(f"   Total doctors: {stats.get('total_doctors', 0)}")
            return True
        else:
            print(f"❌ Quick stats failed: {data.get('error', 'unknown error')}")
    else:
        print(f"❌ Quick stats endpoint failed: {response.status_code}")
    
    return False

def test_quick_setup(cookies):
    """Test quick setup endpoint"""
    print("\n🚀 Testing quick setup...")
    
    setup_data = {
        "hospital_name": "Test SA Healthcare Facility",
        "web_port": 8042,
        "dicom_port": 4242,
        "aet_title": "TEST_ORTHANC",
        "allow_remote": True
    }
    
    response = requests.post(f"{BASE_URL}/api/orthanc/quick-setup", 
                           json=setup_data,
                           cookies=cookies,
                           headers={'Content-Type': 'application/json'})
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Quick setup completed:")
            print(f"   Config updated: {data.get('config_updated', False)}")
            print(f"   Server started: {data.get('server_started', False)}")
            print(f"   Web URL: {data.get('web_url', 'unknown')}")
            print(f"   DICOM port: {data.get('dicom_port', 'unknown')}")
            return True
        else:
            print(f"❌ Quick setup failed: {data.get('error', 'unknown error')}")
    else:
        print(f"❌ Quick setup endpoint failed: {response.status_code}")
    
    return False

def test_patient_share(cookies):
    """Test patient sharing functionality"""
    print("\n👥 Testing patient sharing...")
    
    share_data = {
        "patient_name": "Test Patient",
        "patient_id": "TEST001",
        "study_date": "2024-01-15",
        "study_description": "Test Chest X-Ray"
    }
    
    response = requests.post(f"{BASE_URL}/api/orthanc/patient-shares", 
                           json=share_data,
                           cookies=cookies,
                           headers={'Content-Type': 'application/json'})
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Patient share created:")
            print(f"   Share token: {data.get('share_token', 'unknown')[:20]}...")
            print(f"   Share URL: {data.get('share_url', 'unknown')}")
            print(f"   Expires in: {data.get('expires_in_days', 0)} days")
            return True
        else:
            print(f"❌ Patient share failed: {data.get('error', 'unknown error')}")
    else:
        print(f"❌ Patient share endpoint failed: {response.status_code}")
    
    return False

def test_doctor_management(cookies):
    """Test referring doctor management"""
    print("\n👨‍⚕️ Testing doctor management...")
    
    doctor_data = {
        "name": "Dr. Test Mthembu",
        "email": "test.doctor@hospital.co.za",
        "phone": "+27-11-123-4567",
        "practice_name": "Test Medical Practice",
        "hpcsa_number": "PR0123456"
    }
    
    response = requests.post(f"{BASE_URL}/api/orthanc/doctors", 
                           json=doctor_data,
                           cookies=cookies,
                           headers={'Content-Type': 'application/json'})
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Doctor added successfully:")
            print(f"   Doctor ID: {data.get('doctor_id', 'unknown')}")
            return True
        else:
            print(f"❌ Doctor addition failed: {data.get('error', 'unknown error')}")
    else:
        print(f"❌ Doctor endpoint failed: {response.status_code}")
    
    return False

def test_health_check():
    """Test health check endpoint (no auth required)"""
    print("\n🏥 Testing health check...")
    
    response = requests.get(f"{BASE_URL}/api/orthanc/health-check")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"✅ Health check passed:")
            print(f"   Healthy: {data.get('healthy', False)}")
            print(f"   Status: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"❌ Health check failed: {data.get('error', 'unknown error')}")
    else:
        print(f"❌ Health check endpoint failed: {response.status_code}")
    
    return False

def main():
    """Run all tests"""
    print("🇿🇦 Simple Orthanc Management System - Test Suite")
    print("=" * 60)
    
    # Test health check first (no auth required)
    health_ok = test_health_check()
    
    # Test authentication
    cookies = test_authentication()
    if not cookies:
        print("\n❌ Cannot continue without authentication")
        sys.exit(1)
    
    # Run authenticated tests
    tests = [
        ("Server Status", lambda: test_server_status(cookies)),
        ("Quick Stats", lambda: test_quick_stats(cookies)),
        ("Quick Setup", lambda: test_quick_setup(cookies)),
        ("Patient Sharing", lambda: test_patient_share(cookies)),
        ("Doctor Management", lambda: test_doctor_management(cookies))
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
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results) + 1  # +1 for health check
    
    if health_ok:
        passed += 1
        print("✅ Health Check")
    else:
        print("❌ Health Check")
    
    for test_name, result in results:
        if result:
            passed += 1
            print(f"✅ {test_name}")
        else:
            print(f"❌ {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Simple Orthanc Management System is working correctly.")
        sys.exit(0)
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()