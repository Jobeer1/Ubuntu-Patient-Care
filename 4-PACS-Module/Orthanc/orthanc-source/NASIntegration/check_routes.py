#!/usr/bin/env python3
"""
Check what Flask routes are registered
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import requests

def check_routes():
    """Check what routes are available"""
    print("🔍 Checking Flask App Routes...")
    
    # Test basic endpoints
    endpoints_to_test = [
        "/api/devices",
        "/api/devices/network/discovery-scan",
        "/api/auth/login",
        "/api/admin/users"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            url = f"http://localhost:5000{endpoint}"
            print(f"\n📡 Testing: {url}")
            
            if endpoint == "/api/devices/network/discovery-scan":
                # POST request for scan
                response = requests.post(url, json={"ip_range": "127.0.0.1"}, timeout=5)
            else:
                # GET request
                response = requests.get(url, timeout=5)
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 404:
                print("   ❌ Endpoint not found!")
            elif response.status_code in [200, 401, 403]:
                print("   ✅ Endpoint exists!")
            else:
                print(f"   ⚠️  Status: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Connection failed - server not running?")
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    check_routes()
