#!/usr/bin/env python3
"""
Test the new /patients route and South African theme consistency
"""

import requests
import sys
import os

# Configuration
BASE_URL = "http://localhost:5000"
TEST_ENDPOINTS = [
    {"url": "/", "name": "Dashboard", "auth_required": True},
    {"url": "/patients", "name": "Patient Management", "auth_required": True},
    {"url": "/api/nas/search/stats", "name": "Search Statistics API", "auth_required": False},
    {"url": "/api/health", "name": "Health Check", "auth_required": False}
]

def test_endpoint(endpoint):
    """Test a single endpoint"""
    try:
        url = f"{BASE_URL}{endpoint['url']}"
        response = requests.get(url, timeout=5)
        
        print(f"  {endpoint['name']}: ", end="")
        
        if endpoint['auth_required'] and response.status_code == 302:
            print("🔒 Redirected to login (authentication working)")
            return True
        elif response.status_code == 200:
            print("✅ Accessible")
            return True
        else:
            print(f"❌ HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"  {endpoint['name']}: ❌ Connection refused (app not running?)")
        return False
    except Exception as e:
        print(f"  {endpoint['name']}: ❌ Error: {e}")
        return False

def main():
    print("🏥🇿🇦 South African Medical Imaging System - Route Testing")
    print("=" * 65)
    
    # Test if Flask app is running
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Flask app is running: {health_data.get('message', 'N/A')}")
        else:
            print("⚠️ Flask app running but health check failed")
    except requests.exceptions.ConnectionError:
        print("❌ Flask app is not running or not accessible")
        print("\nTo start the app, run:")
        print("cd C:\\Users\\Admin\\Desktop\\ELC\\Ubuntu-Patient-Care\\Orthanc\\orthanc-source\\NASIntegration\\backend")
        print("python app.py")
        return
    
    print("\n📋 Testing Endpoints:")
    print("-" * 40)
    
    success_count = 0
    total_count = len(TEST_ENDPOINTS)
    
    for endpoint in TEST_ENDPOINTS:
        if test_endpoint(endpoint):
            success_count += 1
    
    print("\n📊 Test Results:")
    print("-" * 40)
    print(f"✅ Successful: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 All endpoints are working correctly!")
        print("\nNext steps:")
        print("1. Visit http://localhost:5000/ to see the dashboard")
        print("2. Navigate to http://localhost:5000/patients for patient search")
        print("3. Check theme consistency across pages")
    else:
        print("⚠️ Some endpoints have issues. Check the Flask app logs.")

if __name__ == "__main__":
    main()