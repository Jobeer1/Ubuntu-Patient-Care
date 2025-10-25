# PHASE 2 PLANNING: ML Segmentation Engine

**Phase**: Phase 2 - ML-based Medical Image Segmentation  
**Duration**: Weeks 3-4 (4 weeks estimated)  
**Target Start**: Immediately after Phase 1 completion (Oct 21, 22:00)  
**Team**: Dev 1 (Backend ML) + Dev 2 (Frontend Integration)  
**Status**: 📋 READY FOR KICKOFF

---

## PHASE 2 OVERVIEW

### Executive Summary
Phase 2 will integrate MONAI (Medical Open Network for AI) to add automated segmentation capabilities to the 3D viewer. Users will be able to:
- Automatically segment anatomical structures (organs, vessels, etc.)
- See segmentation masks overlaid on the 3D volume
- Export segmented regions
- Track segmentation results

### Key Objectives
1. ✅ Set up MONAI ML environment
2. ✅ Download and integrate pre-trained models
3. ✅ Create segmentation API endpoints
4. ✅ Implement async job processing
5. ✅ Build frontend UI for segmentation
6. ✅ Integrate with existing 3D viewer

### High-Level Architecture
```
Frontend                    Backend                 ML Models
─────────────              ──────────              ────────
Segmentation      ──POST──> Segmentation API  ──> MONAI Models
UI Button         Process  Route (async job)      (PyTorch)
                 <─JSON─     
Overlay Viewer    ──GET──>  Result Cache    <──  GPU Acceleration
                            Mask Data
```

---

## WEEK 3: ML ENVIRONMENT & API SETUP

### TASK 2.1.1: MONAI Environment Setup

**Assigned to**: Dev 1  
**Duration**: 4 hours  
**Status**: ⏳ NOT STARTED

**Objectives**:
- Install MONAI and PyTorch with CUDA support
- Download pre-trained models
- Verify GPU acceleration
- Test model loading times

**Detailed Checklist**:

**Step 1: Install MONAI & PyTorch** (1 hour)
```bash
# Check Python version
python --version
# Expected: Python 3.13.6

# Install core packages
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install MONAI
pip install monai

# Install complementary packages
pip install pytorch-cuda scikit-image nibabel pydicom

# Verify installation
python -c "import torch; print(torch.__version__)"
python -c "import monai; print(monai.__version__)"
```

**Expected Output**:
```
torch version: 2.0+
monai version: 1.2+
GPU available: True (if CUDA present)
```

**Step 2: GPU Acceleration Setup** (45 minutes)
```bash
# Check GPU availability
python -c "import torch; print(torch.cuda.is_available())"
python -c "import torch; print(torch.cuda.get_device_name(0))"

# Test GPU computation
python -c "import torch; x = torch.randn(1000, 1000).cuda(); print(x @ x)"
```

**Expected Results**:
- GPU detected (if available)
- GPU memory accessible
- Computation performs on GPU
- Speed advantage over CPU visible

**Step 3: Download Pre-trained Models** (2 hours)

**Option A: Use MONAI Model Zoo**
```bash
python -c "from monai.apps import download_and_register; 
download_and_register('swin_unetr_btcv_segmentation_pretrained')"
```

**Option B: Manual Downloads**

Models to download:
1. **BTCV Organ Segmentation**
   - Name: SWIN UNETR
   - Download: ~100 MB
   - Segmentation targets: 14 organs
   - Use: General organ segmentation

2. **Vessel Segmentation**
   - Name: UNet
   - Download: ~50 MB
   - Segmentation targets: Blood vessels
   - Use: Vascular analysis

3. **Lung Nodule Detection**
   - Name: U-Net
   - Download: ~30 MB
   - Detection type: Nodule classification
   - Use: Lung cancer screening

**Directory Structure After Download**:
```
app/ml_models/
├── models/
│   ├── swin_unetr_btcv_segmentation.pth (100 MB)
│   ├── vessel_segmentation_unet.pth (50 MB)
│   ├── lung_nodule_detection.pth (30 MB)
│   └── model_metadata.json
│
└── model_manager.py
```

**Step 4: Create Model Manager** (30 minutes)
Create `app/ml_models/model_manager.py` (200+ lines)

```python
from pathlib import Path
import torch
from monai.networks.nets import UNETR, UNet
from typing import Dict, Optional

class ModelManager:
    """Manages ML models for segmentation"""
    
    def __init__(self):
        self.models = {}
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_path = Path("app/ml_models/models")
    
    def load_organ_segmentation(self):
        """Load BTCV organ segmentation model"""
        # Load SWIN UNETR model
        # Target: 14 organs
        # Output: Segmentation mask
        pass
    
    def load_vessel_segmentation(self):
        """Load vessel segmentation model"""
        # Load vessel UNet model
        # Target: Blood vessels
        # Output: Vessel mask
        pass
    
    def load_nodule_detection(self):
        """Load lung nodule detection model"""
        # Load nodule detection model
        # Target: Lung nodules
        # Output: Nodule locations + confidence
        pass
    
    def get_model(self, model_name: str):
        """Get model by name"""
        if model_name not in self.models:
            self.load_model(model_name)
        return self.models[model_name]
```

**Step 5: Test Model Loading** (15 minutes)
```python
# Test script to verify models load
from app.ml_models.model_manager import ModelManager

manager = ModelManager()
print("Loading models...")

organ_model = manager.get_model("organ_segmentation")
vessel_model = manager.get_model("vessel_segmentation")
nodule_model = manager.get_model("nodule_detection")

print("✓ All models loaded successfully")
print(f"Device: {manager.device}")
print(f"Memory usage: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
```

**Expected Results**:
- ✅ MONAI installed
- ✅ PyTorch 2.0+
- ✅ GPU acceleration available (if hardware supports)
- ✅ 3 models download successfully
- ✅ Models load in < 5 seconds
- ✅ Memory usage < 5GB
- ✅ No errors in test

**Acceptance Criteria**:
```
[ ] MONAI version >= 1.2 installed
[ ] PyTorch version >= 2.0 installed
[ ] GPU acceleration available
[ ] 3 models downloaded (180 MB total)
[ ] All models load successfully
[ ] Load time per model < 2 seconds
[ ] Model inference ready
```

**Deliverables**:
- ✅ `app/ml_models/model_manager.py` (200+ lines)
- ✅ Downloaded models in `app/ml_models/models/`
- ✅ Test script output showing successful initialization

**Blocker**: None

---

### TASK 2.1.2: Segmentation API Endpoints

**Assigned to**: Dev 1  
**Duration**: 5 hours  
**Status**: ⏳ NOT STARTED

**Objectives**:
- Create 3 new segmentation endpoints
- Implement async job processing
- Add result caching
- Full error handling

**New File**: `app/routes/segmentation.py` (350+ lines)

**Endpoints to Implement**:

#### Endpoint 1: Segment Organs
```
POST /api/segment/organs
Content-Type: application/json

Request Body:
{
  "study_id": "study_123",
  "series_index": 0,
  "model": "swin_unetr",
  "threshold": 0.5
}

Response:
{
  "job_id": "seg_job_12345",
  "status": "processing",
  "progress": 0,
  "estimated_time_seconds": 30
}
```

**Processing Flow**:
1. Validate study_id exists
2. Create async job
3. Return job_id immediately
4. Start MONAI model inference in background
5. Save mask to cache

**Expected Processing Time**: 20-40 seconds per volume

#### Endpoint 2: Segment Vessels
```
POST /api/segment/vessels
Content-Type: application/json

Request Body:
{
  "study_id": "study_123",
  "series_index": 0,
  "model": "vessel_unet",
  "threshold": 0.3
}

Response:
{
  "job_id": "seg_job_12346",
  "status": "processing",
  "progress": 0,
  "estimated_time_seconds": 45
}
```

**Processing Flow**:
1. Validate inputs
2. Create async job
3. Load volume data
4. Preprocess for vessel detection
5. Run UNet model
6. Post-process results
7. Cache segmentation mask

**Expected Processing Time**: 30-60 seconds per volume

#### Endpoint 3: Detect Lung Nodules
```
POST /api/segment/nodules
Content-Type: application/json

Request Body:
{
  "study_id": "study_123",
  "series_index": 0,
  "model": "nodule_detector",
  "confidence_threshold": 0.7
}

Response:
{
  "job_id": "seg_job_12347",
  "status": "processing",
  "progress": 0,
  "estimated_time_seconds": 20
}
```

**Processing Flow**:
1. Extract lung region
2. Run nodule detection model
3. Filter by confidence threshold
4. Return nodule locations

**Expected Processing Time**: 15-30 seconds per volume

#### Endpoint 4: Get Segmentation Status
```
GET /api/segment/status/{job_id}

Response:
{
  "job_id": "seg_job_12345",
  "status": "completed",  // or "processing", "failed"
  "progress": 100,  // 0-100%
  "result_id": "seg_result_1",
  "timestamp": "2025-10-21T22:15:00Z"
}
```

**Purpose**: Poll for completion status

#### Endpoint 5: Download Segmentation Mask
```
GET /api/segment/download-mask/{job_id}

Response:
{
  "mask": "NIfTI binary file",
  "metadata": {
    "shape": [512, 512, 128],
    "segmentation_type": "organs",
    "organs_count": 14,
    "timestamp": "2025-10-21T22:15:00Z"
  }
}
```

**Purpose**: Download processed mask

### Job Queue System Implementation

**Requirements**:
- Async processing (don't block request)
- Track job status
- Cache results
- Timeout handling
- Error reporting

**Implementation Strategy**:
```python
# Use Python background tasks with asyncio
from fastapi import BackgroundTasks
from typing import Dict
import asyncio

class SegmentationQueue:
    """Queue for segmentation jobs"""
    
    def __init__(self):
        self.jobs: Dict[str, dict] = {}
        self.results: Dict[str, dict] = {}
    
    async def create_job(self, study_id: str, task_type: str) -> str:
        """Create new segmentation job"""
        job_id = f"seg_{uuid.uuid4()}"
        self.jobs[job_id] = {
            "status": "queued",
            "progress": 0,
            "study_id": study_id,
            "type": task_type
        }
        return job_id
    
    async def process_segmentation(self, job_id: str, data: dict):
        """Run segmentation in background"""
        # Mark as processing
        # Load model
        # Run inference
        # Save results
        # Mark as complete
        pass
    
    def get_job_status(self, job_id: str) -> dict:
        """Get current job status"""
        return self.jobs.get(job_id)
    
    def get_result(self, job_id: str) -> dict:
        """Get completed result"""
        return self.results.get(job_id)
```

**Pydantic Models to Create**:
```python
class SegmentationRequest(BaseModel):
    study_id: str
    series_index: int
    model: str  # "swin_unetr", "vessel_unet", "nodule_detector"
    threshold: float = 0.5  # Confidence threshold

class SegmentationResponse(BaseModel):
    job_id: str
    status: str  # "queued", "processing", "completed", "failed"
    progress: int  # 0-100
    estimated_time_seconds: int

class SegmentationStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    result_id: Optional[str] = None
```

### Caching Strategy

**Where to cache**:
- Cache mask results in memory
- TTL: 1 hour (configurable)
- Key: `seg_{study_id}_{model_type}_{parameters_hash}`

**What to cache**:
- Segmentation masks (binary)
- Metadata (shape, organs, timestamp)
- Inference time

**Why cache**:
- Avoid re-running same segmentation
- Improve response time for repeated requests
- Reduce GPU/CPU load

### Testing Endpoints

```bash
# Test organ segmentation
curl -X POST http://localhost:8000/api/segment/organs \
  -H "Content-Type: application/json" \
  -d '{"study_id": "test_study", "series_index": 0, "model": "swin_unetr"}'

# Expected response:
# {"job_id": "seg_job_xxx", "status": "processing", "progress": 0}

# Check status
curl http://localhost:8000/api/segment/status/seg_job_xxx

# Expected response:
# {"job_id": "seg_job_xxx", "status": "completed", "progress": 100}
```

**Acceptance Criteria**:
```
[ ] 5 endpoints created
[ ] Request validation working
[ ] Async job processing implemented
[ ] Job status tracking functional
[ ] Result caching working
[ ] Error handling comprehensive
[ ] Response times < 200ms (immediate)
[ ] Processing times < 60s (segmentation)
```

**Deliverables**:
- ✅ `app/routes/segmentation.py` (350+ lines)
- ✅ 5 working endpoints
- ✅ Job queue system
- ✅ Pydantic models
- ✅ Caching system
- ✅ Error handling

**Blocker**: Depends on TASK 2.1.1

---

### TASK 2.1.3: Segmentation Processing Engine

**Assigned to**: Dev 2  
**Duration**: 6 hours  
**Status**: ⏳ NOT STARTED

**Objectives**:
- Implement model inference pipeline
- Add preprocessing (normalization, resizing)
- Add postprocessing (smoothing, cleanup)
- Optimize inference time

**New File**: `app/ml_models/segmentation_engine.py` (400+ lines)

**Core Functions**:

#### Function 1: Preprocess Volume
```python
def preprocess_volume(volume_data: np.ndarray, target_shape: tuple) -> np.ndarray:
    """
    Prepare volume for model inference
    
    Steps:
    1. Normalize HU values to [-1, 1]
    2. Resize to model input shape
    3. Convert to model format
    """
```

**Expected Input**: Raw CT/MRI volume (512×512×128, HU values)  
**Expected Output**: Preprocessed tensor (required shape, normalized)

#### Function 2: Run Organ Segmentation
```python
def segment_organs(volume_data: np.ndarray, model) -> np.ndarray:
    """
    Segment 14 anatomical organs
    
    Steps:
    1. Preprocess volume
    2. Run SWIN UNETR model
    3. Post-process output
    4. Return label map (14 organs)
    """
```

**Output Format**:
```
Label Map:
  0 = Background
  1 = Spleen
  2 = Right Kidney
  3 = Left Kidney
  4 = Gallbladder
  5 = Esophagus
  6 = Liver
  7 = Stomach
  8 = Aorta
  9 = Inferior Vena Cava
  10 = Portal & Splenic Vein
  11 = Pancreas
  12 = Right Adrenal Gland
  13 = Left Adrenal Gland
  14 = Duodenum
```

**Accuracy Target**: > 90% Dice score on validation set

#### Function 3: Run Vessel Segmentation
```python
def segment_vessels(volume_data: np.ndarray, model) -> np.ndarray:
    """
    Segment blood vessels
    
    Steps:
    1. Extract vessel region
    2. Run UNet model
    3. Apply thresholding
    4. Return binary vessel mask
    """
```

**Output Format**: Binary mask (0 = no vessel, 1 = vessel)

#### Function 4: Detect Lung Nodules
```python
def detect_lung_nodules(volume_data: np.ndarray, model) -> List[dict]:
    """
    Detect lung nodules
    
    Steps:
    1. Extract lung region
    2. Run nodule detection model
    3. Post-process detections
    4. Return list of nodules with locations
    """
```

**Output Format**:
```python
[
  {
    "location": [x, y, z],
    "radius_mm": 5.5,
    "confidence": 0.92,
    "classification": "suspicious"  # or "benign"
  },
  # ... more nodules
]
```

#### Function 5: Post-process Mask
```python
def postprocess_mask(mask: np.ndarray, smooth: bool = True) -> np.ndarray:
    """
    Clean up segmentation mask
    
    Steps:
    1. Fill holes
    2. Remove small artifacts
    3. Optional: Smooth surface
    4. Return clean mask
    """
```

**Options**:
- Hole filling (connected components)
- Artifact removal (size threshold)
- Surface smoothing (Gaussian blur)

#### Function 6: Export Mask to NIfTI
```python
def save_mask_nifti(mask: np.ndarray, filepath: str, affine: np.ndarray):
    """
    Save segmentation as NIfTI file
    
    NIfTI format supports:
    - 3D image data
    - Affine transformation
    - Metadata headers
    """
```

**Use Case**: Export for clinical use or further analysis

#### Function 7: Calculate Statistics
```python
def calculate_segmentation_stats(mask: np.ndarray, volume_data: np.ndarray) -> dict:
    """
    Calculate clinical statistics from segmentation
    
    Returns:
    {
      "total_volume_mm3": 125000,
      "mean_hu": 45.2,
      "std_hu": 12.5,
      "organs": {
        "liver": {"volume_mm3": 1500, "mean_hu": 60},
        # ... other organs
      }
    }
    """
```

### Performance Optimization

**Target Inference Times**:
- Organ segmentation: 30-40 seconds
- Vessel segmentation: 45-60 seconds
- Nodule detection: 15-25 seconds

**Optimization Strategies**:
1. **Batch Processing**: Process multiple volumes
2. **GPU Acceleration**: Use CUDA/GPU where available
3. **Model Quantization**: Convert to FP16 for faster inference
4. **Caching**: Don't re-process same volume

**Memory Management**:
- Load one model at a time
- Clear GPU memory after inference
- Monitor peak memory usage

### Testing

```python
# Test preprocessing
test_volume = np.random.randn(512, 512, 128)
preprocessed = preprocess_volume(test_volume, (96, 96, 96))
assert preprocessed.shape == (1, 1, 96, 96, 96)

# Test organ segmentation
organ_mask = segment_organs(preprocessed, model)
assert organ_mask.shape == (96, 96, 96)
assert organ_mask.max() <= 14

# Test statistics
stats = calculate_segmentation_stats(organ_mask, test_volume)
assert "total_volume_mm3" in stats
```

**Acceptance Criteria**:
```
[ ] All 7 functions implemented
[ ] Preprocessing produces correct output shape
[ ] Organ segmentation accuracy > 90%
[ ] Vessel segmentation works
[ ] Nodule detection finds lung nodules
[ ] Post-processing removes artifacts
[ ] NIfTI export creates valid files
[ ] Statistics calculated correctly
[ ] Inference time within targets
[ ] No memory leaks
```

**Deliverables**:
- ✅ `app/ml_models/segmentation_engine.py` (400+ lines)
- ✅ 7 processing functions
- ✅ Performance metrics
- ✅ Test results

**Blocker**: Depends on TASK 2.1.1

---

## WEEK 3: FRONTEND SEGMENTATION UI

### TASK 2.1.4: Segmentation Viewer HTML

**Assigned to**: Dev 2  
**Duration**: 3 hours  
**Status**: ⏳ NOT STARTED

**File**: `static/viewers/segmentation-viewer.html` (300+ lines)

**UI Layout**:
```
┌──────────────────────────────────────────────────────┐
│ HEADER: Segmentation Tools                          │
├───────────────┬──────────────────────────────────────┤
│ LEFT PANEL    │                                      │
│               │ 3D Volume Display                    │
│ 1. Study Sel  │ (with Segmentation Overlay)         │
│ 2. Model Sel  │                                      │
│ 3. Parameters │                                      │ RIGHT PANEL
│ 4. Run Button │                                      │
│ 5. Progress   │                                      │ 1. Seg Results
│ 6. History    │                                      │ 2. Mask Options
│               │                                      │ 3. Export
└───────────────┴──────────────────────────────────────┘
```

**Components to Build**:

#### Component 1: Study Selector
```html
<div class="study-selector">
  <label>Select Study:</label>
  <select id="study-select">
    <option value="">Loading studies...</option>
  </select>
  <button id="load-study">Load</button>
</div>
```

**Functionality**:
- List all available studies
- Show study info (patient name, date, modality)
- Load study when selected

#### Component 2: Model Selector
```html
<div class="model-selector">
  <label>Segmentation Model:</label>
  <select id="model-select">
    <option value="organs">Organ Segmentation (SWIN UNETR)</option>
    <option value="vessels">Vessel Segmentation (UNet)</option>
    <option value="nodules">Lung Nodule Detection</option>
  </select>
</div>
```

**Models Available**:
- Organ Segmentation (14 structures)
- Vessel Segmentation (binary)
- Lung Nodule Detection

#### Component 3: Parameter Controls
```html
<div class="parameters">
  <label>Confidence Threshold:</label>
  <input type="range" min="0" max="1" step="0.1" value="0.5">
  
  <label>Post-processing:</label>
  <input type="checkbox" id="smooth-mask"> Smooth surface
  <input type="checkbox" id="fill-holes"> Fill holes
</div>
```

#### Component 4: Start Segmentation
```html
<button id="start-segmentation" class="primary">
  Start Segmentation
</button>
```

**Behavior**:
- Validate inputs
- Send request to API
- Show progress
- Disable button during processing

#### Component 5: Progress Indicator
```html
<div class="progress">
  <div class="progress-bar">
    <div class="progress-fill" style="width: 0%"></div>
  </div>
  <div class="progress-text">
    <span id="status">Ready</span>
    <span id="progress">0%</span>
  </div>
</div>
```

**Updates Every 2 Seconds**:
- Poll job status
- Update progress bar
- Show ETA
- Show current step

#### Component 6: Results Display
```html
<div class="results">
  <h3>Segmentation Results</h3>
  <div id="result-items">
    <!-- Results appear here -->
  </div>
</div>
```

**Result Item Template**:
```html
<div class="result-item">
  <h4>Liver</h4>
  <p>Volume: 1,250 mm³</p>
  <p>Mean HU: 60</p>
  <button>View</button>
  <button>Export</button>
</div>
```

#### Component 7: Overlay Controls
```html
<div class="overlay-controls">
  <label>Overlay Opacity:</label>
  <input type="range" min="0" max="100" value="50">
  
  <label>Mask Color:</label>
  <input type="color" value="#FF0000">
  
  <label>Show Segmentation:</label>
  <input type="checkbox" checked>
</div>
```

#### Component 8: Export Options
```html
<div class="export">
  <button id="export-nifti">Export as NIfTI</button>
  <button id="export-stl">Export as STL</button>
  <button id="export-csv">Export Statistics</button>
</div>
```

### JavaScript Integration (in segmentation-viewer.html)

```javascript
class SegmentationUI {
  constructor() {
    this.currentJobId = null;
    this.currentResults = null;
  }
  
  async startSegmentation() {
    // 1. Get user inputs
    // 2. Call API
    // 3. Store job ID
    // 4. Poll status
  }
  
  async pollJobStatus() {
    // Check every 2 seconds
    // Update progress bar
    // Show results when complete
  }
  
  displayResults(results) {
    // Show organ names and volumes
    // Enable export buttons
  }
  
  async exportResults(format) {
    // JSON, CSV, or NIfTI
  }
}
```

**Acceptance Criteria**:
```
[ ] HTML structure complete
[ ] All 8 components present
[ ] Responsive layout working
[ ] CSS styled professionally
[ ] JavaScript hooks defined
[ ] Integration points clear for backend
[ ] Load time < 2 seconds
```

**Deliverables**:
- ✅ `static/viewers/segmentation-viewer.html` (300+ lines)
- ✅ All UI components
- ✅ JavaScript integration hooks
- ✅ Responsive design

**Blocker**: Depends on TASK 2.1.2

---

### TASK 2.1.5: Segmentation Overlay Renderer

**Assigned to**: Dev 1  
**Duration**: 5 hours  
**Status**: ⏳ NOT STARTED

**File**: `static/js/viewers/segmentation-overlay.js` (400+ lines)

**Purpose**: Render segmentation masks as colored overlays on 3D volume

**Core Class**: `SegmentationOverlay`

**Methods to Implement**:

#### Method 1: Initialize Overlay
```javascript
init(renderer, scene, volume) {
  // Setup Three.js objects for mask display
  // Create material for segmentation overlay
  // Setup texture rendering
}
```

#### Method 2: Load Segmentation Mask
```javascript
loadMask(maskData, maskType) {
  // maskData: Binary array from backend
  // maskType: "organs", "vessels", "nodules"
  // Convert to Three.js texture
}
```

#### Method 3: Set Mask Opacity
```javascript
setMaskOpacity(opacity) {
  // 0 = invisible
  // 1 = fully opaque
  // Update material transparency
}
```

#### Method 4: Set Mask Color
```javascript
setMaskColor(color, organ = null) {
  // color: HEX color string (e.g., "#FF0000")
  // organ: optional, color specific organ
  // Update material color
}
```

#### Method 5: Highlight Organ
```javascript
highlightOrgan(organLabel) {
  // Highlight one organ in different color
  // Dim other organs
  // Show statistics
}
```

#### Method 6: Show/Hide Segmentation
```javascript
toggleSegmentation(visible) {
  // Show or hide overlay
  // Keep volume visible
}
```

#### Method 7: Export Segmentation
```javascript
exportSegmentation(format) {
  // format: "stl", "obj", "ply", "nifti"
  // Create downloadable file
}
```

### Color Mapping for Organs

```javascript
const ORGAN_COLORS = {
  1: { name: "Spleen", color: "#FF6B6B" },
  2: { name: "Right Kidney", color: "#4ECDC4" },
  3: { name: "Left Kidney", color: "#45B7D1" },
  4: { name: "Gallbladder", color: "#96CEB4" },
  5: { name: "Esophagus", color: "#FFEAA7" },
  6: { name: "Liver", color: "#DDA15E" },
  7: { name: "Stomach", color: "#BC6C25" },
  8: { name: "Aorta", color: "#D62828" },
  9: { name: "IVC", color: "#F77F00" },
  // ... more organs
};
```

### Performance Considerations

**Optimization**:
1. **GPU Texture**: Store mask as GPU texture
2. **Level-of-Detail**: Lower resolution for faster rendering
3. **Culling**: Don't render hidden organs
4. **Caching**: Cache rendered meshes

**Memory**:
- Full mask 512×512×128: ~128 MB
- Compressed texture: ~32 MB
- Keep within 500 MB total

### Integration with Existing Renderer

```javascript
// Integrate with VolumetricRenderer from Phase 1
class VolumetricRenderer {
  // ... existing code ...
  
  // Add overlay support
  setOverlay(segmentationOverlay) {
    this.overlay = segmentationOverlay;
    this.updateRender();
  }
  
  updateRender() {
    // Render volume
    // Render overlay on top
    // Composite final image
  }
}
```

**Acceptance Criteria**:
```
[ ] Overlay renders on volume
[ ] Opacity control works
[ ] Color customization working
[ ] Organ highlighting works
[ ] Performance > 50 FPS with overlay
[ ] Export functionality working
[ ] No memory leaks with overlay
[ ] Visual quality professional
```

**Deliverables**:
- ✅ `static/js/viewers/segmentation-overlay.js` (400+ lines)
- ✅ Color mapping system
- ✅ Overlay rendering
- ✅ Export functionality
- ✅ Integration with Phase 1 renderer

**Blocker**: Depends on TASK 2.1.3

---

## PHASE 2 SCHEDULE

```
Week 3 - ML Segmentation Engine
├─ Mon-Wed (12 hours): TASK 2.1.1 + 2.1.2 + 2.1.3 (parallel)
│   ├─ 4 hrs: MONAI environment setup (Dev 1)
│   ├─ 5 hrs: Segmentation API endpoints (Dev 1)
│   └─ 6 hrs: Processing engine (Dev 2)
│
├─ Wed-Thu (8 hours): Frontend segmentation UI
│   ├─ 3 hrs: Segmentation viewer HTML (Dev 2)
│   └─ 5 hrs: Overlay renderer (Dev 1)
│
└─ Fri (4 hours): Integration testing
    └─ 4 hrs: Phase 2 integration tests (Dev 1 + Dev 2)

Week 4 - Polish & Testing
├─ Mon-Tue: Bug fixes and optimization
├─ Wed: Cross-browser testing
├─ Thu: Performance profiling
└─ Fri: Documentation and deployment prep
```

---

## SUCCESS CRITERIA

### Phase 2 Objectives

| Objective | Success Criteria | Status |
|-----------|-----------------|--------|
| ML Environment | MONAI + PyTorch installed, GPU ready | ⏳ Pending |
| Models Downloaded | 3 pre-trained models, <180 MB | ⏳ Pending |
| API Endpoints | 5 endpoints working, async jobs | ⏳ Pending |
| Processing Engine | Inference time < 60s | ⏳ Pending |
| Frontend UI | Segmentation viewer functional | ⏳ Pending |
| Overlay Rendering | Organs displayed on volume | ⏳ Pending |
| Integration | All components working together | ⏳ Pending |
| Testing | 100% pass rate on tests | ⏳ Pending |

---

## BLOCKERS & DEPENDENCIES

### External Dependencies
- MONAI model zoo accessibility
- GPU availability (optional but beneficial)
- Sufficient disk space (180 MB for models)

### Internal Dependencies
- Phase 1 must be complete (✅ Already done)
- Backend API stable (✅ Already done)
- Frontend responsive (✅ Already done)

### Team Dependencies
- Dev 1 ready for ML work
- Dev 2 ready for frontend integration
- Time slots available for pair programming

---

## NOTES FOR DEV 1 & DEV 2

### For Dev 1 (ML Engineer Track)
- Focus on MONAI setup and model integration
- Ensure GPU acceleration working
- Optimize inference times
- Test with real DICOM data
- Document preprocessing pipeline

### For Dev 2 (Frontend Engineer Track)
- Create professional segmentation UI
- Integrate with existing 3D viewer
- Implement smooth animations
- Test responsiveness
- Optimize rendering performance

### Pair Programming Sessions
- **Mid-Week Sync**: Review MONAI + API implementation
- **Integration Day**: Connect backend to frontend
- **Testing Day**: Joint testing and debugging

---

## PHASE 2 COMPLETION CHECKLIST

**Before Declaring Phase 2 Complete**:
- [ ] All 5 tasks completed
- [ ] Code reviewed and merged
- [ ] All tests passing (100%)
- [ ] Performance metrics met
- [ ] Documentation complete
- [ ] No blockers remaining
- [ ] Ready for Phase 3

---

**Document Date**: October 21, 2025 - 22:30 UTC  
**Version**: 1.0 PLANNING  
**Status**: READY FOR KICKOFF  
**Next Step**: Dev 1 to begin TASK 2.1.1 (MONAI setup)
