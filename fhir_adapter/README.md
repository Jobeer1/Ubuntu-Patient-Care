# FHIR Adapter Module

**Task**: P1-FHIR-004  
**Status**: ✅ Complete

## Overview

The FHIR Adapter module provides bidirectional conversion between local database formats (OpenEMR, Orthanc) and FHIR R4 resources. It uses a plugin-based architecture to support multiple resource types.

## Installation

```bash
# No external dependencies required
# Just import the module
from fhir_adapter import to_fhir, from_fhir
```

## Quick Start

### Convert Local Data to FHIR

```python
from fhir_adapter import to_fhir

# OpenEMR patient to FHIR Patient
openemr_patient = {
    "pid": "12345",
    "fname": "John",
    "lname": "Doe",
    "sex": "M",
    "DOB": "1980-01-15"
}

fhir_patient = to_fhir("Patient", openemr_patient)
# Returns valid FHIR Patient resource
```

### Convert FHIR to Local Format

```python
from fhir_adapter import from_fhir

fhir_patient = {
    "resourceType": "Patient",
    "identifier": [{"system": "urn:openemr:pid", "value": "12345"}],
    "name": [{"family": "Doe", "given": ["John"]}],
    "gender": "male",
    "birthDate": "1980-01-15"
}

openemr_patient = from_fhir("Patient", fhir_patient)
# Returns: {"pid": "12345", "fname": "John", "lname": "Doe", ...}
```

## Supported Resources

### Patient (OpenEMR ↔ FHIR)

**Local Fields**:
- `pid` → `identifier` (system: urn:openemr:pid)
- `fname` → `name[0].given[0]`
- `lname` → `name[0].family`
- `sex` (M/F/U/O) → `gender` (male/female/unknown/other)
- `DOB` → `birthDate`
- `phone_home` → `telecom` (system: phone)
- `email` → `telecom` (system: email)

**Example**:
```python
local = {
    "pid": "12345",
    "fname": "John",
    "lname": "Doe",
    "sex": "M",
    "DOB": "1980-01-15",
    "phone_home": "555-1234",
    "email": "john@example.com"
}

fhir = to_fhir("Patient", local)
```

### ImagingStudy (Orthanc ↔ FHIR)

**Local Fields**:
- `StudyInstanceUID` → `identifier` (system: urn:dicom:uid)
- `PatientID` → `subject.identifier`
- `StudyDate` (YYYYMMDD) + `StudyTime` (HHMMSS) → `started` (ISO 8601)
- `ModalitiesInStudy` → `modality[]`
- `StudyDescription` → `description`
- `Series[]` → `series[]`

**Example**:
```python
orthanc_study = {
    "StudyInstanceUID": "1.2.840.113619.2.55.3.123456789",
    "PatientID": "12345",
    "StudyDate": "20251106",
    "StudyTime": "143000",
    "ModalitiesInStudy": ["CT"],
    "StudyDescription": "Chest CT",
    "Series": [{
        "SeriesInstanceUID": "1.2.840.113619.2.55.3.123456789.1",
        "Modality": "CT",
        "SeriesNumber": 1,
        "SeriesDescription": "Axial"
    }]
}

fhir_study = to_fhir("ImagingStudy", orthanc_study)
```

## Architecture

### Plugin System

The adapter uses a registry pattern to support multiple resource types:

```python
from fhir_adapter.core import BaseAdapter, register_adapter

class MyCustomAdapter(BaseAdapter):
    resource_type = "Observation"
    
    def to_fhir(self, local_record):
        return {
            "resourceType": "Observation",
            # ... conversion logic
        }
    
    def from_fhir(self, fhir_resource):
        return {
            # ... conversion logic
        }

# Register the adapter
MyCustomAdapter.register()

# Or manually
register_adapter("Observation", MyCustomAdapter())
```

### Directory Structure

```
fhir_adapter/
├── __init__.py              # Module entry point
├── core.py                  # Registry and base classes
├── README.md                # This file
└── adapters/
    ├── __init__.py
    ├── patient.py           # Patient adapter
    └── imaging_study.py     # ImagingStudy adapter
```

## Testing

```bash
# Run adapter tests
pytest tests/test_fhir_adapter.py -v

# Test specific adapter
pytest tests/test_fhir_adapter.py::TestPatientAdapter -v

# With coverage
pytest tests/test_fhir_adapter.py --cov=fhir_adapter --cov-report=html
```

## Data Mapping Tables

See `mappings/` directory for detailed CSV mapping tables:
- `openemr_patient_mapping.csv` - Patient field mappings
- `orthanc_imaging_mapping.csv` - ImagingStudy field mappings

## Error Handling

```python
from fhir_adapter import to_fhir

try:
    fhir = to_fhir("InvalidResource", {})
except ValueError as e:
    print(f"Error: {e}")
    # Error: No adapter registered for resource type: InvalidResource
```

## Validation

The adapter produces syntactically valid FHIR resources but does NOT perform full FHIR validation. For production use:

1. Validate against FHIR schemas
2. Check business rules
3. Verify required fields

```python
import requests

# Post to FHIR server for validation
fhir_patient = to_fhir("Patient", local_patient)
response = requests.post(
    "http://localhost:8080/fhir/Patient",
    json=fhir_patient
)

if response.status_code == 201:
    print("Valid FHIR resource")
else:
    print(f"Validation error: {response.json()}")
```

## Extending the Adapter

### Adding a New Resource Type

1. Create adapter file: `fhir_adapter/adapters/my_resource.py`

```python
from ..core import BaseAdapter

class MyResourceAdapter(BaseAdapter):
    resource_type = "MyResource"
    
    def to_fhir(self, local_record):
        return {
            "resourceType": "MyResource",
            # ... mapping logic
        }
    
    def from_fhir(self, fhir_resource):
        return {
            # ... reverse mapping
        }
```

2. Register in `__init__.py`:

```python
from .adapters.my_resource import MyResourceAdapter
MyResourceAdapter.register()
```

3. Add tests in `tests/test_fhir_adapter.py`

4. Document mapping in `mappings/my_resource_mapping.csv`

## Performance

- **to_fhir**: ~0.1ms per record (simple resources)
- **from_fhir**: ~0.1ms per record
- No external API calls (pure Python)
- Thread-safe (stateless adapters)

## Limitations

- Does not validate FHIR resources (use FHIR server for validation)
- Does not handle references automatically (you must set them)
- Date/time conversion assumes UTC
- No support for FHIR extensions (yet)

## Roadmap

- [ ] Add DiagnosticReport adapter (P1-MAP-005)
- [ ] Add ServiceRequest adapter (P1-MAP-006)
- [ ] Add Appointment adapter (P1-MAP-007)
- [ ] Add FHIR validation hooks
- [ ] Support FHIR extensions
- [ ] Add async support for batch conversions

## Contributing

See `Updates in progress/PHASE1_DETAILED_TASKS.md` for available tasks.

To contribute a new adapter:
1. Claim task in GitHub issue
2. Create branch: `bounty/p1/P1-MAP-XXX-yourhandle`
3. Add adapter + tests + mapping CSV
4. Submit PR with task ID

## References

- [FHIR R4 Specification](https://hl7.org/fhir/R4/)
- [Patient Resource](https://hl7.org/fhir/R4/patient.html)
- [ImagingStudy Resource](https://hl7.org/fhir/R4/imagingstudy.html)
- [OpenEMR Database Schema](https://www.open-emr.org/wiki/index.php/Database_Structure)
- [Orthanc DICOM Tags](https://book.orthanc-server.com/dicom-guide.html)

---

**Created**: 2025-11-06  
**Maintainer**: Dev3
