#!/usr/bin/env python3
"""
Test script for Medical Authorization MCP Server
Run this to verify the server works correctly
"""

import sqlite3
import json
from server import (
    validate_medical_aid,
    validate_preauth_requirements,
    estimate_patient_cost,
    create_preauth_request,
    check_preauth_status,
    list_pending_preauths
)

def test_validate_medical_aid():
    """Test medical aid validation"""
    print("\n=== Test 1: Validate Medical Aid ===")
    
    result = validate_medical_aid({
        "member_number": "1234567890",
        "scheme_code": "DISCOVERY"
    })
    
    print(json.dumps(result, indent=2))
    assert result["valid"] == True
    print("✅ PASSED")

def test_validate_preauth_requirements():
    """Test pre-auth requirements check"""
    print("\n=== Test 2: Validate Pre-Auth Requirements ===")
    
    result = validate_preauth_requirements({
        "scheme_code": "DISCOVERY",
        "plan_code": "EXECUTIVE",
        "procedure_code": "3011"
    })
    
    print(json.dumps(result, indent=2))
    assert result["requires_preauth"] == True
    assert result["approval_rate"] == 0.95
    print("✅ PASSED")

def test_estimate_patient_cost():
    """Test cost estimation"""
    print("\n=== Test 3: Estimate Patient Cost ===")
    
    result = estimate_patient_cost({
        "member_number": "1234567890",
        "scheme_code": "DISCOVERY",
        "procedure_code": "3011"
    })
    
    print(json.dumps(result, indent=2))
    assert result["procedure_cost"] == 1850.00
    assert result["patient_portion"] == 185.00
    print("✅ PASSED")

def test_create_preauth_request():
    """Test pre-auth request creation"""
    print("\n=== Test 4: Create Pre-Auth Request ===")
    
    result = create_preauth_request({
        "patient_id": "TEST-001",
        "member_number": "1234567890",
        "scheme_code": "DISCOVERY",
        "procedure_code": "3011",
        "clinical_indication": "Severe headache, rule out intracranial pathology",
        "icd10_codes": ["R51"],
        "urgency": "urgent"
    })
    
    print(json.dumps(result, indent=2))
    assert result["success"] == True
    assert "preauth_id" in result
    
    # Save preauth_id for next test
    global test_preauth_id
    test_preauth_id = result["preauth_id"]
    print("✅ PASSED")

def test_check_preauth_status():
    """Test pre-auth status check"""
    print("\n=== Test 5: Check Pre-Auth Status ===")
    
    result = check_preauth_status({
        "preauth_id": test_preauth_id
    })
    
    print(json.dumps(result, indent=2))
    assert result["status"] == "queued"
    print("✅ PASSED")

def test_list_pending_preauths():
    """Test listing pending pre-auths"""
    print("\n=== Test 6: List Pending Pre-Auths ===")
    
    result = list_pending_preauths({
        "status": "queued"
    })
    
    print(json.dumps(result, indent=2))
    assert result["count"] >= 1
    print("✅ PASSED")

def test_no_preauth_required():
    """Test procedure that doesn't require pre-auth"""
    print("\n=== Test 7: No Pre-Auth Required (X-Ray) ===")
    
    result = validate_preauth_requirements({
        "scheme_code": "DISCOVERY",
        "plan_code": "EXECUTIVE",
        "procedure_code": "2001"  # X-Ray Chest
    })
    
    print(json.dumps(result, indent=2))
    assert result["requires_preauth"] == False
    print("✅ PASSED")

def test_different_schemes():
    """Test different medical schemes"""
    print("\n=== Test 8: Different Medical Schemes ===")
    
    schemes = [
        ("DISCOVERY", "1234567890"),
        ("MOMENTUM", "87654321"),
        ("BONITAS", "BN12345678")
    ]
    
    for scheme_code, member_number in schemes:
        result = validate_medical_aid({
            "member_number": member_number,
            "scheme_code": scheme_code
        })
        print(f"\n{scheme_code}: {result['member']['full_name']}")
        assert result["valid"] == True
    
    print("✅ PASSED")

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Medical Authorization MCP Server - Test Suite")
    print("=" * 60)
    
    try:
        test_validate_medical_aid()
        test_validate_preauth_requirements()
        test_estimate_patient_cost()
        test_create_preauth_request()
        test_check_preauth_status()
        test_list_pending_preauths()
        test_no_preauth_required()
        test_different_schemes()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nServer is ready to use!")
        print("\nNext steps:")
        print("1. Add to Kiro: .kiro/settings/mcp.json")
        print("2. Start using the tools in Kiro IDE")
        print("3. Add real medical scheme data")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()
