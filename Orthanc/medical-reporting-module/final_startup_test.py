#!/usr/bin/env python3
"""
Final comprehensive test to ensure the app starts correctly
"""

import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_critical_imports():
    """Test all critical imports that were causing issues"""
    
    tests = [
        ("Security Service", "from services.security_service import security_service"),
        ("Layout Manager", "from services.layout_manager import layout_manager"),
        ("Service Manager", "from core.service_manager import ServiceManager"),
        ("App Factory", "from core.app_factory import create_app, socketio"),
        ("Reporting Engine", "from core.reporting_engine import reporting_engine"),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, import_statement in tests:
        try:
            exec(import_statement)
            print(f"✅ {test_name}: OK")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name}: FAILED - {e}")
    
    return passed, total

def test_app_creation():
    """Test Flask app creation"""
    try:
        print("\n🔧 Testing Flask app creation...")
        from core.app_factory import create_app
        
        app = create_app('development')
        print("✅ Flask app created successfully")
        
        # Test that the app has the expected configuration
        if hasattr(app, 'service_manager'):
            print("✅ Service manager attached to app")
        else:
            print("⚠️  Service manager not found on app")
        
        return True
        
    except Exception as e:
        print(f"❌ Flask app creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🧪 Final Startup Test")
    print("=" * 50)
    
    # Test imports
    print("1. Testing Critical Imports...")
    passed, total = test_critical_imports()
    
    if passed != total:
        print(f"\n❌ Import tests failed: {passed}/{total} passed")
        return False
    
    # Test app creation
    print("\n2. Testing App Creation...")
    if not test_app_creation():
        return False
    
    print("\n" + "=" * 50)
    print("🎉 ALL TESTS PASSED!")
    print("✅ The app should now start correctly")
    print("\nTo start the app:")
    print("   python app.py")
    print("\nTo access from LAN:")
    print("   http://[YOUR_IP]:5001")
    print("   (Find your IP with: ipconfig)")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)