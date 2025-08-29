#!/usr/bin/env python3
"""
Quick test script to verify device scanning functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import requests
import json

def test_device_scanning():
    """Test the device scanning API"""
    print("🔍 Testing Device Scanning API...")
    
    # Test the discovery scan endpoint
    try:
        # First login as admin
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        session = requests.Session()
        
        print("📱 Logging in as admin...")
        login_response = session.post("http://localhost:5000/api/auth/login", json=login_data)
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.text}")
            return False
        
        print("✅ Login successful!")
        
        # Now test device scanning
        scan_data = {
            "ip_range": "127.0.0.1",  # Test with localhost only
            "ports": [80, 443, 22, 104],
            "max_threads": 5
        }
        
        print("🌐 Testing network discovery scan...")
        scan_response = session.post("http://localhost:5000/api/devices/network/discovery-scan", json=scan_data)
        
        print(f"📊 Scan Response Status: {scan_response.status_code}")
        
        if scan_response.status_code == 200:
            result = scan_response.json()
            print(f"✅ Scan successful!")
            print(f"   - Total devices found: {result.get('total_found', 0)}")
            print(f"   - Medical devices: {result.get('medical_found', 0)}")
            print(f"   - Scan parameters: {result.get('scan_parameters', {})}")
            
            if result.get('discovered_devices'):
                print("\n📱 Discovered devices:")
                for device in result['discovered_devices']:
                    print(f"   - {device.get('ip_address')}: {device.get('open_ports', [])}")
            
            return True
        else:
            print(f"❌ Scan failed: {scan_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing device scanning: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Device Scanning Test Script")
    print("=" * 40)
    
    if test_device_scanning():
        print("\n✅ Device scanning test PASSED!")
    else:
        print("\n❌ Device scanning test FAILED!")
