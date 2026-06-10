# SQLite Database Quick Start for SDOH Agent

## Before Starting

Run the migration once:
```bash
python migrate_json_to_sqlite.py
```

This creates `backend/health_graph.db` from the 2GB JSON file.

---

## Basic Usage

### Import and Initialize

```python
from health_graph_db import HealthGraphDB

db = HealthGraphDB('backend/health_graph.db')
```

### Search Patients

```python
# Find by name or ID
patients = db.search_patients('MANYATHI')
for p in patients:
    print(f"{p['patient_name']} (ID: {p['patient_id']}) - {p['total_studies']} studies")
```

### Get Patient Data

```python
patient_id = '63116-20071031-123600-6461-3116'

# All studies for patient
studies = db.get_patient_studies(patient_id)
# All files for patient
files = db.get_patient_files(patient_id)
```

### Search Studies

```python
# By modality
ct_studies = db.search_studies(modality='CT', limit=100)

# By body part
chest_studies = db.search_studies(body_part='chest', limit=100)

# By date range
feb_2019 = db.search_studies(start_date='20190201', end_date='20190228')

# Combined
feb_ct_chest = db.search_studies(
    modality='CT',
    body_part='chest',
    start_date='20190201',
    end_date='20190228'
)
```

### Keyword Search

```python
# Find files mentioning these keywords
files = db.search_keywords(['chest', 'pa', 'x-ray'], limit=50)
```

### Get Statistics

```python
stats = db.get_stats()
print(f"Patients: {stats['patients']}")
print(f"Studies: {stats['studies']}")
print(f"Files: {stats['files']}")
print(f"Modality breakdown: {stats['modality_breakdown']}")
```

---

## Direct SQL Queries

For advanced use cases:

```python
cursor = db.conn.cursor()

# Get studies per patient
cursor.execute('''
    SELECT patient_id, COUNT(*) as study_count
    FROM studies
    GROUP BY patient_id
    ORDER BY study_count DESC
    LIMIT 10
''')
for row in cursor.fetchall():
    print(f"Patient {row[0]}: {row[1]} studies")

# Get modality breakdown
cursor.execute('''
    SELECT modality, COUNT(*) as count
    FROM studies
    WHERE study_date >= '20190101'
    GROUP BY modality
    ORDER BY count DESC
''')
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]}")
```

---

## Common Queries

### "What studies does patient X have?"

```python
studies = db.get_patient_studies(patient_id)
print(f"{len(studies)} total studies")

by_year = {}
for study in studies:
    year = study['study_date'][:4]
    by_year[year] = by_year.get(year, 0) + 1

for year in sorted(by_year.keys()):
    print(f"  {year}: {by_year[year]} studies")
```

### "What body parts has patient X had scanned?"

```python
cursor = db.conn.cursor()
cursor.execute('''
    SELECT DISTINCT body_part_normalized FROM studies
    WHERE patient_id = ?
    ORDER BY body_part_normalized
''', (patient_id,))

parts = [row[0] for row in cursor.fetchall()]
print(f"Body parts scanned: {', '.join(parts)}")
```

### "Show me all chest X-rays between 2018-2020"

```python
studies = db.search_studies(
    modality='CR',
    body_part='chest',
    start_date='20180101',
    end_date='20201231',
    limit=1000
)
print(f"Found {len(studies)} chest X-rays")
```

### "What's the most common modality?"

```python
stats = db.get_stats()
top_modality = max(
    stats['modality_breakdown'].items(),
    key=lambda x: x[1]
)
print(f"Most common: {top_modality[0]} ({top_modality[1]} studies)")
```

---

## Performance Tips

### Use Indexes

Searches on these fields are fast (indexed):
- `patient_id`
- `study_date`
- `modality`
- `body_part_normalized`
- keywords

### Limit Results

Always use `limit` parameter to avoid loading millions of rows:
```python
# GOOD
studies = db.search_studies(modality='CT', limit=1000)

# BAD - could return 700k+ results
studies = db.search_studies(modality='CT')  # Uses default 100 limit actually
```

### Use Specific Filters

More specific = faster:
```python
# SLOW: Searches all CR studies
db.search_studies(modality='CR')

# FAST: Searches CR + chest + specific date range
db.search_studies(
    modality='CR',
    body_part='chest',
    start_date='20200101',
    end_date='20200331'
)
```

---

## Integration with Existing Code

### For sdoh_document_mixin.py

Replace JSON queries with:
```python
def _query_vault_index_for_folder(self, patient_id: str):
    from health_graph_db import HealthGraphDB
    
    db = HealthGraphDB('backend/health_graph.db')
    studies = db.get_patient_studies(patient_id)
    files = db.get_patient_files(patient_id)
    
    return {
        'patient_id': patient_id,
        'studies': studies,
        'files': files,
        'count': len(files)
    }
```

### For PatientDocumentIndexer

Use the adapter:
```python
from patient_index_adapter import PatientIndexAdapter

adapter = PatientIndexAdapter('backend/health_graph.db')

# Same interface as before
results = adapter.search(modality='CT', limit=10)
stats = adapter.get_stats()
visit_info = adapter.search_for_visit('chest CT scan')
```

---

## Data Format Reference

### Study Record
```python
{
    'id': 1,
    'patient_id': '63116-20071031-123600-6461-3116',
    'study_uid': '1.2.528.1.1001.3.500.16.5789.4337.201909091940464510',
    'study_date': '20190909',
    'study_description': 'CHEST X-RAY',
    'modality': 'CR',
    'body_part': 'CHEST',
    'body_part_normalized': 'chest',
    'series_count': 2,
    'indexed_at': '2026-06-09T02:30:14.226122'
}
```

### File Record
```python
{
    'id': 1,
    'patient_id': '63116-20071031-123600-6461-3116',
    'study_uid': '1.2.528.1.1001.3.500.16.5789.4337.201909091940464510',
    'file_path': '\\\\155.235.81.94\\UV Backup\\UV images\\2019\\9\\9\\106770\\DICOM\\20190909195424.104.9194.dcm',
    'file_type': 'dicom',
    'image_height': 3094,
    'image_width': 3480,
    'summary': 'X-Ray of the chest dated 09/09/2019 from DR C.I. STOYANOV',
    'indexed_at': '2026-06-09T02:30:14.226122'
}
```

---

## Troubleshooting

### "No such table: patients"

Database not initialized. Run migration first:
```bash
python migrate_json_to_sqlite.py
```

### No results found

Check:
1. Parameter format (modality uppercase, body_part lowercase)
2. Date format (YYYYMMDD)
3. Try broader search first
4. Check `db.get_stats()` to see if data exists

### Performance slow

- Use `limit` parameter
- Use more specific filters
- Check if indexes exist: `db.get_stats()`
- Try direct SQL query to diagnose

---

## Cheat Sheet

```python
from health_graph_db import HealthGraphDB

db = HealthGraphDB('backend/health_graph.db')

# Search
patients = db.search_patients('name')
studies = db.search_studies(modality='CT', body_part='chest')
files = db.search_keywords(['keyword1', 'keyword2'])

# Get data
studies = db.get_patient_studies(patient_id)
files = db.get_patient_files(patient_id)

# Info
stats = db.get_stats()

# Close when done
db.close()
```

---

Created: June 2026
