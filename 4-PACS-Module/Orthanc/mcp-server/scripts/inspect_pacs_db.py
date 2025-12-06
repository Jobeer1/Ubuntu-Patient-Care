#!/usr/bin/env python3
"""
Inspect PACS Database Schema
Analyzes the PACS metadata database structure
"""
import sqlite3
from pathlib import Path

# PACS database path
PACS_DB = Path("../../../4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/orthanc-index/pacs_metadata.db")

def inspect_database():
    """Inspect PACS database structure"""
    print("=" * 60)
    print("PACS Database Schema Inspection")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(PACS_DB)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\n📊 Tables found: {len(tables)}")
        print("-" * 60)
        
        for table in tables:
            print(f"\n📋 Table: {table}")
            
            # Get column info
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            
            print("   Columns:")
            for col in columns:
                col_id, name, type_, notnull, default, pk = col
                pk_marker = " [PK]" if pk else ""
                null_marker = " NOT NULL" if notnull else ""
                print(f"     - {name}: {type_}{pk_marker}{null_marker}")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   Rows: {count}")
            
            # Show sample data if exists
            if count > 0:
                cursor.execute(f"SELECT * FROM {table} LIMIT 1")
                sample = cursor.fetchone()
                if sample:
                    print(f"   Sample: {sample[:3]}..." if len(sample) > 3 else f"   Sample: {sample}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Inspection complete")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_database()
