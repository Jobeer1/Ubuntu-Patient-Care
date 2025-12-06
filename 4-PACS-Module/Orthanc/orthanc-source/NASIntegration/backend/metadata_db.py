import os
from pathlib import Path


def get_metadata_db_path() -> str:
    """Return the canonical metadata DB path used by the PACS integration.

    Resolution order:
      1. Environment variable 'PACS_DB_PATH' (recommended for overrides)
      2. A safe metadata DB inside the backend 'orthanc-index' folder: 'pacs_metadata.db'
      3. Fallback legacy names in the backend directory

    Notes:
      - By default we avoid writing to Orthanc's internal 'index' file to prevent corruption.
      - If you truly want to use Orthanc's internal index, set PACS_DB_PATH to that file and
        ensure Orthanc is stopped and you have a backup.
    """
    # 1) Env override
    env_path = os.environ.get('PACS_DB_PATH')
    if env_path:
        return os.path.abspath(os.path.expanduser(env_path))

    # 2) Use orthanc-index/pacs_metadata.db inside backend
    base = os.path.dirname(__file__)
    orthanc_index_dir = os.path.join(base, 'orthanc-index')
    try:
        os.makedirs(orthanc_index_dir, exist_ok=True)
    except Exception:
        # If creation fails, fallback to base
        orthanc_index_dir = base

    safe_db = os.path.join(orthanc_index_dir, 'pacs_metadata.db')
    # Ensure parent dir exists and return
    Path(os.path.dirname(safe_db)).mkdir(parents=True, exist_ok=True)
    return os.path.abspath(safe_db)

