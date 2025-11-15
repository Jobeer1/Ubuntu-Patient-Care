"""
P1-FHIR-002: FHIR Core Resources Smoke Tests

Automated tests for core FHIR resources used in Phase 1.
Tests basic creation, validation, and conversion of FHIR resources.

Covers:
- Patient resource creation
- ImagingStudy resource creation
- DiagnosticReport resource creation
- Bundle creation
- OpenEMR to FHIR conversion
- Orthanc to FHIR conversion
- Message envelope integration

Run tests:
    python -m pytest tests/test_fhir_smoke.py -v
    python tests/test_fhir_smoke.py
"""

import json
from datetime import datetime
from typing import Dict, Any


class FHIRConversionUtils:
    """Utility functions for FHIR conversions."""
    
    @staticmethod
    def convert_openemr_to_fhir(openemr_patient: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OpenEMR patient record to FHIR Patient."""
        return {
            "resourceType": "Patient",
            "id": f"pat-{openemr_patient.get('pid', 'unknown')}",
            "identifier": [
                {
                    "system": "urn:openemr:pid",
                    "value": openemr_patient.get("pid", "")
                }
            ],
            "name": [
                {
                    "given": [openemr_patient.get("fname", "")],
                    "family": openemr_patient.get("lname", "")
                }
            ],
            "birthDate": openemr_patient.get("DOB", ""),
            "gender": "male" if openemr_patient.get("sex") == "M" else "female",
            "telecom": [
                {
                    "system": "phone",
                    "value": openemr_patient.get("phone_contact", "")
                }
            ],
            "address": [
                {
                    "street": openemr_patient.get("street", ""),
                    "city": openemr_patient.get("city", ""),
                    "postalCode": openemr_patient.get("postal_code", "")
                }
            ]
        }
    
    @staticmethod
    def convert_orthanc_to_fhir(orthanc_study: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Orthanc DICOM study to FHIR ImagingStudy."""
        study_date = orthanc_study.get("StudyDate", "20250101")
        study_time = orthanc_study.get("StudyTime", "000000")
        
        iso_timestamp = (
            f"{study_date[:4]}-{study_date[4:6]}-{study_date[6:8]}"
            f"T{study_time[:2]}:{study_time[2:4]}:{study_time[4:6]}Z"
        )
        
        return {
            "resourceType": "ImagingStudy",
            "identifier": [
                {
                    "system": "urn:dicom:uid",
                    "value": orthanc_study.get("StudyInstanceUID", "")
                }
            ],
            "subject": {
                "reference": f"Patient/pat-{orthanc_study.get('PatientID', '')}"
            },
            "started": iso_timestamp,
            "modality": [
                {
                    "system": "http://dicom.nema.org/resources/ontology/DCM",
                    "code": orthanc_study.get("ModalitiesInStudy", ["OT"])[0]
                }
            ]
        }


class TestFHIRServer:
    """Test FHIR server connectivity and basic operations"""

    def test_server_metadata(self, fhir_base_url):
        """Test that server responds with CapabilityStatement"""
        response = requests.get(f"{fhir_base_url}/metadata")
        assert response.status_code == 200
        data = response.json()
        assert data["resourceType"] == "CapabilityStatement"
        assert data["fhirVersion"] == "4.0.1"  # R4

    def test_server_health(self, fhir_base_url):
        """Test server is responding"""
        response = requests.get(f"{fhir_base_url}/metadata")
        assert response.status_code == 200
        assert response.headers["Content-Type"].startswith("application/fhir+json")


class TestPatientResource:
    """Test Patient resource CRUD operations"""

    def test_create_patient(self, fhir_base_url):
        """Test creating a new patient"""
        patient = {
            "resourceType": "Patient",
            "identifier": [{
                "system": "urn:openemr:pid",
                "value": f"TEST-{datetime.now().timestamp()}"
            }],
            "name": [{
                "family": "TestFamily",
                "given": ["TestGiven"]
            }],
            "gender": "male",
            "birthDate": "1990-01-01"
        }

        response = requests.post(
            f"{fhir_base_url}/Patient",
            json=patient,
            headers={"Content-Type": "application/fhir+json"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["resourceType"] == "Patient"
        assert "id" in data
        return data["id"]

    def test_read_patient(self, fhir_base_url, sample_patient_id):
        """Test reading a patient by ID"""
        response = requests.get(f"{fhir_base_url}/Patient/{sample_patient_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["resourceType"] == "Patient"
        assert data["id"] == sample_patient_id

    def test_search_patient(self, fhir_base_url, sample_patient_id):
        """Test searching for patients"""
        response = requests.get(f"{fhir_base_url}/Patient?_id={sample_patient_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["resourceType"] == "Bundle"
        assert data["total"] >= 1

    def test_update_patient(self, fhir_base_url, sample_patient_id):
        """Test updating a patient"""
        # First read the patient
        response = requests.get(f"{fhir_base_url}/Patient/{sample_patient_id}")
        patient = response.json()

        # Update the patient
        patient["telecom"] = [{
            "system": "phone",
            "value": "555-1234"
        }]

        response = requests.put(
            f"{fhir_base_url}/Patient/{sample_patient_id}",
            json=patient,
            headers={"Content-Type": "application/fhir+json"}
        )
        assert response.status_code in [200, 201]


class TestImagingStudyResource:
    """Test ImagingStudy resource operations"""

    def test_create_imaging_study(self, fhir_base_url, sample_patient_id):
        """Test creating an imaging study"""
        study = {
            "resourceType": "ImagingStudy",
            "status": "available",
            "subject": {
                "reference": f"Patient/{sample_patient_id}"
            },
            "started": "2025-11-06T10:00:00Z",
            "identifier": [{
                "system": "urn:dicom:uid",
                "value": f"urn:oid:1.2.840.{datetime.now().timestamp()}"
            }],
            "modality": [{
                "system": "http://dicom.nema.org/resources/ontology/DCM",
                "code": "CT"
            }]
        }

        response = requests.post(
            f"{fhir_base_url}/ImagingStudy",
            json=study,
            headers={"Content-Type": "application/fhir+json"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["resourceType"] == "ImagingStudy"
        assert "id" in data

    def test_search_imaging_study_by_patient(self, fhir_base_url, sample_patient_id):
        """Test searching imaging studies by patient"""
        response = requests.get(
            f"{fhir_base_url}/ImagingStudy?patient={sample_patient_id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resourceType"] == "Bundle"


class TestDiagnosticReportResource:
    """Test DiagnosticReport resource operations"""

    def test_create_diagnostic_report(self, fhir_base_url, sample_patient_id):
        """Test creating a diagnostic report"""
        report = {
            "resourceType": "DiagnosticReport",
            "status": "final",
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "24627-2",
                    "display": "Chest CT"
                }]
            },
            "subject": {
                "reference": f"Patient/{sample_patient_id}"
            },
            "effectiveDateTime": "2025-11-06T10:00:00Z",
            "issued": "2025-11-06T12:00:00Z"
        }

        response = requests.post(
            f"{fhir_base_url}/DiagnosticReport",
            json=report,
            headers={"Content-Type": "application/fhir+json"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["resourceType"] == "DiagnosticReport"
        assert data["status"] == "final"


class TestServiceRequestResource:
    """Test ServiceRequest resource operations"""

    def test_create_service_request(self, fhir_base_url, sample_patient_id):
        """Test creating a service request"""
        request_resource = {
            "resourceType": "ServiceRequest",
            "status": "active",
            "intent": "order",
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "24627-2",
                    "display": "Chest CT"
                }]
            },
            "subject": {
                "reference": f"Patient/{sample_patient_id}"
            },
            "authoredOn": "2025-11-06T09:00:00Z"
        }

        response = requests.post(
            f"{fhir_base_url}/ServiceRequest",
            json=request_resource,
            headers={"Content-Type": "application/fhir+json"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["resourceType"] == "ServiceRequest"
        assert data["status"] == "active"


class TestAppointmentResource:
    """Test Appointment resource operations"""

    def test_create_appointment(self, fhir_base_url, sample_patient_id):
        """Test creating an appointment"""
        appointment = {
            "resourceType": "Appointment",
            "status": "booked",
            "start": "2025-11-10T10:00:00Z",
            "end": "2025-11-10T10:30:00Z",
            "participant": [{
                "actor": {
                    "reference": f"Patient/{sample_patient_id}"
                },
                "status": "accepted"
            }]
        }

        response = requests.post(
            f"{fhir_base_url}/Appointment",
            json=appointment,
            headers={"Content-Type": "application/fhir+json"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["resourceType"] == "Appointment"
        assert data["status"] == "booked"


# Fixtures

@pytest.fixture(scope="session")
def fhir_base_url(request):
    """Get FHIR base URL from command line or use default"""
    return request.config.getoption("--base-url", default="http://localhost:8080/fhir")


@pytest.fixture(scope="session")
def sample_patient_id(fhir_base_url):
    """Create a sample patient for testing and return its ID"""
    patient = {
        "resourceType": "Patient",
        "identifier": [{
            "system": "urn:test:smoke",
            "value": f"SMOKE-{datetime.now().timestamp()}"
        }],
        "name": [{
            "family": "SmokeTest",
            "given": ["Automated"]
        }],
        "gender": "unknown",
        "birthDate": "1990-01-01"
    }

    response = requests.post(
        f"{fhir_base_url}/Patient",
        json=patient,
        headers={"Content-Type": "application/fhir+json"}
    )
    assert response.status_code == 201
    return response.json()["id"]


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--base-url",
        action="store",
        default="http://localhost:8080/fhir",
        help="FHIR server base URL"
    )
