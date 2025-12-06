import sqlite3
from metadata_db import get_metadata_db_path

p = get_metadata_db_path()
print('DB:', p)
conn = sqlite3.connect(p)
cur = conn.cursor()
cur.execute("DELETE FROM instances WHERE sop_instance_uid LIKE '1.2.840.SAMPLE.%' OR file_path LIKE '%SAMPLE_PAT_001%'")
cur.execute("DELETE FROM series WHERE series_instance_uid LIKE '1.2.840.SAMPLE.%'")
cur.execute("DELETE FROM studies WHERE study_instance_uid LIKE '1.2.840.SAMPLE.%'")
cur.execute("DELETE FROM patients WHERE patient_id='SAMPLE_PAT_001'")
conn.commit()
cur.execute('PRAGMA wal_checkpoint(FULL)')
conn.close()

conn = sqlite3.connect(p)
cur = conn.cursor()
cur.execute('VACUUM')
conn.commit()
cur.execute("SELECT COUNT(*) FROM instances WHERE sop_instance_uid LIKE '1.2.840.SAMPLE.%' OR file_path LIKE '%SAMPLE_PAT_001%'")
print('Remaining sample instances:', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM patients WHERE patient_id='SAMPLE_PAT_001'")
print('Remaining sample patients:', cur.fetchone()[0])
conn.close()
