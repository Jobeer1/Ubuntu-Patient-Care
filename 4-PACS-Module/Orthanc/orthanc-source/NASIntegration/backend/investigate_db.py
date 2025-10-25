#!/usr/bin/env python3
"""
Database Investigation Script
Check what's in the nas_patient_index.db and why it's so large
"""

import sqlite3
import os

def investigate_database():
    try:
        from metadata_db import get_metadata_db_path
        db_path = get_metadata_db_path()
    except Exception:
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'nas_patient_index.db'))
    
    if not os.path.exists(db_path):
        print(f"❌ Database {db_path} not found")
        return
    
    # Check file size
    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    print(f"📊 Database size: {size_mb:.2f} MB")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"📋 Tables: {tables}")
        
        # Check each table
        for table in tables:
            table_name = table[0]
            print(f"\n🔍 Table: {table_name}")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            row_count = cursor.fetchone()[0]
            print(f"   Rows: {row_count}")
            
            # Get schema
            cursor.execute(f"PRAGMA table_info({table_name});")
            schema = cursor.fetchall()
            print(f"   Schema: {schema}")
            
            # Sample a few rows to see what's stored
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
            sample_data = cursor.fetchall()
            
            # Check if any columns contain large data
            if sample_data:
                print(f"   Sample data (first 3 rows):")
                for i, row in enumerate(sample_data):
                    print(f"     Row {i+1}:")
                    for j, value in enumerate(row):
                        if isinstance(value, (str, bytes)) and len(str(value)) > 100:
                            print(f"       Column {j}: {type(value).__name__} ({len(str(value))} chars) - LARGE DATA!")
                        else:
                            print(f"       Column {j}: {str(value)[:50]}...")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error investigating database: {e}")

if __name__ == "__main__":
    investigate_database()