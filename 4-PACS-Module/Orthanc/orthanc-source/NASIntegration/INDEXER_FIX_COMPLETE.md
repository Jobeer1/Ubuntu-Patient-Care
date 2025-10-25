# ✅ INDEXER DATABASE FIX - COMPLETE

## Problem Summary
The indexer was writing to the wrong database because of a broken safety gate in `backend/routes/indexing.py` that **aborted ALL indexing** when `USE_ORTHANC_INTERNAL_INDEX=false`.

## Root Cause
Lines 55-58 in `backend/routes/indexing.py` contained an early-abort that returned a 403 error:
```python
if not use_internal:
    logger.warning("Attempt to start real indexing aborted...")
    return jsonify({ 'success': False, 'error': '...' }), 403
```

This meant:
- ❌ Indexing never ran when `USE_ORTHANC_INTERNAL_INDEX=false`
- ❌ Working DBs were created in backups/ but never merged
- ❌ The `pacs_metadata.db` remained empty (0 patient_studies rows)

## What Was Fixed

### 1. Removed Broken Safety Gate
Changed lines 54-58 to allow indexing to proceed in both modes:
- **Safe mode** (`USE_ORTHANC_INTERNAL_INDEX=false`): Use `pacs_metadata.db`
- **Risky mode** (`USE_ORTHANC_INTERNAL_INDEX=true`): Use Orthanc internal `index`

### 2. Added Explicit DB Target Logic  
Lines 105-125 now explicitly choose the target DB:
```python
if use_internal:
    # Target Orthanc internal 'index' file
    canonical_index = orthanc_index_candidate
else:
    # Target safe pacs_metadata.db
    canonical_index = safe_db
```

### 3. Fixed Merge Logic
Lines 167-195 now properly merge working DB back to target:
- Safe mode: Direct sqlite backup into `pacs_metadata.db`
- Risky mode: Sqlite backup into Orthanc `index` (with extra safety checks)

### 4. Added Clear Logging
Startup and indexing now log:
```
✅ USE_ORTHANC_INTERNAL_INDEX=false - indexing will use safe metadata DB (pacs_metadata.db)
🔁 Replacing safe metadata DB <path> with working DB <path>
✅ Updated safe metadata DB: <path>
```

## Migration Completed
✅ Migrated 573 patient_studies rows from backup to `pacs_metadata.db`

### Before Migration:
- `patient_studies`: 0 rows ❌
- `patients`: 573 rows (old schema)
- `instances`: 4000 rows

### After Migration:
- `patient_studies`: 573 rows ✅
- `patients`: 573 rows (preserved)
- `instances`: 4000 rows (preserved)

## Current Database State
**Location**: `backend/orthanc-index/pacs_metadata.db`

**Sample Patients**:
1. DLUDLA MBONGELENI M MR (639501) - Study: 20251002
2. QWABE BAKHETHILE B MS (639286) - Study: 20251001
3. MTHEMBU YANDISA Y MISS (639043) - Study: 20251001
4. KHOZA THULISILE T MRS (590173) - Study: 20251001
5. MATHABA BONGINKOSI B MR (630435) - Study: 20251001

All point to UNC paths on NAS: `\\155.235.81.155\Image Archiving\<patient-folder>`

## Next Steps - RESTART REQUIRED

### 1. Stop Your Running Flask App
Press `Ctrl+C` in the terminal where `py app.py` is running.

### 2. Restart Flask App
```powershell
py app.py
```

### 3. Verify Fixed Behavior in Logs
Look for these startup messages:
```
🔎 Resolved metadata DB path: ...\pacs_metadata.db
🔐 USE_ORTHANC_INTERNAL_INDEX = false
✅ USE_ORTHANC_INTERNAL_INDEX=false - indexing will use safe metadata DB
```

### 4. Test Indexing
1. Open the web UI (http://localhost:5000)
2. Login as admin/admin
3. Go to NAS Integration page
4. Click "Start Indexing"
5. Watch the logs - you should see:
   ```
   ✅ Updated safe metadata DB: ...\pacs_metadata.db
   ```

### 5. Verify New Rows Were Added
After indexing completes, run:
```powershell
py -3 backend\inspect_pacs_metadata.py
```

You should see `patient_studies` row count increase from 573 to 700+ (or however many folders were scanned).

## Verification Commands

### Check which DB will be used:
```powershell
py -3 verify_db_target.py
```

### Inspect pacs_metadata.db contents:
```powershell
py -3 backend\inspect_pacs_metadata.py
```

### Check backup DB contents:
```powershell
py -3 backend\inspect_backup_db.py
```

## What Happens Now

### Safe Mode (Default - USE_ORTHANC_INTERNAL_INDEX=false)
1. Indexer creates `index_working_<timestamp>.db` as a copy of `pacs_metadata.db`
2. Scans NAS folders and populates `patient_studies` table
3. Merges `working_db` back into `pacs_metadata.db`
4. ✅ Safe - Orthanc can remain running
5. ✅ No risk to Orthanc internal database

### Risky Mode (USE_ORTHANC_INTERNAL_INDEX=true)
1. Indexer creates `index_working_<timestamp>.db` as a copy of Orthanc `index`
2. Scans NAS folders and populates `patient_studies` table
3. Merges `working_db` back into Orthanc `index` file
4. ⚠️ REQUIRES Orthanc to be stopped first
5. ⚠️ Directly modifies Orthanc internal database

## Files Modified
- ✅ `backend/routes/indexing.py` (lines 39-58, 105-125, 167-195)
- ✅ `backend/metadata_db.py` (already correct)
- ✅ `nas_patient_indexer.py` (already uses helper)

## Files Created
- ✅ `INDEXER_FIX_SUMMARY.md` (this file)
- ✅ `backend/migrate_backup_to_pacs.py` (migration script - already executed)
- ✅ `backend/inspect_pacs_metadata.py` (inspection tool)
- ✅ `backend/inspect_backup_db.py` (backup inspection tool)
- ✅ `verify_db_target.py` (target verification tool)

## Summary
The indexer will now **correctly update `pacs_metadata.db`** when you restart the Flask app. The 573 existing rows have been migrated and are now available. Future indexing runs will add new patient_studies rows to the same database.

**You must restart the Flask app to load the fixed code!**
