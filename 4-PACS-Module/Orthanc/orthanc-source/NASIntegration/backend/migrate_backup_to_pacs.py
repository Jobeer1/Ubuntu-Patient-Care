"""
Migrate patient_studies rows from backup DB to pacs_metadata.db

This script safely copies the 573 patient_studies rows from the backup database
(created during the failed indexing run) into the main pacs_metadata.db.
"""
import sqlite3
import os
from pathlib import Path

backup_db = r"c:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc\orthanc-source\NASIntegration\backend\orthanc-index\backups\orthanc_index_backup_20251003_113100\index"
target_db = r"c:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc\orthanc-source\NASIntegration\backend\orthanc-index\pacs_metadata.db"

print("=" * 60)
print("MIGRATING PATIENT_STUDIES FROM BACKUP TO PACS_METADATA.DB")
print("=" * 60)

# Verify files exist
if not os.path.exists(backup_db):
    print(f"\n❌ Backup DB not found: {backup_db}")
    exit(1)

if not os.path.exists(target_db):
    print(f"\n❌ Target DB not found: {target_db}")
    exit(1)

print(f"\n📂 Source: {backup_db}")
print(f"📂 Target: {target_db}")

# Connect to both databases
backup_con = sqlite3.connect(backup_db)
target_con = sqlite3.connect(target_db)

backup_cur = backup_con.cursor()
target_cur = target_con.cursor()

# Count rows in backup
backup_cur.execute("SELECT count(*) FROM patient_studies")
backup_count = backup_cur.fetchone()[0]
print(f"\n📊 Backup DB has {backup_count} patient_studies rows")

# Count rows in target before migration
target_cur.execute("SELECT count(*) FROM patient_studies")
target_before = target_cur.fetchone()[0]
print(f"📊 Target DB has {target_before} patient_studies rows (before migration)")

if backup_count == 0:
    print("\n⚠️ No rows to migrate!")
    backup_con.close()
    target_con.close()
    exit(0)

# Get column names from patient_studies
backup_cur.execute("PRAGMA table_info(patient_studies)")
columns = [row[1] for row in backup_cur.fetchall()]
col_list = ', '.join(columns)
placeholders = ', '.join(['?' for _ in columns])

print(f"\n🔄 Migrating {backup_count} rows...")

# Fetch all rows from backup
backup_cur.execute(f"SELECT {col_list} FROM patient_studies")
rows = backup_cur.fetchall()

# Insert into target (using INSERT OR REPLACE to handle duplicates)
migrated = 0
duplicates = 0

for row in rows:
    try:
        target_cur.execute(
            f"INSERT OR REPLACE INTO patient_studies ({col_list}) VALUES ({placeholders})",
            row
        )
        migrated += 1
    except Exception as e:
        print(f"  ⚠️ Failed to insert row: {e}")
        duplicates += 1

target_con.commit()

# Count rows after migration
target_cur.execute("SELECT count(*) FROM patient_studies")
target_after = target_cur.fetchone()[0]

print(f"\n✅ Migration complete!")
print(f"  Rows migrated: {migrated}")
print(f"  Duplicates/errors: {duplicates}")
print(f"  Target DB now has: {target_after} patient_studies rows")

# Close connections
backup_con.close()
target_con.close()

print("\n" + "=" * 60)
print("NEXT STEPS:")
print("=" * 60)
print("1. Restart your Flask app: py app.py")
print("2. Check logs for: 'indexing will use safe metadata DB'")
print("3. Run indexing from the UI")
print("4. Verify with: py -3 backend\\inspect_pacs_metadata.py")
print("=" * 60)
