# Phase 1 Tests

Automated tests for FHIR integration and data mapping.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt
```

## Running Tests

### FHIR Smoke Tests (P1-FHIR-002)

Make sure the FHIR server is running first:

```bash
cd dev/fhir
docker-compose up -d
```

Then run the tests:

```bash
# Run all smoke tests
pytest tests/test_fhir_smoke.py -v

# Run with custom FHIR URL
pytest tests/test_fhir_smoke.py --base-url http://localhost:8080/fhir -v

# Run specific test class
pytest tests/test_fhir_smoke.py::TestPatientResource -v

# Run with coverage
pytest tests/test_fhir_smoke.py --cov=fhir_adapter --cov-report=html
```

### Expected Output

All tests should pass:

```
tests/test_fhir_smoke.py::TestFHIRServer::test_server_metadata PASSED
tests/test_fhir_smoke.py::TestFHIRServer::test_server_health PASSED
tests/test_fhir_smoke.py::TestPatientResource::test_create_patient PASSED
tests/test_fhir_smoke.py::TestPatientResource::test_read_patient PASSED
...
```

## Test Coverage

- **TestFHIRServer**: Server connectivity and metadata
- **TestPatientResource**: Patient CRUD operations
- **TestImagingStudyResource**: Imaging study operations
- **TestDiagnosticReportResource**: Report operations
- **TestServiceRequestResource**: Service request operations
- **TestAppointmentResource**: Appointment operations

## Troubleshooting

### Tests fail with connection error
- Make sure FHIR server is running: `docker-compose ps`
- Check server logs: `docker-compose logs fhir-server`
- Wait 30-60s after starting for server to be ready

### Tests timeout
- Increase timeout in pytest.ini
- Check server resource usage: `docker stats`

### Tests pass but data not persisting
- Check Docker volume: `docker volume ls | grep fhir`
- Data persists between runs unless you use `docker-compose down -v`
