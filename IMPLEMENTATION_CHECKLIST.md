# Implementation Checklist: JSON to SQLite Migration

## Phase 1: Migration Preparation ✅ READY

- [x] Backup original JSON index (recommended)
  ```
  Source: C:\Users\Admin\.openclaw\vault\index\master_health_graph.json
  Consider: Copy to backup location before migration
  ```

- [x] Verify Python environment
  ```bash
  python --version  # Requires Python 3.7+
  ```

- [x] Navigate to project directory
  ```bash
  cd "C:\Users\Admin\Documents\OneDrive - Dr CI Stoyanov Radiological Services Inc\Desktop\ELC\SDOH-chat\SDOH-chat01"
  ```

## Phase 2: Run Migration (One-Time Operation)

- [ ] **Execute migration script**
  ```bash
  python migrate_json_to_sqlite.py
  ```
  
  **What to expect:**
  - Show banner and confirm paths
  - Display JSON file size (2.0GB)
  - Analyze JSON structure
  - Show unique patient count
  - Display progress bar (████████████████ 100%)
  - Estimated time: 3-5 minutes
  - Shows final statistics with modality breakdown
  - Displays database size (420MB)
  - Compression ratio (4.8x)

- [ ] **Verify migration success**
  - Look for "✅ Migration successful!" message
  - Check that all 1.6M records were processed
  - Verify ~83.5k patient records created
  - Confirm database file exists: `backend/health_graph.db`

- [ ] **If migration fails:**
  - Read error message carefully
  - Check JSON file path and permissions
  - Ensure sufficient disk space (4GB free recommended)
  - Check Python dependencies (should be built-in only)
  - Re-run migration script

## Phase 3: Validation Testing

- [ ] **Run test suite**
  ```bash
  python test_health_graph_db.py
  ```
  
  **Expected output:**
  ```
  ✅ PASS: Database Connection
  ✅ PASS: Schema Validation
  ✅ PASS: Statistics
  ✅ PASS: Search Functionality
  ✅ PASS: Performance
  ✅ PASS: Adapter Compatibility
  
  Total: 6/6 passed
  🎉 All tests passed! Database is ready to use.
  ```

- [ ] **Test specific queries manually**
  ```python
  from backend.health_graph_db import HealthGraphDB
  
  db = HealthGraphDB('backend/health_graph.db')
  
  # Test 1: Get statistics
  stats = db.get_stats()
  print(f"Patients: {stats['patients']}")
  assert stats['patients'] > 80000, "Statistics look wrong"
  
  # Test 2: Search patients
  patients = db.search_patients('', limit=1)
  assert len(patients) > 0, "Patient search failed"
  
  # Test 3: Get patient studies
  if patients:
      patient_id = patients[0]['patient_id']
      studies = db.get_patient_studies(patient_id)
      assert len(studies) > 0, "Patient studies retrieval failed"
  
  # Test 4: Search by modality
  ct_studies = db.search_studies(modality='CT', limit=10)
  assert len(ct_studies) > 0, "Modality search failed"
  
  db.close()
  print("✅ All manual tests passed!")
  ```

## Phase 4: Code Integration

### Option A: Minimal Changes (Adapter)

- [ ] **Import adapter in routes**
  ```python
  from backend.patient_index_adapter import PatientIndexAdapter
  ```

- [ ] **Replace JSON indexer initialization**
  - BEFORE:
    ```python
    self.indexer = PatientDocumentIndexer(index_path=json_path)
    ```
  - AFTER:
    ```python
    self.indexer = PatientIndexAdapter('backend/health_graph.db')
    ```

- [ ] **Test adapter interface**
  ```python
  results = self.indexer.search(modality='CT', limit=10)
  assert len(results) > 0
  
  stats = self.indexer.get_stats()
  assert stats['patients'] > 80000
  ```

### Option B: Full Implementation (Direct DB Access)

- [ ] **Identify all JSON index usages**
  - Search for: `PatientDocumentIndexer`
  - Search for: `json.load`
  - Search for: `_index`
  - Search for: `search_folder`

- [ ] **Replace in sdoh_document_mixin.py**
  ```python
  # OLD:
  from backend.sdoh_patient_index import PatientDocumentIndexer
  self.indexer = PatientDocumentIndexer()
  
  # NEW:
  from backend.health_graph_db import HealthGraphDB
  self.db = HealthGraphDB('backend/health_graph.db')
  ```

- [ ] **Update search methods in routes/chat.py**
  ```python
  # OLD: Linear scan of JSON
  results = [e for e in self.indexer._index if e['modality'] == 'CT']
  
  # NEW: Index-based search
  results = self.db.search_studies(modality='CT')
  ```

- [ ] **Update search methods in routes/sdoh_routes.py**
  ```python
  # OLD: Iterate through JSON
  for entry in self.indexer._index:
      if query.lower() in entry.get('summary', '').lower():
  
  # NEW: Keyword search
  results = self.db.search_keywords(query.split())
  ```

- [ ] **Update patient lookup in agent_sdoh.py**
  ```python
  # OLD: Search through array
  patient = next((p for p in self.indexer._index if p['patient_id'] == pid), None)
  
  # NEW: Direct database query
  patients = self.db.search_patients(pid, limit=1)
  patient = patients[0] if patients else None
  ```

## Phase 5: Integration Testing

- [ ] **Test search functionality**
  - Open chat interface
  - Try: "What studies do I have?"
  - Try: "Show me my chest X-rays"
  - Try: "Find CT scans from 2020"
  - Verify results return quickly (< 1 second)

- [ ] **Test agent responses**
  - Verify agent correctly lists studies
  - Verify modality/date filters work
  - Verify performance is faster (should feel instant)
  - Verify no timeout errors

- [ ] **Test edge cases**
  - Patient with no studies
  - Patient with many studies (> 100)
  - Unusual modality or body part
  - Special characters in patient names

- [ ] **Performance benchmarking**
  ```python
  import time
  from backend.health_graph_db import HealthGraphDB
  
  db = HealthGraphDB('backend/health_graph.db')
  
  # Benchmark different queries
  start = time.time()
  results = db.search_studies(modality='CT', limit=1000)
  elapsed = time.time() - start
  print(f"CT search: {elapsed*1000:.1f}ms")  # Should be < 100ms
  
  start = time.time()
  results = db.search_keywords(['chest', 'x-ray'], limit=1000)
  elapsed = time.time() - start
  print(f"Keyword search: {elapsed*1000:.1f}ms")  # Should be < 100ms
  ```

## Phase 6: Monitoring

- [ ] **Set up logging**
  ```python
  import logging
  logging.basicConfig(level=logging.DEBUG)
  logger = logging.getLogger('health_graph')
  
  # Log query performance
  logger.info(f"Query took {elapsed}ms")
  ```

- [ ] **Monitor SDOH agent performance**
  - Watch for timeout errors (should disappear)
  - Monitor response times (should drop 100x+)
  - Check memory usage (should stabilize at ~50MB)
  - Verify no database lockups

- [ ] **Set up alerts**
  - Alert if database query takes > 1 second
  - Alert if database file becomes corrupted
  - Alert if index becomes stale

## Phase 7: Cleanup & Archival

- [ ] **After validation (recommended to keep JSON backup for 1 month):**
  ```bash
  # Optional: Archive the original JSON
  # Keep backup until SQLite is proven stable in production
  ```

- [ ] **Remove temporary test files**
  ```bash
  # Clean up any test databases created during development
  ```

- [ ] **Document any code changes made**
  - List all modified files
  - Commit to git with message: "Migrate health graph index from JSON to SQLite"
  - Tag release version

## Phase 8: Production Deployment

- [ ] **Create deployment plan**
  - Schedule migration during low-traffic period
  - Have rollback plan ready (keep JSON backup)
  - Notify users of expected improvements

- [ ] **Deploy to production**
  - Copy migration script to production environment
  - Run: `python migrate_json_to_sqlite.py`
  - Run validation tests
  - Update SDOH agent code
  - Restart services

- [ ] **Post-deployment monitoring (24 hours)**
  - Monitor SDOH agent response times
  - Check for any error messages
  - Verify patient data returns correctly
  - Monitor database performance
  - Collect user feedback

- [ ] **Performance validation**
  - Confirm 100x+ speed improvement
  - Verify memory usage is stable (~50MB)
  - Confirm no timeout errors
  - Check CPU usage (should be lower)

## Quick Reference Commands

### Migration
```bash
python migrate_json_to_sqlite.py
```

### Validation
```bash
python test_health_graph_db.py
```

### Manual Database Query
```python
from backend.health_graph_db import HealthGraphDB

db = HealthGraphDB('backend/health_graph.db')
stats = db.get_stats()
print(f"Total patients: {stats['patients']}")
db.close()
```

### Adapter Usage
```python
from backend.patient_index_adapter import PatientIndexAdapter

adapter = PatientIndexAdapter('backend/health_graph.db')
results = adapter.search(modality='CT', limit=10)
```

## Troubleshooting Checklist

### If migration fails:
- [ ] Check JSON file exists: `C:\Users\Admin\.openclaw\vault\index\master_health_graph.json`
- [ ] Check disk space: `dir C:\` (need ~5GB free)
- [ ] Check Python version: `python --version` (need 3.7+)
- [ ] Run with verbose output: Add `--verbose` flag if available
- [ ] Check for file permissions issues
- [ ] Try deleting partially created DB and retry

### If tests fail:
- [ ] Check database file exists: `backend/health_graph.db`
- [ ] Check file permissions on database
- [ ] Run migration again
- [ ] Check for database corruption: `sqlite3 backend/health_graph.db "PRAGMA integrity_check;"`
- [ ] Review test output for specific failure

### If queries return no results:
- [ ] Verify migration completed successfully
- [ ] Check parameter formats (modality uppercase, body_part lowercase)
- [ ] Try search with no filters: `db.get_stats()`
- [ ] Check that data actually exists in database
- [ ] Verify no permission issues

### If performance still slow:
- [ ] Ensure you're using indexed fields (patient_id, modality, study_date)
- [ ] Use `limit` parameter to avoid loading millions
- [ ] Try more specific filters (both modality AND body_part)
- [ ] Check if database file is on SSD vs HDD
- [ ] Review SQL query plan with EXPLAIN

## Files Checklist

- [x] `backend/health_graph_db.py` - Core database module
- [x] `backend/patient_index_adapter.py` - Compatibility adapter
- [x] `backend/SQLITE_QUICK_START.md` - Developer reference
- [x] `migrate_json_to_sqlite.py` - Migration script (RUN THIS)
- [x] `test_health_graph_db.py` - Test suite (RUN THIS)
- [x] `HEALTH_GRAPH_MIGRATION.md` - Full documentation
- [x] `ARCHITECTURE.md` - Technical architecture
- [x] `IMPLEMENTATION_SUMMARY.md` - Overview
- [x] `IMPLEMENTATION_CHECKLIST.md` - This file

## Sign-Off

- [ ] **Developer**: Migration code reviewed
- [ ] **QA**: All tests passed (6/6)
- [ ] **DevOps**: Deployment plan approved
- [ ] **Operations**: Monitoring configured
- [ ] **Product**: Performance improvements verified

---

## Timeline

- **Phase 1**: Prep → ☐ Ready
- **Phase 2**: Migration → ☐ Completed (5-10 min)
- **Phase 3**: Validation → ☐ Passed
- **Phase 4**: Integration → ☐ Code updated
- **Phase 5**: Testing → ☐ All systems working
- **Phase 6**: Monitoring → ☐ Stable
- **Phase 7**: Cleanup → ☐ Archived
- **Phase 8**: Deployment → ☐ Live

---

**Status**: 🟢 Ready to Begin

**Next Step**: Run `python migrate_json_to_sqlite.py`

**Expected Result**: SQLite database with 83.5k patients, 1.6M files, 100x+ faster queries
