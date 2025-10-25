"""
End-to-End Integration Tests for Patient Access System

Tests the complete workflow from admin assigning access to patients viewing their images.
"""

import pytest
import requests
import time
from datetime import datetime, timedelta

# Test Configuration
MCP_BASE_URL = "http://localhost:8080"
PACS_BASE_URL = "http://localhost:5000"

# Test Users
ADMIN_USER = {
    "username": "admin",
    "password": "admin123",
    "role": "Admin"
}

PATIENT_USER = {
    "username": "patient001",
    "password": "patient123",
    "role": "Patient",
    "patient_id": "PAT001"
}

DOCTOR_USER = {
    "username": "dr_smith",
    "password": "doctor123",
    "role": "Referring Doctor"
}


class TestPatientAccessE2E:
    """End-to-end tests for patient access workflow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.admin_token = None
        self.patient_token = None
        self.doctor_token = None
        self.created_relationships = []
        
        yield
        
        # Cleanup: Revoke all created relationships
        if self.admin_token:
            for rel_id in self.created_relationships:
                try:
                    requests.delete(
                        f"{MCP_BASE_URL}/access/revoke",
                        headers={"Authorization": f"Bearer {self.admin_token}"},
                        json={"relationship_id": rel_id}
                    )
                except:
                    pass
    
    def login(self, username, password):
        """Login and get access token"""
        response = requests.post(
            f"{MCP_BASE_URL}/auth/login",
            json={"username": username, "password": password}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        return data.get("access_token")
    
    def test_01_admin_login(self):
        """Test: Admin can login successfully"""
        self.admin_token = self.login(ADMIN_USER["username"], ADMIN_USER["password"])
        assert self.admin_token is not None
        assert len(self.admin_token) > 20
        print("✅ Admin login successful")
    
    def test_02_patient_login(self):
        """Test: Patient can login successfully"""
        self.patient_token = self.login(PATIENT_USER["username"], PATIENT_USER["password"])
        assert self.patient_token is not None
        print("✅ Patient login successful")
    
    def test_03_admin_grant_patient_access(self):
        """Test: Admin can grant patient access to their own records"""
        # Login as admin
        self.admin_token = self.login(ADMIN_USER["username"], ADMIN_USER["password"])
        
        # Grant access
        response = requests.post(
            f"{MCP_BASE_URL}/access/patient-relationship",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={
                "user_id": PATIENT_USER["username"],
                "patient_id": PATIENT_USER["patient_id"],
                "access_level": "full",
                "expiration_date": (datetime.now() + timedelta(days=365)).isoformat()
            }
        )
        
        assert response.status_code in [200, 201], f"Failed to grant access: {response.text}"
        data = response.json()
        
        # Track for cleanup
        if "id" in data:
            self.created_relationships.append(data["id"])
        
        print(f"✅ Admin granted access to patient {PATIENT_USER['patient_id']}")
    
    def test_04_patient_view_accessible_patients(self):
        """Test: Patient can view their accessible patients"""
        # Login as patient
        self.patient_token = self.login(PATIENT_USER["username"], PATIENT_USER["password"])
        
        # Get user info to get user_id
        response = requests.get(
            f"{MCP_BASE_URL}/auth/status",
            headers={"Authorization": f"Bearer {self.patient_token}"}
        )
        assert response.status_code == 200
        user_data = response.json()
        user_id = user_data.get("user_id") or user_data.get("username")
        
        # Get accessible patients
        response = requests.get(
            f"{MCP_BASE_URL}/access/user/{user_id}/patients",
            headers={"Authorization": f"Bearer {self.patient_token}"}
        )
        
        assert response.status_code == 200, f"Failed to get patients: {response.text}"
        data = response.json()
        
        # Patient should see at least their own record
        assert "patients" in data or "accessible_patients" in data
        patients = data.get("patients") or data.get("accessible_patients", [])
        
        print(f"✅ Patient can view {len(patients)} accessible patient(s)")
    
    def test_05_patient_access_check(self):
        """Test: Patient access check returns correct result"""
        # Login as patient
        self.patient_token = self.login(PATIENT_USER["username"], PATIENT_USER["password"])
        
        # Check access to own patient ID
        response = requests.get(
            f"{MCP_BASE_URL}/access/check",
            headers={"Authorization": f"Bearer {self.patient_token}"},
            params={"patient_id": PATIENT_USER["patient_id"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have access to own records
        assert data.get("has_access") == True or data.get("access_granted") == True
        print(f"✅ Patient access check passed for {PATIENT_USER['patient_id']}")
    
    def test_06_patient_cannot_access_other_patients(self):
        """Test: Patient cannot access other patients' records"""
        # Login as patient
        self.patient_token = self.login(PATIENT_USER["username"], PATIENT_USER["password"])
        
        # Try to access different patient ID
        other_patient_id = "PAT999"
        response = requests.get(
            f"{MCP_BASE_URL}/access/check",
            headers={"Authorization": f"Bearer {self.patient_token}"},
            params={"patient_id": other_patient_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should NOT have access
        assert data.get("has_access") == False or data.get("access_granted") == False
        print(f"✅ Patient correctly denied access to {other_patient_id}")
    
    def test_07_admin_assign_doctor_to_patient(self):
        """Test: Admin can assign doctor to patient"""
        # Login as admin
        self.admin_token = self.login(ADMIN_USER["username"], ADMIN_USER["password"])
        
        # Assign doctor
        response = requests.post(
            f"{MCP_BASE_URL}/access/doctor-assignment",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={
                "doctor_id": DOCTOR_USER["username"],
                "patient_id": PATIENT_USER["patient_id"],
                "assignment_type": "primary",
                "expiration_date": (datetime.now() + timedelta(days=90)).isoformat()
            }
        )
        
        assert response.status_code in [200, 201], f"Failed to assign doctor: {response.text}"
        data = response.json()
        
        # Track for cleanup
        if "id" in data:
            self.created_relationships.append(data["id"])
        
        print(f"✅ Admin assigned doctor to patient {PATIENT_USER['patient_id']}")
    
    def test_08_doctor_view_assigned_patients(self):
        """Test: Doctor can view assigned patients"""
        # Login as doctor
        self.doctor_token = self.login(DOCTOR_USER["username"], DOCTOR_USER["password"])
        
        # Get user info
        response = requests.get(
            f"{MCP_BASE_URL}/auth/status",
            headers={"Authorization": f"Bearer {self.doctor_token}"}
        )
        assert response.status_code == 200
        user_data = response.json()
        user_id = user_data.get("user_id") or user_data.get("username")
        
        # Get assigned patients
        response = requests.get(
            f"{MCP_BASE_URL}/access/my-patients",
            headers={"Authorization": f"Bearer {self.doctor_token}"}
        )
        
        assert response.status_code == 200, f"Failed to get patients: {response.text}"
        data = response.json()
        
        # Doctor should see assigned patients
        patients = data.get("patients", [])
        print(f"✅ Doctor can view {len(patients)} assigned patient(s)")
    
    def test_09_doctor_access_assigned_patient(self):
        """Test: Doctor can access assigned patient's records"""
        # Login as doctor
        self.doctor_token = self.login(DOCTOR_USER["username"], DOCTOR_USER["password"])
        
        # Check access to assigned patient
        response = requests.get(
            f"{MCP_BASE_URL}/access/check",
            headers={"Authorization": f"Bearer {self.doctor_token}"},
            params={"patient_id": PATIENT_USER["patient_id"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have access to assigned patient
        assert data.get("has_access") == True or data.get("access_granted") == True
        print(f"✅ Doctor access check passed for assigned patient {PATIENT_USER['patient_id']}")
    
    def test_10_admin_revoke_access(self):
        """Test: Admin can revoke access"""
        # Login as admin
        self.admin_token = self.login(ADMIN_USER["username"], ADMIN_USER["password"])
        
        # Create a relationship to revoke
        response = requests.post(
            f"{MCP_BASE_URL}/access/patient-relationship",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={
                "user_id": "temp_user",
                "patient_id": "PAT_TEMP",
                "access_level": "read"
            }
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            rel_id = data.get("id")
            
            if rel_id:
                # Revoke the access
                response = requests.delete(
                    f"{MCP_BASE_URL}/access/revoke",
                    headers={"Authorization": f"Bearer {self.admin_token}"},
                    json={"relationship_id": rel_id}
                )
                
                assert response.status_code in [200, 204], f"Failed to revoke: {response.text}"
                print(f"✅ Admin successfully revoked access")
    
    def test_11_token_expiration_handling(self):
        """Test: System handles expired tokens correctly"""
        # Use an obviously invalid/expired token
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2MDAwMDAwMDB9.invalid"
        
        response = requests.get(
            f"{MCP_BASE_URL}/access/my-patients",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        # Should return 401 Unauthorized
        assert response.status_code == 401
        print("✅ Expired token correctly rejected")
    
    def test_12_performance_check(self):
        """Test: API response times are acceptable"""
        # Login
        self.admin_token = self.login(ADMIN_USER["username"], ADMIN_USER["password"])
        
        # Measure access check performance
        start_time = time.time()
        response = requests.get(
            f"{MCP_BASE_URL}/access/check",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            params={"patient_id": "PAT001"}
        )
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to ms
        
        assert response.status_code == 200
        assert response_time < 500, f"Response too slow: {response_time}ms"
        print(f"✅ Access check completed in {response_time:.2f}ms")


def run_tests():
    """Run all tests and generate report"""
    print("\n" + "="*60)
    print("PATIENT ACCESS SYSTEM - END-TO-END TESTS")
    print("="*60 + "\n")
    
    # Run pytest
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()
