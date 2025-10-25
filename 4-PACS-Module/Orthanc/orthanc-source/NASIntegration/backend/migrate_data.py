#!/usr/bin/env python3
"""
Migrate Essential Data from Backup Database
Transfer only the essential patient/study metadata without the bloated DICOM file records
"""

import sqlite3
import os
from datetime import datetime
try:
    from metadata_db import get_metadata_db_path
except Exception:
    # fallback when running as script in backend dir
    def get_metadata_db_path():
        base = os.path.dirname(__file__)
        return os.path.abspath(os.path.join(base, '..', 'orthanc-index', 'pacs_metadata.db'))

def migrate_essential_data():
    """Migrate essential patient data from backup to new lightweight database"""
    
    # Find the backup database
    backup_files = [f for f in os.listdir('.') if f.startswith('nas_patient_index_backup_') and f.endswith('.db')]
    if not backup_files:
        print("❌ No backup database found")
        return
    
    backup_db = sorted(backup_files)[-1]  # Get the most recent backup
    print(f"📂 Using backup database: {backup_db}")
    
    # Connect to both databases (target is the canonical metadata DB)
    backup_conn = sqlite3.connect(backup_db)
    new_db_path = get_metadata_db_path()
    new_conn = sqlite3.connect(new_db_path)
    
    try:
        backup_cursor = backup_conn.cursor()
        new_cursor = new_conn.cursor()
        
        # Migrate patients data
        print("👥 Migrating patient data...")
        backup_cursor.execute("""
            SELECT DISTINCT patient_id, patient_name, patient_birth_date, patient_sex, 
                   first_study_date, folder_path
            FROM patients 
            WHERE patient_id IS NOT NULL
        """)
        
        patients = backup_cursor.fetchall()
        
        for patient in patients:
            patient_id, name, birth_date, sex, study_date, folder_path = patient
            
            # Insert into new lightweight database
            try:
                new_cursor.execute("""
                    INSERT OR IGNORE INTO patient_studies 
                    (patient_id, patient_name, patient_birth_date, patient_sex, 
                     study_date, folder_path, last_indexed)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (patient_id, name, birth_date, sex, study_date, folder_path, 
                      datetime.now().isoformat()))
            except Exception as e:
                print(f"⚠️ Error inserting patient {patient_id}: {e}")
        
        # Add study information if available
        print("📚 Migrating study data...")
        backup_cursor.execute("""
            SELECT DISTINCT patient_id, study_date, study_description, modality, folder_path
            FROM studies 
            WHERE patient_id IS NOT NULL
        """)
        
        studies = backup_cursor.fetchall()
        
        for study in studies:
            patient_id, study_date, description, modality, folder_path = study
            
            try:
                new_cursor.execute("""
                    INSERT OR IGNORE INTO patient_studies 
                    (patient_id, study_date, study_description, modality, folder_path, last_indexed)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (patient_id, study_date, description, modality, folder_path,
                      datetime.now().isoformat()))
            except Exception as e:
                print(f"⚠️ Error inserting study for patient {patient_id}: {e}")
        
        # Update indexing status
        print("📊 Updating indexing status...")
        new_cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM patient_studies")
        patient_count = new_cursor.fetchone()[0]
        
        new_cursor.execute("""
            INSERT INTO indexing_status 
            (status, folders_scanned, patients_found, completed_at)
            VALUES ('completed', ?, ?, ?)
        """, (patient_count, patient_count, datetime.now().isoformat()))
        
        new_conn.commit()
        
        print(f"✅ Migration complete!")
        print(f"   📊 Migrated {patient_count} patients")
        print(f"   📁 Database size: {os.path.getsize(new_db_path) / 1024:.2f} KB")
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
    finally:
        backup_conn.close()
        new_conn.close()

if __name__ == "__main__":
    print("🔄 Migrating essential data from backup database...")
    migrate_essential_data()