#!/usr/bin/env python3
"""
Diagnose server issues and check endpoint availability
"""

import requests
import time
import sys

def check_server_health():
    """Check if the server is running and responding"""
    base_url = "http://localhost:5000"
    
    print("🏥 South African Medical Imaging System - Server Diagnostics")
    print("=" * 60)
    
    # Test 1: Basic server health
    print("\n1. Testing server health...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Server is responding")
            data = response.json()
            print(f"   System: {data.get('system', 'Unknown')}")
            print(f"   Status: {data.get('status', 'Unknown')}")
        else:
            print(f"   ❌ Server health check failed: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("   ❌ Cannot connect to server - is it running?")
        print("   💡 Start the server with: python app.py")
        return False
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return False
    
    # Test 2: Device endpoints
    print("\n2. Testing device endpoints...")
    device_endpoints = [
        ("/api/devices", "GET"),
        ("/api/devices/modality-types", "GET"),
        ("/api/devices/departments", "GET"),
        ("/api/devices/network/arp-scan", "POST"),
        ("/api/devices/network/discovery-scan", "POST")
    ]
    
    working_endpoints = 0
    for endpoint, method in device_endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{base_url}{endpoint}", timeout=10)
            else:
                response = requests.post(f"{base_url}{endpoint}", 
                                       json={"ip_range": "192.168.1.1"}, 
                                       timeout=10)
            
            if response.status_code == 200:
                print(f"   ✅ {method:4} {endpoint}")
                working_endpoints += 1
            else:
                print(f"   ❌ {method:4} {endpoint} - Status: {response.status_code}")
        except Exception as e:
            print(f"   ❌ {method:4} {endpoint} - Error: {e}")
    
    print(f"\n   📊 Working endpoints: {working_endpoints}/{len(device_endpoints)}")
    
    # Test 3: CORS headers
    print("\n3. Testing CORS headers...")
    try:
        response = requests.options(f"{base_url}/api/devices")
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
        }
        
        if any(cors_headers.values()):
            print("   ✅ CORS headers present")
            for header, value in cors_headers.items():
                if value:
                    print(f"      {header}: {value}")
        else:
            print("   ⚠️  No CORS headers found")
    except Exception as e:
        print(f"   ❌ CORS check error: {e}")
    
    # Test 4: Authentication endpoints
    print("\n4. Testing authentication...")
    try:
        response = requests.get(f"{base_url}/api/auth/test", timeout=5)
        if response.status_code == 200:
            print("   ✅ Auth endpoints working")
        else:
            print(f"   ❌ Auth test failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Auth test error: {e}")
    
    print("\n" + "=" * 60)
    
    if working_endpoints == len(device_endpoints):
        print("🎉 All device endpoints are working correctly!")
        print("\n💡 If the frontend still shows 404 errors:")
        print("   1. Check browser console for CORS errors")
        print("   2. Verify frontend is connecting to http://localhost:5000")
        print("   3. Try refreshing the browser page")
        print("   4. Check if any firewall is blocking the connection")
    else:
        print("⚠️  Some device endpoints are not working properly")
        print("   This might explain the 404 errors in the frontend")
    
    return True

if __name__ == "__main__":
    check_server_health()