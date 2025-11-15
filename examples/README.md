# FHIR Example Resources

Sample FHIR R4 resources for testing and development.

## Usage

### With cURL

```bash
# Create a patient
curl -X POST http://localhost:8080/fhir/Patient \
  -H "Content-Type: application/fhir+json" \
  -d @examples/patient.json

# Create an imaging study
curl -X POST http://localhost:8080/fhir/ImagingStudy \
  -H "Content-Type: application/fhir+json" \
  -d @examples/imaging-study.json

# Create a diagnostic report
curl -X POST http://localhost:8080/fhir/DiagnosticReport \
  -H "Content-Type: application/fhir+json" \
  -d @examples/diagnostic-report.json
```

### With Python

```python
import requests
import json

base_url = "http://localhost:8080/fhir"

# Load and post patient
with open("examples/patient.json") as f:
    patient = json.load(f)

response = requests.post(
    f"{base_url}/Patient",
    json=patient,
    headers={"Content-Type": "application/fhir+json"}
)

print(f"Created Patient ID: {response.json()['id']}")
```

### With the Adapter

```python
from fhir_adapter import to_fhir
import requests

# Convert local format to FHIR
local_patient = {
    "pid": "12345",
    "fname": "John",
    "lname": "Doe",
    "sex": "M",
    "DOB": "1980-01-15"
}

fhir_patient = to_fhir("Patient", local_patient)

# Post to server
response = requests.post(
    "http://localhost:8080/fhir/Patient",
    json=fhir_patient,
    headers={"Content-Type": "application/fhir+json"}
)
```

## Files

- `patient.json` - Sample patient with full demographics
- `imaging-study.json` - CT study with 3 series
- `diagnostic-report.json` - Radiology report
- `README.md` - This file

## Notes

- Update `subject.reference` fields to match actual Patient IDs
- Update `performer.reference` to match actual Practitioner IDs
- All timestamps are in ISO 8601 format (UTC)
- DICOM UIDs should be unique in production

## Validation

Test if resources are valid:

```bash
# Post to FHIR server (validates automatically)
curl -X POST http://localhost:8080/fhir/Patient \
  -H "Content-Type: application/fhir+json" \
  -d @examples/patient.json

# 201 Created = valid
# 400 Bad Request = invalid (check response for details)
```
