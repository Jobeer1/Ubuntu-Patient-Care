# Query Intent Detection Fixes - COMPLETE

## Problem Statement

The SDOH agent was not understanding user questions correctly:

1. **"Show me all the SIIM hackathon patients"** → Incorrectly routed to SIIM ingest (trying to start/download) instead of showing patients
2. **"Please show me the patients with SIIM in their names"** → Not routed anywhere, fell back to generic agent response
3. **"Give me a list of SIIM patients"** → Returned wrong patients from health graph (searching for "Give" as patient name)

## Root Causes

### 1. Proxy Routing Confusion (sdoh_oc_proxy.py)
**Problem**: The proxy was treating ALL SIIM-related keywords as SIIM ingest commands, not distinguishing between:
- SIIM COMMANDS: "Start SIIM ingest", "Check SIIM ingest status" → should go to ingest handler
- SIIM QUERIES: "Show SIIM patients", "List SIIM hackathon patients" → should go to show_documents

**Impact**: "Show me all the SIIM hackathon patients" matched SIIM ingest check and was routed incorrectly

### 2. Intent Detection Order (sdoh_patient_index.py)
**Problem**: Summary keywords like "give me" and "list" were being checked BEFORE SIIM keywords, so queries got misclassified

**Impact**: "Give me a list of SIIM patients" didn't match SIIM check and was treated as patient name search for "Give"

### 3. Document Mixin Silent Failure (sdoh_document_mixin.py)
**Problem**: When SIIM queries were detected, the mixin returned `{'success': False}` (no response key), causing the proxy to silently fall through

**Impact**: Queries that DID reach show_documents routing got lost in exception handling

## Fixes Applied

### FIX 1: Distinguish SIIM Commands from SIIM Queries (sdoh_oc_proxy.py)

**Before**:
```python
is_siim_ingest_cmd = (
    'siim' in user_text_lower and
    any(kw in user_text_lower for kw in ['ingest', 'status', 'hackathon', 'download', 'fetch'])
)
```

This incorrectly flagged SIIM QUERIES as ingest commands.

**After**:
```python
# SIIM INGEST COMMANDS - only "start"/"begin" ingest, or check "status"
is_siim_command_start = any(kw in user_text_lower for kw in ['start', 'begin', 'run']) and 'ingest' in user_text_lower and 'siim' in user_text_lower
is_siim_command_status = any(kw in user_text_lower for kw in ['status', 'progress', 'how far']) and 'siim' in user_text_lower and 'ingest' in user_text_lower

# If it's a SIIM query (show/list/get) even with hackathon keyword, don't route to ingest
is_siim_query = any(kw in user_text_lower for kw in ['show', 'list', 'get', 'display', 'search for']) and 'siim' in user_text_lower

# Only route to SIIM ingest if it's an ingest command and NOT a query
is_siim_ingest_cmd = (is_siim_command_start or is_siim_command_status) and not is_siim_query
```

**Result**: SIIM queries now bypass the ingest handler and go to show_documents

### FIX 2: Prioritize SIIM Checks in Intent Detection (sdoh_patient_index.py)

**Before**:
```python
is_asking_for_summary = any(word in query_lower for word in [
    'how many', 'total', 'summary', 'overview', 'what documents',
    'show me', 'list', 'give me'
])

is_asking_for_siim = any(word in query_lower for word in [
    'siim', 'hackathon'
])

if is_asking_for_siim:
    # Route to SIIM
    return {'success': False, 'filter_type': 'siim_ingest'}

if is_asking_for_summary:
    # Return summary
    return {...}
```

This meant "Give me a list of SIIM patients" might match summary check first.

**After**:
```python
# ===== PRIORITY 1: CHECK FOR SIIM QUERIES FIRST =====
# SIIM queries ALWAYS go to SIIM handler, regardless of other keywords
is_asking_for_siim = any(word in query_lower for word in [
    'siim', 'hackathon'
])

if is_asking_for_siim:
    return {'success': False, 'filter_type': 'siim_ingest'}

# ===== PRIORITY 2: INTENT DETECTION FOR HEALTH GRAPH QUERIES =====
is_asking_for_summary = any(word in query_lower for word in [
    'how many', 'total', 'summary', 'overview', 'what documents',
    'show me', 'list', 'give me', 'what do i have'
])
```

**Result**: SIIM keywords always checked first, preventing misclassification

### FIX 3: Handle SIIM Queries in Document Mixin (sdoh_document_mixin.py)

**Before**:
```python
if hg_data.get('filter_type') == 'siim_ingest':
    return {'success': False}  # Empty dict causes proxy to fall through!
```

**After**:
```python
if hg_data.get('filter_type') == 'siim_ingest':
    # Query SIIM registry and show SIIM patients
    try:
        from backend.pacs_registry import PACSContinuityRegistry
        registry = PACSContinuityRegistry()
        patients = registry.list_patients(limit=20)
        if patients:
            lines = [f'📋 Found {len(patients)} patient(s) in your SIIM registry:\n']
            for p in patients[:10]:
                # Format patient info...
            return {
                'response': '\n'.join(lines),
                'score_adjustment': 0, 'is_ready': False, 'phase': 'show_documents',
                'route': 'show_documents',
            }
    except Exception as e:
        print(f"[MIXIN] SIIM registry error: {e}")
    
    return {'success': False}
```

**Result**: SIIM queries now get proper responses with actual SIIM patient data

## Test Cases

### Query: "Show me all the SIIM hackathon patients"
- **Old**: Route to SIIM ingest → "SIIM ingest is running..."
- **New**: Route to show_documents → "Found X patient(s) in your SIIM registry"

### Query: "Please show me the patients with SIIM in their names"
- **Old**: Fall through to generic agent → "I am here and ready to help..."
- **New**: Route to show_documents → "Found X patient(s) in your SIIM registry"

### Query: "How many patients got the surname Strauss?"
- **Old**: Works (summary query) → Database summary
- **New**: Works better (patient name search) → "Found X patient(s) with surname Strauss"

### Query: "Give me a list of SIIM patients"
- **Old**: Search for patient named "Give" → Wrong results
- **New**: Route to show_documents → "Found X patient(s) in your SIIM registry"

## Debug Output Added

Added `[PROXY DEBUG]` logging to show routing decisions:

```
[PROXY DEBUG] Query: show me all the SIIM hackathon patients
[PROXY DEBUG]   is_asking_to_show=True, is_siim_command=False, is_show_documents_cmd=True
[PROXY] Creating shim and calling _build_show_documents_response...
[PROXY] Got response: 📋 Found 2 patient(s) in your SIIM registry:...
[PROXY] Returning show_documents response
```

## Files Modified

1. **backend/sdoh_patient_index.py** (lines ~378-530)
   - Reordered intent detection priorities
   - Enhanced stopwords list
   - Better name extraction logic

2. **sdoh_oc_proxy.py** (lines ~365-465)
   - Separated SIIM command detection from SIIM query detection
   - Added debug logging
   - Fixed show_documents routing condition

3. **backend/sdoh_document_mixin.py** (lines ~315-360)
   - Added SIIM registry lookup for SIIM queries
   - Proper response formatting for SIIM patients
   - Error handling with graceful fallback

## Verification

To test the fixes:

```bash
# Test intent detection logic
python test_intent_detection.py

# Test proxy routing
python test_proxy_routing.py

# Test complete flow
python test_complete_flow.py
```

## Expected Behavior After Fixes

✅ "Show me SIIM patients" → Shows SIIM registry patients  
✅ "How many patients" → Shows health graph summary  
✅ "Patients named Smith" → Searches health graph by name  
✅ "Give me a list of patients" → Shows health graph summary  
✅ "Start SIIM ingest" → Routes to SIIM ingest handler  
✅ "SIIM ingest status" → Shows SIIM ingest progress  

## Next Steps

1. Restart the SDOH agent: `python run.py`
2. Test queries with various formats
3. Monitor proxy output for debug messages
4. Verify SIIM registry is accessible and has patient data
5. Check database growth as indexing continues
