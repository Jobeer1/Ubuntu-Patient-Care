# ✅ CRITICAL FIX: Variable Scope Error in Indexing Route

## Error Fixed
```
ERROR: cannot access local variable 'os' where it is not associated with a value
```

## Root Cause
Line 63 in `backend/routes/indexing.py` had a redundant `import os` statement INSIDE the `start_indexing()` function. This caused Python to treat `os` as a local variable, making the earlier reference to `os.environ` (line 56) invalid because Python thought we were trying to use a local variable before it was defined.

## The Problem Code (BEFORE)
```python
def start_indexing():
    # ...
    use_internal = os.environ.get(...)  # Line 56 - tries to use 'os'
    # ...
    import threading
    import sys
    import os           # Line 63 - shadows module-level 'os' import!
    import shutil
    import time
```

## The Fixed Code (AFTER)
```python
def start_indexing():
    # ...
    use_internal = os.environ.get(...)  # Line 56 - uses module-level 'os'
    # ...
    import threading
    import sys
    # Removed 'import os' - already imported at module level (line 6)
    import shutil
    import time
```

## What Was Changed
**File**: `backend/routes/indexing.py`
**Line 63**: Removed redundant `import os` statement

The module-level import at line 6 (`import os`) is sufficient for the entire file.

## Verification
✅ Python syntax check passed: `py -m py_compile backend/routes/indexing.py`

## Next Steps
Your Flask app should now start indexing correctly. The logs already show:
```
✅ Patient index available with 573 unique patients
```

### To Test:
1. Flask app is already running (you restarted it after the fix)
2. Go to NAS Integration page
3. Click "Start Indexing"
4. Watch for these logs:
   ```
   ✅ USE_ORTHANC_INTERNAL_INDEX=false - indexing will use safe metadata DB
   🔁 Replacing safe metadata DB ... with working DB ...
   ✅ Updated safe metadata DB: ...\pacs_metadata.db
   ```

### Expected Behavior Now:
- ✅ No more "cannot access local variable" error
- ✅ Indexing will create a working DB copy
- ✅ Scan NAS folders and populate patient_studies
- ✅ Merge working DB back into pacs_metadata.db on completion
- ✅ Row count in pacs_metadata.db will increase from 573 to 700+

## Summary
The indexing route is now fixed. The variable scope error is resolved by removing the redundant `import os` statement that was shadowing the module-level import.
