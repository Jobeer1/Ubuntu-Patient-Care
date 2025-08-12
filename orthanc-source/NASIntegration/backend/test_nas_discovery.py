#!/usr/bin/env python3
"""
Test NAS Discovery API endpoints
"""

import sys
import os
import json

# Add the backend directory to the path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

def test_nas_discovery_endpoints():
    """Test NAS discovery endpoints using Flask test client"""
    try:
        from app import app
        
        print("🏥 Testing NAS Discovery API Endpoints")
        print("=" * 60)
        
        with app.test_client() as client:
            # Test 1: GET /api/nas/suggestions
            print("\n1. Testing GET /api/nas/suggestions")
            response = client.get('/api/nas/suggestions')
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Success: {data.get('success', False)}")
                suggestions = data.get('suggestions', {})
                print(f"   IP ranges: {len(suggestions.get('common_ip_ranges', []))}")
                print(f"   Scan types: {len(suggestions.get('scan_types', []))}")
            else:
                print(f"   Error: {response.get_data(as_text=True)}")
            
            # Test 2: GET /api/nas/devices
            print("\n2. Testing GET /api/nas/devices")
            response = client.get('/api/nas/devices')
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Success: {data.get('success', False)}")
                print(f"   Device count: {data.get('total', 0)}")
            else:
                print(f"   Error: {response.get_data(as_text=True)}")
            
            # Test 3: POST /api/nas/quick-scan
            print("\n3. Testing POST /api/nas/quick-scan")
            response = client.post('/api/nas/quick-scan', 
                                 data=json.dumps({}),
                                 content_type='application/json')
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Success: {data.get('success', False)}")
                print(f"   Discovered devices: {len(data.get('discovered_devices', []))}")
            else:
                print(f"   Error: {response.get_data(as_text=True)}")
            
            # Test 4: POST /api/nas/discover
            print("\n4. Testing POST /api/nas/discover")
            payload = {
                "ip_range": "192.168.1.1-192.168.1.5",
                "scan_type": "quick",
                "max_threads": 5
            }
            response = client.post('/api/nas/discover', 
                                 data=json.dumps(payload),
                                 content_type='application/json')
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Success: {data.get('success', False)}")
                print(f"   Discovered devices: {len(data.get('discovered_devices', []))}")
            else:
                print(f"   Error: {response.get_data(as_text=True)}")
            
            # Test 5: GET /api/nas/config
            print("\n5. Testing GET /api/nas/config")
            response = client.get('/api/nas/config')
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Success: {data.get('success', False)}")
                config = data.get('config', {})
                print(f"   Supported NAS types: {len(config.get('supported_nas_types', []))}")
            else:
                print(f"   Error: {response.get_data(as_text=True)}")
            
            # Test 6: GET /api/nas/status
            print("\n6. Testing GET /api/nas/status")
            response = client.get('/api/nas/status')
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Success: {data.get('success', False)}")
                status = data.get('status', {})
                print(f"   System status: {status.get('discovery_system_status', 'unknown')}")
            else:
                print(f"   Error: {response.get_data(as_text=True)}")
            
            # Test 7: GET /api/nas/healthcare-presets
            print("\n7. Testing GET /api/nas/healthcare-presets")
            response = client.get('/api/nas/healthcare-presets')
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Success: {data.get('success', False)}")
                presets = data.get('healthcare_presets', {})
                print(f"   Healthcare presets: {len(presets)}")
            else:
                print(f"   Error: {response.get_data(as_text=True)}")
            
            # Test 8: GET /api/nas/sa-compliance
            print("\n8. Testing GET /api/nas/sa-compliance")
            response = client.get('/api/nas/sa-compliance')
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Success: {data.get('success', False)}")
                compliance = data.get('compliance_info', {})
                print(f"   Compliance sections: {len(compliance)}")
            else:
                print(f"   Error: {response.get_data(as_text=True)}")
        
        print("\n" + "=" * 60)
        print("✅ NAS Discovery API testing completed!")
        
    except Exception as e:
        print(f"❌ Error testing NAS Discovery API: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_nas_discovery_endpoints()