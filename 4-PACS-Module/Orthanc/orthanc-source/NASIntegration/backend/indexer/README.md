Phase 0: Minimal NAS indexer

This folder contains a minimal, safe indexer used to scan a NAS path for DICOM
files and extract basic metadata. It is intentionally non-destructive (dry-run
mode) and does not import into Orthanc or write to databases unless extended.

Files
- indexer.py: scan_path(root_path, max_files=100, dry_run=True) -> report

How to use (dry-run)
1. From Python code (backend context):
   from indexer.indexer import scan_path
   report = scan_path(r'C:\path\to\nas', max_files=100, dry_run=True)

2. Via the backend API (added route)
   POST /api/nas/indexing/scan
   JSON body: { "path": "C:\\path\\to\\nas", "max_files": 100 }
   Response: { success: true, report: { scanned_count, candidates, errors } }

Notes
- The script optionally requires `pydicom` to extract DICOM metadata. Install
  with `pip install pydicom` if you want metadata in the report.
- This is Phase 0. After you validate the dry-run results, we can implement
  import logic and/or background workers (Celery/RQ) for production usage.
