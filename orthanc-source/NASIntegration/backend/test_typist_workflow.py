#!/usr/bin/env python3
"""
Test script for Typist Workflow System
Verifies Phase 2 implementation works correctly
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

def test_database_migrations(cookies):
    """Test database migrations"""
    print("\n🗄️ Testing database migrations...")
    
    response = requests.post(f"{BASE_URL}/api/reporting/typist/system/migrate", 
                           cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Database migrations completed")
            return True
        else:
            print(f"❌ Migration failed: {data.get('error')}")
    else:
        print(f"❌ Migration endpoint failed: {response.status_code}")
    
    return False

def test_system_status(cookies):
    """Test system status endpoint"""
    print("\n📊 Testing system status...")
    
    response = requests.get(f"{BASE_URL}/api/reporting/typist/system/status", 
                          cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ System status retrieved:")
            migrations = data.get('system_status', {}).get('migrations_applied', {})
            for migration, status in migrations.items():
                status_icon = "✅" if status else "❌"
                print(f"   {status_icon} {migration}: {status}")
            return True
        else:
            print(f"❌ System status failed: {data.get('error')}")
    else:
        print(f"❌ System status endpoint failed: {response.status_code}")
    
    return False

def test_queue_endpoints(cookies):
    """Test typist queue endpoints"""
    print("\n📋 Testing queue endpoints...")
    
    # Test queue retrieval
    response = requests.get(f"{BASE_URL}/api/reporting/typist/queue", 
                          cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            queue_items = data.get('queue_items', [])
            print(f"✅ Queue retrieved: {len(queue_items)} items")
            return True
        else:
            print(f"❌ Queue retrieval failed: {data.get('error')}")
    else:
        print(f"❌ Queue endpoint failed: {response.status_code}")
    
    return False

def test_queue_statistics(cookies):
    """Test queue statistics"""
    print("\n📈 Testing queue statistics...")
    
    response = requests.get(f"{BASE_URL}/api/reporting/typist/stats", 
                          cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            queue_stats = data.get('queue_statistics', {})
            personal_stats = data.get('personal_statistics', {})
            
            print("✅ Statistics retrieved:")
            print(f"   Pending reports: {queue_stats.get('pending_reports', 0)}")
            print(f"   Claimed reports: {queue_stats.get('claimed_reports', 0)}")
            print(f"   Completed today: {personal_stats.get('reports_completed_today', 0)}")
            return True
        else:
            print(f"❌ Statistics failed: {data.get('error')}")
    else:
        print(f"❌ Statistics endpoint failed: {response.status_code}")
    
    return False

def create_test_session(cookies):
    """Create a test dictation session for testing"""
    print("\n🎤 Creating test dictation session...")
    
    try:
        # Create a test session using the reporting API
        response = requests.post(f"{BASE_URL}/api/reporting/sessions", 
                               json={
                                   'patient_id': 'TEST_PATIENT_001',
                                   'study_id': 'TEST_STUDY_001',
                                   'language': 'en-ZA'
                               },
                               cookies=cookies,
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 201:
            data = response.json()
            if data.get('success'):
                session_id = data.get('session', {}).get('session_id')
                print(f"✅ Test session created: {session_id}")
                
                # Simulate STT completion by updating status
                import sqlite3
                conn = sqlite3.connect('reporting.db')
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE dictation_sessions 
                    SET status = 'transcribed', raw_transcript = 'Test transcript for typist review',
                        priority = 'routine'
                    WHERE session_id = ?
                ''', (session_id,))
                
                conn.commit()
                conn.close()
                
                print("✅ Test session marked as ready for typist")
                return session_id
            else:
                print(f"❌ Session creation failed: {data.get('error')}")
        else:
            print(f"❌ Session creation endpoint failed: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Error creating test session: {e}")
    
    return None

def test_claim_release_workflow(cookies, session_id):
    """Test claiming and releasing reports"""
    print(f"\n🔄 Testing claim/release workflow for session {session_id}...")
    
    # Test claiming
    response = requests.post(f"{BASE_URL}/api/reporting/typist/claim/{session_id}", 
                           cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Report claimed successfully")
        else:
            print(f"❌ Claim failed: {data.get('error')}")
            return False
    else:
        print(f"❌ Claim endpoint failed: {response.status_code}")
        return False
    
    # Test releasing
    response = requests.post(f"{BASE_URL}/api/reporting/typist/release/{session_id}", 
                           cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Report released successfully")
            return True
        else:
            print(f"❌ Release failed: {data.get('error')}")
    else:
        print(f"❌ Release endpoint failed: {response.status_code}")
    
    return False

def main():
    """Run all Phase 2 tests"""
    print("🇿🇦 SA Medical Reporting - Phase 2 Typist Workflow Tests")
    print("=" * 70)
    
    # Test authentication
    cookies = test_authentication()
    if not cookies:
        print("\n❌ Cannot continue without authentication")
        sys.exit(1)
    
    # Run tests
    tests = [
        ("Database Migrations", lambda: test_database_migrations(cookies)),
        ("System Status", lambda: test_system_status(cookies)),
        ("Queue Endpoints", lambda: test_queue_endpoints(cookies)),
        ("Queue Statistics", lambda: test_queue_statistics(cookies))
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Test workflow with actual session
    session_id = create_test_session(cookies)
    if session_id:
        workflow_result = test_claim_release_workflow(cookies, session_id)
        results.append(("Claim/Release Workflow", workflow_result))
    
    # Print summary
    print("\n" + "=" * 70)
    print("📋 PHASE 2 TEST SUMMARY")
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
        print("🎉 All Phase 2 tests passed! Typist workflow system is working correctly.")
        sys.exit(0)
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()