#!/usr/bin/env python3
"""
Sample conversion script: OpenEMR & Orthanc -> FHIR (P1-MAP-001)

Demonstrates converting local database records to FHIR resources
using the mapping CSV specifications and the fhir_adapter module.
"""

import json
import sys
from datetime import datetime

# Import the adapter framework from DEV3's work
sys.path.insert(0, '/mnt/c/Users/Admin/Desktop/ELC/Ubuntu-Patient-Care')
from fhir_adapter import to_fhir, from_fhir


def sample_openemr_patient_conversion():
    """
    Convert a sample OpenEMR patient record to FHIR Patient resource.
    
    Maps fields from openemr_patient_mapping.csv
    """
    print("\n" + "="*70)
    print("Sample 1: OpenEMR Patient -> FHIR Patient")
    print("="*70)
    
    # Local OpenEMR patient record (sample data)
    openemr_patient = {
        "pid": "12345",
        "fname": "John",
        "mname": "Michael",
        "lname": "Doe",
        "sex": "M",
        "DOB": "1980-01-15",
        "phone_home": "555-1234",
        "phone_cell": "555-5678",
        "email": "john.doe@example.com",
        "street_address": "123 Main Street",
        "city": "Springfield",
        "state": "IL",
        "zip": "62701",
        "country": "USA",
        "marital_status": "M",
        "race": "White",
        "ethnicity": "Not Hispanic",
        "insurance_id": "INS-987654321",
        "medical_record_number": "MRN-123456",
        "emergency_contact_name": "Jane Doe",
        "emergency_contact_phone": "555-9999",
        "date_created": "2020-01-15T10:30:00Z",
        "active_status": "active"
    }
    
    print("\nLocal OpenEMR Record:")
    print(json.dumps(openemr_patient, indent=2))
    
    try:
        # Use adapter to convert to FHIR
        fhir_patient = to_fhir("Patient", openemr_patient)
        
        print("\nConverted FHIR Patient Resource:")
        print(json.dumps(fhir_patient, indent=2))
        
        # Verify it's valid FHIR
        assert fhir_patient.get("resourceType") == "Patient"
        assert len(fhir_patient.get("identifier", [])) > 0
        assert fhir_patient.get("name", [{}])[0].get("family") == "Doe"
        
        print("\n[OK] Conversion successful!")
        return fhir_patient
        
    except Exception as e:
        print(f"\n[ERROR] Conversion failed: {e}")
        return None


def sample_orthanc_imaging_conversion():
    """
    Convert a sample Orthanc imaging study record to FHIR ImagingStudy resource.
    
    Maps fields from orthanc_imaging_mapping.csv
    """
    print("\n" + "="*70)
    print("Sample 2: Orthanc ImagingStudy -> FHIR ImagingStudy")
    print("="*70)
    
    # Local Orthanc imaging study record (sample data)
    orthanc_study = {
        "PatientID": "12345",
        "PatientName": "Doe^John",
        "StudyInstanceUID": "1.2.840.113619.2.55.3.123456789",
        "StudyDate": "20251106",
        "StudyTime": "143000",
        "StudyDescription": "Chest X-ray for pneumonia screening",
        "ModalitiesInStudy": "CR",
        "StudyID": "STUDY-001",
        "ReferringPhysicianName": "Smith^John",
        "InstitutionName": "General Hospital",
        "AccessionNumber": "ACC-123456",
        "RequestAttributesSequence": {"indication": "chest pain"},
        "PerformedProcedureStepDescription": "Digital radiography",
        "Series": [
            {
                "SeriesInstanceUID": "1.2.840.113619.2.55.3.123456789.1",
                "SeriesDate": "20251106",
                "SeriesTime": "143000",
                "SeriesDescription": "Frontal view",
                "SeriesNumber": "1",
                "Modality": "CR",
                "NumberOfSeriesRelatedInstances": 1
            }
        ]
    }
    
    print("\nLocal Orthanc Record:")
    print(json.dumps(orthanc_study, indent=2))
    
    try:
        # Use adapter to convert to FHIR
        fhir_imaging = to_fhir("ImagingStudy", orthanc_study)
        
        print("\nConverted FHIR ImagingStudy Resource:")
        print(json.dumps(fhir_imaging, indent=2))
        
        # Verify it's valid FHIR
        assert fhir_imaging.get("resourceType") == "ImagingStudy"
        assert len(fhir_imaging.get("identifier", [])) > 0
        
        print("\n[OK] Conversion successful!")
        return fhir_imaging
        
    except Exception as e:
        print(f"\n[ERROR] Conversion failed: {e}")
        return None


def sample_round_trip_conversion():
    """
    Demonstrate round-trip conversion: local -> FHIR -> local
    
    This tests that the adapter preserves data integrity.
    """
    print("\n" + "="*70)
    print("Sample 3: Round-Trip Conversion (local -> FHIR -> local)")
    print("="*70)
    
    # Original OpenEMR patient
    original_openemr = {
        "pid": "54321",
        "fname": "Jane",
        "lname": "Smith",
        "sex": "F",
        "DOB": "1990-06-20",
        "email": "jane.smith@example.com"
    }
    
    print("\nOriginal OpenEMR Record:")
    print(json.dumps(original_openemr, indent=2))
    
    try:
        # Convert to FHIR
        fhir_patient = to_fhir("Patient", original_openemr)
        print("\nConverted to FHIR:")
        print(json.dumps(fhir_patient, indent=2))
        
        # Convert back to local format
        recovered_openemr = from_fhir("Patient", fhir_patient)
        print("\nRecovered OpenEMR Record:")
        print(json.dumps(recovered_openemr, indent=2))
        
        # Verify key fields match
        assert recovered_openemr["pid"] == original_openemr["pid"]
        assert recovered_openemr["fname"] == original_openemr["fname"]
        assert recovered_openemr["lname"] == original_openemr["lname"]
        
        print("\n[OK] Round-trip conversion successful!")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Round-trip conversion failed: {e}")
        return False


def print_mapping_reference():
    """Print a quick reference to the mapping CSV files"""
    print("\n" + "="*70)
    print("Mapping Reference")
    print("="*70)
    
    print("""
The following CSV files define the data mappings:

1. openemr_patient_mapping.csv
   - Maps OpenEMR patient fields to FHIR Patient resource
   - Columns: Local Field, Type, Example, FHIR Resource, FHIR Path, ...
   - Use this to understand how OpenEMR.pid -> FHIR.Patient.identifier

2. orthanc_imaging_mapping.csv
   - Maps Orthanc DICOM tags to FHIR ImagingStudy resource
   - Columns: Orthanc Field, Type, Example, FHIR Resource, FHIR Path, ...
   - Use this to understand how Orthanc.StudyInstanceUID -> FHIR.ImagingStudy.identifier

How to use:
1. Read the CSV file for your local system (OpenEMR or Orthanc)
2. Export a sample record from your local database
3. Manually map fields according to the CSV or use the sample script
4. Call to_fhir(resource_type, local_record) to get FHIR JSON
5. Verify the output is valid FHIR R4 (use FHIR validator if needed)

For more details, see:
- mappings/README.md
- fhir_adapter/README.md (DEV3's module)
""")


def main():
    """Run all sample conversions"""
    print("\n" + "#"*70)
    print("# FHIR Data Mapping Samples (P1-MAP-001)")
    print("# Converting local database records to FHIR standards")
    print("#"*70)
    
    # Print mapping reference
    print_mapping_reference()
    
    # Run samples
    try:
        # Sample 1: OpenEMR Patient conversion
        fhir_patient = sample_openemr_patient_conversion()
        
        # Sample 2: Orthanc ImagingStudy conversion
        # (Note: actual conversion depends on adapters implemented by DEV3)
        # fhir_imaging = sample_orthanc_imaging_conversion()
        
        # Sample 3: Round-trip conversion
        # roundtrip_ok = sample_round_trip_conversion()
        
        print("\n" + "#"*70)
        print("# Samples Complete")
        print("#"*70)
        print("""
Next steps:
1. Review the converted FHIR resources above
2. Upload to FHIR server: POST to http://localhost:8080/fhir/Patient
3. Verify with: GET http://localhost:8080/fhir/Patient?family=Doe
4. Use dev/fhir/README.md for FHIR sandbox testing

For more details:
- Read mappings/README.md
- Review mapping CSV files
- Check fhir_adapter/README.md for API reference
""")
        
    except Exception as e:
        print(f"\nError running samples: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
