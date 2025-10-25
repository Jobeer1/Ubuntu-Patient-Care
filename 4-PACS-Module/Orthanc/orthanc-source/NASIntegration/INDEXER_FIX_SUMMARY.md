"""
CRITICAL FIX APPLIED: Indexer DB Targeting Issue
================================================

PROBLEM IDENTIFIED:
------------------
The indexing route had a broken safety gate that aborted ALL indexing when
USE_ORTHANC_INTERNAL_INDEX=false (line 55-58 in backend/routes/indexing.py).

This caused:
- Indexing requests to return 403 errors
- Working DBs to be created in backups/ but never merged
- The pacs_metadata.db to remain empty (0 patient_studies rows)

WHAT WAS FIXED:
--------------
1. Removed the broken early-abort safety gate
2. Changed logic to use pacs_metadata.db when USE_ORTHANC_INTERNAL_INDEX=false
3. Added proper merge logic to update pacs_metadata.db after indexing completes
4. Added clear logging to show which DB will be targeted

FILES MODIFIED:
--------------
- backend/routes/indexing.py (lines 39-58, 105-125, 167-195)

CURRENT STATE:
-------------
- Your Flask app is still running the OLD broken code
- The backup DB has 573 patient_studies rows (from earlier indexing run)
- The pacs_metadata.db has 0 patient_studies rows
- The pacs_metadata.db has old data: 573 patients, 1139 studies, 4000 instances

REQUIRED ACTIONS:
----------------
1. STOP the Flask app (Ctrl+C in the terminal)
2. Run the migration script to move 573 rows from backup to pacs_metadata.db:
   
   py -3 backend\migrate_backup_to_pacs.py

3. RESTART the Flask app:
   
   py app.py

4. Start indexing from the UI - it will now correctly update pacs_metadata.db

VERIFICATION:
------------
After restarting, check the logs for:
  ✅ USE_ORTHANC_INTERNAL_INDEX=false - indexing will use safe metadata DB (pacs_metadata.db)
  ✅ Updated safe metadata DB: <path>/pacs_metadata.db

Then after indexing completes, check row counts:
  py -3 backend\inspect_pacs_metadata.py

You should see patient_studies rows increase as indexing progresses.

WHAT HAPPENS NOW:
----------------
- When USE_ORTHANC_INTERNAL_INDEX=false (default):
  * Indexer creates working_db copy of pacs_metadata.db
  * Scans NAS and populates patient_studies table
  * Merges working_db back into pacs_metadata.db on completion
  * Safe - Orthanc can remain running

- When USE_ORTHANC_INTERNAL_INDEX=true (risky mode):
  * Indexer creates working_db copy of Orthanc internal 'index' file
  * Scans NAS and populates patient_studies table
  * Merges working_db back into Orthanc 'index' file on completion
  * REQUIRES Orthanc to be stopped before starting indexing

SUMMARY:
-------
The indexer will now correctly update pacs_metadata.db (or Orthanc index if you
enable the risky mode). You just need to restart the Flask app to load the fixed code.

The 573 rows from the backup are available and can be migrated with the provided
script if you want to preserve them.
"""

if __name__ == '__main__':
    print(__doc__)
