#!/usr/bin/env python
"""
Quick test to verify NAS configuration imports work correctly
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

print("=" * 60)
print("🧪 Testing NAS Configuration Module Imports")
print("=" * 60)

try:
    print("\n1. Testing nas_config package import...")
    from nas_config import nas_configuration
    print("   ✅ nas_config.nas_configuration imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import nas_config.nas_configuration: {e}")
    sys.exit(1)

try:
    print("\n2. Testing get_nas_config import...")
    from nas_config.nas_configuration import get_nas_config, get_active_nas_path
    print("   ✅ Functions imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import functions: {e}")
    sys.exit(1)

try:
    print("\n3. Testing get_active_nas_path function...")
    active_path = get_active_nas_path()
    print(f"   ✅ Active NAS path: {active_path}")
except Exception as e:
    print(f"   ❌ Failed to get active NAS path: {e}")
    sys.exit(1)

try:
    print("\n4. Testing get_nas_config function...")
    config = get_nas_config()
    print(f"   ✅ Got NAS config object")
    print(f"   ✅ Active alias: {config.config.get('active_alias', 'unknown')}")
except Exception as e:
    print(f"   ❌ Failed to get NAS config: {e}")
    sys.exit(1)

try:
    print("\n5. Testing indexing blueprint import...")
    from routes.indexing import indexing_bp
    print(f"   ✅ Indexing blueprint imported successfully")
    print(f"   ✅ Blueprint name: {indexing_bp.name}")
except ImportError as e:
    print(f"   ❌ Failed to import indexing blueprint: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ All imports successful!")
print("=" * 60)
print("\nNAS Configuration is ready to use!")
print(f"Active NAS: {active_path}")
