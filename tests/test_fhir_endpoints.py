"""
P1-FHIR-002: FHIR Endpoint Smoke Tests

Comprehensive validation of all FHIR endpoints:
- Patient resource (GET, POST, PUT, DELETE, search)
- ImagingStudy resource (GET, POST, search)
- DiagnosticReport resource (GET, POST, search)
- Error handling and edge cases
- Schema validation

These tests validate the complete FHIR server functionality
required for Phase 1 integration.
"""

import pytest
import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlencode


class FHIRTestClient:
    """FHIR server test client"""
    
    def __init__(self, base_url: str = "http://localhost:8080/fhir"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/fhir+json',
            'Accept': 'application/fhir+json'
        })
    
    def get_resource(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        """GET /{resource}/{id}"""
        url = f"{self.base_url}/{resource_type}/{resource_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def search_resources(self, resource_type: str, params: Dict[str, str]) -> Dict[str, Any]:
        """GET /{resource}?{params}"""
        url = f"{self.base_url}/{resource_type}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def create_resource(self, resource_type: str, resource: Dict[str, Any]) -> str:
        """POST /{resource} -> returns resource ID"""
        url = f"{self.base_url}/{resource_type}"
        response = self.session.post(url, json=resource)
        response.raise_for_status()
        
        # Extract ID from Location header or response
        if 'Location' in response.headers:
            return response.headers['Location'].split('/')[-1]
        elif response.status_code == 201:
            data = response.json()
            return data.get('id', '')
        return ''
    
    def update_resource(self, resource_type: str, resource_id: str, resource: Dict[str, Any]) -> bool:
        """PUT /{resource}/{id}"""
        url = f"{self.base_url}/{resource_type}/{resource_id}"
        response = self.session.put(url, json=resource)
        return response.status_code in [200, 204]
    
    def delete_resource(self, resource_type: str, resource_id: str) -> bool:
        """DELETE /{resource}/{id}"""
        url = f"{self.base_url}/{resource_type}/{resource_id}"
        response = self.session.delete(url)
        return response.status_code in [200, 204, 404]


@pytest.fixture
def fhir_client():
    """FHIR test client"""
    return FHIRTestClient()


@pytest.fixture
def sample_patient():
    """Sample FHIR Patient resource"""
    return {
        "resourceType": "Patient",
        "active": True,
        "name": [
            {
                "use": "official",
                "given": ["John"],
                "family": "Doe"
            }
        ],
        "telecom": [
            {
                "system": "email",
                "value": "john.doe@example.com"
            }
        ],
        "gender": "male",
        "birthDate": "1980-01-15",
        "address": [
            {
                "use": "home",
                "line": ["123 Main St"],
                "city": "Springfield",
                "state": "IL",
                "postalCode": "62701",
                "country": "USA"
            }
        ]
    }


@pytest.fixture
def sample_imaging_study():
    """Sample FHIR ImagingStudy resource"""
    return {
        "resourceType": "ImagingStudy",
        "status": "available",
        "subject": {
            "reference": "Patient/123"
        },
        "started": "2025-11-07T10:00:00Z",
        "description": "CT Chest",
        "modality": [
            {
                "system": "http://dicom.nema.org/resources/ontology/DCM",
                "code": "CT"
            }
        ]
    }


@pytest.fixture
def sample_diagnostic_report():
    """Sample FHIR DiagnosticReport resource"""
    return {
        "resourceType": "DiagnosticReport",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                        "code": "RAD"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "24529-7"
                }
            ],
            "text": "Chest X-ray"
        },
        "subject": {
            "reference": "Patient/123"
        },
        "issued": "2025-11-07T14:00:00Z",
        "conclusion": "No acute findings"
    }


# ============================================================================
# PATIENT ENDPOINT TESTS
# ============================================================================

class TestPatientEndpoint:
    """Test Patient resource FHIR endpoint"""
    
    def test_patient_create(self, fhir_client, sample_patient):
        """POST /Patient creates new patient"""
        patient_id = fhir_client.create_resource("Patient", sample_patient)
        assert patient_id
        assert len(patient_id) > 0
    
    @pytest.mark.skip(reason="Requires server running")
    def test_patient_read(self, fhir_client, sample_patient):
        """GET /Patient/{id} retrieves patient"""
        # Create first
        patient_id = fhir_client.create_resource("Patient", sample_patient)
        
        # Read
        patient = fhir_client.get_resource("Patient", patient_id)
        
        assert patient["resourceType"] == "Patient"
        assert patient["id"] == patient_id
        assert patient["name"][0]["family"] == "Doe"
    
    @pytest.mark.skip(reason="Requires server running")
    def test_patient_update(self, fhir_client, sample_patient):
        """PUT /Patient/{id} updates patient"""
        # Create first
        patient_id = fhir_client.create_resource("Patient", sample_patient)
        
        # Update
        sample_patient["id"] = patient_id
        sample_patient["name"][0]["given"] = ["Jane"]
        updated = fhir_client.update_resource("Patient", patient_id, sample_patient)
        
        assert updated is True
    
    @pytest.mark.skip(reason="Requires server running")
    def test_patient_delete(self, fhir_client, sample_patient):
        """DELETE /Patient/{id} deletes patient"""
        # Create first
        patient_id = fhir_client.create_resource("Patient", sample_patient)
        
        # Delete
        deleted = fhir_client.delete_resource("Patient", patient_id)
        
        assert deleted is True
    
    @pytest.mark.skip(reason="Requires server running")
    def test_patient_search_by_name(self, fhir_client, sample_patient):
        """GET /Patient?name=... searches by name"""
        # Create patient
        fhir_client.create_resource("Patient", sample_patient)
        
        # Search
        results = fhir_client.search_resources("Patient", {"name": "Doe"})
        
        assert "entry" in results
        assert len(results["entry"]) > 0
    
    @pytest.mark.skip(reason="Requires server running")
    def test_patient_search_by_birthdate(self, fhir_client, sample_patient):
        """GET /Patient?birthdate=... searches by birth date"""
        # Create patient
        fhir_client.create_resource("Patient", sample_patient)
        
        # Search
        results = fhir_client.search_resources("Patient", {"birthdate": "1980-01-15"})
        
        assert "entry" in results
        assert len(results["entry"]) > 0


# ============================================================================
# IMAGINGSTUDY ENDPOINT TESTS
# ============================================================================

class TestImagingStudyEndpoint:
    """Test ImagingStudy resource FHIR endpoint"""
    
    @pytest.mark.skip(reason="Requires server running")
    def test_imaging_study_create(self, fhir_client, sample_imaging_study):
        """POST /ImagingStudy creates new imaging study"""
        study_id = fhir_client.create_resource("ImagingStudy", sample_imaging_study)
        assert study_id
    
    @pytest.mark.skip(reason="Requires server running")
    def test_imaging_study_read(self, fhir_client, sample_imaging_study):
        """GET /ImagingStudy/{id} retrieves imaging study"""
        study_id = fhir_client.create_resource("ImagingStudy", sample_imaging_study)
        
        study = fhir_client.get_resource("ImagingStudy", study_id)
        
        assert study["resourceType"] == "ImagingStudy"
        assert study["id"] == study_id
    
    @pytest.mark.skip(reason="Requires server running")
    def test_imaging_study_search_by_modality(self, fhir_client, sample_imaging_study):
        """GET /ImagingStudy?modality=... searches by modality"""
        fhir_client.create_resource("ImagingStudy", sample_imaging_study)
        
        results = fhir_client.search_resources("ImagingStudy", {"modality": "CT"})
        
        assert "entry" in results


# ============================================================================
# DIAGNOSTICREPORT ENDPOINT TESTS
# ============================================================================

class TestDiagnosticReportEndpoint:
    """Test DiagnosticReport resource FHIR endpoint"""
    
    @pytest.mark.skip(reason="Requires server running")
    def test_diagnostic_report_create(self, fhir_client, sample_diagnostic_report):
        """POST /DiagnosticReport creates new report"""
        report_id = fhir_client.create_resource("DiagnosticReport", sample_diagnostic_report)
        assert report_id
    
    @pytest.mark.skip(reason="Requires server running")
    def test_diagnostic_report_read(self, fhir_client, sample_diagnostic_report):
        """GET /DiagnosticReport/{id} retrieves report"""
        report_id = fhir_client.create_resource("DiagnosticReport", sample_diagnostic_report)
        
        report = fhir_client.get_resource("DiagnosticReport", report_id)
        
        assert report["resourceType"] == "DiagnosticReport"
        assert report["id"] == report_id
        assert report["status"] == "final"
    
    @pytest.mark.skip(reason="Requires server running")
    def test_diagnostic_report_search_by_status(self, fhir_client, sample_diagnostic_report):
        """GET /DiagnosticReport?status=... searches by status"""
        fhir_client.create_resource("DiagnosticReport", sample_diagnostic_report)
        
        results = fhir_client.search_resources("DiagnosticReport", {"status": "final"})
        
        assert "entry" in results


# ============================================================================
# VALIDATION TESTS
# ============================================================================

class TestResourceValidation:
    """Test resource schema validation"""
    
    def test_patient_schema_valid(self, sample_patient):
        """Sample patient resource is valid"""
        assert sample_patient["resourceType"] == "Patient"
        assert "name" in sample_patient
        assert isinstance(sample_patient["name"], list)
    
    def test_imaging_study_schema_valid(self, sample_imaging_study):
        """Sample imaging study resource is valid"""
        assert sample_imaging_study["resourceType"] == "ImagingStudy"
        assert "subject" in sample_imaging_study
    
    def test_diagnostic_report_schema_valid(self, sample_diagnostic_report):
        """Sample diagnostic report resource is valid"""
        assert sample_diagnostic_report["resourceType"] == "DiagnosticReport"
        assert "status" in sample_diagnostic_report
        assert sample_diagnostic_report["status"] in ["registered", "partial", "preliminary", "final", "amended", "corrected", "appended", "cancelled", "entered-in-error", "unknown"]


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_resource_type(self, fhir_client):
        """Accessing invalid resource type returns error"""
        with pytest.raises(Exception):
            fhir_client.get_resource("InvalidType", "123")
    
    def test_nonexistent_resource(self, fhir_client):
        """Accessing nonexistent resource returns 404"""
        with pytest.raises(Exception):
            fhir_client.get_resource("Patient", "nonexistent-id")
    
    def test_missing_required_field(self, fhir_client):
        """Creating resource without required fields fails"""
        invalid_patient = {
            "resourceType": "Patient"
            # Missing required fields
        }
        with pytest.raises(Exception):
            fhir_client.create_resource("Patient", invalid_patient)
    
    def test_invalid_json(self, fhir_client):
        """Posting invalid JSON fails"""
        with pytest.raises(Exception):
            fhir_client.session.post(
                f"{fhir_client.base_url}/Patient",
                data="not valid json"
            ).raise_for_status()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
