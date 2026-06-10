# SDOH Agent Folder Indexing Fix

## Problem
The SDOH agent was showing an unhelpful error message when users tried to index a folder on a network drive (e.g., `X:\UV images\2026`):
```
I could not find the folder path: X:\UV images\2026. Please confirm the drive is mounted and try again with a valid path.
```

This error didn't distinguish between:
1. **Drive not mounted** (e.g., X: drive is disconnected)
2. **Folder doesn't exist** (e.g., the path is wrong or folder was deleted)
3. **Permission denied** (e.g., user can't access the folder)

## Root Cause
The `_build_index_guidance()` method in `backend/sdoh_document_mixin.py` had weak diagnostics:
- Path validation was checking if parent directory exists but not clearly identifying which problem occurred
- Error messages didn't distinguish between drive and folder issues
- Diagnostic information collected wasn't being properly formatted and shown to the user

## Solution
Improved the diagnostic logic in `backend/sdoh_document_mixin.py` (lines 130-270):

### 1. Better Drive Detection
Added explicit drive mounting checks:
```python
# Try to access drive root to see if it's mounted
drive_root = f"{drive_letter}:\\"
try:
    os.listdir(drive_root)
    drive_mounted = True
except (OSError, FileNotFoundError):
    drive_mounted = False
```

### 2. Contextual Error Messages
Now provides different messages based on what failed:

**If drive is NOT mounted:**
```
❌ Cannot access the folder path: X:\UV images\2026

The drive X: is not mounted or not accessible.

Please:
  1. Confirm the drive X: is physically connected and powered on
  2. Check that it appears in Windows File Explorer
  3. Try again with the path

Diagnostic checks performed:
  • Drive X: is NOT mounted or not accessible
```

**If drive IS mounted but folder doesn't exist:**
```
❌ Cannot find the folder: X:\UV images\2026

The drive X: is mounted, but this folder does not exist.

Please:
  1. Verify the folder path is correct (check spelling and capitalization)
  2. Confirm the folder exists in Windows File Explorer
  3. Make sure you have read permission to access it
  4. Try again with a valid path

Diagnostic checks performed:
  • Parent path exists: X:\UV images
  • Drive X: is mounted
  • Folder not found: X:\UV images\2026
```

### 3. Detailed Diagnostic Information
The diagnostic list now includes:
- Whether the drive is mounted
- Whether the parent folder exists
- Specific access errors (if any)
- Clear drive letter identification

## Benefits
✅ **Users get clear, actionable guidance**  
✅ **Distinguishes between different failure modes**  
✅ **Shows diagnostic checks performed**  
✅ **Helps users troubleshoot quickly**  
✅ **No changes to core indexing logic**  

## Files Modified
- `backend/sdoh_document_mixin.py` - Enhanced `_build_index_guidance()` method

## How to Test
1. Try indexing with an unmounted drive: `index "Z:\some\path"`
   - Should see: "The drive Z: is NOT mounted"
2. Try indexing with wrong folder path on mounted drive: `index "X:\wrong\path"`
   - Should see: "The drive X: is mounted, but this folder does not exist"
3. Try indexing with a valid path: `index "X:\UV images\2026"`
   - Should either scan successfully or give specific access errors

## Deployment Notes
- Syntax checked: ✅ No errors
- No breaking changes to public API
- Backward compatible with existing configurations
- Will work on both local and network drives
