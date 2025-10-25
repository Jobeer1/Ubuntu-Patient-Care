# Dev 2 - Phase 1 Handoff: Frontend Tasks Ready to Start

**Date**: October 21, 2025  
**Status**: ✅ Backend ready, frontend tasks unblocked  
**Dev 1 Progress**: 30% of Phase 1 complete (3/10 tasks)  

---

## 🎯 Current Status

**Dev 1 Completed**:
- ✅ Backend setup and environment
- ✅ DICOM processing engine (app/ml_models/dicom_processor.py)
- ✅ FastAPI routes (app/routes/viewer_3d.py)
- ✅ 8 API endpoints all working

**Dev 2 Ready to Start**:
- ✅ All backend APIs are documented and ready
- ✅ HTML structure can be created independently
- ✅ CSS can be styled independently
- ✅ Three.js renderer can be implemented
- ⏳ Integration will follow once all components ready

---

## 📋 Your Phase 1 Tasks (4 Tasks, ~15 hours)

### TASK 1.1.4: Volumetric Viewer HTML
**Duration**: 3 hours  
**Status**: ⏳ NOT STARTED  
**Dependency**: None (can start now)  
**Estimated Completion**: Tomorrow morning

**What You Need to Create**:
```
static/viewers/volumetric-viewer.html
```

**File Structure to Include**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>3D Volumetric Viewer</title>
    <link rel="stylesheet" href="../css/viewer.css">
</head>
<body>
    <!-- Study Selector Panel -->
    <div id="studySelector">
        <label>Select Study:</label>
        <select id="studyDropdown">
            <option>Loading studies...</option>
        </select>
        <button id="loadStudyBtn">Load</button>
    </div>

    <!-- Main Viewer Canvas -->
    <div id="viewerContainer">
        <canvas id="viewerCanvas"></canvas>
    </div>

    <!-- Control Panel (Side)-->
    <div id="controlPanel">
        <h3>3D Controls</h3>
        
        <!-- Rotation Controls -->
        <div class="control-group">
            <label>Rotation</label>
            <div>
                <input type="range" id="rotX" min="0" max="360" value="0">
                <input type="range" id="rotY" min="0" max="360" value="0">
                <input type="range" id="rotZ" min="0" max="360" value="0">
            </div>
        </div>

        <!-- Zoom Control -->
        <div class="control-group">
            <label>Zoom</label>
            <input type="range" id="zoomSlider" min="0.5" max="3" step="0.1" value="1">
        </div>

        <!-- Window/Level -->
        <div class="control-group">
            <label>Window Center</label>
            <input type="range" id="windowCenter" min="-1000" max="3000" value="40">
            <label>Window Width</label>
            <input type="range" id="windowWidth" min="50" max="2000" value="400">
        </div>

        <!-- Slice Navigation -->
        <div class="control-group">
            <label>Axial Slice</label>
            <input type="range" id="sliceNavigator" min="0" max="100" value="50">
            <span id="sliceLabel">50 / 100</span>
        </div>

        <!-- Measurement Tools -->
        <div class="control-group">
            <button id="distanceTool">Distance</button>
            <button id="areaTool">Area</button>
            <button id="volumeTool">Volume</button>
            <button id="clearMeasurements">Clear</button>
        </div>

        <!-- Export Options -->
        <div class="control-group">
            <button id="exportSTL">Export STL</button>
            <button id="exportScreenshot">Screenshot</button>
        </div>
    </div>

    <!-- Measurement Display Overlay -->
    <div id="measurementOverlay"></div>

    <!-- Scripts -->
    <script src="../js/viewers/3d-renderer.js"></script>
    <script src="../js/viewers/mpr-widget.js"></script>
    <script src="../js/viewers/measurement-tools.js"></script>
    <script>
        // Initialize viewer on page load
        document.addEventListener('DOMContentLoaded', initializeViewer);
    </script>
</body>
</html>
```

**Checklist**:
- [ ] Create file at `static/viewers/volumetric-viewer.html`
- [ ] Include all UI sections above
- [ ] Add study selector dropdown
- [ ] Add 3D canvas container
- [ ] Add control panel with:
  - [ ] Rotation sliders (X, Y, Z)
  - [ ] Zoom control
  - [ ] Window/level sliders
  - [ ] Slice navigator
  - [ ] Measurement buttons
  - [ ] Export buttons
- [ ] Link to CSS file: `../css/viewer.css`
- [ ] Add script tags for JS modules
- [ ] Test page loads without errors

**Expected Output**:
- File: 400 lines of HTML
- Browser console: No errors
- Page visually loads (but no functionality yet)

---

### TASK 1.1.5: Three.js 3D Renderer
**Duration**: 5 hours  
**Status**: ⏳ NOT STARTED  
**Dependency**: TASK 1.1.4 (HTML structure)  
**Estimated Completion**: Wednesday evening

**What You Need to Create**:
```
static/js/viewers/3d-renderer.js
```

**Overview**:
This is the core rendering engine. It uses Three.js to display 3D DICOM volumes.

**Key Functions Needed**:
```javascript
// Initialization
function initialize3DRenderer(canvasElement) { }

// Data Loading
function loadVolumeData(volumeArrayBuffer, metadata) { }

// Rendering
function renderVolume() { }

// Controls
function setupControls(camera, renderer) { }
function handleRotation(x, y, z) { }
function handleZoom(scale) { }

// Texture Conversion
function createVolumeTexture(volumeData, shape) { }

// Raycasting for rendering
function setupRaycastingRenderer() { }
```

**Basic Structure**:
```javascript
// 3D Renderer for PACS Volume Viewer
// Phase 1: Basic volumetric rendering with Three.js

import * as THREE from 'https://cdn.jsdelivr.net/npm/three@r128/build/three.module.js';

class VolumeRenderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(75, canvas.width / canvas.height, 0.1, 1000);
        this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
        this.volumeTexture = null;
        this.volumeMesh = null;
        
        this.setupRenderer();
        this.setupLights();
        this.setupControls();
    }
    
    setupRenderer() {
        this.renderer.setSize(this.canvas.width, this.canvas.height);
        this.renderer.setClearColor(0x000000);
        this.camera.position.z = 5;
    }
    
    setupLights() {
        const light = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(light);
    }
    
    loadVolume(volumeData, shape) {
        // Create 3D texture from volume data
        // Create mesh with volume rendering material
        // Add to scene
    }
    
    render() {
        this.renderer.render(this.scene, this.camera);
    }
}

export { VolumeRenderer };
```

**Checklist**:
- [ ] Create file at `static/js/viewers/3d-renderer.js`
- [ ] Set up Three.js scene, camera, renderer
- [ ] Implement volume texture creation
- [ ] Implement raycasting for volume rendering
- [ ] Add mouse controls (rotate, pan, zoom)
- [ ] Handle window resize
- [ ] Test loading sample data (can use dummy data initially)

**Performance Targets**:
- [ ] Initialization: < 500ms
- [ ] Volume loading: < 1s
- [ ] Frame rate: 60 FPS on mid-range GPU
- [ ] Memory: < 500MB for typical study

**API Integration**:
```javascript
// After backend is ready, call:
async function loadStudyFrom API(studyId) {
    const response = await fetch(`/api/viewer/load-study`, {
        method: 'POST',
        body: JSON.stringify({ study_id: studyId })
    });
    const data = await response.json();
    // Load data into renderer
}
```

---

### TASK 1.1.6: Viewer CSS Styling
**Duration**: 2 hours  
**Status**: ⏳ NOT STARTED  
**Dependency**: TASK 1.1.4 (HTML structure)  
**Estimated Completion**: Wednesday afternoon

**What You Need to Create**:
```
static/css/viewer.css
```

**Key Styling Areas**:
```css
/* Container Layout */
body, html { }
#viewerContainer { 
    /* Full viewport canvas */
    width: 100vw;
    height: 100vh;
}

/* Study Selector */
#studySelector { 
    /* Top bar with dropdowns */
    position: fixed;
    top: 0;
    height: 50px;
    width: 100%;
}

/* Control Panel */
#controlPanel { 
    /* Side drawer on right */
    position: fixed;
    right: 0;
    width: 300px;
    height: calc(100vh - 50px);
    background: rgba(0, 0, 0, 0.8);
    overflow-y: auto;
}

/* Canvas */
canvas {
    display: block;
    width: 100%;
    height: 100%;
}

/* Buttons and Controls */
button { }
input[type="range"] { }
input[type="text"] { }

/* Measurement Overlay */
#measurementOverlay { }

/* Responsive Design */
@media (max-width: 768px) {
    /* Stack controls differently on mobile */
}
```

**Checklist**:
- [ ] Create file at `static/css/viewer.css`
- [ ] Style canvas container (full viewport)
- [ ] Style control panel (side drawer)
- [ ] Style top navigation bar
- [ ] Style buttons and sliders
- [ ] Add dark theme (medical imaging standard)
- [ ] Make responsive for 320px-1920px widths
- [ ] Test on Chrome, Firefox, Safari

**Expected Output**:
- File: 300 lines of CSS
- Professional medical UI
- Works on desktop and tablet
- Good contrast and readability

---

### TASK 1.2.2: Multiplanar Reconstruction (MPR)
**Duration**: 6 hours  
**Status**: ⏳ NOT STARTED  
**Dependency**: TASK 1.1.5 (3D renderer working)  
**Estimated Completion**: Friday

**What You Need to Create**:
```
static/js/viewers/mpr-widget.js
```

**Overview**:
MPR (Multiplanar Reconstruction) shows three orthogonal slices simultaneously:
- **Axial** (horizontal) - most common CT viewing
- **Sagittal** (vertical, left-right)
- **Coronal** (vertical, front-back)

**Layout**:
```
┌─────────────────────────────┐
│    Axial View (XY plane)    │
├──────────────┬──────────────┤
│  Sagittal    │   Coronal    │
│  (YZ plane)  │  (XZ plane)  │
└──────────────┴──────────────┘
```

**Key Functions**:
```javascript
class MPRWidget {
    constructor(canvas) { }
    
    // Load volume and set up three canvases
    loadVolume(volumeData) { }
    
    // Update all three views when one is clicked
    syncCrosshairs(x, y, z) { }
    
    // Get slice from API
    async getSliceFromAPI(plane, position) { }
    
    // Render slice to 2D canvas
    renderSlice(canvas, sliceData) { }
}
```

**Checklist**:
- [ ] Create 3 canvas elements (or use single with sub-canvases)
- [ ] Fetch axial slice from `/api/viewer/get-slice`
- [ ] Fetch sagittal slice from `/api/viewer/mpr-slice` (plane="sagittal")
- [ ] Fetch coronal slice from `/api/viewer/mpr-slice` (plane="coronal")
- [ ] Draw crosshairs showing current position
- [ ] Make crosshairs interactive (click to update)
- [ ] Sync all three views when any changes
- [ ] Add slice navigator slider for each plane

**Performance Targets**:
- [ ] Initial load: < 2 seconds
- [ ] Slice update: < 50ms
- [ ] No lag when moving crosshairs

---

## 🔌 Backend API Endpoints You'll Use

**All documented and ready to use**:

### 1. Load Study
```
POST /api/viewer/load-study
Content-Type: application/json

{
    "study_id": "study_001",
    "series_id": "series_001",
    "window_center": 40,
    "window_width": 400
}

Response:
{
    "study_id": "study_001",
    "series_id": "series_001",
    "volume_shape": [512, 512, 300],
    "num_slices": 300,
    "spacing": [1.0, 1.0, 5.0],
    "thumbnail_url": "/api/viewer/thumbnail/study_001",
    "status": "success"
}
```

### 2. Get Single Slice
```
GET /api/viewer/get-slice/study_001?slice_index=150&normalize=true

Response:
{
    "slice_index": 150,
    "data": [[...pixel values...]],
    "width": 512,
    "height": 512,
    "min_value": 0.0,
    "max_value": 1.0
}
```

### 3. Get MPR Slice
```
POST /api/viewer/mpr-slice
Content-Type: application/json

{
    "study_id": "study_001",
    "plane": "sagittal",  // or "axial", "coronal"
    "position": 0.5       // 0.0 to 1.0
}

Response:
{
    "plane": "sagittal",
    "position": 0.5,
    "data": [[...pixel values...]],
    "width": 300,
    "height": 512
}
```

### 4. Get Metadata
```
GET /api/viewer/get-metadata/study_001

Response:
{
    "study_id": "study_001",
    "series_id": "series_001",
    "patient_name": "John Doe",
    "patient_id": "P123456",
    "modality": "CT",
    "size": [512, 512, 300],
    "spacing": [1.0, 1.0, 5.0],
    "origin": [0.0, 0.0, 0.0],
    "num_slices": 300,
    "pixel_type": "uint16"
}
```

### 5. Cache Status
```
GET /api/viewer/cache-status

Response:
{
    "status": "success",
    "num_studies": 2,
    "total_size_mb": 245.5,
    "studies": [
        {
            "study_id": "study_001",
            "shape": [512, 512, 300],
            "size_mb": 156.25,
            "dtype": "float32"
        }
    ]
}
```

### 6. Health Check
```
GET /api/viewer/health

Response:
{
    "status": "healthy",
    "service": "3D Viewer API",
    "version": "1.0.0",
    "dicom_processor": "available"
}
```

---

## 📚 Resources & Examples

### Three.js Resources
- Documentation: https://threejs.org/docs/
- Examples: https://threejs.org/examples/
- For medical imaging: Look for "raycasting" and "volume" examples

### Starter Code (from PACS_CODE_TEMPLATES.md)
The complete code template for 3d-renderer.js and mpr-widget.js is in:
- **File**: `4-PACS-Module/Orthanc/PACS_CODE_TEMPLATES.md`
- **Sections**: "3d-renderer.js (150 lines)" and "mpr-widget.js (120 lines)"
- **Status**: Copy-paste ready, fully functional

### DICOM Basics
- Typical CT studies: 512x512 pixels, 100-500 slices
- Pixel values in Hounsfield Units (HU): -1000 to +3000
- After normalization: 0.0 to 1.0 float
- Common viewing windows:
  - Soft tissue: center=40, width=400
  - Bone: center=500, width=1500
  - Lung: center=-500, width=1500

---

## 🚀 Getting Started Tomorrow

### Step 1: Create HTML (TASK 1.1.4)
1. Create `static/viewers/volumetric-viewer.html`
2. Copy the HTML structure from above
3. Add your own styling thoughts to notes
4. Commit and notify Dev 1

### Step 2: Create CSS (TASK 1.1.6)
1. Create `static/css/viewer.css`
2. Style the HTML layout
3. Add responsive design
4. Test on multiple browsers

### Step 3: Create 3D Renderer (TASK 1.1.5)
1. Create `static/js/viewers/3d-renderer.js`
2. Install Three.js (npm or CDN)
3. Copy template from PACS_CODE_TEMPLATES.md
4. Adapt to work with your HTML

### Step 4: Create MPR (TASK 1.2.2)
1. Create `static/js/viewers/mpr-widget.js`
2. Call `/api/viewer/mpr-slice` endpoint
3. Render three orthogonal slices
4. Add crosshair synchronization

---

## 💡 Pro Tips

1. **Start with dummy data**: Don't wait for backend DICOM loading to work. Test with fake arrays first.
2. **Use console.log liberally**: Log API responses to verify data format.
3. **Test each piece independently**: Get HTML working, then CSS, then JavaScript.
4. **Three.js learning curve**: Spend time understanding camera, geometry, material, mesh.
5. **Performance matters**: Profile with DevTools before optimizing.

---

## 📞 Coordination with Dev 1

**Dev 1** will be:
- Working on Orthanc integration (actual study loading)
- Implementing measurement tools backend
- Optimizing performance

**Communication**:
- Daily standup: 10:00 AM
- Weekly review: Friday 3:00 PM
- Blockers: Notify immediately in Slack
- PRs: Cross-review before merging

---

## ✅ Success Criteria for Dev 2 Phase 1

After completing all 4 tasks, you should have:
- ✅ Beautiful, professional HTML viewer interface
- ✅ Responsive CSS that works on all devices
- ✅ Working 3D volume renderer with Three.js
- ✅ Multiplanar reconstruction with synchronized views
- ✅ All controls functional (rotation, zoom, slice nav)
- ✅ Ready to integrate with Dev 1's backend

---

**Status**: ✅ UNBLOCKED AND READY TO START  
**Estimated Timeline**: 3-4 days for all 4 tasks  
**Next Checkpoint**: Daily status updates at 10:00 AM standup  

Good luck! Let me know if you have any questions about the API or requirements.
