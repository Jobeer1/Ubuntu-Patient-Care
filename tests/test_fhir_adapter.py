"""
Tests for FHIR adapter module (P1-FHIR-004)

Tests the mapping between local database formats and FHIR resources.
"""

import pytest
from fhir_adapter import to_fhir, from_fhir, get_registered_adapters


class TestPatientAdapter:
    """Test Patient resource mapping"""
    
    def test_openemr_to_fhir_patient(self):
        """Test converting OpenEMR patient to FHIR"""
        local_patient = {
            "pid": "12345",
            "fname": "John",
            "lname": "Doe",
            "sex": "M",
            "DOB": "1980-01-15",
            "phone_home": "555-1234",
            "email": "john.doe@example.com"
        }
        
        fhir_patient = to_fhir("Patient", local_patient)
        
        assert fhir_patient["resourceType"] == "Patient"
        assert fhir_patient["identifier"][0]["system"] == "urn:openemr:pid"
        assert fhir_patient["identifier"][0]["value"] == "12345"
        assert fhir_patient["name"][0]["family"] == "Doe"
        assert fhir_patient["name"][0]["given"][0] == "John"
        assert fhir_patient["gender"] == "male"
        assert fhir_patient["birthDate"] == "1980-01-15"
        assert len(fhir_patient["telecom"]) == 2
    
    def test_fhir_to_openemr_patient(self):
        """Test converting FHIR patient to OpenEMR"""
        fhir_patient = {
            "resourceType": "Patient",
            "identifier": [{
                "system": "urn:openemr:pid",
                "value": "12345"
            }],
            "name": [{
                "family": "Doe",
                "given": ["John"]
            }],
            "gender": "male",
            "birthDate": "1980-01-15",
            "telecom": [
                {"system": "phone", "value": "555-1234"},
                {"system": "email", "value": "john.doe@example.com"}
            ]
        }
        
        local_patient = from_fhir("Patient", fhir_patient)
        
        assert local_patient["pid"] == "12345"
        assert local_patient["fname"] == "John"
        assert local_patient["lname"] == "Doe"
        assert local_patient["sex"] == "M"
        assert local_patient["DOB"] == "1980-01-15"
        assert local_patient["phone_home"] == "555-1234"
        assert local_patient["email"] == "john.doe@example.com"
    
    def test_patient_round_trip(self):
        """Test that patient data survives round-trip conversion"""
        original = {
            "pid": "99999",
            "fname": "Jane",
            "lname": "Smith",
            "sex": "F",
            "DOB": "1990-05-20"
        }
        
        fhir = to_fhir("Patient", original)
        restored = from_fhir("Patient", fhir)
        
        assert restored["pid"] == original["pid"]
        assert restored["fname"] == original["fname"]
        assert restored["lname"] == original["lname"]
        assert restored["sex"] == original["sex"]
        assert restored["DOB"] == original["DOB"]
    
    def test_patient_gender_mapping(self):
        """Test gender code mapping"""
        test_cases = [
            ("M", "male"),
            ("F", "female"),
            ("U", "unknown"),
            ("O", "other")
        ]
        
        for local_gender, fhir_gender in test_cases:
            local = {"pid": "1", "sex": local_gender}
            fhir = to_fhir("Patient", local)
            assert fhir["gender"] == fhir_gender


class TestImagingStudyAdapter:
    """Test ImagingStudy resource mapping"""
    
    def test_orthanc_to_fhir_imaging_study(self):
        """Test converting Orthanc metadata to FHIR"""
        local_study = {
            "StudyInstanceUID": "1.2.840.113619.2.55.3.123456789",
            "PatientID": "12345",
            "StudyDate": "20251106",
            "StudyTime": "143000",
            "ModalitiesInStudy": ["CT"],
            "StudyDescription": "Chest CT with contrast",
            "NumberOfStudyRelatedSeries": 3,
            "NumberOfStudyRelatedInstances": 150
        }
        
        fhir_study = to_fhir("ImagingStudy", local_study)
        
        assert fhir_study["resourceType"] == "ImagingStudy"
        assert fhir_study["status"] == "available"
        assert "urn:oid:1.2.840.113619.2.55.3.123456789" in fhir_study["identifier"][0]["value"]
        assert fhir_study["subject"]["identifier"]["value"] == "12345"
        assert fhir_study["started"] == "2025-11-06T14:30:00Z"
        assert fhir_study["modality"][0]["code"] == "CT"
        assert fhir_study["description"] == "Chest CT with contrast"
        assert fhir_study["numberOfSeries"] == 3
        assert fhir_study["numberOfInstances"] == 150
    
    def test_fhir_to_orthanc_imaging_study(self):
        """Test converting FHIR ImagingStudy to Orthanc"""
        fhir_study = {
            "resourceType": "ImagingStudy",
            "status": "available",
            "identifier": [{
                "system": "urn:dicom:uid",
                "value": "urn:oid:1.2.840.113619.2.55.3.123456789"
            }],
            "subject": {
                "identifier": {
                    "system": "urn:openemr:pid",
                    "value": "12345"
                }
            },
            "started": "2025-11-06T14:30:00Z",
            "modality": [{
                "system": "http://dicom.nema.org/resources/ontology/DCM",
                "code": "CT"
            }],
            "description": "Chest CT",
            "numberOfSeries": 3,
            "numberOfInstances": 150
        }
        
        local_study = from_fhir("ImagingStudy", fhir_study)
        
        assert local_study["StudyInstanceUID"] == "1.2.840.113619.2.55.3.123456789"
        assert local_study["PatientID"] == "12345"
        assert local_study["StudyDate"] == "20251106"
        assert local_study["StudyTime"] == "143000"
        assert local_study["ModalitiesInStudy"] == ["CT"]
        assert local_study["StudyDescription"] == "Chest CT"
    
    def test_imaging_study_with_series(self):
        """Test ImagingStudy with series information"""
        local_study = {
            "StudyInstanceUID": "1.2.3.4.5",
            "PatientID": "999",
            "StudyDate": "20251106",
            "ModalitiesInStudy": ["CT"],
            "Series": [
                {
                    "SeriesInstanceUID": "1.2.3.4.5.1",
                    "Modality": "CT",
                    "SeriesNumber": 1,
                    "SeriesDescription": "Axial",
                    "NumberOfSeriesRelatedInstances": 50
                },
                {
                    "SeriesInstanceUID": "1.2.3.4.5.2",
                    "Modality": "CT",
                    "SeriesNumber": 2,
                    "SeriesDescription": "Coronal",
                    "NumberOfSeriesRelatedInstances": 40
                }
            ]
        }
        
        fhir_study = to_fhir("ImagingStudy", local_study)
        
        assert len(fhir_study["series"]) == 2
        assert fhir_study["series"][0]["uid"] == "1.2.3.4.5.1"
        assert fhir_study["series"][0]["number"] == 1
        assert fhir_study["series"][0]["description"] == "Axial"
        assert fhir_study["series"][0]["numberOfInstances"] == 50
    
    def test_imaging_study_round_trip(self):
        """Test ImagingStudy round-trip conversion"""
        original = {
            "StudyInstanceUID": "1.2.3.4.5.6.7",
            "PatientID": "TEST-001",
            "StudyDate": "20251106",
            "StudyTime": "120000",
            "ModalitiesInStudy": ["MR", "CT"]
        }
        
        fhir = to_fhir("ImagingStudy", original)
        restored = from_fhir("ImagingStudy", fhir)
        
        assert restored["StudyInstanceUID"] == original["StudyInstanceUID"]
        assert restored["PatientID"] == original["PatientID"]
        assert restored["StudyDate"] == original["StudyDate"]
        assert restored["StudyTime"] == original["StudyTime"]
        assert set(restored["ModalitiesInStudy"]) == set(original["ModalitiesInStudy"])


class TestAdapterRegistry:
    """Test adapter registration system"""
    
    def test_registered_adapters(self):
        """Test that adapters are registered"""
        adapters = get_registered_adapters()
        assert "Patient" in adapters
        assert "ImagingStudy" in adapters
    
    def test_invalid_resource_type(self):
        """Test error handling for unregistered resource type"""
        with pytest.raises(ValueError, match="No adapter registered"):
            to_fhir("InvalidResource", {})
    
    def test_invalid_resource_type_from_fhir(self):
        """Test error handling for unregistered resource type"""
        with pytest.raises(ValueError, match="No adapter registered"):
            from_fhir("InvalidResource", {})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
