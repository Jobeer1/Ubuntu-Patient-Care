#!/usr/bin/env python3
"""
Simple test script to check if the server is running and accessible
"""

import requests
import json

def test_server():
    base_url = "http://localhost:5000"
    
    print("Testing server connectivity...")
    
    # Test 1: Basic server ping
    try:
        response = requests.get(f"{base_url}/api/auth/status", timeout=5)
        print(f"✓ Server is running - Status endpoint: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Server connection failed: {e}")
        return
    
    # Test 2: Login
    try:
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        session = requests.Session()
        response = session.post(f"{base_url}/api/auth/login", 
                              json=login_data,
                              headers={'Content-Type': 'application/json'})
        
        print(f"✓ Login attempt: {response.status_code}")
        if response.status_code == 200:
            print(f"  Login response: {response.json()}")
        else:
            print(f"  Login failed: {response.text}")
            
        # Test 3: Admin users endpoint
        response = session.get(f"{base_url}/api/admin/users")
        print(f"✓ Admin users endpoint: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Users returned: {len(data.get('users', []))}")
        else:
            print(f"  Admin endpoint failed: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}")

if __name__ == "__main__":
    test_server()
