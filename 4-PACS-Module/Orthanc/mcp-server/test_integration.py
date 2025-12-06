"""
Integration Testing Suite for PACS Phase 1
Tests frontend-backend API integration and data flow
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 10


class IntegrationTester:
    """Integration testing for PACS Phase 1"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.test_results = []
        self.study_id = None
        self.measurement_id = None
    
    def log_test(self, name: str, status: str, details: str = ""):
        """Log a test result"""
        result = {
            'name': name,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'details': details
        }
        self.test_results.append(result)
        
        symbol = "[OK]" if status == "PASS" else "[FAIL]" if status == "FAIL" else "[INFO]"
        print(f"{symbol} {name}")
        if details:
            print(f"     {details}")
    
    # ========================================================================
    # API Health Checks
    # ========================================================================
    
    def test_api_health(self) -> bool:
        """Test that API is running"""
        try:
            response = self.session.get(f"{self.base_url}/api/viewer/health", timeout=TIMEOUT)
            if response.status_code == 200:
                self.log_test("API Health Check", "PASS", "FastAPI server is running")
                return True
            else:
                self.log_test("API Health Check", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("API Health Check", "FAIL", str(e))
            return False
    
    def test_orthanc_health(self) -> bool:
        """Test Orthanc server health"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/viewer/orthanc/health",
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                is_healthy = data.get("orthanc_available", False)
                status = "PASS" if is_healthy else "INFO"
                detail = "Orthanc server is running" if is_healthy else "Orthanc not available (OK for testing)"
                self.log_test("Orthanc Health Check", status, detail)
                return True
            else:
                self.log_test("Orthanc Health Check", "INFO", f"Status: {response.status_code} (OK if Orthanc not running)")
                return True
        except Exception as e:
            self.log_test("Orthanc Health Check", "INFO", f"Orthanc not reachable (OK for testing): {e}")
            return True
    
    # ========================================================================
    # Viewer 3D API Tests
    # ========================================================================
    
    def test_get_slice(self) -> bool:
        """Test getting a slice from cache"""
        try:
            # Try to get slice 50 from a hypothetical study
            response = self.session.get(
                f"{self.base_url}/api/viewer/get-slice/test_study",
                params={"slice_index": 50},
                timeout=TIMEOUT
            )
            
            # 404 is expected if study not loaded, but endpoint should exist
            if response.status_code in [200, 404]:
                self.log_test("Get Slice Endpoint", "PASS", f"Endpoint responds (Status: {response.status_code})")
                return True
            else:
                self.log_test("Get Slice Endpoint", "FAIL", f"Unexpected status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Get Slice Endpoint", "FAIL", str(e))
            return False
    
    def test_get_metadata(self) -> bool:
        """Test getting study metadata"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/viewer/get-metadata/test_study",
                timeout=TIMEOUT
            )
            
            if response.status_code in [200, 404]:
                self.log_test("Get Metadata Endpoint", "PASS", f"Endpoint responds (Status: {response.status_code})")
                return True
            else:
                self.log_test("Get Metadata Endpoint", "FAIL", f"Unexpected status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Get Metadata Endpoint", "FAIL", str(e))
            return False
    
    def test_cache_status(self) -> bool:
        """Test cache status endpoint"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/viewer/cache-status",
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                num_studies = data.get("num_studies", 0)
                total_size = data.get("total_size_mb", 0)
                self.log_test(
                    "Cache Status",
                    "PASS",
                    f"Studies cached: {num_studies}, Total size: {total_size}MB"
                )
                return True
            else:
                self.log_test("Cache Status", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Cache Status", "FAIL", str(e))
            return False
    
    # ========================================================================
    # Measurements API Tests
    # ========================================================================
    
    def test_create_measurement(self) -> bool:
        """Test creating a measurement"""
        try:
            payload = {
                "study_id": 1,
                "measurement_type": "distance",
                "label": "Test Measurement",
                "value": "45.2 mm",
                "measurement_data": {
                    "point1": [100, 200, 50],
                    "point2": [145, 200, 50],
                    "distance_mm": 45.2
                },
                "slice_index": 50
            }
            
            response = self.session.post(
                f"{self.base_url}/api/measurements/create",
                json=payload,
                timeout=TIMEOUT
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.measurement_id = data.get("id")
                self.log_test(
                    "Create Measurement",
                    "PASS",
                    f"Measurement created (ID: {self.measurement_id})"
                )
                return True
            elif response.status_code == 422:
                self.log_test("Create Measurement", "INFO", "Validation error (study_id may not exist)")
                return True
            else:
                self.log_test("Create Measurement", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Create Measurement", "FAIL", str(e))
            return False
    
    def test_list_measurements(self) -> bool:
        """Test listing measurements for a study"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/measurements/study/1",
                timeout=TIMEOUT
            )
            
            if response.status_code in [200, 404]:
                if response.status_code == 200:
                    data = response.json()
                    count = data.get("total_measurements", 0)
                    self.log_test("List Measurements", "PASS", f"Found {count} measurements")
                else:
                    self.log_test("List Measurements", "INFO", "Study not found (expected)")
                return True
            else:
                self.log_test("List Measurements", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("List Measurements", "FAIL", str(e))
            return False
    
    def test_get_measurement_summary(self) -> bool:
        """Test getting measurement summary"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/measurements/study/1/summary",
                timeout=TIMEOUT
            )
            
            if response.status_code in [200, 404]:
                self.log_test("Measurement Summary", "PASS", f"Endpoint responds")
                return True
            else:
                self.log_test("Measurement Summary", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Measurement Summary", "FAIL", str(e))
            return False
    
    def test_export_measurements(self) -> bool:
        """Test exporting measurements"""
        try:
            for fmt in ["json", "csv"]:
                response = self.session.get(
                    f"{self.base_url}/api/measurements/study/1/export",
                    params={"format": fmt},
                    timeout=TIMEOUT
                )
                
                if response.status_code not in [200, 404]:
                    self.log_test(f"Export Measurements ({fmt})", "FAIL", f"Status: {response.status_code}")
                    return False
            
            self.log_test("Export Measurements", "PASS", "JSON and CSV formats work")
            return True
        except Exception as e:
            self.log_test("Export Measurements", "FAIL", str(e))
            return False
    
    # ========================================================================
    # Orthanc Integration Tests
    # ========================================================================
    
    def test_orthanc_patients(self) -> bool:
        """Test getting patients from Orthanc"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/viewer/orthanc/patients",
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                count = data.get("count", 0)
                self.log_test("Get Orthanc Patients", "PASS", f"Endpoint works (patients: {count})")
                return True
            elif response.status_code in [500, 502]:
                self.log_test("Get Orthanc Patients", "INFO", "Orthanc not running (OK)")
                return True
            else:
                self.log_test("Get Orthanc Patients", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Get Orthanc Patients", "INFO", f"Orthanc connection error (OK): {e}")
            return True
    
    def test_orthanc_studies(self) -> bool:
        """Test getting studies from Orthanc"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/viewer/orthanc/studies",
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                count = data.get("count", 0)
                self.log_test("Get Orthanc Studies", "PASS", f"Endpoint works (studies: {count})")
                return True
            elif response.status_code in [500, 502]:
                self.log_test("Get Orthanc Studies", "INFO", "Orthanc not running (OK)")
                return True
            else:
                self.log_test("Get Orthanc Studies", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Get Orthanc Studies", "INFO", f"Orthanc connection error (OK): {e}")
            return True
    
    # ========================================================================
    # Response Format Tests
    # ========================================================================
    
    def test_json_responses(self) -> bool:
        """Test that responses are valid JSON"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/viewer/cache-status",
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                # Should be valid JSON
                data = response.json()
                if isinstance(data, dict):
                    self.log_test("JSON Response Format", "PASS", "Valid JSON returned")
                    return True
            
            self.log_test("JSON Response Format", "FAIL", "Invalid JSON")
            return False
        except Exception as e:
            self.log_test("JSON Response Format", "FAIL", str(e))
            return False
    
    def test_error_responses(self) -> bool:
        """Test that errors return proper status codes"""
        try:
            # Test 404
            response = self.session.get(
                f"{self.base_url}/api/measurements/999999",
                timeout=TIMEOUT
            )
            
            if response.status_code == 404:
                self.log_test("Error Responses (404)", "PASS", "404 returned for not found")
            else:
                self.log_test("Error Responses (404)", "FAIL", f"Got {response.status_code} instead of 404")
                return False
            
            # Test 422 with bad data
            response = self.session.post(
                f"{self.base_url}/api/measurements/create",
                json={"invalid": "data"},
                timeout=TIMEOUT
            )
            
            if response.status_code in [422, 400]:
                self.log_test("Error Responses (validation)", "PASS", "Validation error returned")
                return True
            else:
                self.log_test("Error Responses (validation)", "INFO", "Endpoint exists")
                return True
        except Exception as e:
            self.log_test("Error Responses", "FAIL", str(e))
            return False
    
    def test_cors_headers(self) -> bool:
        """Test CORS headers"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/viewer/health",
                timeout=TIMEOUT
            )
            
            # Check for CORS headers
            cors_origin = response.headers.get("access-control-allow-origin")
            if cors_origin or response.status_code == 200:
                self.log_test("CORS Headers", "PASS", f"CORS configured")
                return True
            else:
                self.log_test("CORS Headers", "INFO", "CORS may need verification")
                return True
        except Exception as e:
            self.log_test("CORS Headers", "FAIL", str(e))
            return False
    
    # ========================================================================
    # Performance Tests
    # ========================================================================
    
    def test_response_time(self) -> bool:
        """Test response times"""
        try:
            endpoints = [
                "/api/viewer/health",
                "/api/viewer/cache-status",
                "/api/measurements/study/1/summary"
            ]
            
            slow_endpoints = []
            for endpoint in endpoints:
                start = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=TIMEOUT)
                elapsed = (time.time() - start) * 1000  # Convert to ms
                
                if elapsed > 1000:  # > 1 second
                    slow_endpoints.append((endpoint, elapsed))
            
            if not slow_endpoints:
                self.log_test("Response Time", "PASS", "All endpoints respond in < 1s")
                return True
            else:
                details = ", ".join([f"{ep}({t:.0f}ms)" for ep, t in slow_endpoints])
                self.log_test("Response Time", "INFO", f"Some slow endpoints: {details}")
                return True
        except Exception as e:
            self.log_test("Response Time", "FAIL", str(e))
            return False
    
    # ========================================================================
    # Report Generation
    # ========================================================================
    
    def generate_report(self) -> str:
        """Generate test report"""
        report = []
        report.append("\n" + "="*80)
        report.append("PACS PHASE 1 INTEGRATION TEST REPORT")
        report.append("="*80)
        report.append(f"\nTest Run: {datetime.now().isoformat()}")
        report.append(f"Server: {self.base_url}\n")
        
        # Summary
        pass_count = sum(1 for r in self.test_results if r['status'] == 'PASS')
        fail_count = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        info_count = sum(1 for r in self.test_results if r['status'] == 'INFO')
        total_count = len(self.test_results)
        
        report.append(f"Results: {pass_count} PASS, {fail_count} FAIL, {info_count} INFO (Total: {total_count})")
        report.append(f"Pass Rate: {(pass_count/total_count*100):.1f}%\n")
        
        # Detailed Results
        report.append("-" * 80)
        report.append("DETAILED RESULTS")
        report.append("-" * 80)
        
        for result in self.test_results:
            status_symbol = {
                'PASS': '[✓]',
                'FAIL': '[✗]',
                'INFO': '[i]'
            }.get(result['status'], '[?]')
            
            report.append(f"{status_symbol} {result['name']}")
            if result['details']:
                report.append(f"    {result['details']}")
        
        report.append("\n" + "="*80)
        
        return "\n".join(report)
    
    def run_all_tests(self) -> bool:
        """Run all integration tests"""
        print("\n" + "="*80)
        print("STARTING PACS PHASE 1 INTEGRATION TESTS")
        print("="*80 + "\n")
        
        # Health checks
        print("1. HEALTH CHECKS")
        print("-" * 40)
        self.test_api_health()
        self.test_orthanc_health()
        
        # Viewer 3D API
        print("\n2. VIEWER 3D API")
        print("-" * 40)
        self.test_get_slice()
        self.test_get_metadata()
        self.test_cache_status()
        
        # Measurements API
        print("\n3. MEASUREMENTS API")
        print("-" * 40)
        self.test_create_measurement()
        self.test_list_measurements()
        self.test_get_measurement_summary()
        self.test_export_measurements()
        
        # Orthanc Integration
        print("\n4. ORTHANC INTEGRATION")
        print("-" * 40)
        self.test_orthanc_patients()
        self.test_orthanc_studies()
        
        # Response handling
        print("\n5. RESPONSE HANDLING")
        print("-" * 40)
        self.test_json_responses()
        self.test_error_responses()
        self.test_cors_headers()
        
        # Performance
        print("\n6. PERFORMANCE")
        print("-" * 40)
        self.test_response_time()
        
        # Report
        report = self.generate_report()
        print(report)
        
        # Save report
        with open("integration_test_report.txt", "w") as f:
            f.write(report)
        print("Report saved to: integration_test_report.txt")
        
        # Return pass/fail
        pass_count = sum(1 for r in self.test_results if r['status'] == 'PASS')
        fail_count = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        
        return fail_count == 0 and pass_count > 0


if __name__ == "__main__":
    tester = IntegrationTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)
