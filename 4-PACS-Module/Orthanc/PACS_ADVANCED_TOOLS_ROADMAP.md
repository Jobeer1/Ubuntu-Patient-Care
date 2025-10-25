# PACS Advanced Tools - Implementation Roadmap

## Executive Summary

Your Orthanc PACS system currently has **basic viewing capabilities** but is **missing advanced diagnostic tools**. This document outlines what exists, what's needed, and implementation strategies.

---

## 📊 CURRENT STATE ANALYSIS

### ✅ What You HAVE

#### 1. **Core Infrastructure**
- ✅ Orthanc PACS Server (orthanc-server/)
- ✅ OHIF Plugin (orthanc-ohif/) - Basic DICOM Web Viewer
- ✅ Stone Framework (orthanc-stone/) - Lightweight rendering
- ✅ GDCM Support (orthanc-gdcm/) - DICOM format handling
- ✅ Authentication & Access Control System
- ✅ Medical Reporting Module
- ✅ User Role-Based Access (16 permissions)

#### 2. **Current Viewing Capabilities**
- ✅ Basic 2D DICOM image display
- ✅ Multi-slice navigation
- ✅ Window/Level adjustment
- ✅ Pan, zoom, rotate operations
- ✅ OHIF Viewer integration
- ✅ Basic measurements

#### 3. **Data Management**
- ✅ Patient/Study/Series organization
- ✅ DICOM metadata indexing (orthanc-indexer/)
- ✅ Object storage support (orthanc-object-storage/)
- ✅ Database backend (SQLite)
- ✅ Authorization layer

---

## ❌ What You're MISSING

### Critical Advanced Tools (Not Implemented)

| Feature | Status | Priority | Complexity |
|---------|--------|----------|------------|
| **3D Volumetric Rendering** | ❌ Missing | CRITICAL | High |
| **Multiplanar Reconstruction (MPR)** | ❌ Missing | CRITICAL | High |
| **Automatic Vessel Segmentation** | ❌ Missing | High | Very High |
| **Cardiac CT Analysis** | ❌ Missing | High | Very High |
| **Coronary Artery Analysis** | ❌ Missing | High | Very High |
| **Calcium Scoring** | ❌ Missing | High | Very High |
| **CT Perfusion Analysis** | ❌ Missing | Medium | Very High |
| **MR Perfusion Analysis** | ❌ Missing | Medium | Very High |
| **MR Diffusion Analysis** | ❌ Missing | Medium | Very High |
| **Digital Mammography Tools** | ❌ Missing | Medium | High |
| **Structured Reporting Templates** | ⚠️ Partial | High | Medium |
| **Speech Recognition Integration** | ❌ Missing | Medium | Medium |
| **Advanced Display Protocols** | ❌ Missing | Medium | Medium |
| **Zero-Footprint Viewer** | ⚠️ Partial | Low | Medium |

---

## 🎯 IMPLEMENTATION PLAN

### Phase 1: Core Advanced Viewing (Weeks 1-2)
**Goal**: Enable 3D viewing and multi-planar reconstruction

#### 1.1 Install Three.js for 3D Rendering
```bash
cd mcp-server
npm install three
npm install @react-three/fiber @react-three/drei
npm install dicom-parser
npm install cornerstone3d
```

**Files to Create**:
- `mcp-server/app/routes/viewer_3d.py` (API endpoints)
- `mcp-server/static/viewers/volumetric-viewer.html` (UI)
- `mcp-server/static/js/viewers/3d-renderer.js` (Three.js implementation)

#### 1.2 Add Python Medical Imaging Libraries
```bash
pip install SimpleITK
pip install nibabel
pip install scipy
pip install scikit-image
pip install numpy
```

**Purpose**:
- SimpleITK: 3D image processing and reconstruction
- nibabel: Neuroimaging file formats
- scikit-image: Advanced image processing
- scipy: Mathematical operations

---

### Phase 2: ML-Based Segmentation (Weeks 3-4)
**Goal**: Implement vessel segmentation and organ detection

#### 2.1 Install Deep Learning Framework
```bash
pip install torch torchvision
pip install onnx onnxruntime
pip install monai  # Medical Open Network for AI
pip install medsegpy
```

**Pre-trained Models to Download**:
- Vessel Segmentation: `retinal-vessel-segmentation` (MONAI)
- Organ Segmentation: `spleen-segmentation` (MONAI)
- Coronary Detection: `coronary-artery-segmentation.onnx`

#### 2.2 Create ML Pipeline
```
mcp-server/app/ml_models/
├── segmentation/
│   ├── vessel_segmentation.py
│   ├── organ_segmentation.py
│   └── coronary_detection.py
├── analysis/
│   ├── cardiac_analysis.py
│   ├── calcium_scoring.py
│   └── perfusion_analysis.py
└── models/ (download pre-trained weights)
```

---

### Phase 3: Specialized Analysis Tools (Weeks 5-6)
**Goal**: Implement domain-specific analysis modules

#### 3.1 Cardiac CT Analysis
```python
# File: mcp-server/app/routes/cardiac_analysis.py

Features:
- Coronary artery detection and quantification
- Left/right ventricle measurement
- Ejection fraction calculation
- Cardiac motion analysis
- Wall thickness measurement
```

#### 3.2 Calcium Scoring
```python
# File: mcp-server/app/routes/calcium_scoring.py

Features:
- Automatic CAC detection
- Agatston score calculation
- Risk stratification
- Percentile ranking
- Serial comparison
```

#### 3.3 Perfusion Analysis
```python
# File: mcp-server/app/routes/perfusion_analysis.py

Features:
- CT perfusion maps generation
- MR perfusion analysis
- Time-intensity curves
- Blood flow quantification
- Delay map computation
```

---

### Phase 4: Reporting & Templates (Weeks 7-8)
**Goal**: Advanced structured reporting

#### 4.1 Reporting Templates
```
mcp-server/app/templates/
├── cardiac_ct_template.json
├── mammography_template.json
├── neuro_ct_template.json
├── lung_screening_template.json
└── abdominal_ct_template.json
```

#### 4.2 Speech Recognition Integration
```bash
pip install google-cloud-speech
pip install azure-cognitiveservices-speech
pip install pyaudio
```

#### 4.3 Template Engine
```python
# File: mcp-server/app/routes/reporting.py

Features:
- Template creation/editing
- Auto-population from measurements
- Speech-to-text dictation
- Report generation
- PDF export
```

---

### Phase 5: Enterprise Viewer (Weeks 9-10)
**Goal**: Zero-footprint web-based viewer

#### 5.1 Progressive Web App (PWA)
```
mcp-server/static/
├── service-worker.js
├── manifest.json
├── offline-viewer.html
└── offline-cache-strategy.js
```

#### 5.2 WASM Support (Optional but Recommended)
```bash
npm install emscripten
# Compile GDCM to WebAssembly for client-side processing
```

---

## 📋 FILE-BY-FILE IMPLEMENTATION GUIDE

### Backend Files to Create

#### 1. **viewer_3d.py** (Advanced 3D Viewing API)
```python
# Location: mcp-server/app/routes/viewer_3d.py
# Size: ~300 lines
# Purpose: API endpoints for 3D rendering

Routes:
- POST /viewer/3d/load - Load DICOM series for 3D
- GET /viewer/3d/volume/{study_id} - Get volumetric data
- POST /viewer/3d/mpr - Generate MPR reconstructions
- POST /viewer/3d/render-settings - Apply rendering settings
- GET /viewer/3d/measurements/{study_id} - Get measurements

Key Libraries:
- SimpleITK for volume processing
- numpy for data manipulation
- scipy for interpolation
```

#### 2. **segmentation_engine.py** (ML Segmentation)
```python
# Location: mcp-server/app/ml_models/segmentation_engine.py
# Size: ~400 lines
# Purpose: Handle automatic segmentation

Functions:
- segment_vessels(volume) - Vessel extraction
- segment_organs(volume) - Organ detection
- detect_coronary(volume) - Coronary artery detection
- apply_threshold(volume, min, max) - Threshold operations

Dependencies:
- MONAI for pre-trained models
- ONNX Runtime for inference
- PyTorch for model execution
```

#### 3. **cardiac_analyzer.py** (Cardiac Analysis)
```python
# Location: mcp-server/app/routes/cardiac_analyzer.py
# Size: ~350 lines
# Purpose: Cardiac-specific measurements

Functions:
- compute_ejection_fraction(lvot, lv_volume)
- measure_wall_thickness(roi, segmentation)
- analyze_coronary_stenosis(vessel_points)
- calculate_cardiac_function_indices()

Outputs:
- Measurement reports
- Risk assessment scores
- Comparison with prior studies
```

#### 4. **calcium_scoring.py** (Coronary Calcium Scoring)
```python
# Location: mcp-server/app/routes/calcium_scoring.py
# Size: ~250 lines
# Purpose: CAC score calculation

Features:
- Auto-detect calcifications
- Agatston score calculation
- Risk stratification
- Volume/mass scoring
- 10-year risk prediction

Output Format:
{
  "agatston_score": 254,
  "volume_score": 180,
  "mass_score": 89,
  "risk_category": "moderate",
  "percentile_rank": 72,
  "framingham_risk": "8.5%"
}
```

#### 5. **perfusion_analyzer.py** (Perfusion Analysis)
```python
# Location: mcp-server/app/routes/perfusion_analyzer.py
# Size: ~300 lines
# Purpose: Dynamic perfusion imaging analysis

Features:
- Extract time-density curves
- Calculate blood flow parameters
- Generate perfusion maps
- Mean transit time (MTT)
- Cerebral blood volume (CBV)

Output:
- Parametric maps
- Vessel time curves
- Quantitative metrics
```

#### 6. **mammography_tools.py** (Digital Mammography)
```python
# Location: mcp-server/app/routes/mammography_tools.py
# Size: ~300 lines
# Purpose: Mammography-specific tools

Features:
- Lesion detection assistance
- Microcalcification analysis
- Density assessment (BI-RADS)
- Comparison tools
- CAD (Computer-Aided Detection)

Tools:
- Zoom and magnification
- Annotation tools
- Density overlay
```

#### 7. **reporting_engine.py** (Advanced Reporting)
```python
# Location: mcp-server/app/routes/reporting_engine.py
# Size: ~400 lines
# Purpose: Structured reporting with templates

Features:
- Template management
- Auto-population from measurements
- Speech recognition integration
- Report generation
- PDF export
- Database storage

Templates Included:
- Cardiac CT
- Lung Screening
- Neuro CT
- Abdominal CT
- Mammography
```

### Frontend Files to Create

#### 1. **volumetric-viewer.html** (3D Viewer Interface)
```html
<!-- Location: mcp-server/static/viewers/volumetric-viewer.html -->
<!-- Size: ~400 lines -->

Features:
- 3D volume rendering
- Slice slider controls
- Rotation/pan/zoom
- Measurement tools
- Segmentation overlay display
- Real-time statistics
```

#### 2. **3d-renderer.js** (Three.js Implementation)
```javascript
// Location: mcp-server/static/js/viewers/3d-renderer.js
// Size: ~500 lines

Functions:
- initializeScene() - Set up Three.js scene
- loadVolume(data) - Load DICOM volume
- applyVolumeRendering() - Render as 3D
- generateMPR(plane) - Create multiplanar views
- addSegmentationOverlay() - Show segmentation
- handleInteraction() - User input handling
```

#### 3. **mpr-widget.js** (Multiplanar Reconstruction)
```javascript
// Location: mcp-server/static/js/viewers/mpr-widget.js
// Size: ~300 lines

Features:
- Axial, sagittal, coronal views
- Synchronized cursor
- Interactive plane manipulation
- Link to 3D view
- Measurement integration
```

#### 4. **measurement-tools.js** (Advanced Measurements)
```javascript
// Location: mcp-server/static/js/viewers/measurement-tools.js
// Size: ~300 lines

Tools:
- Distance measurement
- Area measurement
- Volume measurement
- Angle measurement
- Density histogram
- ROI analysis
- Automatic spine measurement
```

#### 5. **segmentation-overlay.js** (Display Segmentation)
```javascript
// Location: mcp-server/static/js/viewers/segmentation-overlay.js
// Size: ~250 lines

Features:
- Render segmentation masks
- Color mapping (organs, vessels)
- Opacity control
- Toggle visibility
- Extract ROI statistics
```

---

## 🛠️ Installation & Setup Instructions

### Step 1: Backend Dependencies
```bash
cd 4-PACS-Module/Orthanc/mcp-server

# Medical imaging libraries
pip install SimpleITK scikit-image scipy nibabel

# Deep learning (for segmentation)
pip install torch torchvision
pip install monai onnxruntime

# Speech recognition (for dictation)
pip install google-cloud-speech azure-cognitiveservices-speech

# Reporting
pip install reportlab python-pptx

# Data processing
pip install pandas openpyxl
```

### Step 2: Frontend Dependencies
```bash
npm install three @react-three/fiber @react-three/drei
npm install cornerstone3d cornerstone-wado-image-loader
npm install dicom-parser dcmjs
npm install plotly.js chart.js
```

### Step 3: Download Pre-trained Models
```bash
# Create models directory
mkdir -p mcp-server/app/ml_models/pretrained/

# Download segmentation models from MONAI Model Zoo
python -c "
import monai
monai.apps.download('spleen_segmentation_3d_tc', './ml_models/pretrained/')
monai.apps.download('pancreas_ct_segmentation_3d', './ml_models/pretrained/')
"
```

### Step 4: Create API Routes
```bash
# Copy the route files from below to mcp-server/app/routes/
# Update __init__.py to include new routes
```

### Step 5: Update Web Interface
```bash
# Create new viewer pages
# Add navigation menu items
# Register new endpoints
```

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│           ENHANCED PACS SYSTEM ARCHITECTURE            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  FRONTEND LAYER                                         │
│  ├─ Basic 2D Viewer (OHIF)                              │
│  ├─ 3D Volumetric Viewer (Three.js)                     │
│  ├─ MPR Widget (Axial/Sagittal/Coronal)                 │
│  ├─ Measurement Tools                                   │
│  ├─ Segmentation Overlay                                │
│  └─ Reporting Interface                                 │
│                                                         │
│  ↓ REST API                                             │
│                                                         │
│  API LAYER (mcp-server/app/routes/)                     │
│  ├─ /viewer/* (basic viewing)                           │
│  ├─ /viewer_3d/* (3D viewing)                           │
│  ├─ /analysis/cardiac (cardiac analysis)                │
│  ├─ /analysis/calcium (calcium scoring)                 │
│  ├─ /analysis/perfusion (perfusion analysis)            │
│  ├─ /segmentation/* (ML segmentation)                   │
│  ├─ /reporting/* (structured reports)                   │
│  └─ /measurements/* (advanced measurements)             │
│                                                         │
│  PROCESSING LAYER                                       │
│  ├─ Image Processing (SimpleITK, scikit-image)          │
│  ├─ ML Models (MONAI, PyTorch, ONNX)                    │
│  ├─ Volume Rendering (VTK bindings)                     │
│  ├─ Medical Analysis (custom algorithms)                │
│  └─ Template Engine (reporting)                         │
│                                                         │
│  DATA LAYER                                             │
│  ├─ DICOM Server (Orthanc)                              │
│  ├─ Database (SQLite/PostgreSQL)                        │
│  ├─ Object Storage (for processed data)                 │
│  └─ ML Model Store                                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📈 Implementation Timeline

| Phase | Duration | Deliverables | Team Size |
|-------|----------|--------------|-----------|
| 1: 3D Viewer | 2 weeks | Volumetric rendering, MPR | 2-3 dev |
| 2: ML Segmentation | 2 weeks | Vessel & organ detection | 2-3 dev |
| 3: Specialized Tools | 2 weeks | Cardiac, calcium, perfusion | 2 dev |
| 4: Reporting | 2 weeks | Templates, speech, export | 1-2 dev |
| 5: Enterprise Viewer | 2 weeks | PWA, offline capability | 1-2 dev |
| Testing & Polish | 2 weeks | QA, optimization | 2-3 dev |
| **TOTAL** | **~12 weeks** | **Full Suite** | **2-3 dev** |

---

## 💾 Storage & Performance Considerations

### Volume Data Management
```
Per Study Sizing:
- Raw DICOM: ~100-500 MB
- Processed Volume: ~50-200 MB
- Segmentation Masks: ~5-20 MB
- Pre-computed MPR: ~30-100 MB
- Total per study: ~200-800 MB

Storage Recommendations:
- Use object storage for large files
- Implement image caching
- Enable progressive loading
- Compress processed data
```

### Performance Optimization
```
Backend:
- GPU acceleration for 3D rendering (CUDA/OpenCL)
- Async processing for heavy computations
- Caching of processed results
- Queue system for analysis jobs

Frontend:
- WebWorkers for heavy JS computation
- Progressive image loading
- Viewport-aware rendering
- Client-side caching
```

---

## 🔐 Security Considerations

```
Advanced Tools Security:
✅ Role-based access to analysis tools
✅ Audit logging for measurements/reports
✅ Data encryption in transit and at rest
✅ Model inference logging
✅ Report access control
✅ AI analysis verification workflow
```

---

## 📊 Success Metrics

After implementation, you should have:

| Metric | Target |
|--------|--------|
| 3D rendering load time | < 3 seconds |
| MPR reconstruction | < 2 seconds |
| Segmentation inference | < 30 seconds |
| Report generation | < 5 seconds |
| System uptime | > 99.5% |
| User satisfaction | > 4.5/5 |

---

## 🚀 Getting Started

### Immediate Next Steps

1. **Week 1**: Install and test core dependencies
   ```bash
   pip install SimpleITK scikit-image scipy
   npm install three cornerstone3d
   ```

2. **Week 2**: Build basic 3D viewer
   - Create `viewer_3d.py` API
   - Create `volumetric-viewer.html` UI
   - Implement Three.js rendering

3. **Week 3**: Add ML segmentation
   - Set up MONAI models
   - Create `segmentation_engine.py`
   - Integrate with viewer

4. **Continue with remaining phases**

---

## 📞 Support & Resources

### Open Source Tools to Integrate
- **Cornerstone.js** - Medical imaging viewer
- **MONAI** - Medical imaging ML
- **VTK.js** - 3D visualization
- **ITK.js** - Image processing (WebAssembly)
- **dcmjs** - DICOM parsing

### Documentation Links
- MONAI: https://monai.io/
- SimpleITK: https://simpleitk.org/
- Cornerstone: https://www.cornerstonejs.org/
- OHIF: https://ohif.org/

---

## ✅ Checklist for Getting Started

- [ ] Review this roadmap with your team
- [ ] Prioritize which tools are most important
- [ ] Allocate development resources
- [ ] Set up development environment
- [ ] Install core dependencies
- [ ] Create feature branches
- [ ] Start Phase 1 implementation
- [ ] Plan testing strategy
- [ ] Define success criteria

---

**Document Status**: Complete Roadmap ✅  
**Last Updated**: Today  
**Next Review**: After Phase 1 completion
