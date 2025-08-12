#!/usr/bin/env python3
"""
Test script to verify device management endpoints are working
"""

import requests
import json
import sys

def test_device_endpoints():
    """Test device management endpoints"""
    base_url = "http://localhost:5000"
    
    print("🧪 Testing Device Management Endpoints")
    print("=" * 50)
    
    # Test 1: Get devices
    print("\n1. Testing GET /api/devices")
    try:
        response = requests.get(f"{base_url}/api/devices", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test 2: Network discovery scan
    print("\n2. Testing POST /api/devices/network/discovery-scan")
    try:
        payload = {
            "ip_range": "192.168.1.1-192.168.1.10",
            "ports": [104, 80, 443],
            "max_threads": 5
        }
        response = requests.post(
            f"{base_url}/api/devices/network/discovery-scan", 
            json=payload, 
            timeout=30
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {len(data.get('discovered_devices', []))} devices")
            print(f"   Medical devices: {len(data.get('medical_devices', []))}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test 3: ARP scan
    print("\n3. Testing POST /api/devices/network/arp-scan")
    try:
        response = requests.post(f"{base_url}/api/devices/network/arp-scan", timeout=30)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {len(data.get('discovered_devices', []))} devices")
            print(f"   Medical devices: {len(data.get('medical_devices', []))}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test 4: Get modality types
    print("\n4. Testing GET /api/devices/modality-types")
    try:
        response = requests.get(f"{base_url}/api/devices/modality-types", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Available modalities: {len(data.get('modality_types', []))}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test 5: Get departments
    print("\n5. Testing GET /api/devices/departments")
    try:
        response = requests.get(f"{base_url}/api/devices/departments", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Available departments: {len(data.get('departments', []))}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Device endpoint testing completed!")

if __name__ == "__main__":
    test_device_endpoints()