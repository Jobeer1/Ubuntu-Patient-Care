#!/usr/bin/env python3
"""
Test script to verify the fixes for the medical reporting app
"""

import requests
import time
import sys
import os

def test_dashboard():
    """Test if the dashboard loads without errors"""
    try:
        response = requests.get('https://localhost:5443/', verify=False, timeout=10)
        if response.status_code == 200:
            print("✅ Dashboard loads successfully")
            
            # Check if the date is displayed correctly (not showing August 2025)
            if "August 2025" in response.text or "Augustus 2025" in response.text:
                print("❌ Date issue still present - showing August 2025")
                return False
            else:
                print("✅ Date display appears to be fixed")
            
            # Check if the template exists
            if "dashboard_sa.html" in response.text or "SA Medical Reporting" in response.text:
                print("✅ Dashboard template is working")
                return True
            else:
                print("❌ Dashboard template issue")
                return False
        else:
            print(f"❌ Dashboard failed with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")
        return False

def test_voice_demo():
    """Test if the voice demo page loads"""
    try:
        response = requests.get('https://localhost:5443/voice-demo', verify=False, timeout=10)
        if response.status_code == 200:
            print("✅ Voice demo page loads successfully")
            
            # Check if the language is properly set (English with Afrikaans only for greeting/date)
            if "How to Use" in response.text and "SA Medical Terms Recognition" in response.text:
                print("✅ Language localization is correct (English with limited Afrikaans)")
                return True
            else:
                print("❌ Language localization issue")
                return False
        else:
            print(f"❌ Voice demo failed with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Voice demo test failed: {e}")
        return False

def test_service_manager():
    """Test if the service manager is working"""
    try:
        # Import the service manager to see if it loads without errors
        sys.path.append(os.path.dirname(__file__))
        from core.service_manager import ServiceManager
        
        sm = ServiceManager()
        status = sm.get_all_service_status()
        
        if isinstance(status, dict) and len(status) > 0:
            print("✅ Service manager is working")
            print(f"   Services: {list(status.keys())}")
            return True
        else:
            print("❌ Service manager returned invalid status")
            return False
    except Exception as e:
        print(f"❌ Service manager test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Medical Reporting App Fixes...")
    print("=" * 50)
    
    # Wait a moment for the server to fully start
    print("⏳ Waiting for server to start...")
    time.sleep(3)
    
    tests = [
        ("Service Manager", test_service_manager),
        ("Dashboard", test_dashboard),
        ("Voice Demo", test_voice_demo)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All fixes are working correctly!")
        return True
    else:
        print("⚠️  Some issues remain - check the failed tests above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)