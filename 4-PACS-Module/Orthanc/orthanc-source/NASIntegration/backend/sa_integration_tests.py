#!/usr/bin/env python3
"""
🧪 SA Healthcare Integration Testing Framework
Comprehensive testing framework for all SA healthcare components
"""

import unittest
import requests
import json
import time
import sqlite3
import os
from datetime import datetime
import threading
import subprocess
import sys
import concurrent.futures

class SAIntegrationTestFramework:
    """Main testing framework for SA healthcare integration"""
    
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.setup_complete = False
        
    def setup_test_environment(self):
        """Setup test environment"""
        print("🔧 Setting up SA Healthcare test environment...")
        
        # Wait for server to be ready
        self.wait_for_server()
        
        # Login to get session
        self.login_test_user()
        
        self.setup_complete = True
        print("✅ Test environment ready")
    
    def wait_for_server(self, timeout=30):
        """Wait for Flask server to be ready"""
        print("⏳ Waiting for server to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.base_url}/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Server is ready")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        
        raise Exception("Server not ready within timeout")
    
    def login_test_user(self):
        """Login with test credentials"""
        login_data = {
            'username': 'admin',
            'pin': 'admin'
        }
        
        response = self.session.post(f"{self.base_url}/api/auth/login", json=login_data)
        if response.status_code != 200:
            raise Exception(f"Login failed: {response.text}")
        
        print("✅ Test user logged in")
    
    def run_all_tests(self):
        """Run all integration tests"""
        if not self.setup_complete:
            self.setup_test_environment()
        
        print("\n🧪 Running SA Healthcare Integration Tests")
        print("=" * 60)
        
        test_suites = [
            self.test_authentication_system,
            self.test_healthcare_professionals_api,
            self.test_medical_aid_integration,
            self.test_multilanguage_support,
            self.test_orthanc_integration,
            self.test_compliance_system,
            self.test_web_interfaces,
            self.test_database_operations,
            self.test_error_handling,
            self.test_performance
        ]
        
        for test_suite in test_suites:
            try:
                test_suite()
            except Exception as e:
                self.record_test_result(test_suite.__name__, False, str(e))
        
        self.generate_test_report()
    
    def record_test_result(self, test_name, success, details=""):
        """Record test result"""
        result = {
            'test_name': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if not success and details:
            print(f"   Details: {details}")
    
    def test_authentication_system(self):
        """Test authentication system"""
        print("\n🔐 Testing Authentication System...")
        
        # Test login
        response = self.session.post(f"{self.base_url}/api/auth/login", json={
            'username': 'admin',
            'pin': 'admin'
        })
        self.record_test_result("auth_login", response.status_code == 200)
        
        # Test session validation
        response = self.session.get(f"{self.base_url}/api/auth/validate")
        self.record_test_result("auth_validate", response.status_code == 200)
        
        # Test logout
        response = self.session.post(f"{self.base_url}/api/auth/logout")
        self.record_test_result("auth_logout", response.status_code == 200)
        
        # Re-login for other tests
        self.login_test_user()
    
    def test_healthcare_professionals_api(self):
        """Test healthcare professionals API"""
        print("\n🏥 Testing Healthcare Professionals API...")
        
        # Test get categories
        response = self.session.get(f"{self.base_url}/api/sa/professionals/categories")
        self.record_test_result("professionals_categories", response.status_code == 200)
        
        # Test get provinces
        response = self.session.get(f"{self.base_url}/api/sa/professionals/provinces")
        self.record_test_result("professionals_provinces", response.status_code == 200)
        
        # Test list professionals
        response = self.session.get(f"{self.base_url}/api/sa/professionals")
        self.record_test_result("professionals_list", response.status_code == 200)
        
        # Test create professional
        test_professional = {
            'hpcsa_number': 'MP999999',
            'first_name': 'Test',
            'last_name': 'Professional',
            'email': 'test@example.com',
            'registration_category': 'MP',
            'province_code': 'GP'
        }
        
        response = self.session.post(f"{self.base_url}/api/sa/professionals", json=test_professional)
        self.record_test_result("professionals_create", response.status_code == 201)
        
        # Test search professionals
        response = self.session.get(f"{self.base_url}/api/sa/professionals?search=Test")
        self.record_test_result("professionals_search", response.status_code == 200)
    
    def test_medical_aid_integration(self):
        """Test medical aid integration"""
        print("\n🏥 Testing Medical Aid Integration...")
        
        # Test get schemes
        response = self.session.get(f"{self.base_url}/api/sa/medical-aid/schemes")
        self.record_test_result("medical_aid_schemes", response.status_code == 200)
        
        # Test validate member
        test_member = {
            'scheme_code': 'DISC',
            'member_number': '123456789',
            'id_number': '8001015009087'
        }
        
        response = self.session.post(f"{self.base_url}/api/sa/medical-aid/validate", json=test_member)
        self.record_test_result("medical_aid_validate", response.status_code in [200, 404])
        
        # Test get member info
        response = self.session.get(f"{self.base_url}/api/sa/medical-aid/member/DISC/123456789")
        self.record_test_result("medical_aid_member_info", response.status_code in [200, 404])
    
    def test_multilanguage_support(self):
        """Test multi-language support"""
        print("\n🌍 Testing Multi-Language Support...")
        
        # Test get supported languages
        response = self.session.get(f"{self.base_url}/api/sa/language/languages")
        self.record_test_result("language_list", response.status_code == 200)
        
        # Test set language
        response = self.session.post(f"{self.base_url}/api/sa/language/set", json={'language': 'af'})
        self.record_test_result("language_set", response.status_code == 200)
        
        # Test get medical translations
        response = self.session.get(f"{self.base_url}/api/sa/language/translate/medical?language=af")
        self.record_test_result("language_medical_translations", response.status_code == 200)
        
        # Test get UI translations
        response = self.session.get(f"{self.base_url}/api/sa/language/translate/ui?language=zu")
        self.record_test_result("language_ui_translations", response.status_code == 200)
        
        # Test batch translation
        test_terms = {
            'terms': ['patient', 'doctor', 'hospital'],
            'language': 'xh',
            'category': 'medical'
        }
        response = self.session.post(f"{self.base_url}/api/sa/language/translate/batch", json=test_terms)
        self.record_test_result("language_batch_translate", response.status_code == 200)
    
    def test_orthanc_integration(self):
        """Test Orthanc integration"""
        print("\n🏥 Testing Orthanc Integration...")
        
        # Test Orthanc system info
        response = self.session.get(f"{self.base_url}/api/orthanc/system")
        self.record_test_result("orthanc_system_info", response.status_code == 200)
        
        # Test Orthanc statistics
        response = self.session.get(f"{self.base_url}/api/orthanc/statistics")
        self.record_test_result("orthanc_statistics", response.status_code == 200)
        
        # Test patients list
        response = self.session.get(f"{self.base_url}/api/orthanc/patients")
        self.record_test_result("orthanc_patients", response.status_code == 200)
        
        # Test studies list
        response = self.session.get(f"{self.base_url}/api/orthanc/studies")
        self.record_test_result("orthanc_studies", response.status_code == 200)
    
    def test_compliance_system(self):
        """Test compliance system"""
        print("\n⚖️ Testing Compliance System...")
        
        # Test HPCSA validation
        test_hpcsa = {'hpcsa_number': 'MP123456'}
        response = self.session.post(f"{self.base_url}/api/sa/professionals/validate-hpcsa", json=test_hpcsa)
        self.record_test_result("compliance_hpcsa_validation", response.status_code in [200, 400])
        
        # Test SA ID validation
        test_id = {'id_number': '8001015009087'}
        response = self.session.post(f"{self.base_url}/api/sa/validate-id", json=test_id)
        self.record_test_result("compliance_id_validation", response.status_code in [200, 400])
        
        # Test audit log creation
        audit_entry = {
            'action': 'TEST_ACTION',
            'resource': 'TEST_RESOURCE',
            'details': 'Integration test audit entry'
        }
        response = self.session.post(f"{self.base_url}/api/audit/log", json=audit_entry)
        self.record_test_result("compliance_audit_log", response.status_code in [200, 201])
    
    def test_web_interfaces(self):
        """Test web interfaces"""
        print("\n🌐 Testing Web Interfaces...")
        
        # Test main dashboard
        response = self.session.get(f"{self.base_url}/")
        self.record_test_result("web_dashboard", response.status_code == 200)
        
        # Test patient viewer
        response = self.session.get(f"{self.base_url}/patient-viewer")
        self.record_test_result("web_patient_viewer", response.status_code == 200)
        
        # Test DICOM viewer
        response = self.session.get(f"{self.base_url}/dicom-viewer")
        self.record_test_result("web_dicom_viewer", response.status_code == 200)
        
        # Test server management
        response = self.session.get(f"{self.base_url}/server-management")
        self.record_test_result("web_server_management", response.status_code == 200)
    
    def test_database_operations(self):
        """Test database operations"""
        print("\n🗄️ Testing Database Operations...")
        
        # Test database health
        response = self.session.get(f"{self.base_url}/api/database/health")
        self.record_test_result("database_health", response.status_code == 200)
        
        # Test database statistics
        response = self.session.get(f"{self.base_url}/api/database/stats")
        self.record_test_result("database_stats", response.status_code == 200)
        
        # Test data migration status
        response = self.session.get(f"{self.base_url}/api/migration/status")
        self.record_test_result("database_migration_status", response.status_code == 200)
    
    def test_error_handling(self):
        """Test error handling"""
        print("\n❌ Testing Error Handling...")
        
        # Test invalid authentication
        invalid_session = requests.Session()
        response = invalid_session.get(f"{self.base_url}/api/sa/professionals")
        self.record_test_result("error_invalid_auth", response.status_code == 401)
        
        # Test invalid data
        response = self.session.post(f"{self.base_url}/api/sa/professionals", json={'invalid': 'data'})
        self.record_test_result("error_invalid_data", response.status_code == 400)
        
        # Test non-existent endpoint
        response = self.session.get(f"{self.base_url}/api/nonexistent")
        self.record_test_result("error_not_found", response.status_code == 404)
    
    def test_performance(self):
        """Test basic performance"""
        print("\n⚡ Testing Performance...")
        
        # Test response times
        start_time = time.time()
        response = self.session.get(f"{self.base_url}/api/sa/professionals")
        response_time = time.time() - start_time
        
        self.record_test_result("performance_professionals_api", 
                              response.status_code == 200 and response_time < 2.0,
                              f"Response time: {response_time:.2f}s")
        
        # Test concurrent requests
        def make_request():
            return self.session.get(f"{self.base_url}/api/sa/language/languages")
        
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        concurrent_time = time.time() - start_time
        success_count = sum(1 for r in results if r.status_code == 200)
        
        self.record_test_result("performance_concurrent_requests",
                              success_count >= 8 and concurrent_time < 5.0,
                              f"Successful: {success_count}/10, Time: {concurrent_time:.2f}s")
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 60)
        print("🧪 SA HEALTHCARE INTEGRATION TEST REPORT")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test_name']}: {result['details']}")
        
        print("\n📊 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"  {status} {result['test_name']}")
            if result['details']:
                print(f"    Details: {result['details']}")
        
        # Save report to file
        report_file = f"sa_integration_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': (passed_tests/total_tests)*100,
                    'timestamp': datetime.now().isoformat()
                },
                'results': self.test_results
            }, f, indent=2)
        
        print(f"\n📄 Report saved to: {report_file}")
        
        return passed_tests == total_tests


class SAHealthcareTestRunner:
    """Test runner for SA Healthcare Integration"""
    
    def __init__(self):
        self.framework = SAIntegrationTestFramework()
    
    def run_quick_tests(self):
        """Run quick smoke tests"""
        print("🚀 Running Quick SA Healthcare Tests...")
        
        self.framework.setup_test_environment()
        
        # Run essential tests only
        self.framework.test_authentication_system()
        self.framework.test_healthcare_professionals_api()
        self.framework.test_multilanguage_support()
        self.framework.test_web_interfaces()
        
        return self.framework.generate_test_report()
    
    def run_full_tests(self):
        """Run comprehensive test suite"""
        print("🧪 Running Full SA Healthcare Integration Tests...")
        return self.framework.run_all_tests()
    
    def run_performance_tests(self):
        """Run performance-focused tests"""
        print("⚡ Running Performance Tests...")
        
        self.framework.setup_test_environment()
        self.framework.test_performance()
        
        return self.framework.generate_test_report()


def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SA Healthcare Integration Tests')
    parser.add_argument('--mode', choices=['quick', 'full', 'performance'], 
                       default='quick', help='Test mode to run')
    parser.add_argument('--url', default='http://localhost:5000', 
                       help='Base URL for testing')
    
    args = parser.parse_args()
    
    # Create test runner
    runner = SAHealthcareTestRunner()
    runner.framework.base_url = args.url
    
    try:
        if args.mode == 'quick':
            success = runner.run_quick_tests()
        elif args.mode == 'full':
            success = runner.run_full_tests()
        elif args.mode == 'performance':
            success = runner.run_performance_tests()
        
        if success:
            print("\n🎉 All tests passed!")
            sys.exit(0)
        else:
            print("\n💥 Some tests failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()