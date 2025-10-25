#!/usr/bin/env python3
"""
Test device scanning with proper authentication
"""
import requests
import json

def test_authenticated_scanning():
    """Test device scanning with proper authentication"""
    print("🔐 Testing Device Scanning with Authentication...")
    
    session = requests.Session()
    
    # Step 1: Login
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    print("📱 Logging in as admin...")
    login_response = session.post("http://localhost:5000/api/auth/login", json=login_data)
    print(f"   Login Status: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print(f"   ❌ Login failed: {login_response.text}")
        return False
    
    print("   ✅ Login successful!")
    
    # Step 2: Test device list
    print("\n📋 Testing device list...")
    devices_response = session.get("http://localhost:5000/api/devices")
    print(f"   Devices Status: {devices_response.status_code}")
    
    if devices_response.status_code == 200:
        devices_data = devices_response.json()
        print(f"   ✅ Got {len(devices_data.get('devices', []))} devices")
    else:
        print(f"   ❌ Devices request failed: {devices_response.text}")
    
    # Step 3: Test network scanning
    print("\n🌐 Testing network discovery scan...")
    scan_data = {
        "ip_range": "127.0.0.1",
        "ports": [80, 443, 22],
        "max_threads": 5
    }
    
    scan_response = session.post("http://localhost:5000/api/devices/network/discovery-scan", json=scan_data)
    print(f"   Scan Status: {scan_response.status_code}")
    
    if scan_response.status_code == 200:
        scan_result = scan_response.json()
        print("   ✅ Network scan successful!")
        print(f"   📊 Total devices found: {scan_result.get('total_found', 0)}")
        print(f"   🏥 Medical devices: {scan_result.get('medical_found', 0)}")
        
        if scan_result.get('discovered_devices'):
            print("   📱 Discovered devices:")
            for device in scan_result['discovered_devices']:
                print(f"      - {device.get('ip_address')}: {device.get('open_ports', [])}")
        
        return True
    else:
        print(f"   ❌ Scan failed: {scan_response.text}")
        return False

if __name__ == "__main__":
    print("🧪 Device Scanning Authentication Test")
    print("=" * 45)
    
    if test_authenticated_scanning():
        print("\n✅ All tests PASSED! Device scanning works with proper authentication.")
    else:
        print("\n❌ Tests FAILED! There's an authentication or scanning issue.")
