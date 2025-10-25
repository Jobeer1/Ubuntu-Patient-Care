# Orthanc Explorer Theme Fix - Summary

## Problem
The Orthanc Explorer at `http://localhost:8042/app/explorer.html` had inconsistent styling compared to the SA Medical Imaging theme used in the Patients page and dashboard.

## Solution
Created a themed proxy route that fetches Orthanc's Explorer HTML and applies the SA color scheme and styling without modifying Orthanc's original files.

## Changes Made

### 1. New Themed Explorer Route
**File**: `backend/routes/web_routes.py`
- Added route: `GET /orthanc/explorer`
- Fetches original Orthanc Explorer HTML from `http://localhost:8042/app/explorer.html`
- Rewrites asset URLs to use the reverse proxy: `/api/nas/orthanc-proxy/`
- Injects custom SA theme CSS
- Adds JavaScript shim to ensure fetch/XHR calls route through proxy

### 2. SA Theme Stylesheet
**File**: `backend/static/css/orthanc_theme.css`
- Applies SA Medical Imaging color scheme:
  - SA Green: #006533
  - SA Gold: #FFB81C
  - SA Blue: #005580
- Styles all Orthanc Explorer elements:
  - Gradient backgrounds
  - Themed buttons (primary, success, info, default)
  - Professional panel and table styling
  - Rounded corners and modern shadows
  - Form controls with SA branding

### 3. Updated All "Open Orthanc" Buttons
Updated the following files to use `/orthanc/explorer` instead of `http://localhost:8042`:

- `backend/web_interfaces/templates/orthanc_server_management.py`
  - Function: `openOrthancWeb()`
  
- `backend/templates/ohif_viewer.html`
  - Function: `openOrthancWeb()`
  - Function: `openOrthancDirectly()`
  
- `backend/templates/simple_dicom_viewer.html`
  - Function: `openOrthancViewer()`

## Usage

### Before
Clicking "Open Orthanc" buttons opened: `http://localhost:8042/app/explorer.html`
- Plain Bootstrap styling
- Inconsistent with SA theme
- Localhost dependency

### After
Clicking "Open Orthanc" buttons opens: `/orthanc/explorer`
- SA Medical Imaging theme (green/gold/blue gradients)
- Consistent with Patients page styling
- Same-origin (no CORS issues)
- All API calls proxied through `/api/nas/orthanc-proxy/`

## URLs

- **Themed Explorer**: `http://155.235.81.41:5000/orthanc/explorer`
- **Original (still accessible)**: `http://localhost:8042/app/explorer.html`

## Benefits

1. **Consistent UX**: All pages now share the SA Medical Imaging theme
2. **Professional Look**: Modern gradients, rounded corners, better colors
3. **Same-Origin**: No CORS issues when accessing Orthanc from the web app
4. **Non-Invasive**: Original Orthanc installation remains untouched
5. **Easy Updates**: Theme can be adjusted by editing one CSS file

## Technical Details

### Proxy Flow
```
User clicks "Open Orthanc" 
  → Opens /orthanc/explorer
  → Flask fetches http://localhost:8042/app/explorer.html
  → Rewrites asset URLs: /app/* → /api/nas/orthanc-proxy/app/*
  → Injects orthanc_theme.css
  → Injects fetch/XHR shim for API calls
  → Serves modified HTML to user
  → All Orthanc API calls route through /api/nas/orthanc-proxy/*
```

### Files Modified
- ✅ `backend/routes/web_routes.py` (new route)
- ✅ `backend/static/css/orthanc_theme.css` (new theme)
- ✅ `backend/web_interfaces/templates/orthanc_server_management.py`
- ✅ `backend/templates/ohif_viewer.html`
- ✅ `backend/templates/simple_dicom_viewer.html`

## Future Enhancements (Optional)

- Add direct link to themed explorer in dashboard navigation
- Create custom Orthanc Explorer plugins page with SA branding
- Add patient quick-search in themed explorer header
- Integrate SA logo in themed explorer navbar

## Testing

1. Login to the SA Medical Imaging system
2. Navigate to Orthanc Manager
3. Click "Open Orthanc Web"
4. Verify the explorer has SA theme (green/gold/blue)
5. Test patient browsing, study viewing
6. Verify all API calls work correctly

---
**Status**: ✅ Complete and deployed
**Date**: October 1, 2025
