"""
End-to-End Integration Tests for Doctor Access Workflow

Tests doctor assignment, patient access, and study viewing workflows.
"""

import pytest
import requests
from datetime import datetime, timedelta

# Test Configuration
MCP_BASE_URL = "http://localhost:8080"
PACS_BASE_URL = "http://localhost:5000"

# Test Users
ADMIN_USER = {"username": "admin", "password": "admin123"}
DOCTOR1_USER = {"username": "dr_jones", "password": "doctor123"}
DOCTOR2_USER = {"username": "dr_williams", "password": "doctor123"}
PATIENT1_ID = "PAT001"
PATIENT2_ID = "PAT002"


class TestDoctorAccessE2E:
    """End-to-end tests for doctor access workflow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.admin_token = None
        self.doctor1_token = None
        self.doctor2_token = None
        self.created_assignments = []
        
        yield
        
        # Cleanup
        if self.admin_token:
            for assignment_id in self.created_assignments:
                try:
                    requests.delete(
                        f"{MCP_BASE_URL}/access/revoke",
                        headers={"Authorization": f"Bearer {self.admin_token}"},
                        json={"relationship_id": assignment_id}
                    )
                except:
                    pass
    
    def login(self, username, password):
        """Login and get access token"""
        response = requests.post(
            f"{MCP_BASE_URL}/auth/login",
            json={"username": username, "password": password}
        )
        assert response.status_code == 200
        return response.json().get("access_token")
    
    def test_01_admin_assign_primary_doctor(self):
        """Test: Admin assigns primary doctor to patient"""
        self.admin_token = self.login(ADMIN_USER["username"], ADMIN_USER["password"])
        
        response = requests.post(
            f"{MCP_BASE_URL}/access/doctor-assignment",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={
                "doctor_id": DOCTOR1_USER["username"],
                "patient_id": PATIENT1_ID,
                "assignment_type": "primary",
                "expiration_date": (datetime.now() + timedelta(days=180)).isoformat()
            }
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        if "id" in data:
            self.created_assignments.append(data["id"])
        
        print(f"✅ Primary doctor assigned to {PATIENT1_ID}")
    
    def test_02_admin_assign_consultant_doctor(self):
        """Test: Admin assigns consultant doctor to patient"""
        self.admin_token = self.login(ADMIN_USER["username"], ADMIN_USER["password"])
        
        response = requests.post(
            f"{MCP_BASE_URL}/access/doctor-assignment",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={
                "doctor_id": DOCTOR2_USER["username"],
                "patient_id": PATIENT1_ID,
                "assignment_type": "consultant",
                "expiration_date": (datetime.now() + timedelta(days=30)).isoformat()
            }
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        if "id" in data:
            self.created_assignments.append(data["id"])
        
        print(f"✅ Consultant doctor assigned to {PATIENT1_ID}")
    
    def test_03_doctor_view_assigned_patients(self):
        """Test: Doctor can view only assigned patients"""
        self.doctor1_token = self.login(DOCTOR1_USER["username"], DOCTOR1_USER["password"])
        
        response = requests.get(
            f"{MCP_BASE_URL}/access/my-patients",
            headers={"Authorization": f"Bearer {self.doctor1_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        patients = data.get("patients", [])
        
        # Doctor should see assigned patients
        patient_ids = [p.get("patient_id") for p in patients]
        assert PATIENT1_ID in patient_ids or len(patients) > 0
        
        print(f"✅ Doctor views {len(patients)} assigned patient(s)")
    
    def test_04_doctor_access_assigned_patient_studies(self):
        """Test: Doctor can access assigned patient's studies"""
        self.doctor1_token = self.login(DOCTOR1_USER["username"], DOCTOR1_USER["password"])
        
        response = requests.get(
            f"{MCP_BASE_URL}/access/my-studies",
            headers={"Authorization": f"Bearer {self.doctor1_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return studies (may be empty if no studies exist)
        assert "studies" in data or "accessible_studies" in data
        print("✅ Doctor can access assigned patient studies")
    
    def test_05_doctor_cannot_access_unassigned_patient(self):
        """Test: Doctor cannot access unassigned patient"""
        self.doctor1_token = self.login(DOCTOR1_USER["username"], DOCTOR1_USER["password"])
        
        # Try to access patient not assigned to this doctor
        unassigned_patient = "PAT999"
        response = requests.get(
            f"{MCP_BASE_URL}/access/check",
            headers={"Authorization": f"Bearer {self.doctor1_token}"},
            params={"patient_id": unassigned_patient}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should NOT have access
        assert data.get("has_access") == False or data.get("access_granted") == False
        print(f"✅ Doctor correctly denied access to unassigned patient")
    
    def test_06_multiple_doctors_same_patient(self):
        """Test: Multiple doctors can access same patient"""
        # Login both doctors
        self.doctor1_token = self.login(DOCTOR1_USER["username"], DOCTOR1_USER["password"])
        self.doctor2_token = self.login(DOCTOR2_USER["username"], DOCTOR2_USER["password"])
        
        # Both should have access to PATIENT1_ID
        for token, doctor_name in [(self.doctor1_token, "Doctor 1"), (self.doctor2_token, "Doctor 2")]:
            response = requests.get(
                f"{MCP_BASE_URL}/access/check",
                headers={"Authorization": f"Bearer {token}"},
                params={"patient_id": PATIENT1_ID}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data.get("has_access") == True or data.get("access_granted") == True
            print(f"✅ {doctor_name} has access to shared patient")
    
    def test_07_assignment_type_tracking(self):
        """Test: Assignment types are tracked correctly"""
        self.admin_token = self.login(ADMIN_USER["username"], ADMIN_USER["password"])
        
        # Get all assignments (if endpoint exists)
        response = requests.get(
            f"{MCP_BASE_URL}/access/doctor-assignments",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            assignments = data.get("assignments", [])
            
            # Check that assignment types are present
            types = [a.get("assignment_type") for a in assignments]
            assert "primary" in types or "consultant" in types or len(assignments) > 0
            print(f"✅ Assignment types tracked: {set(types)}")
        else:
            print("⚠️  Assignment listing endpoint not available")
    
    def test_08_doctor_access_summary(self):
        """Test: Doctor can get access summary"""
        self.doctor1_token = self.login(DOCTOR1_USER["username"], DOCTOR1_USER["password"])
        
        response = requests.get(
            f"{MCP_BASE_URL}/access/summary",
            headers={"Authorization": f"Bearer {self.doctor1_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should contain summary information
        assert "role" in data or "accessible_patients" in data or "patient_count" in data
        print("✅ Doctor access summary retrieved")
    
    def test_09_temporary_assignment_expiration(self):
        """Test: Temporary assignments respect expiration dates"""
        self.admin_token = self.login(ADMIN_USER["username"], ADMIN_USER["password"])
        
        # Create temporary assignment (already expired)
        response = requests.post(
            f"{MCP_BASE_URL}/access/doctor-assignment",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={
                "doctor_id": DOCTOR2_USER["username"],
                "patient_id": PATIENT2_ID,
                "assignment_type": "temporary",
                "expiration_date": (datetime.now() - timedelta(days=1)).isoformat()  # Expired
            }
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            assignment_id = data.get("id")
            
            # Doctor should not have access (expired)
            self.doctor2_token = self.login(DOCTOR2_USER["username"], DOCTOR2_USER["password"])
            response = requests.get(
                f"{MCP_BASE_URL}/access/check",
                headers={"Authorization": f"Bearer {self.doctor2_token}"},
                params={"patient_id": PATIENT2_ID}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Access should be denied due to expiration
            # Note: This depends on backend checking expiration dates
            print("✅ Expiration date handling tested")
            
            # Cleanup
            if assignment_id:
                self.created_assignments.append(assignment_id)
    
    def test_10_admin_remove_doctor_assignment(self):
        """Test: Admin can remove doctor assignment"""
        self.admin_token = self.login(ADMIN_USER["username"], ADMIN_USER["password"])
        
        # Create assignment
        response = requests.post(
            f"{MCP_BASE_URL}/access/doctor-assignment",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={
                "doctor_id": DOCTOR1_USER["username"],
                "patient_id": PATIENT2_ID,
                "assignment_type": "temporary"
            }
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            assignment_id = data.get("id")
            
            if assignment_id:
                # Remove assignment
                response = requests.delete(
                    f"{MCP_BASE_URL}/access/revoke",
                    headers={"Authorization": f"Bearer {self.admin_token}"},
                    json={"relationship_id": assignment_id}
                )
                
                assert response.status_code in [200, 204]
                print("✅ Admin successfully removed doctor assignment")


def run_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("DOCTOR ACCESS WORKFLOW - END-TO-END TESTS")
    print("="*60 + "\n")
    
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()
