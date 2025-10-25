# Client-Side GPU Implementation Plan - PACS Features

**Date**: October 23, 2025  
**Status**: Ready for Implementation  
**Goal**: Move GPU-intensive features to client-side processing  
**Impact**: No server GPU required, improved performance, better scalability

---

## 📊 Executive Summary

```
CURRENT STATE:
├─ Phase 1 (3D Viewer): 100% ✅ - Already client-side (Three.js WebGL)
├─ Phase 2 (Segmentation): 100% ✅ - Server-side (needs migration)
├─ Phase 3 (Cardiac/Calcium): 67% ⏸️ - Server-side (needs migration)
├─ Phase 4 (Perfusion/Mammo): 100% ✅ - Server-side (needs migration)
└─ Phase 5 (Reporting): 50% ✅ - Mostly client-side

TARGET STATE:
├─ Phase 1: No changes (already optimal) ✅
├─ Phase 2: TensorFlow.js + ONNX.js for segmentation 🎯
├─ Phase 3: WebGL compute shaders + Canvas 2D 🎯
├─ Phase 4: Canvas 2D + GPU.js compute 🎯
└─ Phase 5: No changes (already client-side) ✅

BENEFITS:
✅ Zero server GPU required
✅ 5-10x faster processing (local GPU access)
✅ Better scalability (unlimited concurrent users)
✅ Enhanced privacy (medical data stays in browser)
✅ Reduced infrastructure costs
✅ Offline capability for browsers with GPU
```

---

## 🏗️ Implementation Strategy

### Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                  BROWSER (Client-Side)                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │          GPU COMPUTE LAYER                       │  │
│  ├──────────────────────────────────────────────────┤  │
│  │ WebGL/WebGPU        │ TensorFlow.js    │GPU.js   │  │
│  │ (Graphics)          │ (ML Inference)   │(Compute)│  │
│  └──────────────────────────────────────────────────┘  │
│                           ↑                             │
│  ┌──────────────────────────────────────────────────┐  │
│  │       ML/COMPUTE LAYER (JavaScript)              │  │
│  ├──────────────────────────────────────────────────┤  │
│  │ Segmentation  │ Calcium  │ Perfusion │ Mammo CAD│  │
│  │ (TensorFlow)  │ (WebGL)  │ (Canvas) │(TFFlow)  │  │
│  └──────────────────────────────────────────────────┘  │
│                           ↑                             │
│  ┌──────────────────────────────────────────────────┐  │
│  │         DATA/VISUALIZATION LAYER                 │  │
│  ├──────────────────────────────────────────────────┤  │
│  │ DICOM Viewer │ Render Engines │ Analysis Tools   │  │
│  └──────────────────────────────────────────────────┘  │
│                           ↑                             │
├─────────────────────────────────────────────────────────┤
│                     HTTP/REST API                       │
│          (Data transfer only - no processing)           │
├─────────────────────────────────────────────────────────┤
│                  SERVER (Minimal)                       │
├─────────────────────────────────────────────────────────┤
│  ORTHANC DICOM DATABASE  │ AUTHENTICATION              │
│  (Read-only data access)  │ (No GPU needed)            │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Phase 3: Cardiac & Calcium Analysis (67% → 100%)

### Current Tasks (4/6 Complete)
- ✅ TASK 3.1.1: Cardiac Analysis Engine (Server)
- ⏳ TASK 3.1.2: Client Cardiac Viewer (Needs update for client-side)
- ✅ TASK 3.1.3: Coronary Analysis Engine (Server)
- ⏳ TASK 3.1.4: Client Coronary Viewer (Needs update)
- ⏳ TASK 3.1.5: Calcium Scoring Engine (needs completion)
- ⏳ TASK 3.1.6: Calcium Viewer UI (needs completion)

### New Implementation Plan

#### TASK 3.1.5: Client-Side Calcium Scoring Engine ✨
**Technology**: WebGL Compute Shaders + Canvas 2D  
**Duration**: 4 hours  
**Files**:
- `static/js/compute/calcium-scoring.js` (main engine)
- `static/js/compute/webgl-compute.js` (helper utilities)

**Implementation Steps**:

1. **WebGL Texture Creation** (600 lines)
   - Convert DICOM volume to WebGL 3D texture
   - Handle different DICOM bit depths
   - Implement tensor conversion utilities
   - Memory management for large volumes

2. **Compute Shaders** (400 lines)
   - Agatston score calculation shader
   - Volume calculation shader
   - Mass calculation shader
   - Density categorization shader

3. **CPU-GPU Pipeline** (300 lines)
   - Upload volume data to GPU
   - Manage compute shader execution
   - Read back results asynchronously
   - Handle fallback to CPU if GPU unavailable

4. **Algorithm Implementation** (250 lines)
   - Threshold detection (HU > 130)
   - 4-category density scoring
   - Area summation
   - Percentile calculation

**Code Template**:
```javascript
class ClientCalciumScoring {
    constructor() {
        this.canvas = document.createElement('canvas');
        this.gl = this.canvas.getContext('webgl2');
        this.volumeTexture = null;
    }
    
    async calculateAgatstonScore(volumeData, threshold = 130) {
        // Step 1: Upload to GPU
        this.createVolumeTexture(volumeData);
        
        // Step 2: Run compute shader
        const scoreMap = this.runComputeShader('agatston', {
            texture: this.volumeTexture,
            threshold: threshold
        });
        
        // Step 3: Process results
        const results = this.processResults(scoreMap);
        
        // Step 4: Return results
        return {
            agatstonScore: results.agatston,
            volume: results.volume,
            mass: results.mass,
            percentile: results.percentile,
            riskCategory: results.risk
        };
    }
}
```

**Performance Targets**:
- Agatston calculation: < 2 seconds
- Volume calculation: < 1 second
- Total processing: < 3 seconds
- GPU memory: < 500MB

#### TASK 3.1.6: Calcium Scoring UI & Viewer (NEW)
**Technology**: Canvas 2D + Chart.js  
**Duration**: 3 hours  
**Files**:
- `static/viewers/calcium-viewer.html` (600 lines)
- `static/js/viewers/calcium-viewer-controller.js` (400 lines)

**Features**:
- Real-time score calculation as user loads study
- Visual heatmap of calcium deposits
- Risk category badge (Low/Moderate/High/Very High)
- Percentile calculator (compared to age/sex cohort)
- Regional calcium distribution
- Trend analysis (if multiple scans available)
- Export report (PDF with scoring breakdown)

---

## 🔄 Phase 4: Perfusion & Mammography (100% → Client-Side Migration)

### Current Implementation
- ✅ TASK 4.1.1: Perfusion Analysis Engine (Server)
- ✅ TASK 4.1.3: Perfusion Viewer (Client-side display only)
- ✅ TASK 4.1.2: Mammography Tools (Server)
- ✅ TASK 4.1.4: Mammography Viewer (Client-side display only)

### Client-Side Migration

#### TASK 4.2.1: Client-Side Perfusion Analysis (NEW)
**Technology**: Canvas 2D + GPU.js  
**Duration**: 5 hours  
**Responsibilities**:
- Move TIC extraction to Canvas 2D
- Move parametric map generation to GPU.js
- Move deconvolution to WebGL compute
- Keep server for data loading only

**Implementation**:
```javascript
class ClientPerfusionAnalysis {
    // TIC Extraction - Canvas 2D (fast)
    extractTIC(dynamicSeries, roi) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        const tic = dynamicSeries.map(frame => {
            ctx.putImageData(frame, 0, 0);
            const pixels = ctx.getImageData(roi.x, roi.y, roi.width, roi.height);
            return this.meanIntensity(pixels.data);
        });
        
        return tic;
    }
    
    // Parametric Map - GPU.js (massively parallel)
    generateCBFMap(dynamicSeries) {
        const gpu = new GPU();
        
        const kernel = gpu.createKernel(function(series) {
            // Each GPU thread handles one pixel
            const cbf = this.thread.y;
            return cbf;
        });
        
        return kernel(dynamicSeries);
    }
    
    // Deconvolution - WebGL Compute
    deconvolveAIF(tic, aif) {
        // Use WebGL for matrix operations
        return this.webglDeconvolve(tic, aif);
    }
}
```

#### TASK 4.2.2: Client-Side Mammography CAD (NEW)
**Technology**: TensorFlow.js  
**Duration**: 4 hours  
**Responsibilities**:
- Load pre-trained ONNX mammography detection model
- Run lesion detection on client GPU
- Generate BI-RADS assessments locally
- No server processing needed

**Implementation**:
```javascript
class ClientMammographyCAD {
    async loadModel() {
        // Load pre-trained model from CDN or local storage
        this.model = await onnx.InferenceSession.create('/models/mammo_cad.onnx', {
            executionProviders: ['webgl', 'wasm']
        });
    }
    
    async detectLesions(mammogramImage) {
        // Preprocess
        const tensor = this.preprocessImage(mammogramImage);
        
        // Inference on client GPU
        const results = await this.model.run({
            images: new onnx.Tensor('float32', tensor, [1, 3, 512, 512])
        });
        
        // Post-process
        return this.postprocessResults(results);
    }
}
```

---

## 📦 Required Libraries (CDN)

### Add to All HTML Viewers

```html
<!-- Core Graphics -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>

<!-- ML Inference -->
<script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.11.0"></script>
<script src="https://cdn.jsdelivr.net/npm/onnxruntime-web@1.16.0/dist/ort.min.js"></script>

<!-- GPU Computing -->
<script src="https://cdn.jsdelivr.net/npm/gpu.js@2.16.0/dist/gpu-browser.min.js"></script>

<!-- Visualization -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist@2.26.0/plotly.min.js"></script>

<!-- Utilities -->
<script src="https://cdn.jsdelivr.net/npm/ndarray@1.0.19/ndarray.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/zip@1.6.0/dist/zip.min.js"></script>
```

---

## 🔧 Server-Side Changes (Minimal)

### Endpoint Updates

#### Phase 2: Segmentation
**Old**: `/api/segment/organs` - Runs inference server-side  
**New**: `/api/segment/organs` - Returns model file only  
```python
@router.get("/api/segment/organs")
async def get_organ_model():
    return FileResponse("models/organ_seg.onnx", media_type="application/octet-stream")
```

#### Phase 3: Calcium Scoring
**Old**: `/api/cardiac/calcium-score` - Runs calculation server-side  
**New**: `/api/cardiac/calcium-score` - Optional validation only  
```python
@router.post("/api/cardiac/calcium-score")
async def validate_calcium_score(score: CalciumScoreRequest):
    # Optional: validate client-calculated score
    # Or return medical reference data (percentiles, risk tables)
    return {"percentile": calculate_percentile(score.agatston)}
```

#### Phase 4: Perfusion Analysis
**Old**: `/api/perfusion/extract-tic` - Full processing  
**New**: `/api/perfusion/aif-reference` - Reference data only  
```python
@router.get("/api/perfusion/aif-reference")
async def get_aif_reference():
    # Return arterial input function templates
    # (client does deconvolution)
    return {"aif_templates": [...]}
```

---

## 📈 Performance Projections

### Before (Server-Side GPU)
```
3D Viewer:          100ms     (Three.js WebGL)
Segmentation:       25,000ms  (Server GPU inference)
Cardiac Analysis:   10,000ms  (Server CPU)
Calcium Scoring:    8,000ms   (Server CPU)
Perfusion:          15,000ms  (Server CPU/GPU)
Mammography CAD:    20,000ms  (Server GPU)
─────────────────────────────────
TOTAL:              78,100ms  (~78 seconds)
```

### After (Client-Side GPU)
```
3D Viewer:          100ms     (Three.js WebGL)
Segmentation:       8,000ms   (TensorFlow.js client GPU)
Cardiac Analysis:   3,000ms   (Canvas 2D)
Calcium Scoring:    2,000ms   (WebGL compute)
Perfusion:          5,000ms   (Canvas 2D + GPU.js)
Mammography CAD:    6,000ms   (ONNX.js client GPU)
─────────────────────────────────
TOTAL:              24,100ms  (~24 seconds)
```

**Improvement**: 69% faster! ⚡

---

## 🚀 Implementation Roadmap

### Week 1: Phase 3 Client-Side Migration
```
Day 1-2: TASK 3.1.5 - Calcium Scoring Engine (WebGL)
Day 3:   TASK 3.1.6 - Calcium Viewer UI
Day 4:   Testing & Integration
Day 5:   Buffer & Optimization
```

### Week 2: Phase 4 Client-Side Migration
```
Day 1-2: TASK 4.2.1 - Perfusion Analysis (Canvas 2D)
Day 3:   TASK 4.2.2 - Mammography CAD (TensorFlow.js)
Day 4:   Model Export & Optimization
Day 5:   Testing & Performance tuning
```

### Week 3: Phase 2 Migration & Optimization
```
Day 1-2: TASK 2.3.1 - Model Conversion (PyTorch → ONNX)
Day 3-4: TASK 2.3.2 - Client Segmentation (ONNX.js)
Day 5:   Server Cleanup & Testing
```

---

## ✅ Completion Criteria

### For Each Phase

- [ ] All GPU processing moved to client
- [ ] Server endpoints updated (data-only, no processing)
- [ ] Performance tests pass (targets met)
- [ ] Memory tests pass (< 500MB per operation)
- [ ] Browser compatibility verified (Chrome, Firefox, Safari, Edge)
- [ ] Fallback to CPU if GPU unavailable
- [ ] Error handling comprehensive
- [ ] Documentation complete
- [ ] Tests 100% passing
- [ ] No GPU instance required on server

---

## 💡 Key Design Decisions

### 1. Why WebGL for compute?
- ✅ Excellent GPU support across browsers
- ✅ Better than WebGPU (wider device support)
- ✅ Pixel-perfect precision for medical imaging
- ✅ Compute shaders available in WebGL 2.0

### 2. Why TensorFlow.js vs ONNX.js?
- TensorFlow.js: Better for complex ML models (segmentation)
- ONNX.js: Better for model interoperability, smaller models
- **Strategy**: Use both - TF.js for complex models, ONNX.js for efficient models

### 3. Fallback Strategy
- All clients default to GPU if available
- Automatic fallback to CPU (slower, but works)
- Progressive enhancement approach
- No critical feature blocked by GPU availability

### 4. Model Distribution
- Store ONNX/SavedModel files in `/static/models/`
- Serve via CDN for better performance
- Cache models in browser IndexedDB
- Versioning for model updates

---

## 📝 Documentation Deliverables

1. **CLIENT_SIDE_GPU_ARCHITECTURE.md** - Overall architecture (✅ Done)
2. **PHASE3_CLIENT_GPU_IMPLEMENTATION.md** - Cardiac & Calcium details
3. **PHASE4_CLIENT_GPU_MIGRATION.md** - Perfusion & Mammography details
4. **GPU_PERFORMANCE_BENCHMARKS.md** - Performance metrics & graphs
5. **CLIENT_GPU_TROUBLESHOOTING.md** - Common issues & solutions
6. **BROWSER_GPU_COMPATIBILITY.md** - Browser support matrix
7. **MODEL_EXPORT_GUIDE.md** - PyTorch → ONNX conversion guide

---

## 🎯 Success Metrics

```
✅ Zero server GPU required
✅ 70% improvement in processing speed
✅ 99%+ client GPU availability (auto-fallback to CPU)
✅ Medical imaging accuracy maintained (>99%)
✅ Browser compatibility: 95%+ of users
✅ No breaking changes to existing APIs
✅ Backward compatible with CPU-only deployment
✅ Full offline capability for supported browsers
```

---

**Status**: Ready for Implementation 🚀  
**Team**: Dev 1 (Server optimization) + Dev 2 (Client GPU)  
**Timeline**: 3 weeks to completion  
**Priority**: High (enables Phase 5 reporting)
