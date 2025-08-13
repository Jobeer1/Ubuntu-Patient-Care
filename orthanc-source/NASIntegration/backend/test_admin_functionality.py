#!/usr/bin/env python3
"""
Test admin dashboard functionality
"""

import requests
import json

def test_admin_functionality():
    """Test all admin dashboard features"""
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    print("🧪 Testing Admin Dashboard Functionality")
    print("=" * 50)
    
    # Step 1: Login
    print("1. Logging in...")
    login_data = {'username': 'admin', 'pin': 'admin123'}
    response = session.post(f"{base_url}/api/auth/login", json=login_data)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        return False
    
    print("✅ Login successful")
    
    # Step 2: Test user listing
    print("\n2. Testing user listing...")
    response = session.get(f"{base_url}/api/admin/users")
    
    if response.status_code != 200:
        print(f"❌ User listing failed: {response.text}")
        return False
    
    users_data = response.json()
    print(f"✅ Found {len(users_data.get('users', []))} users")
    
    # Step 3: Test user creation
    print("\n3. Testing user creation...")
    new_user = {
        "username": "testuser",
        "email": "test@hospital.co.za",
        "name": "Test User",
        "role": "nurse",
        "province": "gauteng",
        "facility_name": "Test Hospital",
        "pin": "test123",
        "phone_number": "+27-11-111-1111"
    }
    
    response = session.post(f"{base_url}/api/admin/users", 
                           json=new_user, 
                           headers={'Content-Type': 'application/json'})
    
    if response.status_code == 201:
        result = response.json()
        if result.get('success'):
            print("✅ User creation successful")
            new_user_id = result.get('user_id')
            
            # Step 4: Test user update
            print("\n4. Testing user update...")
            update_data = {"name": "Updated Test User", "role": "technologist"}
            response = session.put(f"{base_url}/api/admin/users/{new_user_id}",
                                 json=update_data,
                                 headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200 and response.json().get('success'):
                print("✅ User update successful")
            else:
                print(f"❌ User update failed: {response.text}")
            
            # Step 5: Test user deletion
            print("\n5. Testing user deletion...")
            response = session.delete(f"{base_url}/api/admin/users/{new_user_id}")
            
            if response.status_code == 200 and response.json().get('success'):
                print("✅ User deletion successful")
            else:
                print(f"❌ User deletion failed: {response.text}")
                
        else:
            print(f"❌ User creation failed: {result.get('error')}")
    else:
        print(f"❌ User creation failed: {response.text}")
    
    # Step 6: Test debug endpoint
    print("\n6. Testing debug endpoint...")
    response = session.get(f"{base_url}/api/admin/debug/session")
    
    if response.status_code == 200:
        debug_data = response.json()
        print(f"✅ Debug endpoint working - Admin status: {debug_data.get('is_admin')}")
    else:
        print(f"❌ Debug endpoint failed: {response.text}")
    
    print("\n🎉 Admin dashboard functionality test completed!")
    return True

if __name__ == '__main__':
    test_admin_functionality()
