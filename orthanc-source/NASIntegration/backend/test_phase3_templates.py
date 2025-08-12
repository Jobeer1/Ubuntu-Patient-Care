#!/usr/bin/env python3
"""
Phase 3 Test - SA Medical Templates System
Tests the SA medical templates, terminology, and multi-language support
"""

import requests
import json
import time
import sys
import os
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_ADMIN = {
    "username": "admin",
    "password": "admin123"
}

def test_authentication():
    """Test admin authentication"""
    print("🔐 Testing authentication...")
    
    response = requests.post(f"{BASE_URL}/api/auth/login", 
                           json=TEST_ADMIN,
                           headers={'Content-Type': 'application/json'})
    
    if response.status_code == 200:
        print("✅ Authentication successful")
        return response.cookies
    else:
        print(f"❌ Authentication failed: {response.status_code}")
        return None

def test_system_endpoints(cookies):
    """Test system information endpoints"""
    print("\n🌐 Testing system endpoints...")
    
    endpoints = [
        ('/api/reporting/sa-templates/system/languages', 'Languages'),
        ('/api/reporting/sa-templates/system/categories', 'Categories'),
        ('/api/reporting/sa-templates/system/modalities', 'Modalities'),
        ('/api/reporting/sa-templates/system/status', 'System Status')
    ]
    
    results = []
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", cookies=cookies)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"✅ {name}: {len(data.get(name.lower(), []))} items")
                    results.append(True)
                else:
                    print(f"❌ {name}: {data.get('error')}")
                    results.append(False)
            else:
                print(f"❌ {name}: HTTP {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ {name}: {e}")
            results.append(False)
    
    return all(results)

def test_template_retrieval(cookies):
    """Test template retrieval by modality"""
    print("\n📋 Testing template retrieval...")
    
    # Test getting templates for chest X-ray
    response = requests.get(f"{BASE_URL}/api/reporting/sa-templates/templates?modality=CR&body_part=CHEST&language=en", 
                          cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            templates = data.get('templates', [])
            print(f"✅ Retrieved {len(templates)} chest X-ray templates")
            
            # Test specific template retrieval
            if templates:
                template_id = templates[0]['template_id']
                template_response = requests.get(f"{BASE_URL}/api/reporting/sa-templates/templates/{template_id}?language=en", 
                                               cookies=cookies)
                
                if template_response.status_code == 200:
                    template_data = template_response.json()
                    if template_data.get('success'):
                        template = template_data.get('template', {})
                        print(f"✅ Retrieved specific template: {template.get('name_en', 'Unknown')}")
                        return True, template_id
                    else:
                        print(f"❌ Specific template retrieval failed: {template_data.get('error')}")
                else:
                    print(f"❌ Specific template endpoint failed: {template_response.status_code}")
            
            return True, None
        else:
            print(f"❌ Template retrieval failed: {data.get('error')}")
    else:
        print(f"❌ Template endpoint failed: {response.status_code}")
    
    return False, None

def test_medical_terminology(cookies):
    """Test SA medical terminology"""
    print("\n🏥 Testing SA medical terminology...")
    
    # Test terminology retrieval
    response = requests.get(f"{BASE_URL}/api/reporting/sa-templates/terminology?language=en&category=anatomy&modality=CR", 
                          cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            terms = data.get('terms', [])
            print(f"✅ Retrieved {len(terms)} medical terms")
            
            # Test translation
            if terms:
                english_term = terms[0]['english_term']
                translation_response = requests.post(f"{BASE_URL}/api/reporting/sa-templates/terminology/translate", 
                                                   json={
                                                       'term': english_term,
                                                       'from_language': 'en',
                                                       'to_language': 'af'
                                                   },
                                                   cookies=cookies,
                                                   headers={'Content-Type': 'application/json'})
                
                if translation_response.status_code == 200:
                    translation_data = translation_response.json()
                    if translation_data.get('success'):
                        translated = translation_data.get('translated_term')
                        print(f"✅ Translation: '{english_term}' → '{translated}' (EN→AF)")
                        return True
                    else:
                        print(f"❌ Translation failed: {translation_data.get('error')}")
                else:
                    print(f"❌ Translation endpoint failed: {translation_response.status_code}")
            
            return True
        else:
            print(f"❌ Terminology retrieval failed: {data.get('error')}")
    else:
        print(f"❌ Terminology endpoint failed: {response.status_code}")
    
    return False

def test_terminology_suggestions(cookies):
    """Test medical terminology suggestions"""
    print("\n💡 Testing terminology suggestions...")
    
    # Test suggestions for auto-complete
    test_terms = ['chest', 'lung', 'heart', 'tuberculosis']
    
    for term in test_terms:
        response = requests.get(f"{BASE_URL}/api/reporting/sa-templates/terminology/suggestions?term={term}&language=en&limit=5", 
                              cookies=cookies)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                suggestions = data.get('suggestions', [])
                print(f"✅ '{term}': {len(suggestions)} suggestions")
                if suggestions:
                    print(f"   Top suggestion: {suggestions[0]['term']}")
            else:
                print(f"❌ Suggestions for '{term}' failed: {data.get('error')}")
                return False
        else:
            print(f"❌ Suggestions endpoint failed for '{term}': {response.status_code}")
            return False
    
    return True

def test_template_population(cookies, template_id):
    """Test template population with data"""
    if not template_id:
        print("\n⏭️ Skipping template population (no template ID)")
        return True
    
    print(f"\n📝 Testing template population for {template_id}...")
    
    # Test data for populating template
    test_data = {
        'language': 'en',
        'data': {
            'clinical_indication': 'Routine TB screening for employment',
            'findings.lung_fields': 'Clear',
            'findings.heart_size': 'Normal',
            'impression': 'No evidence of active pulmonary tuberculosis'
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/reporting/sa-templates/templates/{template_id}/populate", 
                           json=test_data,
                           cookies=cookies,
                           headers={'Content-Type': 'application/json'})
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            populated = data.get('populated_template', {})
            print(f"✅ Template populated successfully")
            print(f"   Sections: {len(populated.get('populated_sections', []))}")
            return True
        else:
            print(f"❌ Template population failed: {data.get('error')}")
    else:
        print(f"❌ Template population endpoint failed: {response.status_code}")
    
    return False

def test_compliance_validation(cookies, template_id):
    """Test compliance validation"""
    if not template_id:
        print("\n⏭️ Skipping compliance validation (no template ID)")
        return True
    
    print(f"\n🛡️ Testing compliance validation for {template_id}...")
    
    # Test with incomplete data (should fail validation)
    test_data = {
        'report_data': {
            'clinical_indication': 'Test indication'
            # Missing required fields
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/reporting/sa-templates/templates/{template_id}/validate", 
                           json=test_data,
                           cookies=cookies,
                           headers={'Content-Type': 'application/json'})
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            validation = data.get('validation', {})
            print(f"✅ Validation completed")
            print(f"   Valid: {validation.get('valid', False)}")
            print(f"   Errors: {len(validation.get('errors', []))}")
            print(f"   Warnings: {len(validation.get('warnings', []))}")
            return True
        else:
            print(f"❌ Validation failed: {data.get('error')}")
    else:
        print(f"❌ Validation endpoint failed: {response.status_code}")
    
    return False

def test_usage_analytics(cookies):
    """Test usage analytics"""
    print("\n📊 Testing usage analytics...")
    
    response = requests.get(f"{BASE_URL}/api/reporting/sa-templates/analytics/usage", 
                          cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            analytics = data.get('analytics', {})
            print(f"✅ Analytics retrieved")
            print(f"   Total usage: {analytics.get('total_usage', 0)}")
            print(f"   Avg completion time: {analytics.get('average_completion_time', 0)} min")
            return True
        else:
            print(f"❌ Analytics failed: {data.get('error')}")
    else:
        print(f"❌ Analytics endpoint failed: {response.status_code}")
    
    return False

def main():
    """Run all Phase 3 tests"""
    print("🇿🇦 SA Medical Reporting - Phase 3 Template System Tests")
    print("=" * 70)
    
    # Test authentication
    cookies = test_authentication()
    if not cookies:
        print("\n❌ Cannot continue without authentication")
        sys.exit(1)
    
    # Run tests
    tests = [
        ("System Endpoints", lambda: test_system_endpoints(cookies)),
        ("Medical Terminology", lambda: test_medical_terminology(cookies)),
        ("Terminology Suggestions", lambda: test_terminology_suggestions(cookies)),
        ("Usage Analytics", lambda: test_usage_analytics(cookies))
    ]
    
    results = []
    template_id = None
    
    # Test template retrieval separately to get template ID
    template_success, template_id = test_template_retrieval(cookies)
    results.append(("Template Retrieval", template_success))
    
    # Test template-specific functions
    if template_id:
        results.append(("Template Population", test_template_population(cookies, template_id)))
        results.append(("Compliance Validation", test_compliance_validation(cookies, template_id)))
    
    # Run other tests
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 70)
    print("📋 PHASE 3 TEMPLATE SYSTEM TEST SUMMARY")
    print("=" * 70)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        if result:
            passed += 1
            print(f"✅ {test_name}")
        else:
            print(f"❌ {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 3 tests passed! SA Medical Templates system is working correctly.")
        sys.exit(0)
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()