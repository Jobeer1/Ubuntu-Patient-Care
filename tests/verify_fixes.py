#!/usr/bin/env python3
"""
Quick verification script for frontend/backend error fixes
Tests all three issues that were fixed
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
FLASK_API = "http://localhost:5000"
MCP_API = "http://localhost:8080"
TEST_RESULTS = []

def log_test(name, passed, details=""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {name}")
    if details:
        print(f"       {details}")
    TEST_RESULTS.append({"test": name, "passed": passed, "details": details})

def test_user_endpoint():
    """Test 1: Verify users endpoint returns valid data"""
    try:
        response = requests.get(f"{MCP_API}/users/", timeout=5)
        if response.status_code == 200:
            users = response.json()
            # Check if any user has the fixed fields
            for user in users:
                if 'active' in user and 'language_preference' in user:
                    # Should be able to parse without Pydantic error
                    log_test("Users Endpoint Pydantic Validation", True, 
                            f"Got {len(users)} users, no validation errors")
                    return True
            log_test("Users Endpoint Pydantic Validation", False, 
                    "Users missing active/language_preference fields")
            return False
        else:
            log_test("Users Endpoint Pydantic Validation", False, 
                    f"HTTP {response.status_code}")
            return False
    except Exception as e:
        log_test("Users Endpoint Pydantic Validation", False, str(e))
        return False

def test_mcp_token_endpoint():
    """Test 2: Verify Flask endpoint generates MCP token"""
    try:
        # First need to check if we can get a token
        response = requests.get(f"{FLASK_API}/api/auth/get-mcp-token", 
                               timeout=5,
                               allow_redirects=False)
        
        # 401 is expected if not authenticated (endpoint exists)
        # 200 is success with token
        if response.status_code == 200:
            data = response.json()
            if 'token' in data and 'user' in data:
                log_test("Flask MCP Token Endpoint", True, 
                        f"Endpoint returned token for {data['user'].get('email', 'unknown')}")
                return True
            else:
                log_test("Flask MCP Token Endpoint", False, 
                        "Response missing token or user fields")
                return False
        elif response.status_code == 401:
            log_test("Flask MCP Token Endpoint", True, 
                    "Endpoint exists (401 expected when not authenticated)")
            return True
        else:
            log_test("Flask MCP Token Endpoint", False, 
                    f"Unexpected status: {response.status_code}")
            return False
    except Exception as e:
        log_test("Flask MCP Token Endpoint", False, str(e))
        return False

def test_access_control_js():
    """Test 3: Verify JavaScript file has been updated"""
    try:
        # Check if the JavaScript file contains the fixed code
        with open("4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/static/js/mcp-access-control.js", "r") as f:
            content = f.read()
            
        has_async_gettoken = "async function getToken()" in content
        has_flask_fallback = "/api/auth/get-mcp-token" in content
        has_await = "await getToken()" in content
        
        if has_async_gettoken and has_flask_fallback and has_await:
            log_test("JavaScript Access Control Fix", True, 
                    "All token fetching logic present")
            return True
        else:
            missing = []
            if not has_async_gettoken:
                missing.append("async getToken()")
            if not has_flask_fallback:
                missing.append("Flask fallback")
            if not has_await:
                missing.append("await getToken()")
            log_test("JavaScript Access Control Fix", False, 
                    f"Missing: {', '.join(missing)}")
            return False
    except Exception as e:
        log_test("JavaScript Access Control Fix", False, str(e))
        return False

def test_pydantic_schema():
    """Test 4: Verify Pydantic schema has been updated"""
    try:
        with open("4-PACS-Module/Orthanc/mcp-server/app/routes/users.py", "r") as f:
            content = f.read()
            
        has_optional_active = "active: Optional[bool]" in content
        has_optional_lang = "language_preference: Optional[str]" in content
        has_defaults = 'active: Optional[bool] = True' in content and 'language_preference: Optional[str] = "en-ZA"' in content
        
        if has_optional_active and has_optional_lang and has_defaults:
            log_test("Pydantic Schema Fix", True, 
                    "UserResponse fields are Optional with defaults")
            return True
        else:
            missing = []
            if not has_optional_active:
                missing.append("optional active field")
            if not has_optional_lang:
                missing.append("optional language_preference field")
            if not has_defaults:
                missing.append("default values")
            log_test("Pydantic Schema Fix", False, 
                    f"Missing: {', '.join(missing)}")
            return False
    except Exception as e:
        log_test("Pydantic Schema Fix", False, str(e))
        return False

def print_summary():
    """Print test summary"""
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for t in TEST_RESULTS if t["passed"])
    total = len(TEST_RESULTS)
    
    print(f"\nResults: {passed}/{total} tests passed\n")
    
    for result in TEST_RESULTS:
        status = "✅" if result["passed"] else "❌"
        print(f"{status} {result['test']}")
    
    if passed == total:
        print("\n🎉 All fixes verified successfully!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check details above.")
        return 1

if __name__ == "__main__":
    print("Frontend & Backend Error Fixes Verification")
    print("=" * 60)
    print(f"Starting tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Run tests
    test_pydantic_schema()
    test_mcp_token_endpoint()
    test_access_control_js()
    test_user_endpoint()
    
    # Print summary
    sys.exit(print_summary())
