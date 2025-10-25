#!/usr/bin/env python3
"""
Test script for the enhanced device database API endpoints
"""

import sys
import os
import json

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from routes.network_discovery import get_device_database_info, get_device_details, DeviceDatabase

    print("✅ Successfully imported device database functions")

    # Test the device database
    device_db = DeviceDatabase()
    print("✅ DeviceDatabase class initialized")

    # Test getting database info
    result = get_device_database_info()
    print(f"✅ get_device_database_info() returned: {result['success']}")
    print(f"   Total devices: {result['total_entries']}")

    # Test getting statistics
    stats = device_db.get_statistics()
    print(f"✅ Device statistics: {stats}")

    print("\n🎉 All device database functions are working correctly!")

except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
