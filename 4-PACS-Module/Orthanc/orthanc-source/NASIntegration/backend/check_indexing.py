#!/usr/bin/env python3
"""
Check for missing patients from 2025-10-20 in the database
"""
import sqlite3
import sys
from pathlib import Path

db_path = r"C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\4-PACS-Module\Orthanc\orthanc-source\NASIntegration\backend\orthanc-index\pacs_metadata.db"

print("=" * 70)
print("PACS Database Indexing Check - October 2025")
print("=" * 70)

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Check if database exists and has patient_studies table
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='patient_studies'")
    if not cur.fetchone():
        print("❌ Table 'patient_studies' not found!")
        sys.exit(1)
    
    # Check for 2025-10-20 specifically
    print("\n🔍 Checking for patients from 2025-10-20:")
    print("-" * 70)
    cur.execute("""
        SELECT patient_id, patient_name, study_date, study_description 
        FROM patient_studies 
        WHERE study_date = '20251020'
        ORDER BY patient_id
    """)
    results_20 = cur.fetchall()
    
    if results_20:
        print(f"✅ Found {len(results_20)} patients from 2025-10-20:")
        for row in results_20[:10]:  # Show first 10
            print(f"   {row[0]} - {row[1]} ({row[3]})")
        if len(results_20) > 10:
            print(f"   ... and {len(results_20) - 10} more")
    else:
        print("❌ NO patients found from 2025-10-20")
    
    # Check all dates in October 2025
    print("\n📊 All patient studies in October 2025:")
    print("-" * 70)
    cur.execute("""
        SELECT study_date, COUNT(*) as count 
        FROM patient_studies 
        WHERE study_date LIKE '202510%' 
        GROUP BY study_date 
        ORDER BY study_date DESC
    """)
    october_dates = cur.fetchall()
    
    if october_dates:
        for date, count in october_dates:
            formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
            status = "⚠️  MISSING 2025-10-20" if date == "20251020" and count == 0 else "✅"
            print(f"{status} {formatted_date}: {count} patients")
    else:
        print("❌ NO patients found in October 2025")
    
    # Check total patients in database
    print("\n📈 Total Statistics:")
    print("-" * 70)
    cur.execute("SELECT COUNT(*) FROM patient_studies")
    total = cur.fetchone()[0]
    print(f"Total patients in database: {total}")
    
    # Check date range
    cur.execute("SELECT MIN(study_date), MAX(study_date) FROM patient_studies")
    min_date, max_date = cur.fetchone()
    if min_date and max_date:
        print(f"Date range: {min_date[:4]}-{min_date[4:6]}-{min_date[6:8]} to {max_date[:4]}-{max_date[4:6]}-{max_date[6:8]}")
    
    # Check last indexed time
    cur.execute("SELECT MAX(last_indexed) FROM patient_studies")
    last_indexed = cur.fetchone()[0]
    if last_indexed:
        print(f"Last indexed: {last_indexed}")
    
    conn.close()
    
    # Summary
    print("\n" + "=" * 70)
    if not results_20:
        print("⚠️  ISSUE CONFIRMED: No patients from 2025-10-20 found in database")
        print("\n💡 Possible causes:")
        print("   1. Indexing hasn't run since 2025-10-20")
        print("   2. DICOM files from that date are in a different location")
        print("   3. Files may not have been scanned yet")
        print("\n🔧 Recommended action:")
        print("   Run the indexing process to scan for new patients")
    else:
        print(f"✅ Database contains {len(results_20)} patients from 2025-10-20")
    print("=" * 70)
    
except sqlite3.Error as e:
    print(f"❌ Database error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
