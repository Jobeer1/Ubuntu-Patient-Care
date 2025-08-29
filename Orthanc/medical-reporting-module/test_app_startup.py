#!/usr/bin/env python3
"""
Test script to check if the app starts without errors
"""

import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_app_startup():
    """Test if the app can start without import errors"""
    try:
        print("Testing app imports...")
        
        # Test critical imports first
        print("1. Testing security service...")
        from services.security_service import security_service
        print("   ✓ Security service imported")
        
        print("2. Testing layout manager...")
        from services.layout_manager import layout_manager
        print("   ✓ Layout manager imported")
        
        print("3. Testing app factory...")
        from core.app_factory import create_app
        print("   ✓ App factory imported")
        
        print("4. Testing app creation...")
        app = create_app('development')
        print("   ✓ App created successfully")
        
        print("\n✅ All tests passed! App should start correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_app_startup()
    sys.exit(0 if success else 1)