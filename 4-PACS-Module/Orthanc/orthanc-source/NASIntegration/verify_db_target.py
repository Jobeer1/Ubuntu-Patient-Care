"""
Quick verification script to show which database the indexer will use
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from metadata_db import get_metadata_db_path

print("=" * 60)
print("DATABASE PATH RESOLUTION TEST")
print("=" * 60)

# Check environment variable
use_internal = os.environ.get('USE_ORTHANC_INTERNAL_INDEX', 'false').lower()
pacs_db_env = os.environ.get('PACS_DB_PATH', '<not set>')

print(f"\n📊 Environment Variables:")
print(f"  USE_ORTHANC_INTERNAL_INDEX = {use_internal}")
print(f"  PACS_DB_PATH = {pacs_db_env}")

# Get canonical path from helper
canonical = get_metadata_db_path()
print(f"\n🔎 Canonical metadata DB (from helper): {canonical}")
print(f"  Exists: {os.path.exists(canonical)}")

# Simulate what indexing route will do
canonical_dir = os.path.dirname(canonical)
if use_internal == 'true':
    orthanc_index = os.path.join(canonical_dir, 'index')
    if os.path.exists(orthanc_index):
        target = orthanc_index
        print(f"\n✅ USE_ORTHANC_INTERNAL_INDEX=true: Will target Orthanc internal index")
        print(f"  Target: {target}")
    else:
        target = canonical
        print(f"\n⚠️ USE_ORTHANC_INTERNAL_INDEX=true but 'index' not found")
        print(f"  Fallback target: {target}")
else:
    safe_db = os.path.join(canonical_dir, 'pacs_metadata.db')
    target = safe_db
    print(f"\n✅ USE_ORTHANC_INTERNAL_INDEX=false: Will use safe metadata DB")
    print(f"  Target: {target}")
    print(f"  Exists: {os.path.exists(target)}")

print("\n" + "=" * 60)
print("EXPECTED BEHAVIOR:")
print("=" * 60)
if use_internal == 'true':
    print("⚠️ RISKY MODE: Indexing will attempt to merge into Orthanc internal")
    print("   'index' file after completion. Orthanc MUST be stopped first.")
else:
    print("✅ SAFE MODE: Indexing will write to pacs_metadata.db")
    print("   (Orthanc can remain running)")
print("=" * 60)
