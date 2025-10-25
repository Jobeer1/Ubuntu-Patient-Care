#!/usr/bin/env python3
"""Test script to verify API fixes"""

import requests
import json

def test_api_endpoints():
    """Test the newly created API endpoints"""
    base_url = "https://localhost:5443"
    
    # Test System API
    print("Testing System API...")
    try:
        response = requests.get(f"{base_url}/api/system/health", verify=False)
        print(f"System Health: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"System API Error: {e}")
    
    # Test Security API
    print("\nTesting Security API...")
    try:
        response = requests.get(f"{base_url}/api/security/auth/check?user_id=demo_user", verify=False)
        print(f"Auth Check: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Security API Error: {e}")
    
    # Test Medical API
    print("\nTesting Medical API...")
    try:
        response = requests.get(f"{base_url}/api/medical/templates", verify=False)
        print(f"Medical Templates: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Medical API Error: {e}")
    
    # Test Reports API
    print("\nTesting Reports API...")
    try:
        response = requests.get(f"{base_url}/api/reports/list?user_id=demo_user", verify=False)
        print(f"Reports List: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Reports API Error: {e}")
    
    # Test Demo Shortcuts API
    print("\nTesting Demo Shortcuts API...")
    try:
        response = requests.get(f"{base_url}/api/voice/shortcuts/demo?user_id=demo_user", verify=False)
        print(f"Demo Shortcuts: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Demo Shortcuts API Error: {e}")

if __name__ == "__main__":
    print("Testing Medical Reporting Module API Fixes...")
    test_api_endpoints()
    print("\nTest completed!")