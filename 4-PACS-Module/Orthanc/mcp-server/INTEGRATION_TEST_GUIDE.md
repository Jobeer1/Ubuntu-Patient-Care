# Integration Testing Guide - PACS Phase 1

## Overview

The integration testing suite validates the frontend-backend connection and data flow for the PACS 3D Viewer system. This guide covers running, extending, and troubleshooting integration tests.

---

## Quick Start

### 1. Prerequisites

```bash
# Install required packages
pip install requests

# Verify FastAPI server is running
python app/main.py
# Should see: "Uvicorn running on http://127.0.0.1:8000"
```

### 2. Run Full Test Suite

```bash
# From the mcp-server directory
python test_integration.py
```

**Expected Output:**
```
================================================================================
STARTING PACS PHASE 1 INTEGRATION TESTS
================================================================================

1. HEALTH CHECKS
----------------------------------------
[OK] API Health Check
[OK] Orthanc Health Check

2. VIEWER 3D API
----------------------------------------
[OK] Get Slice Endpoint
[OK] Get Metadata Endpoint
[OK] Cache Status
...
```

### 3. Check Results

- **Console**: Real-time test execution results
- **File**: `integration_test_report.txt` (auto-generated after run)

---

## Test Categories

### 1. Health Checks (2 tests)

Tests whether core services are available.

| Test | Purpose | Success Criteria |
|------|---------|-----------------|
| `test_api_health()` | FastAPI server responding | Status 200 |
| `test_orthanc_health()` | Orthanc DICOM server available | Health endpoint responds (optional) |

**Expected Results:** Both tests should PASS or INFO

---

### 2. Viewer 3D API (3 tests)

Tests the core DICOM viewing API endpoints.

| Endpoint | Test | Expected Status |
|----------|------|-----------------|
| `GET /api/viewer/get-slice/{study_id}` | `test_get_slice()` | 200 or 404 (if study not loaded) |
| `GET /api/viewer/get-metadata/{study_id}` | `test_get_metadata()` | 200 or 404 |
| `GET /api/viewer/cache-status` | `test_cache_status()` | 200 |

**Validation:**
- Endpoint exists and responds
- Returns valid JSON
- Status codes are appropriate

---

### 3. Measurements API (4 tests)

Tests CRUD operations for measurements.

| Endpoint | Test | Details |
|----------|------|---------|
| `POST /api/measurements/create` | `test_create_measurement()` | Creates distance measurement |
| `GET /api/measurements/study/{id}` | `test_list_measurements()` | Lists all measurements |
| `GET /api/measurements/study/{id}/summary` | `test_get_measurement_summary()` | Gets statistics |
| `GET /api/measurements/study/{id}/export` | `test_export_measurements()` | Tests JSON and CSV export |

**Measurement Data Structure:**
```json
{
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
```

**Validation:**
- POST returns 200/201 or 422 (validation error OK)
- GET returns 200 or 404 (if study doesn't exist)
- Export formats are generated correctly

---

### 4. Orthanc Integration (2 tests)

Tests connection to Orthanc DICOM server.

| Endpoint | Test | Details |
|----------|------|---------|
| `GET /api/viewer/orthanc/patients` | `test_orthanc_patients()` | Lists all patients |
| `GET /api/viewer/orthanc/studies` | `test_orthanc_studies()` | Lists all studies |

**Notes:**
- Tests pass if Orthanc is running (returns data)
- Tests pass as INFO if Orthanc is not available (expected during development)
- Connection errors are handled gracefully

---

### 5. Response Handling (3 tests)

Tests API response quality and error handling.

| Test | Validates |
|------|-----------|
| `test_json_responses()` | Valid JSON returned |
| `test_error_responses()` | Proper HTTP status codes (404, 422) |
| `test_cors_headers()` | CORS configured correctly |

**Validation:**
- All JSON responses parse correctly
- 404 for missing resources
- 422 for validation failures
- CORS headers present

---

### 6. Performance (1 test)

Tests response time performance.

| Metric | Threshold | Test |
|--------|-----------|------|
| Response Time | < 1000ms | `test_response_time()` |

**Measured Endpoints:**
- `/api/viewer/health`
- `/api/viewer/cache-status`
- `/api/measurements/study/1/summary`

**Success Criteria:** All endpoints respond in < 1 second

---

## Running Individual Tests

### Test Specific Categories

```python
from test_integration import IntegrationTester

tester = IntegrationTester()

# Run only measurements tests
tester.test_create_measurement()
tester.test_list_measurements()
tester.test_export_measurements()

# Run only Orthanc tests
tester.test_orthanc_patients()
tester.test_orthanc_studies()

# View results
print(tester.generate_report())
```

### Test Specific Endpoints

```python
# Direct endpoint test
import requests

response = requests.get("http://localhost:8000/api/viewer/health")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

---

## Troubleshooting

### Issue: "Connection refused"

**Cause:** FastAPI server not running

**Solution:**
```bash
# Terminal 1: Start the server
cd mcp-server
python app/main.py

# Terminal 2: Run tests
python test_integration.py
```

### Issue: "All tests fail with status 500"

**Cause:** Server error or missing dependencies

**Solution:**
```bash
# Check server logs for errors
# Verify all imports in app/main.py:
#   - from app.ml_models.dicom_processor import get_processor
#   - from app.ml_models.orthanc_client import get_orthanc_client
#   - from app.routes.measurements import router as measurements_router

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "Orthanc tests fail with 502"

**Cause:** Orthanc server not running (expected during development)

**Solution:**
- This is OK - tests report as INFO
- To test Orthanc integration, start Orthanc:
  ```bash
  docker run -p 8042:8042 jodogne/orthanc
  # Update BASE_URL to include Orthanc config if needed
  ```

### Issue: "Measurement creation returns 422"

**Cause:** Database or validation issue

**Solution:**
```bash
# Check that study_id exists in database
# Or use study_id of existing study:

# Terminal: Check database
python
from app.models import DicomStudy
from app.database import Session
session = Session()
studies = session.query(DicomStudy).all()
print([s.id for s in studies])
```

### Issue: "Tests hang or timeout"

**Cause:** Slow endpoints or network issues

**Solution:**
```python
# Increase timeout
tester = IntegrationTester()
# Modify timeout in test_* methods or main timeout constant
TIMEOUT = 30  # seconds

# Check endpoint performance
tester.test_response_time()
```

---

## Extending Tests

### Add New Test

```python
class IntegrationTester:
    def test_new_feature(self) -> bool:
        """Test description"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/path/to/endpoint",
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                # Validate data
                self.log_test("Feature Name", "PASS", "Details")
                return True
            else:
                self.log_test("Feature Name", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Feature Name", "FAIL", str(e))
            return False
```

### Add to Test Suite

```python
def run_all_tests(self) -> bool:
    # ... existing tests ...
    
    # Add new section
    print("\n7. NEW FEATURE TESTS")
    print("-" * 40)
    self.test_new_feature()
    
    # Continue with report generation
```

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.13
      
      - name: Install dependencies
        run: |
          pip install -r mcp-server/requirements.txt
      
      - name: Start server
        run: |
          cd mcp-server
          python app/main.py &
          sleep 2  # Wait for startup
      
      - name: Run integration tests
        run: |
          cd mcp-server
          python test_integration.py
```

---

## Performance Benchmarks

### Expected Baselines (Phase 1)

| Endpoint | Target | Acceptable |
|----------|--------|-----------|
| Health check | 10ms | < 100ms |
| Get metadata | 50ms | < 500ms |
| Get slice | 100ms | < 1000ms |
| List measurements | 50ms | < 500ms |
| Export data | 200ms | < 2000ms |

### Monitoring Performance

```python
# Run with timing details
tester = IntegrationTester()
tester.run_all_tests()

# Check report for slow endpoints
# Investigate in order:
# 1. Database query optimization
# 2. Network latency
# 3. DICOM processing time
```

---

## Test Data Setup

### Using Sample DICOM

To test with real DICOM data:

1. **Add sample DICOM files:**
   ```
   mcp-server/
   └── test_data/
       ├── sample_ct.dcm
       └── sample_series/
           ├── image_001.dcm
           ├── image_002.dcm
           └── ...
   ```

2. **Load in tests:**
   ```python
   from pathlib import Path
   dcm_path = Path("test_data/sample_ct.dcm")
   
   # Test with real data
   with open(dcm_path, 'rb') as f:
       response = self.session.post(
           f"{self.base_url}/api/viewer/load-study",
           files={'file': f}
       )
   ```

### Database Setup

```bash
# Reset test database
python
from app.database import Base, engine
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# Seed sample data
from app.models import DicomStudy
from app.database import Session
session = Session()
study = DicomStudy(
    orthanc_study_id="test_001",
    patient_name="Test Patient",
    study_description="Test Study"
)
session.add(study)
session.commit()
```

---

## Report Analysis

### Sample Report

```
================================================================================
PACS PHASE 1 INTEGRATION TEST REPORT
================================================================================

Test Run: 2025-10-21T10:30:45.123456
Server: http://localhost:8000

Results: 16 PASS, 0 FAIL, 2 INFO (Total: 18)
Pass Rate: 88.9%

================================================================================
DETAILED RESULTS
================================================================================
[✓] API Health Check
    FastAPI server is running
[✓] Orthanc Health Check
    Orthanc server is running
[✓] Get Slice Endpoint
    Endpoint responds (Status: 404)
...
```

### Interpreting Results

- **[✓] PASS**: Test successful, feature working
- **[✗] FAIL**: Test failed, needs investigation
- **[i] INFO**: Test OK but informational (e.g., optional service unavailable)

### Next Steps

1. All PASS → Ready for frontend integration
2. Some FAIL → Debug and fix issues
3. All INFO → Optional components not available (OK during dev)

---

## Continuous Monitoring

### Add to Development Workflow

```bash
# Run tests after each change
git add .
git commit -m "feature: new endpoint"
python test_integration.py

# Only push if tests pass
git push
```

### Automated Testing

```bash
# Watch mode (re-run on code changes)
pip install pytest-watch
ptw -- test_integration.py
```

---

## Next Steps

After integration tests pass:

1. **Frontend Integration Testing** (Dev 2)
   - Test Three.js 3D rendering
   - Test UI interaction with API
   - Test measurement drawing

2. **System Testing** (Both teams)
   - Full workflow: Open → View → Measure → Export
   - Cross-browser testing
   - Performance profiling

3. **Phase 2 Backend** (Dev 1)
   - Add ML segmentation
   - Add image processing features
   - Add batch processing

---

## Support

- **Documentation**: See `/README.md` for architecture overview
- **API Specs**: Check `/api/docs` (Swagger UI at http://localhost:8000/docs)
- **Code**: See `/app/routes/` for implementation details

---

**Created:** October 21, 2025  
**Task:** PACS Phase 1.2.2 - Integration Testing Script  
**Status:** Complete - Ready for frontend integration testing
