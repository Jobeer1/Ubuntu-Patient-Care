#!/usr/bin/env python3
"""
🇿🇦 Direct SA Templates API Test

Test SA templates API endpoints directly without Flask app.
"""

import requests
import json
import sys

def test_sa_templates_api():
    """Test SA templates API endpoints"""
    base_url = "http://localhost:5000"
    
    # First login to get session
    print("🔐 Testing authentication...")
    login_response = requests.post(f"{base_url}/api/auth/login", 
                                 json={"username": "admin", "password": "admin123"},
                                 headers={"Content-Type": "application/json"})
    
    if login_response.status_code != 200:
        print(f"❌ Authentication failed: {login_response.status_code}")
        return False
    
    print("✅ Authentication successful")
    
    # Get session cookies
    session_cookies = login_response.cookies
    
    # Test endpoints
    endpoints = [
        ("/api/reporting/sa-templates/system/languages", "Languages"),
        ("/api/reporting/sa-templates/system/categories", "Categories"),
        ("/api/reporting/sa-templates/system/modalities", "Modalities"),
        ("/api/reporting/sa-templates/system/status", "System Status"),
        ("/api/reporting/sa-templates/templates?modality=CR&body_part=CHEST&language=en", "Templates"),
        ("/api/reporting/sa-templates/terminology?language=en&category=anatomy&modality=CR", "Terminology"),
        ("/api/reporting/sa-templates/terminology/suggestions?term=chest&language=en&limit=5", "Suggestions"),
        ("/api/reporting/sa-templates/analytics/usage", "Analytics")
    ]
    
    results = []
    
    for endpoint, name in endpoints:
        print(f"🧪 Testing {name}...")
        try:
            response = requests.get(f"{base_url}{endpoint}", cookies=session_cookies)
            if response.status_code == 200:
                print(f"✅ {name}: Success")
                results.append(True)
            else:
                print(f"❌ {name}: HTTP {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ {name}: Error - {e}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All SA Templates API tests passed!")
        return True
    else:
        print("⚠️ Some tests failed. The Flask app may need to be restarted.")
        return False

if __name__ == "__main__":
    success = test_sa_templates_api()
    sys.exit(0 if success else 1)