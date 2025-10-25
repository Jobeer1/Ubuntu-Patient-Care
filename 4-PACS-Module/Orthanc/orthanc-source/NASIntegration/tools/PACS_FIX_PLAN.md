## PACS Fix & Indexer Plan

Goal
----
Build a fast, accurate, non-destructive PACS indexer and small web UI so staff can search patients on the NAS and generate secure single-series share links. The index will contain only text metadata (no image pixels).

Requirements (must-haves)
- Index contains only metadata (Patient/Study/Series fields) and file paths — no pixel data.
- Index is grouped by Series (SeriesInstanceUID or fallback) with `SeriesKey` and `file_count`.
- Fast enumeration of NAS files without copying (PowerShell or robocopy list-only).
- Concurrent, header-only reads (pydicom.dcmread stop_before_pixels=True) with progress reporting.
- Frontend shows progress bar / live stats and provides search + share link creation.
- Share links are short-lived, logged, and stream the specific series (zip stream or per-file URLs).

Phases
------
1. Fast file enumeration
   - Use `Get-ChildItem -Recurse -File` or `robocopy /L /S /FP` to quickly produce `nas_dicom_files.txt` (UNC paths).
   - Do not copy files.

2. Header-only parallel indexing
   - Python indexer reads `nas_dicom_files.txt` and uses ThreadPoolExecutor to read headers.
   - Group by `SeriesInstanceUID` (fallback to StudyUID+SeriesNumber). Compute `SeriesKey` (SHA1).
   - Persist incremental index to `index.json` so the FE can query partial results.

3. Backend API + progress
   - Endpoints: POST `/api/index/start`, GET `/api/index/status`, GET `/api/search?q=`, GET `/api/series/<SeriesKey>`.
   - Status includes `enumerated_files`, `files_processed`, `series_count`, `errors`.

4. Frontend
   - Simple single-page UI (`ui.html`) that starts indexing, polls status, displays progress bar and live results, supports search and share link creation.

5. Secure sharing
   - Small sqlite table `shares.db` storing token, seriesKey, expires_at, optional passcode, access logs.
   - `/share/create` returns token and URL; `/share/<token>` streams the requested series as a zip stream (on-the-fly) or serves per-file temporary URLs.

Performance notes
-----------------
- Enumeration should be done with native Windows tooling for speed on SMB (robocopy/Get-ChildItem). Python `os.walk` over SMB is slower and was the cause of the long runs.
- Parallel header read throughput depends on NAS latency; tune workers (8–16) to maximize throughput without saturating NAS.
- Use incremental persistence to let FE show partial results while work continues.
- **CRITICAL UPDATE**: Full directory traversal (Get-ChildItem -Recurse) is the bottleneck due to SMB latency. Implement database indexing for long-term speed. For immediate fix, use robocopy /L with mapped drive and optimize directory structure.

Security & operational notes
--------------------------
- Store NAS credentials out of repo; use runtime config or have the user mount the NAS locally and pass a drive letter (e.g. `Z:\Image Archiving`).
- Links must expire and be logged. Limit concurrent streaming jobs.
- Handle SMB encryption/auth errors clearly and suggest mounting locally if needed.

Files to deliver (shortlist)
- `tools/enum_nas_ps.ps1` — fast enumerator writing `nas_dicom_files.txt`
- `tools/build_index.py` — concurrent header-only indexer with incremental save and status file
- `tools/index_server.py` (Flask) — API endpoints and status management
- `tools/ui.html` — frontend with progress bar, search, share UI
- `tools/stream_share.py` — on-the-fly zip streaming helper
- `tools/run_build_index_robocopy.ps1` — optional robocopy enumerator

How to run a safe sample (suggested)
1. Mount NAS to a drive letter or ensure UNC path is accessible.
2. Produce a file list (first 200 files) using the enumerator (PowerShell script). Example command from `tools` folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_build_index.ps1 -sampleLimit 200 -indexLimit 200
```

3. Or run the Python indexer directly on the list:

```powershell
python .\build_index.py --list nas_dicom_files.txt --out index_sample.json --limit 200
```

Next steps I will implement on your confirmation
- Fix and harden `build_index.py` to use concurrent header reads, incremental state and a small status endpoint.
- Add the Flask `index_server.py` and `ui.html` frontend with progress polling.
- Add `run_build_index_robocopy.ps1` as a fast enumerator fallback.

Please confirm the sample size to run (suggest 200) and whether you want anonymous short-lived share links (24h) or passcode-protected links. Once you confirm I'll implement and run the safe sample and return `index_sample.json` and a short demo UI.

---
Actionable task list (trackable)
--------------------------------
1) Create fast enumerator script (PowerShell)
   - File: `tools/enum_nas_getchild.ps1`
   - Owner: implementer
   - ETA: 1 hour
   - Acceptance: produces `nas_dicom_files.txt` with UNC paths, completed within 2 minutes for 10k files on LAN.
   - Test: run script, verify file count matches `Get-ChildItem` manual run.
   - Status: DONE (Performance issue with Get-ChildItem identified)

2) Build concurrent header-only indexer (Python)
   - File: `tools/build_index.py` (production-ready)
   - Owner: implementer
   - ETA: 4 hours
   - Acceptance: reads `nas_dicom_files.txt`, creates incremental `index.json`, supports `--limit` for sample runs, uses ThreadPoolExecutor and atomic writes.
   - Test: run `python build_index.py --list nas_dicom_files.txt --limit 200` -> generate `index_sample.json` within 5 minutes and confirm entries for known PatientID.
   - Status: DONE (Verified fast performance)

3) Add status file and API hooks
   - File: `tools/index_server.py`
   - Owner: implementer
   - ETA: 2 hours
   - Acceptance: Server provides `/api/index/start`, `/api/index/status`, `/api/search`.
   - Test: Run server, open UI, start indexing, see status updates, search for patient.
   - Status: DONE

4) Build small frontend (UI) with progress bar and search
   - File: `tools/ui.html` (Modern, SA-focused, multi-format support)
   - Owner: implementer / QA
   - ETA: 3 hours
   - Acceptance: Eye-candy UI with SA flag, medical aid detection, multiple NAS types, modern design
   - Test: manual QA: run index, watch progress, perform search for SA patients, verify medical aid detection
   - Status: DONE

5) South African Healthcare Enhancements
   - Features: SA timezone, medical aid detection, hospital recognition, multi-format NAS support
   - Status: DONE

6) Backend API enhancements for different NAS types
   - Support: Pure DICOM, JPEG2000/Firebird DB, Mixed formats
   - Status: DONE

Progress tracking conventions
----------------------------
- Each task has: Owner, ETA, Acceptance criteria, Test steps, Status (TODO / IN-PROGRESS / DONE).
- For long-running indexing tasks, indexer writes `index_status.json` with: enumerated_files, files_processed, series_count, errors, last_updated, running(true/false).
- FE polls `/api/index/status` every 2s and shows a progress bar and last_updated timestamp.

Acceptance test examples (explicit)
----------------------------------
- Test A - Sample index
  1. Generate `nas_dicom_files.txt` with 200 paths.
  2. Run: `python tools/build_index.py --list nas_dicom_files.txt --out tools/index_sample.json --limit 200`.
  3. Assert `tools/index_sample.json` exists and is valid JSON.
  4. Assert one entry contains PatientID `71709-20090204-151715-5920-7122` (from screenshot) or similar.

- Test B - Search and share
  1. Start Flask server: `python tools/index_server.py` (or `nas_web_indexer.py`).
  2. Use FE `tools/ui.html` to search for patient name or ID.
  3. Create a share link for found SeriesKey and request download.
  4. Confirm downloaded zip has same number of files as `file_count` and DICOM headers match.

Notes on performance tuning
--------------------------
- If indexing is slow: mount NAS locally (Z:) and re-run enumerator against Z: to avoid SMB traversal overhead.
- Increase worker count until network or NAS CPU becomes the bottleneck.

---
Generated: 2025-09-18
