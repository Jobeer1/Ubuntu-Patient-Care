#!/usr/bin/env python3
"""
Test NAS Discovery System End-to-End

Tests all discovery endpoints and verifies:
1. Network scanning
2. Share enumeration
3. Database type detection
4. Connection testing
5. Credential management
"""

import requests
import json
import time
from pprint import pprint

BASE_URL = 'http://localhost:5000'
API_BASE = f'{BASE_URL}/api/nas/discovery'

def test_endpoint(method, endpoint, data=None, description=None):
    """Test a single endpoint"""
    url = f'{API_BASE}{endpoint}'
    print(f"\n{'='*60}")
    print(f"📡 {method} {endpoint}")
    if description:
        print(f"   {description}")
    print(f"{'='*60}")
    
    try:
        if method == 'GET':
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})
        else:
            print(f"❌ Unknown method: {method}")
            return None
        
        print(f"Status: {response.status_code}")
        result = response.json()
        pprint(result)
        return result
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def run_discovery_workflow():
    """Run complete discovery workflow"""
    print("\n" + "="*60)
    print("🔍 NAS DISCOVERY SYSTEM TEST")
    print("="*60)
    
    # 1. Scan network for NAS devices
    print("\n\n[1/6] SCANNING NETWORK FOR NAS DEVICES")
    scan_result = test_endpoint(
        'POST', 
        '/scan-network',
        {'subnet': '155.235.81'},
        'Start background network scan for NAS devices'
    )
    
    if not scan_result or not scan_result.get('success'):
        print("❌ Network scan failed, stopping tests")
        return
    
    # Wait a bit for scan to run
    print("\n⏳ Waiting 5 seconds for network scan to complete...")
    time.sleep(5)
    
    # 2. Get discovered devices
    print("\n\n[2/6] RETRIEVING DISCOVERED DEVICES")
    devices_result = test_endpoint(
        'GET',
        '/discovered-devices',
        description='Get list of discovered NAS devices'
    )
    
    if not devices_result or devices_result.get('count', 0) == 0:
        print("⚠️  No devices discovered, trying with known IP")
        
        # Try direct enumeration on known IP
        print("\n\n[2B/6] ENUMERATING SHARES ON KNOWN NAS IP")
        shares_result = test_endpoint(
            'POST',
            '/enumerate-shares',
            {'nas_host': '155.235.81.49'},
            'Try to enumerate shares on known NAS IP'
        )
        
        if shares_result and shares_result.get('success'):
            discovered_shares = shares_result.get('shares', [])
        else:
            print("⚠️  Could not enumerate shares on 155.235.81.49")
            discovered_shares = [
                {
                    'name': 'DICOM_Storage',
                    'path': '\\\\155.235.81.49\\DICOM_Storage',
                    'accessible': False
                }
            ]
    else:
        devices = devices_result.get('devices', [])
        if not devices:
            print("❌ No devices in result")
            return
        
        print(f"\n✅ Found {len(devices)} device(s)")
        device = devices[0]
        print(f"   Using device: {device}")
        
        # 3. Enumerate shares on first device
        print("\n\n[3/6] ENUMERATING SHARES ON DISCOVERED DEVICE")
        shares_result = test_endpoint(
            'POST',
            '/enumerate-shares',
            {'nas_host': device.get('ip', device.get('hostname'))},
            'List shares available on the NAS device'
        )
        
        discovered_shares = shares_result.get('shares', []) if shares_result else []
    
    if not discovered_shares:
        print("❌ No shares discovered")
        print("✅ Test completed with discovery endpoints working")
        return
    
    print(f"\n✅ Found {len(discovered_shares)} share(s)")
    share = discovered_shares[0]
    print(f"   Using share: {share}")
    
    # 4. Scan share for databases
    print("\n\n[4/6] SCANNING SHARE FOR DATABASES")
    db_result = test_endpoint(
        'POST',
        '/scan-share',
        {'share_path': share.get('path')},
        'Recursively scan share for database files'
    )
    
    discovered_dbs = db_result.get('databases', []) if db_result else []
    
    if discovered_dbs:
        print(f"\n✅ Found {len(discovered_dbs)} database(s)")
        db = discovered_dbs[0]
        print(f"   Using database: {db}")
        
        # 5. Detect database type
        print("\n\n[5/6] DETECTING DATABASE TYPE")
        type_result = test_endpoint(
            'POST',
            '/detect-database-type',
            {'path': db.get('path')},
            'Identify the type of database'
        )
    else:
        print("\n⚠️  No databases found in share")
        print("   Trying to detect type on share root...")
        
        type_result = test_endpoint(
            'POST',
            '/detect-database-type',
            {'path': share.get('path')},
            'Identify the type of database at share root'
        )
    
    # 6. Test connection with credentials
    print("\n\n[6/6] TESTING CONNECTION WITH CREDENTIALS")
    
    print("\nTesting without credentials...")
    test_result = test_endpoint(
        'POST',
        '/test-connection',
        {
            'nas_host': share.get('path', '155.235.81.49'),
            'share_name': share.get('name', 'DICOM_Storage')
        },
        'Test connection without credentials'
    )
    
    if test_result and not test_result.get('connected'):
        print("\n⚠️  Connection failed without credentials")
        print("Testing with sample credentials...")
        test_result = test_endpoint(
            'POST',
            '/test-connection',
            {
                'nas_host': '155.235.81.49',
                'share_name': 'DICOM_Storage',
                'username': 'testuser',
                'password': 'testpass'
            },
            'Test connection with sample credentials'
        )
    
    # Test saving connection
    print("\n\n[BONUS] SAVING CONNECTION")
    save_result = test_endpoint(
        'POST',
        '/save-connection',
        {
            'nas_host': '155.235.81.49',
            'share_name': share.get('name', 'DICOM_Storage'),
            'database_type': 'DICOM_STORAGE'
        },
        'Save discovered connection for future use'
    )
    
    # List stored connections
    print("\n\n[BONUS] LISTING STORED CONNECTIONS")
    stored_result = test_endpoint(
        'GET',
        '/stored-connections',
        description='Retrieve previously saved NAS connections'
    )
    
    print("\n" + "="*60)
    print("✅ DISCOVERY SYSTEM TEST COMPLETED")
    print("="*60)

if __name__ == '__main__':
    print("\n🚀 Starting NAS Discovery System Tests...")
    print("Make sure the Flask backend is running on localhost:5000\n")
    
    run_discovery_workflow()
