# TASK 1.2.4: Phase 1 Integration Testing - Execution Plan

**Status**: ⏸️ IN PROGRESS  
**Assigned to**: Dev 1 & Dev 2 (Pair)  
**Duration**: 4 hours  
**Start Time**: [Session Start]  
**Target Completion**: Phase 1 Week 2 End  

---

## 1. EXECUTION OVERVIEW

This document provides the step-by-step plan for comprehensive Phase 1 integration testing. All 9 core Phase 1 components must be tested together to verify the system works end-to-end.

### System Under Test
```
Frontend Modules:
  ✓ volumetric-viewer.html (850+ lines)
  ✓ ViewerController application class
  ✓ api-integration.js (456 lines) - ViewerAPIClient
  ✓ 3d-renderer.js (520 lines) - VolumetricRenderer
  ✓ measurement-tools.js (520 lines) - MeasurementTools
  ✓ mpr-widget.js (580 lines) - MPRWidget
  ✓ viewer.css (620 lines)

Backend Components:
  ✓ app/routes/viewer_3d.py (754 lines, 8 endpoints)
  ✓ app/ml_models/dicom_processor.py (259 lines)
```

### Performance Targets
```
Volume Load:      < 3 seconds
Slice Render:     < 50ms
MPR Update:       < 50ms
Measurement:      < 100ms
Memory Usage:      < 500MB
API Response:      < 3 seconds for 95th percentile
```

---

## 2. PRE-TEST CHECKLIST

### Environment Verification
- [ ] Python 3.13.6 installed: `python --version`
- [ ] FastAPI running: `python app/main.py`
- [ ] All dependencies installed: Check requirements.txt
- [ ] Test data available (DICOM files or mock study)
- [ ] Ports available: 8000 (API), 3000+ (frontend dev server if used)
- [ ] Browser console enabled for debugging (F12)
- [ ] Performance profiler ready (Chrome DevTools or similar)

### File Verification
```bash
# Verify all production files exist
ls -la app/routes/viewer_3d.py
ls -la app/ml_models/dicom_processor.py
ls -la static/js/viewers/api-integration.js
ls -la static/js/viewers/3d-renderer.js
ls -la static/js/viewers/measurement-tools.js
ls -la static/js/viewers/mpr-widget.js
ls -la static/viewers/volumetric-viewer.html
ls -la static/css/viewer.css
```

### Dependencies Check
```bash
# Verify key packages
pip show fastapi
pip show simpleitk
pip show numpy
pip show torch
```

---

## 3. TEST PHASES

### Phase 3A: API Unit Verification (1 hour)

Run the existing integration test suite to verify all API endpoints work.

```bash
# From mcp-server directory
python test_integration.py
```

**Test Coverage**:
- [x] Health checks (2 tests)
- [x] Viewer 3D API endpoints (3 tests)
- [x] Measurements API (4 tests)
- [x] Orthanc integration (optional, 2 tests)
- [x] Database operations (4 tests)

**Expected Results**:
- ✓ 15/15 tests PASS
- ✓ No errors in console
- ✓ Response times < 3s
- ✓ Measurement data saved to database

**Acceptance Criteria**:
```
All health checks: PASS
All API endpoints: PASS
All measurement CRUD: PASS
Report saved to: integration_test_report.txt
```

---

### Phase 3B: Frontend Load Testing (30 minutes)

Manual testing of frontend UI in browser.

#### Test 3B.1: Page Load
**File**: `static/viewers/volumetric-viewer.html`
**Steps**:
1. Open `http://localhost:8000/static/viewers/volumetric-viewer.html`
2. Wait for page to fully load
3. Verify all UI elements present

**Verification**:
- [ ] Page loads without errors
- [ ] Left sidebar fully visible (6 panels)
- [ ] Right sidebar fully visible (4 panels)
- [ ] Canvas area displays correctly
- [ ] Header shows status "Ready"
- [ ] No console errors (F12 → Console tab)
- [ ] Load time < 5 seconds

**Expected Output**:
```
✓ HTML structure loads
✓ CSS applied correctly (purple theme)
✓ All JavaScript modules loaded
✓ ViewerController initialized
✓ Status shows "Ready"
✓ No 404 errors for assets
```

#### Test 3B.2: Study Loading
**Steps**:
1. In left sidebar "Study Selector" panel, select a study
2. Click "Load Study" button
3. Wait for volume to appear in canvas

**Verification Checklist**:
- [ ] Loading spinner appears
- [ ] API call to `/api/viewer/load-study` succeeds
- [ ] 3D volume appears in canvas within 3 seconds
- [ ] "Processing..." status shown
- [ ] Status changes to "Ready" when complete
- [ ] No console errors
- [ ] Console logs show load time (e.g., "Study loaded in 2.3s")

**Performance Check**:
```
Expected: 1-3 seconds for volume load
Measured: _________ seconds

✓ PASS if < 3s
✗ FAIL if > 3s
```

#### Test 3B.3: 3D Rendering Controls
**Steps**:
1. With volume loaded, test mouse controls:
   - [ ] Left-click + drag: Rotate volume (should spin smoothly)
   - [ ] Right-click + drag: Pan (should move up/down/left/right)
   - [ ] Mouse wheel: Zoom (should zoom in/out)

2. Test keyboard shortcuts:
   - [ ] Press `R`: Reset view (volume returns to center)
   - [ ] Press `F`: Toggle fullscreen
   - [ ] Press `A`: Toggle auto-rotate (cube spins slowly)

**Expected Behavior**:
- Rotation smooth at 60 FPS
- Pan responds immediately
- Zoom smooth with scroll
- All keyboard shortcuts work
- Console shows "View reset" or similar messages

**Performance Check**:
```
FPS counter in bottom-right:
  Expected: 50-60 FPS
  Measured: ________ FPS
```

#### Test 3B.4: Render Mode Switching
**Steps**:
1. In "Render Controls" panel, find "Render Mode" dropdown
2. Select each mode and verify:
   - [ ] Volume (isosurface rendering)
   - [ ] MIP (maximum intensity projection)
   - [ ] Surface (surface extraction)

**Expected Behavior**:
```
Volume Mode:   Volume appears translucent with internal details ✓
MIP Mode:      Volume appears bright with maximum intensities highlighted ✓
Surface Mode:  Volume appears as solid mesh surface ✓
```

#### Test 3B.5: Window/Level Adjustment
**Steps**:
1. In "Window/Level Controls" panel:
   - [ ] Adjust "Window Center" slider (left)
   - [ ] Adjust "Window Width" slider (right)
   - Observe volume appearance changes

2. Test presets:
   - [ ] Click "Bone Preset" → Image should appear white with bone detail
   - [ ] Click "Lung Preset" → Image should appear dark with lung detail
   - [ ] Click "Soft Tissue" → Normal contrast
   - [ ] Click "Brain Preset" → Brain tissue highlighted
   - [ ] Click "Liver Preset" → Liver detail highlighted

**Expected Behavior**:
```
Presets change volume appearance quickly (< 100ms)
Window/level sliders continuously adjust image
All presets have distinct visual appearance
```

---

### Phase 3C: MPR Widget Testing (20 minutes)

Test the 4-panel Multiplanar Reconstruction view.

#### Test 3C.1: MPR Layout
**Steps**:
1. In right sidebar, find "MPR Controls" panel
2. Click "Show MPR" or similar button
3. Verify 4-panel grid appears with:
   - [ ] Top-left: Axial view (red crosshair)
   - [ ] Top-right: Sagittal view (green crosshair)
   - [ ] Bottom-left: Coronal view (blue crosshair)
   - [ ] Bottom-right: 3D view (showing intersection point)

**Expected Layout**:
```
┌─────────────┬──────────────┐
│   Axial     │  Sagittal    │
│  (Red ⊕)    │  (Green ⊕)   │
├─────────────┼──────────────┤
│   Coronal   │   3D View    │
│  (Blue ⊕)   │  (Yellow •)  │
└─────────────┴──────────────┘

Crosshairs all intersect at same point in 3D space
```

#### Test 3C.2: Slice Navigation
**Steps**:
1. In each panel (Axial, Sagittal, Coronal), locate the slice slider
2. Move slider left/right
3. Observe:
   - [ ] Slice index updates (shows current/max)
   - [ ] Slice image changes in real-time
   - [ ] Other planes update automatically

**Expected Behavior**:
```
Slice updates: < 50ms
All planes synchronized: YES
No lag or delay: YES
Image quality maintained: YES
```

#### Test 3C.3: Interactive Crosshairs
**Steps**:
1. Click on any point in the Axial view
2. Observe:
   - [ ] Crosshair moves to clicked point
   - [ ] Sagittal view updates to show that vertical plane
   - [ ] Coronal view updates to show that horizontal plane
   - [ ] 3D view shows intersection point

3. Repeat by clicking in Sagittal and Coronal views

**Expected Behavior**:
```
Click-to-navigate works in all 3 planes
Updates are instant (< 50ms)
3D indicator shows correct intersection
All views stay synchronized
```

#### Test 3C.4: Orientation Markers
**Steps**:
1. Examine each panel corner for orientation markers
2. Verify markers are correct:
   - [ ] Axial: Shows "A/P" (anterior/posterior) and "L/R" (left/right)
   - [ ] Sagittal: Shows "A/P" and "S/I" (superior/inferior)
   - [ ] Coronal: Shows "L/R" and "S/I"

3. Rotate 3D volume with mouse
4. Observe orientation markers remain correct

**Expected Behavior**:
```
Markers visible and readable: YES
Markers match DICOM standard: YES
Markers update with rotation: YES
```

---

### Phase 3D: Measurement Tools Testing (25 minutes)

Test all 5 measurement types and their accuracy.

#### Test 3D.1: Distance Measurement
**Steps**:
1. In left sidebar, find "Measurements" button or right sidebar "Measurements" panel
2. Click "Distance Tool" (or activate with keyboard `D`)
3. In the 3D volume:
   - [ ] Click point 1 (red sphere appears)
   - [ ] Click point 2 (yellow sphere appears)
   - [ ] Measurement displays as line with distance value

**Expected Behavior**:
```
Tool activates: YES
First click shows red sphere: YES
Second click shows yellow sphere: YES
Distance displayed in mm: YES (e.g., "45.2 mm")
Line connects the two points: YES
Measurement saved automatically: YES
```

**Accuracy Test**:
```
Known distance: _________ mm (from test DICOM)
Measured distance: _________ mm
Error: _________ mm
Accuracy ±0.5mm: [ ] PASS [ ] FAIL
```

#### Test 3D.2: Angle Measurement
**Steps**:
1. Activate "Angle Tool"
2. Click 3 points:
   - [ ] Point 1 (red)
   - [ ] Vertex/corner (yellow) - this is the angle apex
   - [ ] Point 2 (blue)

**Expected Behavior**:
```
Three points create angle arc: YES
Angle value displayed (e.g., "45.2°"): YES
Arc visible between rays: YES
Measurement saved: YES
```

**Accuracy Test**:
```
Known angle: _________ degrees
Measured angle: _________ degrees
Error: _________ degrees
Accuracy ±0.1°: [ ] PASS [ ] FAIL
```

#### Test 3D.3: Area Measurement
**Steps**:
1. Activate "Area Tool"
2. Click 3+ points to create polygon
3. After 3rd point, area should display
4. Optional: Add more points to refine polygon shape

**Expected Behavior**:
```
Polygon renders in 3D: YES
Area calculated in mm²: YES
Value displayed (e.g., "1250 mm²"): YES
Polygon closes when finished: YES
Measurement saved: YES
```

**Accuracy Test**:
```
Known area: _________ mm²
Measured area: _________ mm²
Error: _________ mm² (±1%)
Accuracy ±1%: [ ] PASS [ ] FAIL
```

#### Test 3D.4: Volume Measurement
**Steps**:
1. Activate "Volume Tool"
2. Click multiple points around a region of interest
3. Tool should calculate enclosed volume

**Expected Behavior**:
```
Region selection works: YES
Volume calculated in mm³: YES
Value displayed (e.g., "5000 mm³"): YES
Measurement saved: YES
```

**Accuracy Test**:
```
Known volume: _________ mm³
Measured volume: _________ mm³
Error: _________ mm³ (±2%)
Accuracy ±2%: [ ] PASS [ ] FAIL
```

#### Test 3D.5: Hounsfield Unit Measurement
**Steps**:
1. Activate "Hounsfield (HU) Tool"
2. Click a point in the volume
3. HU value should display

**Expected Behavior**:
```
Single point click works: YES
HU value displayed (e.g., "-400 HU"): YES
Tissue type identified (e.g., "Lung"): YES
Measurement saved: YES
```

**Tissue Identification Check**:
```
Click on different tissue types and verify identification:
  Bone (bright white): _________ HU [ ] Air  [X] Bone  [ ] Soft  [ ] Liquid
  Lung (dark): _________ HU        [ ] Air  [ ] Bone  [ ] Soft  [ ] Liquid
  Soft tissue (gray): _________ HU  [X] Air  [ ] Bone  [ ] Soft  [ ] Liquid
  Liquid (dark): _________ HU       [ ] Air  [ ] Bone  [X] Soft  [ ] Liquid
```

#### Test 3D.6: Measurement List & Export
**Steps**:
1. After creating all 5 measurements, find "Measurements" panel
2. Verify all measurements listed with:
   - [ ] Measurement type (Distance, Angle, etc.)
   - [ ] Value with units
   - [ ] Timestamp
3. Click "Export" button
4. Test export formats:
   - [ ] JSON: File downloads as `.json`
   - [ ] CSV: File downloads as `.csv`
   - [ ] HTML: File downloads as `.html` (opens in new window)

**Expected Behavior**:
```
All 5 measurements in list: YES
Each with type, value, units: YES
Export button functional: YES
Exports contain all data: YES
File formats correct: YES
```

**Export Content Verification**:
```
JSON export contains:
  [ ] Array of measurement objects
  [ ] Each with type, value, units, timestamp
  [ ] Valid JSON structure

CSV export contains:
  [ ] Header row: Type, Value, Units, Timestamp
  [ ] One measurement per row
  [ ] Values properly comma-separated

HTML export contains:
  [ ] Table with all measurements
  [ ] Formatted nicely
  [ ] Browser renders correctly
```

#### Test 3D.7: Measurement Deletion & Keyboard Shortcuts
**Steps**:
1. Select a measurement in the list
2. Press `Backspace` or click "Delete" button
3. Measurement should be removed from list and from display

4. Test keyboard shortcut:
   - [ ] `D`: Activate Distance tool
   - [ ] `A`: Activate Angle tool (if configured)
   - [ ] `ESC`: Deactivate current tool

**Expected Behavior**:
```
Delete removes measurement: YES
Measurement disappears from 3D view: YES
Keyboard shortcuts work: YES
ESC properly deactivates tool: YES
```

---

### Phase 3E: Performance Profiling (30 minutes)

Measure and verify performance against targets.

#### Test 3E.1: Memory Usage
**Tools**: Chrome DevTools Memory tab

**Steps**:
1. Open DevTools (F12)
2. Go to Memory tab
3. Note initial memory usage
4. Load volume
5. Wait 30 seconds
6. Take heap snapshot
7. Record memory usage

**Expected Results**:
```
Initial memory:            _________ MB
After load:                _________ MB
After 30s idle:            _________ MB
Max observed:              _________ MB

Target: < 500 MB
✓ PASS if < 500 MB
✗ FAIL if > 500 MB

Memory leaks (increasing over time):
  [ ] None observed
  [ ] Minor (< 1MB/min)
  [ ] Major (> 1MB/min)
```

#### Test 3E.2: Load Time
**Tools**: Chrome DevTools Performance or Network tabs

**Steps**:
1. Open DevTools Network tab
2. Refresh page
3. Record time to "First Contentful Paint"
4. Record time to "Largest Contentful Paint"
5. Record time to Interactive

**Expected Results**:
```
First Contentful Paint:    _________ ms  (target: < 2000)
Largest Contentful Paint:  _________ ms  (target: < 3000)
Time to Interactive:       _________ ms  (target: < 4000)
```

#### Test 3E.3: Render Performance
**Tools**: Chrome DevTools Performance tab with FPS counter

**Steps**:
1. In browser, enable FPS meter (Chrome: Ctrl+Shift+P, type "FPS")
2. Rotate volume with mouse (slow continuous motion)
3. Record FPS for 10 seconds
4. Pan volume (continuous motion)
5. Record FPS for 10 seconds

**Expected Results**:
```
Rotation FPS:              _________ fps  (target: 50-60)
Panning FPS:               _________ fps  (target: 50-60)
Average FPS:               _________ fps  (target: > 50)

Frame drops observed:       [ ] None  [ ] Occasional  [ ] Frequent

✓ PASS if average > 50 FPS
✗ FAIL if average < 50 FPS
```

#### Test 3E.4: API Response Times
**Steps**:
1. Open DevTools Network tab
2. Load volume (monitor `/api/viewer/load-study`)
3. Navigate slices (monitor `/api/viewer/get-slice`)
4. Request measurements export (monitor `/api/measurements/study/*/export`)

**Expected Results**:
```
/load-study:               _________ ms  (target: < 3000)
/get-slice:                _________ ms  (target: < 1000)
/get-metadata:             _________ ms  (target: < 500)
/measurements/*/export:    _________ ms  (target: < 2000)

95th percentile response:   _________ ms  (target: < 3000)

✓ PASS if all < targets
✗ FAIL if any exceeds targets
```

#### Test 3E.5: UI Responsiveness
**Steps**:
1. With volume loaded, rapidly click buttons in UI
2. Try interactions while volume is loading
3. Create measurements while rotating
4. Switch between different tools rapidly

**Expected Behavior**:
```
UI remains responsive: YES
No freezing observed: YES
Buttons respond immediately: YES
Measurements create without delay: YES
Tool switches instant: YES
```

---

### Phase 3F: Cross-Browser Testing (15 minutes)

Test on multiple browsers if available.

#### Supported Browsers

| Browser | Version | Test URL | Status |
|---------|---------|----------|--------|
| Chrome | Latest | volumetric-viewer.html | [ ] PASS [ ] FAIL |
| Firefox | Latest | volumetric-viewer.html | [ ] PASS [ ] FAIL |
| Safari | Latest | volumetric-viewer.html | [ ] PASS [ ] FAIL |
| Edge | Latest | volumetric-viewer.html | [ ] PASS [ ] FAIL |

**Checks per Browser**:
- [ ] Page loads without errors
- [ ] 3D volume renders
- [ ] All controls responsive
- [ ] Measurements work
- [ ] No console errors
- [ ] Performance acceptable

**Browser-Specific Notes**:
```
Chrome:
  Issues: _____________________
  Performance: _________________

Firefox:
  Issues: _____________________
  Performance: _________________

Safari:
  Issues: _____________________
  Performance: _________________

Edge:
  Issues: _____________________
  Performance: _________________
```

---

### Phase 3G: Accessibility Testing (10 minutes)

Verify WCAG 2.1 AA compliance.

#### Test 3G.1: Keyboard Navigation
**Steps**:
1. Press `Tab` repeatedly to navigate through UI
2. Verify focus indicator visible at each step
3. Try keyboard shortcuts: `R`, `F`, `A`, `I`, `V`, `S`, `ESC`

**Expected Behavior**:
```
Tab navigation works: YES
Focus indicators visible: YES
All shortcuts respond: YES
Can access all features via keyboard: YES
```

#### Test 3G.2: Color Contrast
**Steps**:
1. Use browser's accessibility inspector (DevTools → Accessibility)
2. Check contrast ratios for:
   - [ ] Text vs background
   - [ ] UI buttons vs background
   - [ ] Active vs inactive states

**Expected Results**:
```
All text: WCAG AA (4.5:1) or better
Buttons: WCAG AA (3:1) or better
UI Controls: Clearly distinguishable

✓ PASS if all meet AA standards
```

#### Test 3G.3: Screen Reader Compatibility
**Steps** (if screen reader available):
1. Enable screen reader (NVDA, JAWS, or built-in)
2. Navigate page elements
3. Verify alt text for images
4. Check ARIA labels on buttons

**Expected Behavior**:
```
All buttons have accessible labels: YES
Images have alt text or aria-label: YES
Form inputs labeled properly: YES
Navigation structure logical: YES
```

---

## 4. ISSUE TRACKING

### Critical Issues (Blocks Release)
```
Issue #: _______
Title: _____________________________
Description: _____________________________
Severity: CRITICAL
Status: [ ] NEW [ ] IN PROGRESS [ ] RESOLVED
```

### Major Issues (Needs Fix)
```
Issue #: _______
Title: _____________________________
Description: _____________________________
Severity: MAJOR
Status: [ ] NEW [ ] IN PROGRESS [ ] RESOLVED
```

### Minor Issues (Nice to Have)
```
Issue #: _______
Title: _____________________________
Description: _____________________________
Severity: MINOR
Status: [ ] NEW [ ] IN PROGRESS [ ] RESOLVED
```

---

## 5. SUMMARY & SIGN-OFF

### Test Execution Summary
```
Date Started: _____________________
Date Completed: _____________________
Total Time: _____________________
Tester(s): _____________________

Total Tests: 25+
Tests PASSED: _______
Tests FAILED: _______
Tests SKIPPED: _______
Pass Rate: _______%

Critical Issues: _______
Major Issues: _______
Minor Issues: _______
```

### Performance Summary
```
Memory Usage:             [ ] PASS [ ] FAIL
Load Time:                [ ] PASS [ ] FAIL
Render Performance (FPS): [ ] PASS [ ] FAIL
API Response Times:       [ ] PASS [ ] FAIL
UI Responsiveness:        [ ] PASS [ ] FAIL
```

### Sign-Off
```
[ ] Dev 1 Approves Integration Testing Complete
[ ] Dev 2 Approves Integration Testing Complete
[ ] All Critical Issues Resolved
[ ] Phase 1 Ready for Deployment

Approved by: ____________________________
Date: ____________________________
Time: ____________________________
```

---

## 6. APPENDIX: QUICK REFERENCE

### Test Commands
```bash
# Run automated tests
python test_integration.py

# Check API health
curl http://localhost:8000/api/viewer/health

# Check cache status
curl http://localhost:8000/api/viewer/cache-status

# View test report
cat integration_test_report.txt
```

### Troubleshooting

#### "API not responding"
```
1. Check FastAPI server: python app/main.py
2. Verify port 8000 is not in use: netstat -tlnp | grep 8000
3. Check firewall settings
4. View server logs for errors
```

#### "Volume not rendering"
```
1. Verify study data loaded: Check console for "/load-study" response
2. Check GPU if using hardware acceleration
3. Verify Three.js library loaded (check Network tab)
4. Check browser console for WebGL errors
```

#### "Measurements not saving"
```
1. Verify database connection: Check server logs
2. Check API response: DevTools Network tab
3. Verify /api/measurements/create endpoint responds with 200
4. Check measurement data validation
```

#### "Performance slow"
```
1. Check memory usage (DevTools Memory tab)
2. Check FPS (Chrome FPS meter)
3. Look for memory leaks (heap snapshots over time)
4. Check network waterfalls for slow API calls
5. Profile CPU usage (DevTools Performance)
```

### Performance Baseline
```
These are the target metrics all measurements should achieve:

Volume Load Time:    Target 1-3s,   Measured: _______ s
Slice Render Time:   Target <50ms,  Measured: _______ ms
MPR Update Time:     Target <50ms,  Measured: _______ ms
Measurement Create:  Target <100ms, Measured: _______ ms
API Response (95%):  Target <3s,    Measured: _______ s
FPS (avg):           Target >50,    Measured: _______ fps
Memory Usage (max):  Target <500MB, Measured: _______ MB

If any measurement exceeds target, investigate and document issue.
```

---

## 7. NEXT STEPS

### After Phase 1 Testing Complete

1. **Document Results**
   - [ ] Fill out all test results
   - [ ] Create test report with metrics
   - [ ] Document any issues found

2. **Fix Issues** (if any)
   - [ ] Critical: Fix before release
   - [ ] Major: Fix or document workaround
   - [ ] Minor: Add to Phase 2 backlog

3. **Update Task List**
   - [ ] Mark TASK 1.2.4 as COMPLETE
   - [ ] Update Phase 1 status to 100%
   - [ ] Begin Phase 2 Planning

4. **Prepare Phase 2**
   - [ ] MONAI environment setup (TASK 2.1.1)
   - [ ] Segmentation API endpoints (TASK 2.1.2)
   - [ ] ML model integration

---

**Document Version**: 1.0  
**Last Updated**: [Current Session]  
**Status**: ⏸️ IN PROGRESS - Ready for execution
