#!/usr/bin/env python3
"""
Check what routes are available in the Flask app
"""

import sys
import os

# Add the backend directory to the path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

try:
    from app import app
    
    print("🔍 Available Routes in Flask App:")
    print("=" * 60)
    
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': rule.rule
        })
    
    # Sort routes by rule
    routes.sort(key=lambda x: x['rule'])
    
    device_routes = []
    nas_routes = []
    other_routes = []
    
    for route in routes:
        if '/api/devices' in route['rule']:
            device_routes.append(route)
        elif '/api/nas' in route['rule']:
            nas_routes.append(route)
        else:
            other_routes.append(route)
    
    print(f"\n📱 Device Management Routes ({len(device_routes)}):")
    print("-" * 40)
    for route in device_routes:
        methods = [m for m in route['methods'] if m not in ['HEAD', 'OPTIONS']]
        print(f"  {', '.join(methods):15} {route['rule']}")
    
    print(f"\n💾 NAS Discovery Routes ({len(nas_routes)}):")
    print("-" * 40)
    for route in nas_routes:
        methods = [m for m in route['methods'] if m not in ['HEAD', 'OPTIONS']]
        print(f"  {', '.join(methods):15} {route['rule']}")
    
    print(f"\n🌐 Other Routes ({len(other_routes)}):")
    print("-" * 40)
    for route in other_routes[:15]:  # Show first 15
        methods = [m for m in route['methods'] if m not in ['HEAD', 'OPTIONS']]
        print(f"  {', '.join(methods):15} {route['rule']}")
    
    if len(other_routes) > 15:
        print(f"  ... and {len(other_routes) - 15} more routes")
    
    print(f"\n📊 Summary:")
    print(f"  Total routes: {len(routes)}")
    print(f"  Device routes: {len(device_routes)}")
    print(f"  NAS routes: {len(nas_routes)}")
    print(f"  Other routes: {len(other_routes)}")
    
    if len(device_routes) == 0:
        print("\n❌ No device routes found! Device API endpoints are not registered.")
    elif len(nas_routes) == 0:
        print("\n❌ No NAS routes found! NAS Discovery endpoints are not registered.")
    else:
        print(f"\n✅ Device and NAS API endpoints are registered successfully!")

except Exception as e:
    print(f"❌ Error checking routes: {e}")
    import traceback
    traceback.print_exc()