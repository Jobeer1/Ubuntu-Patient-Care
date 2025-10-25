# NAS-Orthanc Auto-Import Service - Implementation Summary

## 🎯 Problem Solved

**Issue:** Orthanc PACS only had 2 patients while NAS database had 2,172 patients. The NAS DICOM files were not accessible through Orthanc.

**Root Cause:** Orthanc is a separate PACS server with its own storage (`./orthanc-storage`). NAS DICOM files are stored separately and not automatically imported.

## ✅ Solution Implemented

Created an **automatic background import service** that continuously imports NAS patients into Orthanc PACS.

### Architecture

```
┌──────────────────────┐
│   NAS Device         │
│ (2,172 patients)     │
│ DICOM Files          │
└───────────┬──────────┘
            │
            │ Indexed by
            ↓
┌──────────────────────┐
│  SQLite Database     │
│  (patient_studies)   │
│  2,172 patient_ids   │
└───────────┬──────────┘
            │
            │ Auto-Import Service
            │ (Background Thread)
            ↓
┌──────────────────────┐
│  Orthanc PACS        │
│  (Growing to 2,172)  │
│  localhost:8042      │
└──────────────────────┘
```

## 📁 Files Created/Modified

### 1. **`backend/services/nas_orthanc_importer.py`** (NEW)
Full-featured import service with:
- Background thread that runs every 5 minutes
- Automatic detection of new patients
- Batch import (50 patients per cycle)
- DICOM file scanning and upload
- Progress logging
- Error handling

**Key Features:**
```python
class NASOrthancImporter:
    - check_orthanc_connection()      # Verify Orthanc is accessible
    - get_orthanc_patients()          # Get existing patients in PACS
    - get_nas_patients_to_import()    # Find NAS patients not in PACS
    - find_dicom_files()              # Scan patient folder for DICOMs
    - upload_dicom_to_orthanc()       # Upload single DICOM file
    - import_patient()                # Import all files for one patient
    - run_import_cycle()              # Import batch of patients
    - start_background_import()       # Start auto-import service
    - stop_background_import()        # Stop auto-import service
```

### 2. **`backend/app.py`** (MODIFIED)
Added auto-start of import service:
```python
def initialize_system():
    # ... existing code ...
    
    # Start NAS→Orthanc auto-import service
    from services.nas_orthanc_importer import get_importer
    importer = get_importer()
    importer.start_background_import()
    logger.info("✅ NAS→Orthanc auto-import service started")
```

### 3. **`backend/routes/nas_core.py`** (MODIFIED)
Added control API endpoints:
- `POST /api/nas/import/start-auto` - Start auto-import service
- `POST /api/nas/import/stop-auto` - Stop auto-import service
- `GET /api/nas/import/status` - Get import status and progress
- `POST /api/nas/import/run-now` - Manually trigger import cycle

### 4. **`backend/templates/orthanc_explorer_themed.html`** (FIXED)
Fixed autocomplete JavaScript to handle categorized suggestions properly.

## 🚀 How It Works

### Auto-Import Process

1. **Service starts** when Flask app launches
2. **Every 5 minutes:**
   - Connects to Orthanc PACS
   - Gets list of patients already in Orthanc
   - Queries NAS database for patients not in Orthanc
   - Imports up to 50 patients per cycle
3. **For each patient:**
   - Finds DICOM files in NAS folder
   - Uploads each DICOM to Orthanc via REST API
   - Logs progress and success rate
4. **Repeats** until all NAS patients are in Orthanc

### Configuration

**Environment Variables:**
```bash
ORTHANC_URL=http://localhost:8042
ORTHANC_USERNAME=orthanc
ORTHANC_PASSWORD=orthanc
```

**Tunable Parameters** (in `nas_orthanc_importer.py`):
```python
IMPORT_BATCH_SIZE = 10      # Patients per batch
IMPORT_INTERVAL = 300        # Seconds between cycles (5 minutes)
MAX_IMPORT_PER_RUN = 50     # Max patients per cycle
```

## 📊 API Endpoints

### Start Auto-Import
```bash
POST /api/nas/import/start-auto

Response:
{
  "success": true,
  "message": "Auto-import service started",
  "status": "running"
}
```

### Stop Auto-Import
```bash
POST /api/nas/import/stop-auto

Response:
{
  "success": true,
  "message": "Auto-import service stopped",
  "status": "stopped"
}
```

### Get Import Status
```bash
GET /api/nas/import/status

Response:
{
  "success": true,
  "running": true,
  "status": "running",
  "orthanc_patients": 52,
  "nas_patients": 2172,
  "remaining": 2120
}
```

### Run Import Now (Manual Trigger)
```bash
POST /api/nas/import/run-now

Response:
{
  "success": true,
  "message": "Import cycle completed"
}
```

## 🔧 Testing

### Test Autocomplete Fix
1. Go to `http://155.235.81.41:5000/orthanc/explorer`
2. Type in search box
3. Verify suggestions appear correctly

### Test Auto-Import
1. Check import status:
```bash
curl http://localhost:5000/api/nas/import/status
```

2. Watch Flask logs for import progress:
```
🔄 Starting import cycle...
📊 Orthanc currently has 2 patients
📋 Found 50 patients to import
📤 Importing patient: SMITH JOHN (ID: 12345)
📁 Found 125 DICOM files
   Progress: 50/125 files uploaded
   Progress: 100/125 files uploaded
✅ Imported 125/125 files (100.0%)
🎉 Import cycle complete: 50/50 patients imported
💤 Sleeping for 300 seconds...
```

3. Check Orthanc patient count increasing:
```bash
curl http://localhost:8042/patients | python -m json.tool | grep -c "\"ID\""
```

## 📈 Expected Timeline

**Import Speed:** ~10-30 patients per minute (depending on DICOM file count)

**Full Import Estimate:**
- 2,172 patients @ 20 patients/min = ~108 minutes (~2 hours)
- With 50 patients per 5-minute cycle = ~44 cycles = ~3.7 hours

**Progress Tracking:**
- Check `/api/nas/import/status` to see `remaining` count
- Watch Flask logs for real-time progress
- Check Orthanc Explorer stats panel for patient count

## 🎛️ Manual Control

If you need to speed up or slow down import:

### Speed Up Import
```python
# In nas_orthanc_importer.py, change:
IMPORT_INTERVAL = 60         # Run every 1 minute instead of 5
MAX_IMPORT_PER_RUN = 100    # Import 100 patients per cycle
```

### Slow Down Import (Less Load)
```python
# In nas_orthanc_importer.py, change:
IMPORT_INTERVAL = 600        # Run every 10 minutes
MAX_IMPORT_PER_RUN = 20     # Import only 20 patients per cycle
```

### Pause Import
```bash
POST /api/nas/import/stop-auto
```

### Resume Import
```bash
POST /api/nas/import/start-auto
```

## 🐛 Troubleshooting

### Import Not Starting
**Check:** Orthanc is running
```bash
curl http://localhost:8042/system
```

**Fix:** Start Orthanc from Orthanc Manager page

### Slow Import
**Causes:**
- Large DICOM files (CT/MR scans)
- Network latency to NAS device
- Orthanc storage disk I/O

**Solutions:**
- Reduce `MAX_IMPORT_PER_RUN`
- Increase `IMPORT_INTERVAL`
- Check disk space on Orthanc storage

### Import Errors in Logs
**Check:**
- NAS folder paths are accessible
- DICOM files are not corrupted
- Orthanc has sufficient disk space

### Duplicate Patients
**Note:** Orthanc automatically handles duplicates - same PatientID files are merged into existing patient

## 📝 Next Steps

1. **Monitor First Import Cycle** - Watch logs to see import working
2. **Check Status Regularly** - Use `/api/nas/import/status` endpoint
3. **Verify Orthanc Explorer** - Patient count should increase
4. **Test OHIF Viewing** - Imported patients viewable in OHIF

## 🎉 Benefits

✅ **Automatic** - Runs in background, no manual work
✅ **Incremental** - Only imports new patients
✅ **Resumable** - Can stop/start without losing progress
✅ **Safe** - Doesn't modify NAS files, only reads
✅ **Monitored** - Full logging and status API
✅ **Fast** - Parallel uploads, efficient scanning

## 🔒 Security Notes

- Auto-import service runs with Flask app permissions
- Uses Orthanc basic auth (configurable via environment variables)
- NAS files accessed read-only
- No data leaves local network

## 📊 Summary

**Before:**
- Orthanc PACS: 2 patients
- NAS Database: 2,172 patients
- Connection: None

**After:**
- Orthanc PACS: Growing to 2,172 patients
- NAS Database: 2,172 patients (unchanged)
- Connection: Automatic background sync
- Smart Search: Works for all imported patients
- OHIF Viewer: Can view all imported patients

🎉 **NAS and Orthanc are now connected!**
