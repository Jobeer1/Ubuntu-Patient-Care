#!/usr/bin/env python3
"""
Fix database search to return individual studies instead of aggregated patients
"""
import sqlite3

def fix_database_search():
    """Update the database search to show individual studies"""
    
    # First, let's create a proper search function that returns studies
    search_script = """
# Modified database search to return individual studies
def search_patients_in_database_fixed(search_params):
    \"\"\"Search for STUDIES (not patients) in the database to show all studies per patient\"\"\"
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        patient_id = search_params.get('patient_id', '').strip()
        patient_name = search_params.get('patient_name', '').strip()
        study_date = search_params.get('study_date', '').strip()
        
        # Build query for patient_studies table (not patients table)
        conditions = []
        params = []
        
        if patient_id:
            conditions.append("patient_id LIKE ?")
            params.append(f'%{patient_id}%')
        
        if patient_name:
            conditions.append("patient_name LIKE ?")
            params.append(f'%{patient_name}%')
        
        if study_date:
            conditions.append("study_date LIKE ?")
            params.append(f'%{study_date}%')
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Query patient_studies table to get individual studies
        query = f'''
        SELECT 
            patient_id,
            patient_name, 
            patient_birth_date,
            patient_sex,
            study_date,
            study_description,
            modality,
            folder_path,
            dicom_file_count as total_instances,
            folder_size_mb,
            last_indexed
        FROM patient_studies 
        WHERE {where_clause}
        ORDER BY study_date DESC
        LIMIT 100
        '''
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert to patient format expected by UI
        patients = []
        for row in rows:
            patient = {
                'patient_id': row[0],
                'patient_name': row[1],
                'patient_birth_date': row[2] or '',
                'patient_sex': row[3] or '',
                'age': '',  # Calculate if needed
                'folder_path': row[7],
                'total_studies': 1,  # Each row is one study
                'total_series': 0,
                'total_instances': row[8] or 0,
                'first_study_date': row[4],
                'last_study_date': row[4],
                'study_date': row[4],  # Individual study date
                'file_count': row[8] or 0,  # Individual study file count
                'studies': [{
                    'study_date': row[4],
                    'study_description': row[5] or '',
                    'modality': row[6] or '',
                    'file_count': row[8] or 0,
                    'size_mb': row[9] or 0
                }]
            }
            patients.append(patient)
        
        return patients
        
    except Exception as e:
        logger.error(f"Database search error: {e}")
        return []
    finally:
        if conn:
            conn.close()
"""
    
    print("The issue is that the search function queries the 'patients' table")
    print("which aggregates studies per patient, showing only 1 result.")
    print("")
    print("We need to modify the search to query 'patient_studies' table")
    print("to show individual studies as separate results.")
    print("")
    print("I'll create a patch for the database_operations.py file...")

    # Read the current file
    with open('services/database_operations.py', 'r') as f:
        content = f.read()
    
    # Check if we need to patch it
    if 'FROM patient_studies' in content:
        print("✅ File already uses patient_studies table")
        return
    
    # Create backup
    with open('services/database_operations.py.backup', 'w') as f:
        f.write(content)
    
    # Replace the patients table query with patient_studies query
    old_query = "SELECT * FROM patients"
    new_query = """SELECT 
            patient_id,
            patient_name, 
            patient_birth_date,
            patient_sex,
            study_date,
            study_description,
            modality,
            folder_path,
            dicom_file_count,
            folder_size_mb,
            last_indexed
        FROM patient_studies"""
    
    new_content = content.replace(old_query, new_query)
    
    # Also need to update the field mappings
    old_mapping = """patient = {
                'patient_id': row['patient_id'],
                'patient_name': row['patient_name'],
                'patient_birth_date': row['birth_date'] or '',
                'patient_sex': row['sex'] or '',
                'age': row['age'] or '',
                'folder_path': row['folder_path'],
                'total_studies': row['total_studies'],
                'total_series': row['total_series'],
                'total_instances': row['total_instances'],
                'first_study_date': row['first_study_date'] or '',
                'last_study_date': row['last_study_date'] or '',"""
    
    new_mapping = """patient = {
                'patient_id': row['patient_id'],
                'patient_name': row['patient_name'],
                'patient_birth_date': row['patient_birth_date'] or '',
                'patient_sex': row['patient_sex'] or '',
                'age': '',
                'folder_path': row['folder_path'],
                'total_studies': 1,
                'total_series': 0,
                'total_instances': row['dicom_file_count'] or 0,
                'first_study_date': row['study_date'] or '',
                'last_study_date': row['study_date'] or '',
                'study_date': row['study_date'] or '',
                'file_count': row['dicom_file_count'] or 0,"""
    
    new_content = new_content.replace(old_mapping, new_mapping)
    
    # Write the updated file
    with open('services/database_operations.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Patched database_operations.py to use patient_studies table")
    print("This should now return individual studies instead of aggregated patients")

if __name__ == "__main__":
    fix_database_search()