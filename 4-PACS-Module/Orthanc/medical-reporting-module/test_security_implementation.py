#!/usr/bin/env python3
"""
Test Security Implementation for Medical STT System
Tests user authentication, secure audio handling, and POPIA compliance
"""

import os
import sys
import tempfile
import json
import requests
from datetime import datetime

# Add the medical-reporting-module to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_security_features():
    """Test all security features"""
    print("🔒 Testing Medical STT Security Implementation")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    # Test 1: User Registration
    print("\n1. Testing User Registration...")
    try:
        registration_data = {
            "username": "test_doctor",
            "email": "test@medical.local",
            "password": "secure123",
            "role": "doctor"
        }
        
        response = requests.post(f"{base_url}/api/auth/register", json=registration_data)
        if response.status_code == 201:
            print("✅ User registration successful")
            user_data = response.json()
            print(f"   User ID: {user_data['user']['id']}")
        else:
            print(f"❌ Registration failed: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Registration test failed: {e}")
    
    # Test 2: User Login
    print("\n2. Testing User Login...")
    session = requests.Session()
    try:
        login_data = {
            "username": "test_doctor",
            "password": "secure123"
        }
        
        response = session.post(f"{base_url}/api/auth/login", json=login_data)
        if response.status_code == 200:
            print("✅ User login successful")
            login_result = response.json()
            print(f"   Session ID: {login_result['session']['id']}")
        else:
            print(f"❌ Login failed: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Login test failed: {e}")
    
    # Test 3: Session Validation
    print("\n3. Testing Session Validation...")
    try:
        response = session.get(f"{base_url}/api/auth/session/validate")
        if response.status_code == 200:
            print("✅ Session validation successful")
            session_data = response.json()
            print(f"   Valid: {session_data['valid']}")
        else:
            print(f"❌ Session validation failed: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Session validation test failed: {e}")
    
    # Test 4: Voice Session with Authentication
    print("\n4. Testing Authenticated Voice Session...")
    try:
        session_data = {"report_id": "test_report"}
        response = session.post(f"{base_url}/api/voice/session/start", json=session_data)
        if response.status_code == 201:
            print("✅ Authenticated voice session started")
            voice_session = response.json()
            print(f"   Session ID: {voice_session['session']['session_id']}")
        else:
            print(f"❌ Voice session failed: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Voice session test failed: {e}")
    
    # Test 5: Training Session
    print("\n5. Testing Medical Training Session...")
    try:
        training_data = {"category": "anatomy"}
        response = session.post(f"{base_url}/api/voice/training/start", json=training_data)
        if response.status_code == 200:
            print("✅ Training session started")
            training_result = response.json()
            print(f"   Category: {training_result['category']}")
            print(f"   Terms available: {len(training_result['terms'])}")
        else:
            print(f"❌ Training session failed: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Training session test failed: {e}")
    
    # Test 6: Data Summary (POPIA Compliance)
    print("\n6. Testing Data Summary (POPIA)...")
    try:
        response = session.get(f"{base_url}/api/auth/data-summary")
        if response.status_code == 200:
            print("✅ Data summary retrieved")
            summary = response.json()
            print(f"   Data categories: {len(summary['summary']['data_categories'])}")
        else:
            print(f"❌ Data summary failed: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Data summary test failed: {e}")
    
    # Test 7: Audio Security Stats
    print("\n7. Testing Audio Security Stats...")
    try:
        response = session.get(f"{base_url}/api/voice/security/stats")
        if response.status_code == 200:
            print("✅ Audio security stats retrieved")
            stats = response.json()
            print(f"   Retention hours: {stats['retention_policy']['audio_retention_hours']}")
        else:
            print(f"❌ Audio security stats failed: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Audio security stats test failed: {e}")
    
    # Test 8: Consent Management
    print("\n8. Testing Consent Management...")
    try:
        consent_data = {
            "consent_granted": True,
            "retention_years": 7
        }
        response = session.post(f"{base_url}/api/auth/consent", json=consent_data)
        if response.status_code == 200:
            print("✅ Consent updated successfully")
            consent_result = response.json()
            print(f"   Consent granted: {consent_result['consent']['consent_granted']}")
        else:
            print(f"❌ Consent update failed: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Consent test failed: {e}")
    
    # Test 9: Demo Login (Fallback)
    print("\n9. Testing Demo Login...")
    demo_session = requests.Session()
    try:
        response = demo_session.post(f"{base_url}/api/auth/demo/login")
        if response.status_code == 200:
            print("✅ Demo login successful")
            demo_result = response.json()
            print(f"   Demo mode: {demo_result.get('demo_mode', False)}")
        else:
            print(f"❌ Demo login failed: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Demo login test failed: {e}")
    
    # Test 10: Logout
    print("\n10. Testing User Logout...")
    try:
        response = session.post(f"{base_url}/api/auth/logout")
        if response.status_code == 200:
            print("✅ User logout successful")
        else:
            print(f"❌ Logout failed: {response.json().get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Logout test failed: {e}")
    
    print("\n" + "=" * 50)
    print("🔒 Security Implementation Test Complete")
    print("\nNext Steps:")
    print("1. Start the Flask application: python app.py")
    print("2. Visit http://localhost:5000/auth to test the UI")
    print("3. Register a new user or use demo login")
    print("4. Test voice features with authentication")
    print("5. Check POPIA compliance features in profile")

def test_secure_audio_handler():
    """Test secure audio handler functionality"""
    print("\n🔊 Testing Secure Audio Handler")
    print("-" * 30)
    
    try:
        from core.secure_audio_handler import SecureAudioHandler
        
        # Create test audio handler
        handler = SecureAudioHandler("temp/test_audio")
        
        # Test audio storage
        test_audio_data = b"fake_audio_data_for_testing"
        user_id = "test_user_123"
        
        print("1. Testing audio storage...")
        storage_result = handler.store_audio_securely(test_audio_data, user_id, "test")
        if storage_result:
            print(f"✅ Audio stored: {storage_result['file_id']}")
            
            # Test audio retrieval
            print("2. Testing audio retrieval...")
            retrieved = handler.retrieve_audio_securely(storage_result['file_id'], user_id)
            if retrieved and retrieved['data'] == test_audio_data:
                print("✅ Audio retrieved successfully")
            else:
                print("❌ Audio retrieval failed")
            
            # Test stats
            print("3. Testing audio stats...")
            stats = handler.get_user_audio_stats(user_id)
            print(f"✅ Stats: {stats['total_files']} files, {stats['total_size']} bytes")
            
            # Test cleanup
            print("4. Testing cleanup...")
            cleanup_count = handler.cleanup_expired_files()
            print(f"✅ Cleanup completed: {cleanup_count} files processed")
            
        else:
            print("❌ Audio storage failed")
            
    except Exception as e:
        print(f"❌ Secure audio handler test failed: {e}")

def test_popia_compliance():
    """Test POPIA compliance features"""
    print("\n📋 Testing POPIA Compliance")
    print("-" * 30)
    
    try:
        from core.popia_compliance import POPIACompliance
        
        user_id = "test_user_popia"
        
        print("1. Testing data summary...")
        summary = POPIACompliance.get_user_data_summary(user_id)
        if summary:
            print(f"✅ Data summary generated for {user_id}")
            print(f"   Categories: {len(summary['data_categories'])}")
        else:
            print("❌ Data summary failed")
        
        print("2. Testing data export...")
        exported_json = POPIACompliance.export_user_data(user_id, 'json')
        if exported_json:
            print("✅ JSON export successful")
        else:
            print("❌ JSON export failed")
        
        exported_csv = POPIACompliance.export_user_data(user_id, 'csv')
        if exported_csv:
            print("✅ CSV export successful")
        else:
            print("❌ CSV export failed")
        
        print("3. Testing consent management...")
        consent_updated = POPIACompliance.update_user_consent(user_id, True, 7)
        if consent_updated:
            print("✅ Consent updated successfully")
            
            consent_status = POPIACompliance.get_consent_status(user_id)
            if consent_status:
                print(f"✅ Consent status retrieved: {consent_status['consent_granted']}")
            else:
                print("❌ Consent status retrieval failed")
        else:
            print("❌ Consent update failed")
            
    except Exception as e:
        print(f"❌ POPIA compliance test failed: {e}")

if __name__ == "__main__":
    print("🧪 Medical STT Security Test Suite")
    print("=" * 50)
    
    # Test individual components first
    test_secure_audio_handler()
    test_popia_compliance()
    
    # Test full API integration
    print("\n🌐 Testing API Integration...")
    print("Note: This requires the Flask app to be running on localhost:5000")
    
    try:
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Flask app is running, proceeding with API tests...")
            test_security_features()
        else:
            print("❌ Flask app not responding correctly")
    except requests.exceptions.ConnectionError:
        print("❌ Flask app not running. Start with: python app.py")
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
    
    print("\n🎉 Test suite completed!")