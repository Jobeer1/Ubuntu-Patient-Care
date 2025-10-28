#!/usr/bin/env python3
"""
Test script for AI Brain integration
Tests all AI-powered features
"""

import requests
import json
import time

BASE_URL = "http://localhost:8080/api/ai-brain"

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")

def test_health():
    """Test if AI Brain is operational"""
    print("Checking AI Brain health...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        data = response.json()
        
        if data["status"] == "operational":
            print(f"✅ AI Brain is {data['status']}")
            print(f"   Model: {data['model']}")
            print(f"   Tools Available: {data['tools_available']}")
            return True
        else:
            print(f"⚠️  AI Brain status: {data['status']}")
            print(f"   Message: {data['message']}")
            return False
    
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to FastAPI server")
        print("   Start server with: uvicorn server:fast_app --port 8080")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_simple_query():
    """Test simple member validation query"""
    print("Testing simple member validation query...")
    
    try:
        response = requests.post(f"{BASE_URL}/query", json={
            "query": "Is patient 1234567890 enrolled in Discovery?",
            "context": {"patient_id": "P12345"}
        }, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Query processed successfully")
            print(f"\n   AI Response:")
            print(f"   {result['response']}\n")
            print(f"   Confidence: {result['confidence']:.0%}")
            print(f"   Tools Called: {[t['tool'] for t in result['tool_results']]}")
            return True
        else:
            print(f"❌ Query failed: {response.status_code}")
            print(f"   {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_complex_query():
    """Test complex multi-part query"""
    print("Testing complex multi-part query...")
    
    try:
        response = requests.post(f"{BASE_URL}/query", json={
            "query": "Is patient 1234567890 enrolled in Discovery and what will CT Head cost?",
            "context": {"patient_id": "P12345"}
        }, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Complex query processed")
            print(f"\n   AI Response:")
            print(f"   {result['response']}\n")
            print(f"   Tools Called: {len(result['tool_results'])} tools")
            for tool_result in result['tool_results']:
                print(f"      - {tool_result['tool']}")
            return True
        else:
            print(f"❌ Query failed: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_preauth_optimization():
    """Test pre-auth optimization"""
    print("Testing pre-auth optimization...")
    
    try:
        response = requests.post(f"{BASE_URL}/optimize-preauth", json={
            "patient_id": "P12345",
            "procedure": "CT Head",
            "clinical_indication": "Severe headache",
            "context": {
                "age": 45,
                "symptoms": "photophobia, neck stiffness"
            }
        }, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Pre-auth optimized")
            print(f"\n   Optimized Justification:")
            print(f"   {result.get('optimized_justification', 'N/A')}\n")
            print(f"   Approval Likelihood: {result.get('approval_likelihood', 0):.0%}")
            print(f"   Confidence: {result.get('confidence', 0):.0%}")
            return True
        else:
            print(f"❌ Optimization failed: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_consultation():
    """Test medical consultation"""
    print("Testing medical consultation...")
    
    try:
        response = requests.post(f"{BASE_URL}/consult", json={
            "query": "Should patient with severe headache get imaging?",
            "context": {
                "age": 45,
                "symptoms": "Severe headache, photophobia, neck stiffness"
            }
        }, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Consultation completed")
            print(f"\n   AI Consultation:")
            print(f"   {result['consultation']}\n")
            print(f"   Confidence: {result['confidence']:.0%}")
            print(f"   Tools Used: {result['tools_used']}")
            return True
        else:
            print(f"❌ Consultation failed: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print_section("🧪 AI BRAIN INTEGRATION TEST SUITE")
    
    print("Testing Ubuntu Patient Care AI Brain")
    print("This will test all AI-powered features\n")
    
    # Track results
    tests_passed = 0
    tests_total = 5
    
    # Test 1: Health check
    print_section("1️⃣ Health Check")
    if test_health():
        tests_passed += 1
    else:
        print("\n⚠️  AI Brain not available. Remaining tests will fail.")
        print("   Make sure:")
        print("   1. FastAPI server is running: uvicorn server:fast_app --port 8080")
        print("   2. OPENAI_API_KEY is set in .env file")
        return
    
    # Test 2: Simple query
    print_section("2️⃣ Simple Query Test")
    if test_simple_query():
        tests_passed += 1
    
    # Test 3: Complex query
    print_section("3️⃣ Complex Query Test")
    if test_complex_query():
        tests_passed += 1
    
    # Test 4: Pre-auth optimization
    print_section("4️⃣ Pre-Auth Optimization Test")
    if test_preauth_optimization():
        tests_passed += 1
    
    # Test 5: Medical consultation
    print_section("5️⃣ Medical Consultation Test")
    if test_consultation():
        tests_passed += 1
    
    # Summary
    print_section("📊 TEST RESULTS")
    print(f"Tests Passed: {tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("\n🎉 ✅ ALL TESTS PASSED!")
        print("   AI Brain is fully operational and ready for production!")
    elif tests_passed > 0:
        print(f"\n⚠️  {tests_total - tests_passed} test(s) failed")
        print("   Check the error messages above for details")
    else:
        print("\n❌ All tests failed")
        print("   Verify your setup and try again")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
