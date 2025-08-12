#!/usr/bin/env python3
"""
Simple test script for the authentication API
"""

import requests
import json

def test_login():
    """Test the login endpoint"""
    url = "http://localhost:5000/api/auth/login"
    
    # Test data
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(url, json=login_data)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Content: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Login successful! User: {data.get('user', {}).get('name', 'Unknown')}")
            return data
        else:
            print(f"Login failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error testing login: {e}")
        return None

def test_users_endpoint(session_token=None):
    """Test the users endpoint"""
    url = "http://localhost:5000/api/admin/users"
    
    headers = {}
    if session_token:
        headers['Authorization'] = f'Bearer {session_token}'
    
    try:
        response = requests.get(url, headers=headers)
        
        print(f"\nUsers endpoint - Status Code: {response.status_code}")
        print(f"Response Content: {response.text}")
        
    except Exception as e:
        print(f"Error testing users endpoint: {e}")

if __name__ == "__main__":
    print("🔐 Testing South African Healthcare Authentication System")
    print("=" * 60)
    
    # Test login
    result = test_login()
    
    # Test admin endpoint
    if result:
        session_token = result.get('user', {}).get('session_token')
        test_users_endpoint(session_token)
    
    print("\n✅ Test complete!")
