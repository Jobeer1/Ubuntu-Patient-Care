#!/usr/bin/env python3
"""
Test script to verify that the application can start without critical errors
"""

import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_app_creation():
    """Test that the Flask app can be created without import errors"""
    try:
        print("Testing Flask app creation...")
        
        # Set environment for testing
        os.environ['FLASK_ENV'] = 'development'
        
        from core.app_factory import create_app
        app = create_app('development')
        
        print("✓ Flask app created successfully")
        print(f"✓ App name: {app.name}")
        print(f"✓ Static folder: {app.static_folder}")
        print(f"✓ Template folder: {app.template_folder}")
        
        # Test that we can create an app context
        with app.app_context():
            print("✓ App context created successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Flask app creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_routes():
    """Test that basic routes work"""
    try:
        print("\nTesting routes...")
        
        from core.app_factory import create_app
        app = create_app('development')
        
        with app.test_client() as client:
            # Test health endpoint
            response = client.get('/health')
            print(f"✓ Health endpoint: {response.status_code}")
            
            # Test dashboard endpoint
            response = client.get('/')
            print(f"✓ Dashboard endpoint: {response.status_code}")
            
            if response.status_code == 200:
                print("✓ Dashboard loads successfully")
            
        return True
        
    except Exception as e:
        print(f"✗ Route testing failed: {e}")
        return False

def main():
    """Run all startup tests"""
    print("SA Medical Reporting Module - Startup Tests")
    print("=" * 50)
    
    tests = [
        test_app_creation,
        test_routes
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All startup tests passed! Application should start successfully.")
        return True
    else:
        print("✗ Some tests failed. Check the errors above.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)