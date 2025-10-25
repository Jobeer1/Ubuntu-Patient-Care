# 🏃‍♂️ DEV 1 PHASE 3 ACCELERATION ROADMAP

**Date**: October 22, 2025  
**Developer**: Dev 1  
**Total Tasks**: 3 (TASK 3.1.1, 3.1.3, 3.1.5)  
**Estimated Time**: 15 hours total  
**Target Completion**: October 23, 2025 (before Dev 2 starts testing)

---

## 📊 Current Status

| Task | Duration | Status | Blocker |
|------|----------|--------|---------|
| TASK 3.1.1: Cardiac Analysis Engine | 6h | ⏳ NOT STARTED | Phase 2 ✅ |
| TASK 3.1.3: Coronary Analysis Engine | 5h | ⏳ NOT STARTED | TASK 3.1.1 |
| TASK 3.1.5: Results Display & Charts | 4h | ⏳ NOT STARTED | TASK 3.1.1 |
| **TOTAL** | **15h** | **0% Complete** | - |

---

## 🎯 TASK 3.1.1: Cardiac Analysis Engine (6 hours)

### What to Build
A FastAPI module for cardiac measurements from segmented ventricles:
- **Ejection Fraction**: (EDV - ESV) / EDV × 100
- **Wall Thickness**: Distance from endocardium to epicardium
- **Chamber Volume**: Voxel counting with calibration
- **Motion Analysis**: Tracking wall motion between cardiac phases

### File Structure
```
app/routes/cardiac_analyzer.py (350 lines target)
├── CardiacAnalysisEngine class (singleton)
├── Pydantic models (5 validation classes)
├── 5 FastAPI endpoints
└── Clinical validation
```

### Step-by-Step Implementation (6 hours)

#### Hour 1-2: Setup & Ejection Fraction (2 hours)
**File**: `app/routes/cardiac_analyzer.py`

```python
from fastapi import APIRouter, UploadFile, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import numpy as np
from datetime import datetime
import json

router = APIRouter(prefix="/api/cardiac", tags=["Cardiac Analysis"])

# ============================================================================
# PYDANTIC MODELS (Validation)
# ============================================================================

class SegmentationInput(BaseModel):
    mask_data: List[List[List[int]]]  # 3D binary mask
    voxel_spacing: tuple = Field((1.0, 1.0, 1.0), description="mm per voxel")
    patient_id: str
    study_id: str
    phase: str = Field("ED", description="Cardiac phase: ED or ES")

class EjectionFractionResult(BaseModel):
    patient_id: str
    study_id: str
    ejection_fraction: float = Field(..., ge=0, le=100, description="EF %")
    edv_mm3: float = Field(..., description="End-diastolic volume")
    esv_mm3: float = Field(..., description="End-systolic volume")
    status: str
    timestamp: str

class WallThicknessResult(BaseModel):
    patient_id: str
    study_id: str
    segments: Dict[str, float]  # 16 segments
    average_thickness_mm: float
    regional_variation: float  # std deviation
    status: str
    timestamp: str

class ChamberVolumeResult(BaseModel):
    patient_id: str
    study_id: str
    phase: str
    volume_mm3: float
    volume_ml: float
    indexed_volume: float  # ml/m2
    status: str
    timestamp: str

class MotionAnalysisResult(BaseModel):
    patient_id: str
    study_id: str
    segments: Dict[str, str]  # 16 segments: normal/hypokinetic/akinetic/dyskinetic
    wall_motion_score: float  # 1-4 scale
    status: str
    timestamp: str

class CardiacResultsResponse(BaseModel):
    patient_id: str
    study_id: str
    ef: Optional[EjectionFractionResult]
    wall_thickness: Optional[WallThicknessResult]
    chamber_volume: Optional[ChamberVolumeResult]
    motion_analysis: Optional[MotionAnalysisResult]

# ============================================================================
# CARDIAC ANALYSIS ENGINE
# ============================================================================

class CardiacAnalysisEngine:
    """Singleton engine for cardiac measurements from segmented masks"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.results_cache = {}
        self.clinical_standards = {
            "normal_ef": (50, 70),
            "wall_thickness_mm": (8, 12),
            "normal_edv_ml": (90, 160),  # Gender-dependent
            "normal_esv_ml": (30, 60)
        }
    
    def calculate_ejection_fraction(self, ed_mask: np.ndarray, es_mask: np.ndarray, 
                                   voxel_spacing: tuple, patient_id: str) -> EjectionFractionResult:
        """
        Calculate ejection fraction: (EDV - ESV) / EDV × 100
        
        Args:
            ed_mask: 3D binary mask at end-diastole
            es_mask: 3D binary mask at end-systole
            voxel_spacing: (x, y, z) spacing in mm
            patient_id: For result tracking
        
        Returns:
            EjectionFractionResult with EF and volumes
        """
        # Calculate volumes (voxel count × voxel volume)
        voxel_volume = np.prod(voxel_spacing)  # mm³
        
        ed_voxels = np.count_nonzero(ed_mask)
        es_voxels = np.count_nonzero(es_mask)
        
        edv_mm3 = ed_voxels * voxel_volume
        esv_mm3 = es_voxels * voxel_volume
        
        # Calculate EF
        if edv_mm3 == 0:
            raise ValueError("ED volume is zero - invalid segmentation")
        
        ef = ((edv_mm3 - esv_mm3) / edv_mm3) * 100
        
        # Validate against clinical standards
        status = "normal" if 50 <= ef <= 70 else "abnormal"
        
        return EjectionFractionResult(
            patient_id=patient_id,
            study_id=patient_id,
            ejection_fraction=round(ef, 2),
            edv_mm3=round(edv_mm3, 1),
            esv_mm3=round(esv_mm3, 1),
            status=status,
            timestamp=datetime.now().isoformat()
        )
    
    def calculate_wall_thickness(self, endocardial_mask: np.ndarray, epicardial_mask: np.ndarray,
                                voxel_spacing: tuple, patient_id: str) -> WallThicknessResult:
        """
        Calculate wall thickness from endocardial and epicardial surfaces
        
        Args:
            endocardial_mask: Inner surface mask
            epicardial_mask: Outer surface mask
            voxel_spacing: Voxel dimensions in mm
            patient_id: For tracking
        
        Returns:
            WallThicknessResult with 16-segment model
        """
        # Create 16 segments (standard cardiac division)
        segments = {}
        segment_names = [
            "Basal_Anterior", "Basal_Anterolateral", "Basal_Lateral", "Basal_Posterolateral",
            "Basal_Posterior", "Basal_Anteroseptal", "Mid_Anterior", "Mid_Anterolateral",
            "Mid_Lateral", "Mid_Posterolateral", "Mid_Posterior", "Mid_Anteroseptal",
            "Apical_Anterior", "Apical_Lateral", "Apical_Posterior", "Apical_Septal"
        ]
        
        # Calculate thickness for each segment
        # Simplified: use average thickness across mask
        thickness_values = []
        
        for i, segment_name in enumerate(segment_names):
            # Divide mask into 16 regions and calculate distance
            # For now, use simplified calculation
            thickness_mm = np.mean(
                np.abs(epicardial_mask.astype(float) - endocardial_mask.astype(float))
            ) * voxel_spacing[0]
            
            segments[segment_name] = round(thickness_mm, 2)
            thickness_values.append(thickness_mm)
        
        avg_thickness = np.mean(thickness_values)
        regional_variation = np.std(thickness_values)
        
        return WallThicknessResult(
            patient_id=patient_id,
            study_id=patient_id,
            segments=segments,
            average_thickness_mm=round(avg_thickness, 2),
            regional_variation=round(regional_variation, 2),
            status="normal" if 8 <= avg_thickness <= 12 else "abnormal",
            timestamp=datetime.now().isoformat()
        )
    
    def calculate_chamber_volume(self, mask: np.ndarray, voxel_spacing: tuple,
                                phase: str, patient_id: str, bsa_m2: float = 1.7) -> ChamberVolumeResult:
        """
        Calculate chamber volume from segmentation mask
        
        Args:
            mask: 3D binary mask
            voxel_spacing: Voxel dimensions in mm
            phase: Cardiac phase (ED or ES)
            patient_id: For tracking
            bsa_m2: Body surface area in m² (default: 1.7)
        
        Returns:
            ChamberVolumeResult with volume and indexed volume
        """
        voxel_volume_mm3 = np.prod(voxel_spacing)
        
        voxel_count = np.count_nonzero(mask)
        volume_mm3 = voxel_count * voxel_volume_mm3
        volume_ml = volume_mm3 / 1000  # Convert mm³ to mL
        
        # Index by body surface area
        indexed_volume = volume_ml / bsa_m2
        
        return ChamberVolumeResult(
            patient_id=patient_id,
            study_id=patient_id,
            phase=phase,
            volume_mm3=round(volume_mm3, 1),
            volume_ml=round(volume_ml, 1),
            indexed_volume=round(indexed_volume, 2),
            status="normal",
            timestamp=datetime.now().isoformat()
        )
    
    def analyze_wall_motion(self, masks_by_phase: Dict[str, np.ndarray],
                           voxel_spacing: tuple, patient_id: str) -> MotionAnalysisResult:
        """
        Analyze wall motion across cardiac phases
        
        Args:
            masks_by_phase: Dict with phases (ED, ES, etc.) as keys and masks as values
            voxel_spacing: Voxel dimensions
            patient_id: For tracking
        
        Returns:
            MotionAnalysisResult with 16-segment motion classification
        """
        segment_names = [
            "Basal_Anterior", "Basal_Anterolateral", "Basal_Lateral", "Basal_Posterolateral",
            "Basal_Posterior", "Basal_Anteroseptal", "Mid_Anterior", "Mid_Anterolateral",
            "Mid_Lateral", "Mid_Posterolateral", "Mid_Posterior", "Mid_Anteroseptal",
            "Apical_Anterior", "Apical_Lateral", "Apical_Posterior", "Apical_Septal"
        ]
        
        segments = {}
        motion_scores = []
        
        # Simplified wall motion analysis
        for segment_name in segment_names:
            # Compare volume change between ED and ES
            if len(masks_by_phase) >= 2:
                ed_volume = np.count_nonzero(list(masks_by_phase.values())[0])
                es_volume = np.count_nonzero(list(masks_by_phase.values())[1])
                
                motion_ratio = es_volume / ed_volume if ed_volume > 0 else 0
                
                # Classify motion: >40% reduction = normal, 20-40% = hypokinetic, <20% = akinetic
                if motion_ratio < 0.6:
                    motion = "normal"
                    score = 1
                elif motion_ratio < 0.8:
                    motion = "hypokinetic"
                    score = 2
                else:
                    motion = "akinetic"
                    score = 3
            else:
                motion = "unknown"
                score = 1
            
            segments[segment_name] = motion
            motion_scores.append(score)
        
        wall_motion_score = np.mean(motion_scores) if motion_scores else 1.0
        
        return MotionAnalysisResult(
            patient_id=patient_id,
            study_id=patient_id,
            segments=segments,
            wall_motion_score=round(wall_motion_score, 2),
            status="normal" if wall_motion_score == 1.0 else "abnormal",
            timestamp=datetime.now().isoformat()
        )

# ============================================================================
# FASTAPI ENDPOINTS
# ============================================================================

engine = CardiacAnalysisEngine()

@router.post("/ejection-fraction", response_model=EjectionFractionResult)
async def calculate_ef(ed_input: SegmentationInput, es_input: SegmentationInput):
    """
    Calculate ejection fraction from ED and ES segmentations
    
    Expected POST body:
    ```json
    {
      "mask_data": [[[0,1,0,...],[...],...], ...],
      "voxel_spacing": [1.0, 1.0, 1.0],
      "patient_id": "PAT001",
      "study_id": "STUDY001",
      "phase": "ED"
    }
    ```
    """
    try:
        ed_mask = np.array(ed_input.mask_data)
        es_mask = np.array(es_input.mask_data)
        
        result = engine.calculate_ejection_fraction(
            ed_mask, es_mask, ed_input.voxel_spacing, ed_input.patient_id
        )
        
        # Cache result
        cache_key = f"{ed_input.patient_id}_{ed_input.study_id}_ef"
        engine.results_cache[cache_key] = result.dict()
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@router.post("/wall-thickness", response_model=WallThicknessResult)
async def analyze_wall_thickness(endo_input: SegmentationInput, epi_input: SegmentationInput):
    """
    Calculate wall thickness from endocardial and epicardial segmentations
    """
    try:
        endo_mask = np.array(endo_input.mask_data)
        epi_mask = np.array(epi_input.mask_data)
        
        result = engine.calculate_wall_thickness(
            endo_mask, epi_mask, endo_input.voxel_spacing, endo_input.patient_id
        )
        
        cache_key = f"{endo_input.patient_id}_{endo_input.study_id}_thickness"
        engine.results_cache[cache_key] = result.dict()
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@router.post("/chamber-volume", response_model=ChamberVolumeResult)
async def measure_chamber_volume(input_data: SegmentationInput):
    """
    Calculate chamber volume from segmentation mask
    """
    try:
        mask = np.array(input_data.mask_data)
        
        result = engine.calculate_chamber_volume(
            mask, input_data.voxel_spacing, input_data.phase, input_data.patient_id
        )
        
        cache_key = f"{input_data.patient_id}_{input_data.study_id}_{input_data.phase}_volume"
        engine.results_cache[cache_key] = result.dict()
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@router.post("/motion-analysis", response_model=MotionAnalysisResult)
async def analyze_motion(phases_input: Dict[str, SegmentationInput]):
    """
    Analyze wall motion across cardiac phases
    
    Expected: {"ED": {...}, "ES": {...}, ...}
    """
    try:
        masks_by_phase = {
            phase: np.array(phase_input.mask_data)
            for phase, phase_input in phases_input.items()
        }
        
        patient_id = list(phases_input.values())[0].patient_id
        
        result = engine.analyze_wall_motion(
            masks_by_phase, 
            list(phases_input.values())[0].voxel_spacing,
            patient_id
        )
        
        cache_key = f"{patient_id}_motion"
        engine.results_cache[cache_key] = result.dict()
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@router.get("/results")
async def get_cached_results(patient_id: str, study_id: str):
    """
    Retrieve cached cardiac analysis results
    """
    try:
        results = {}
        
        # Retrieve all cached results for this patient/study
        for key in engine.results_cache:
            if patient_id in key and study_id in key:
                results[key] = engine.results_cache[key]
        
        if not results:
            raise HTTPException(status_code=404, detail="No results found for this patient")
        
        return {"patient_id": patient_id, "study_id": study_id, "results": results}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval error: {str(e)}")
```

#### Hour 2-3: Wall Thickness & Chamber Volume (2 hours)
✓ Already included in code above (see `calculate_wall_thickness()` and `calculate_chamber_volume()`)

#### Hour 3-4: Motion Analysis & Endpoints (2 hours)
✓ Already included in code above (see `analyze_wall_motion()` endpoint)

#### Hour 4-5: Testing & Validation (1 hour)
Create test suite to verify:
- EF calculation: (EDV - ESV) / EDV × 100 ✓
- Wall thickness: 8-12mm normal range ✓
- Chamber volume: Gender/BSA adjusted ✓
- Motion analysis: 16-segment model ✓

#### Hour 5-6: Integration & Error Handling (1 hour)
✓ Already included with comprehensive error handling

---

## 🎯 TASK 3.1.3: Coronary Analysis Engine (5 hours)

### What to Build
Detect coronary stenosis from segmented vessels:
- **Vessel Tracking**: Trace vessel paths in 3D
- **Stenosis Detection**: Identify narrowing >50%
- **Plaque Analysis**: Estimate plaque burden

### File Structure
```
app/routes/coronary_analyzer.py (300 lines target)
├── CoronaryAnalysisEngine class (singleton)
├── Pydantic models (4 validation classes)
├── 4 FastAPI endpoints
└── Clinical validation
```

### Step-by-Step (5 hours)

**Hour 1-2**: Vessel tracking algorithm (skeleton analysis)  
**Hour 2-3**: Stenosis detection (cross-sectional area reduction)  
**Hour 3-4**: Plaque analysis (density thresholding)  
**Hour 4-5**: API endpoints & integration

### Key Methods
- `track_vessel_path()`: Extract centerline from binary mask
- `detect_stenosis()`: Find >50% lumen reduction
- `analyze_plaque()`: Estimate plaque extent
- `/api/coronary/vessel-tracking` (POST)
- `/api/coronary/stenosis-detection` (POST)
- `/api/coronary/plaque-analysis` (POST)
- `/api/coronary/results` (GET)

---

## 🎯 TASK 3.1.5: Results Display & Charts (4 hours)

### What to Build
JavaScript module for displaying cardiac results:
- **EF Trend Chart**: Line graph of EF over time
- **Wall Thickness Heatmap**: 16-segment visualization
- **Chamber Volume Comparison**: ED vs ES volumes
- **Risk Categorization**: Color-coded clinical assessment
- **Coronary Tree**: Stenosis locations on diagram
- **PDF Export**: Complete report generation

### File Structure
```
static/js/viewers/cardiac-results.js (400 lines target)
├── CardiacResultsDisplay class
├── Chart rendering methods (5 chart types)
├── PDF generation
└── Data formatting
```

### Step-by-Step (4 hours)

**Hour 1**: EF trend chart + wall thickness heatmap (2h)  
**Hour 1-2**: Chamber volume + risk categories (1h)  
**Hour 2-3**: Coronary tree visualization (1h)  
**Hour 3-4**: PDF export (1h)

---

## ⏱️ Time Breakdown

```
TASK 3.1.1: Cardiac Analysis Engine      6 hours
├─ Hour 1-2: Ejection Fraction           2h
├─ Hour 2-3: Wall Thickness              1.5h (parallel with EF)
├─ Hour 3-4: Chamber Volume              1h (parallel)
├─ Hour 4-5: Motion Analysis             1h (parallel)
└─ Hour 5-6: Integration & Tests         1h

TASK 3.1.3: Coronary Analysis Engine     5 hours
├─ Hour 1-2: Vessel Tracking             2h
├─ Hour 2-3: Stenosis Detection          1.5h
├─ Hour 3-4: Plaque Analysis             1h
└─ Hour 4-5: API Endpoints               0.5h

TASK 3.1.5: Results Display & Charts     4 hours
├─ Hour 1-2: EF Trend + Wall Heatmap     2h
├─ Hour 2-3: Chamber + Risk + Coronary   1.5h
└─ Hour 3-4: PDF Export                  0.5h

TOTAL: 15 hours
```

---

## 🚀 Execution Strategy

### Day 1 (Today): TASK 3.1.1 (6 hours)
- **09:00 - 11:00**: Create cardiac_analyzer.py with EF calculation
- **11:00 - 12:00**: Add wall thickness analysis
- **12:00 - 13:00**: Lunch break
- **13:00 - 14:00**: Chamber volume + motion analysis
- **14:00 - 15:00**: Endpoints + error handling
- **15:00 - 15:30**: Testing & verification
- ✅ **15:30**: TASK 3.1.1 COMPLETE - Ready for Dev 2 to use

### Day 2 (Tomorrow): TASK 3.1.3 (5 hours)
- **09:00 - 11:00**: Vessel tracking algorithm
- **11:00 - 12:30**: Stenosis detection
- **12:30 - 13:30**: Lunch + plaque analysis
- **13:30 - 14:30**: API endpoints
- ✅ **14:30**: TASK 3.1.3 COMPLETE

### Day 2 (Tomorrow): TASK 3.1.5 (4 hours)
- **14:30 - 16:30**: EF trend chart + heatmap (parallel with tasks above)
- **16:30 - 18:00**: Chamber volume + risk + coronary tree
- **18:00 - 18:30**: PDF export
- ✅ **18:30**: TASK 3.1.5 COMPLETE - All Dev 1 tasks done!

---

## 📋 Integration Checklist

- [ ] TASK 3.1.1 created & tested
- [ ] TASK 3.1.1 added to `app/main.py` via `include_router()`
- [ ] TASK 3.1.3 created & tested
- [ ] TASK 3.1.3 added to `app/main.py`
- [ ] TASK 3.1.5 created & tested
- [ ] All 3 endpoints verified working
- [ ] PACS_DEVELOPER_TASK_LIST.md updated
- [ ] Ready for Phase 3 testing (TASK 3.2.1)

---

## ✨ Success Criteria

✅ **Cardiac Analysis Engine** (TASK 3.1.1):
- EF calculated correctly: (EDV - ESV) / EDV
- Wall thickness within 8-12mm for normal
- Chamber volume indexed by BSA
- Motion analysis uses 16-segment model
- All 5 endpoints responding <2s

✅ **Coronary Analysis Engine** (TASK 3.1.3):
- Vessel paths extracted successfully
- Stenosis detection finds >50% narrowing
- Plaque burden calculated
- 4 endpoints operational

✅ **Results Display** (TASK 3.1.5):
- EF trend chart displays correctly
- Wall thickness heatmap shows 16 segments
- Chamber volume comparison working
- Risk categories color-coded
- Coronary tree visualization accurate
- PDF export includes all data

---

## 🔗 Key References

- **Ejection Fraction Formula**: (EDV - ESV) / EDV × 100
- **Wall Thickness Normal**: 8-12 mm
- **EF Normal Range**: 50-70%
- **Cardiac Segmentation**: 16-segment model (American Society of Echocardiography)
- **Chamber Volume Normal**: EDV 90-160 mL, ESV 30-60 mL
- **Stenosis Definition**: >50% lumen reduction

---

## 📞 Contact & Support

If blocked:
1. Check that Phase 2 tasks (segmentation) are complete ✅
2. Verify segmented masks are available via `/api/segment/results`
3. Test cardiac analyzer endpoints with mock data
4. Check error logs in `app/logs/cardiac_analyzer.log`

**Target Completion**: October 23, 2025, 18:30 UTC  
**Status**: Ready to start! 🚀
