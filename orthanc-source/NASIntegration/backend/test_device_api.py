#!/usr/bin/env python3
"""
Test device API endpoints directly
"""

import sys
import os
import json

# Add the backend directory to the path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

def test_device_endpoints():
    """Test device endpoints using Flask test client"""
    try:
        from app import app
        
        print("🧪 Testing Device API Endpoints")
        print("=" * 50)
        
        with app.test_client() as client:
            # Test 1: GET /api/devices
            print("\n1. Testing GET /api/devices")
            response = client.get('/api/devices')
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Success: {data.get('success', False)}")
                print(f"   Device count: {data.get('count', 0)}")
            else:
                print(f"   Error: {response.get_data(as_text=True)}")
            
            # Test 2: GET /api/devices/modality-types
            print("\n2. Testing GET /api/devices/modality-types")
            response = client.get('/api/devices/modality-types')
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Success: {data.get('success', False)}")
                print(f"   Modality types: {len(data.get('modality_types', []))}")
            else:
                print(f"   Error: {response.get_data(as_text=True)}")
            
            # Test 3: GET /api/devices/departments
            print("\n3. Testing GET /api/devices/departments")
            response = client.get('/api/devices/departments')
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Success: {data.get('success', False)}")
                print(f"   Departments: {len(data.get('departments', []))}")
            else:
                print(f"   Error: {response.get_data(as_text=True)}")
            
            # Test 4: POST /api/devices/network/arp-scan
            print("\n4. Testing POST /api/devices/network/arp-scan")
            response = client.post('/api/devices/network/arp-scan')
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Success: {data.get('success', False)}")
                print(f"   Discovered devices: {len(data.get('discovered_devices', []))}")
            else:
                print(f"   Error: {response.get_data(as_text=True)}")
            
            # Test 5: POST /api/devices/network/discovery-scan
            print("\n5. Testing POST /api/devices/network/discovery-scan")
            payload = {
                "ip_range": "192.168.1.1-192.168.1.5",
                "ports": [104, 80],
                "max_threads": 2
            }
            response = client.post('/api/devices/network/discovery-scan', 
                                 data=json.dumps(payload),
                                 content_type='application/json')
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Success: {data.get('success', False)}")
                print(f"   Discovered devices: {len(data.get('discovered_devices', []))}")
            else:
                print(f"   Error: {response.get_data(as_text=True)}")
        
        print("\n" + "=" * 50)
        print("✅ Device API testing completed!")
        
    except Exception as e:
        print(f"❌ Error testing device API: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_device_endpoints()