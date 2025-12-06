from services.intelligent_indexing_service import IntelligentDICOMIndexer
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'orthanc-index', 'pacs_metadata.db')
print('Using DB:', db_path)
try:
    idx = IntelligentDICOMIndexer(db_path, nas_path='\\\\155.235.81.155\\Image Archiving')
    print('Indexer initialized successfully')
except Exception as e:
    print('Indexer initialization failed:', e)
    raise
