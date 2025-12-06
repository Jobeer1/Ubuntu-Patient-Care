#!/usr/bin/env python3
"""
Quick test to verify the application starts without errors
"""

import sys
import traceback

def test_app_creation():
    """Test that the app can be created without errors"""
    try:
        from core.app_factory import create_app
        
        print("🔍 Testing app creation...")
        app = create_app('development')
        
        print("✅ App created successfully!")
        print(f"✅ App name: {app.name}")
        print(f"✅ Debug mode: {app.debug}")
        
        # Test that we can get the app context
        with app.app_context():
            print("✅ App context works")
        
        return True
        
    except Exception as e:
        print(f"❌ App creation failed: {e}")
        print("Full traceback:")
        traceback.print_exc()
        return False

def test_api_imports():
    """Test that all API modules can be imported"""
    apis = [
        'api.voice_api',
        'api.reporting_api', 
        'api.layout_api',
        'api.sync_api',
        'api.realtime_api',
        'api.system_api',
        'api.dicom_api',
        'api.security_api',
        'api.demo_api',
        'api.auth_api',
        'api.medical_api',
        'api.reports_api'
    ]
    
    print("\n🔍 Testing API imports...")
    
    success_count = 0
    for api in apis:
        try:
            __import__(api)
            print(f"✅ {api}")
            success_count += 1
        except Exception as e:
            print(f"❌ {api}: {e}")
    
    print(f"\n📊 API Import Results: {success_count}/{len(apis)} successful")
    return success_count == len(apis)

def test_javascript_files():
    """Test that JavaScript files exist and are properly structured"""
    import os
    
    print("\n🔍 Testing JavaScript files...")
    
    js_files = [
        'frontend/static/js/voice-demo.js',
        'frontend/static/js/modules/audio-processor.js',
        'frontend/static/js/modules/ui-manager.js',
        'frontend/static/js/modules/transcription-service.js',
        'frontend/static/js/modules/shortcuts-manager.js'
    ]
    
    success_count = 0
    for js_file in js_files:
        if os.path.exists(js_file):
            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = len(content.splitlines())
                    
                if lines <= 500:
                    print(f"✅ {os.path.basename(js_file)}: {lines} lines")
                    success_count += 1
                else:
                    print(f"❌ {os.path.basename(js_file)}: {lines} lines (too long)")
            except Exception as e:
                print(f"❌ {os.path.basename(js_file)}: Error reading - {e}")
        else:
            print(f"❌ {js_file}: File not found")
    
    print(f"\n📊 JavaScript Files: {success_count}/{len(js_files)} valid")
    return success_count == len(js_files)

def main():
    """Run all startup tests"""
    print("🧪 Medical Reporting Module - Startup Tests\n")
    
    tests = [
        ("App Creation", test_app_creation),
        ("API Imports", test_api_imports), 
        ("JavaScript Files", test_javascript_files)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print('='*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! The application is ready to use.")
        return True
    else:
        print(f"\n⚠️ {len(results) - passed} test(s) failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)