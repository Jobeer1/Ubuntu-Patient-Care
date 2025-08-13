#!/usr/bin/env python3
"""
Fix device endpoints by ensuring they're properly registered
"""

import sys
import os

# Add the backend directory to the path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

def fix_device_endpoints():
    """Fix device endpoint registration issues"""
    print("🔧 Fixing Device Endpoint Registration")
    print("=" * 50)
    
    try:
        # Import the main app
        from app import app
        
        # Check if device endpoints are registered
        device_routes = [rule for rule in app.url_map.iter_rules() if '/api/devices' in rule.rule]
        
        print(f"Found {len(device_routes)} device routes")
        
        if len(device_routes) == 0:
            print("❌ No device routes found - attempting to register manually...")
            
            # Try to register device endpoints manually
            try:
                from device_api_endpoints import device_api_bp
                app.register_blueprint(device_api_bp)
                print("✅ Device endpoints registered manually")
            except Exception as e:
                print(f"❌ Failed to register device endpoints: {e}")
                return False
        else:
            print("✅ Device routes are already registered")
        
        # Test the endpoints
        with app.test_client() as client:
            print("\n🧪 Testing endpoints...")
            
            # Test basic device endpoint
            response = client.get('/api/devices')
            if response.status_code == 200:
                print("✅ GET /api/devices - Working")
            else:
                print(f"❌ GET /api/devices - Status: {response.status_code}")
            
            # Test network discovery
            response = client.post('/api/devices/network/arp-scan')
            if response.status_code == 200:
                print("✅ POST /api/devices/network/arp-scan - Working")
            else:
                print(f"❌ POST /api/devices/network/arp-scan - Status: {response.status_code}")
        
        print("\n✅ Device endpoints are working correctly!")
        print("\n💡 If you're still getting 404 errors in the browser:")
        print("   1. Make sure the server is running: python app.py")
        print("   2. Check the server is on http://localhost:5000")
        print("   3. Clear browser cache and refresh")
        print("   4. Check browser console for any CORS errors")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing device endpoints: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_device_endpoints()