import sqlite3
from pathlib import Path

db = Path('orthanc-index/pacs_metadata.db')
conn = sqlite3.connect(str(db))
cur = conn.cursor()

q = '85'
pattern = f"%{q}%"
print('DB:', db)

# Check patients table/view exists
cur.execute("SELECT name, type FROM sqlite_master WHERE name='patients'")
print('patients entry:', cur.fetchone())

# Count matches by patient_id
cur.execute("SELECT COUNT(*) FROM patients WHERE patient_id LIKE ?", (pattern,))
print('patient_id LIKE count:', cur.fetchone()[0])

# Sample matches
cur.execute("SELECT patient_id, patient_name, first_study_date, last_study_date FROM patients WHERE patient_id LIKE ? LIMIT 10", (pattern,))
rows = cur.fetchall()
print('patient_id samples:')
for r in rows:
    print(r)

# Count matches by patient_name
cur.execute("SELECT COUNT(*) FROM patients WHERE patient_name LIKE ?", (pattern,))
print('patient_name LIKE count:', cur.fetchone()[0])
cur.execute("SELECT patient_id, patient_name FROM patients WHERE patient_name LIKE ? LIMIT 10", (pattern,))
for r in cur.fetchall():
    print(r)

conn.close()