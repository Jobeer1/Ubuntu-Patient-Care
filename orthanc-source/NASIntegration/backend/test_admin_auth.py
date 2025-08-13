#!/usr/bin/env python3
"""
Test script to verify admin authentication is working
"""

import requests
import sys

def test_auth_flow():
    """Test the complete authentication flow"""
    base_url = "http://localhost:5000"
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    print("🔐 Testing Admin Authentication Flow")
    print("=" * 50)
    
    # Step 1: Login
    print("1. Testing login...")
    login_data = {
        'username': 'admin',
        'pin': 'admin123'  # Using pin field as defined in auth_api
    }
    
    try:
        response = session.post(f"{base_url}/api/auth/login", json=login_data, timeout=10)
        print(f"   Login Status: {response.status_code}")
        
        if response.status_code == 200:
            login_result = response.json()
            print(f"   ✅ Login successful")
            print(f"   User: {login_result.get('user', {}).get('username')}")
            print(f"   Role: {login_result.get('user', {}).get('role')}")
        else:
            print(f"   ❌ Login failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Login error: {e}")
        return False
    
    # Step 2: Test admin endpoint
    print("\n2. Testing admin endpoint access...")
    try:
        response = session.get(f"{base_url}/api/admin/users", timeout=10)
        print(f"   Admin API Status: {response.status_code}")
        
        if response.status_code == 200:
            users_data = response.json()
            print(f"   ✅ Admin access successful")
            print(f"   Users returned: {len(users_data.get('users', []))}")
        else:
            print(f"   ❌ Admin access failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Admin endpoint error: {e}")
        return False
    
    print("\n✅ Authentication flow working correctly!")
    return True

if __name__ == '__main__':
    if test_auth_flow():
        sys.exit(0)
    else:
        sys.exit(1)
