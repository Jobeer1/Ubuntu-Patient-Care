"""
3D Viewer API Routes
Phase 1: 3D Volumetric Viewing and MPR
Endpoints for loading studies, getting slices, and MPR reconstruction
"""

import logging
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
import numpy as np

from app.ml_models.dicom_processor import get_processor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/viewer", tags=["3D Viewer"])


# ============================================================================
# Pydantic Models for Request/Response Validation
# ============================================================================

class LoadStudyRequest(BaseModel):
    """Request to load a DICOM study"""
    study_id: str
    series_id: Optional[str] = None
    window_center: int = 40
    window_width: int = 400


class LoadStudyResponse(BaseModel):
    """Response with study metadata and initial data"""
    study_id: str
    series_id: str
    volume_shape: tuple
    num_slices: int
    spacing: tuple
    thumbnail_url: str
    status: str = "success"


class SliceResponse(BaseModel):
    """Response with a single slice of data"""
    slice_index: int
    data: list  # Serialized as list for JSON
    width: int
    height: int
    min_value: float
    max_value: float


class MetadataResponse(BaseModel):
    """DICOM metadata response"""
    study_id: str
    series_id: str
    patient_name: Optional[str]
    patient_id: Optional[str]
    modality: str
    size: tuple
    spacing: tuple
    origin: tuple
    num_slices: int
    pixel_type: str


class MPRSliceRequest(BaseModel):
    """Request for MPR slice reconstruction"""
    study_id: str
    plane: str  # 'axial', 'sagittal', 'coronal'
    position: float  # 0.0-1.0 normalized position


class MPRSliceResponse(BaseModel):
    """Response with MPR slice"""
    plane: str
    position: float
    data: list
    width: int
    height: int


# ============================================================================
# In-Memory Cache for Loaded Studies
# ============================================================================

_loaded_studies = {}  # Cache: {study_id: {'volume': ndarray, 'metadata': dict, ...}}


def cache_study(study_id: str, volume: np.ndarray, metadata: Dict):
    """Cache a loaded study in memory"""
    _loaded_studies[study_id] = {
        'volume': volume,
        'metadata': metadata,
        'cached_at': None,  # Could add timestamp
    }
    logger.info(f"Cached study {study_id}: shape={volume.shape}")


def get_cached_study(study_id: str) -> Optional[Dict]:
    """Retrieve cached study"""
    return _loaded_studies.get(study_id)


def clear_study_cache(study_id: str = None):
    """Clear study cache"""
    if study_id:
        if study_id in _loaded_studies:
            del _loaded_studies[study_id]
            logger.info(f"Cleared cache for study {study_id}")
    else:
        _loaded_studies.clear()
        logger.info("Cleared all study cache")


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/load-study", response_model=LoadStudyResponse)
async def load_study(request: LoadStudyRequest):
    """
    Load a DICOM study for 3D visualization
    
    Args:
        request: LoadStudyRequest with study_id and optional series_id
        
    Returns:
        LoadStudyResponse with metadata and thumbnail
        
    Example:
        POST /api/viewer/load-study
        {
            "study_id": "study_001",
            "series_id": "series_001",
            "window_center": 40,
            "window_width": 400
        }
    """
    try:
        logger.info(f"Loading study: {request.study_id}")
        
        # Check if already cached
        cached = get_cached_study(request.study_id)
        if cached:
            logger.info(f"Returning cached study {request.study_id}")
            metadata = cached['metadata']
            return LoadStudyResponse(
                study_id=request.study_id,
                series_id=request.series_id or metadata.get('series_id', 'unknown'),
                volume_shape=metadata['size'],
                num_slices=metadata['size'][0],
                spacing=metadata['spacing'],
                thumbnail_url=f"/api/viewer/thumbnail/{request.study_id}",
                status="cached"
            )
        
        # TODO: Load from Orthanc database
        # This is a placeholder - actual implementation would query Orthanc
        # processor = get_processor()
        # dicom_data = processor.process_dicom_series(dicom_path, ...)
        
        # For now, return example response
        raise HTTPException(
            status_code=501,
            detail="Study loading not yet implemented - awaiting Orthanc integration"
        )
        
    except Exception as e:
        logger.error(f"Error loading study: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get-slice/{study_id}")
async def get_slice(
    study_id: str,
    slice_index: int = Query(0, ge=0),
    normalize: bool = Query(True)
) -> SliceResponse:
    """
    Get a single slice from loaded study
    
    Args:
        study_id: Study ID
        slice_index: Index of slice (0 to num_slices-1)
        normalize: Whether to normalize to 0-1 range
        
    Returns:
        SliceResponse with slice data
        
    Example:
        GET /api/viewer/get-slice/study_001?slice_index=50&normalize=true
    """
    try:
        cached = get_cached_study(study_id)
        if not cached:
            raise HTTPException(status_code=404, detail=f"Study {study_id} not loaded")
        
        volume = cached['volume']
        
        if slice_index < 0 or slice_index >= volume.shape[0]:
            raise HTTPException(
                status_code=400,
                detail=f"Slice index {slice_index} out of range [0, {volume.shape[0]-1}]"
            )
        
        # Get slice data
        slice_data = volume[slice_index, :, :]
        
        # Convert to list for JSON serialization
        slice_list = slice_data.tolist()
        
        return SliceResponse(
            slice_index=slice_index,
            data=slice_list,
            width=slice_data.shape[1],
            height=slice_data.shape[0],
            min_value=float(slice_data.min()),
            max_value=float(slice_data.max()),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting slice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get-metadata/{study_id}", response_model=MetadataResponse)
async def get_metadata(study_id: str):
    """
    Get DICOM metadata for study
    
    Args:
        study_id: Study ID
        
    Returns:
        MetadataResponse with study information
        
    Example:
        GET /api/viewer/get-metadata/study_001
    """
    try:
        cached = get_cached_study(study_id)
        if not cached:
            raise HTTPException(status_code=404, detail=f"Study {study_id} not loaded")
        
        metadata = cached['metadata']
        
        return MetadataResponse(
            study_id=study_id,
            series_id=metadata.get('series_id', 'unknown'),
            patient_name=metadata.get('patient_name'),
            patient_id=metadata.get('patient_id'),
            modality=metadata.get('modality', 'CT'),
            size=metadata.get('size', (0, 0, 0)),
            spacing=metadata.get('spacing', (1, 1, 1)),
            origin=metadata.get('origin', (0, 0, 0)),
            num_slices=metadata.get('size', [0])[0],
            pixel_type=metadata.get('pixel_type', 'uint16'),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mpr-slice", response_model=MPRSliceResponse)
async def get_mpr_slice(request: MPRSliceRequest):
    """
    Get Multiplanar Reconstruction slice
    
    Args:
        request: MPRSliceRequest with study_id, plane, and position
        
    Returns:
        MPRSliceResponse with reconstructed slice
        
    Planes:
        - 'axial': Z plane (default CT viewing)
        - 'sagittal': Y plane (left-right)
        - 'coronal': X plane (front-back)
        
    Position:
        - 0.0 = start
        - 1.0 = end
        - 0.5 = middle
        
    Example:
        POST /api/viewer/mpr-slice
        {
            "study_id": "study_001",
            "plane": "sagittal",
            "position": 0.5
        }
    """
    try:
        cached = get_cached_study(request.study_id)
        if not cached:
            raise HTTPException(status_code=404, detail=f"Study {request.study_id} not loaded")
        
        volume = cached['volume']
        
        # Validate plane
        if request.plane not in ['axial', 'sagittal', 'coronal']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid plane '{request.plane}'. Must be: axial, sagittal, coronal"
            )
        
        # Validate position
        if not 0.0 <= request.position <= 1.0:
            raise HTTPException(
                status_code=400,
                detail=f"Position must be between 0.0 and 1.0"
            )
        
        # Extract MPR slice based on plane
        if request.plane == 'axial':
            # Z plane (normal CT view)
            idx = int(request.position * (volume.shape[0] - 1))
            mpr_slice = volume[idx, :, :]
            
        elif request.plane == 'sagittal':
            # Y plane (left-right)
            idx = int(request.position * (volume.shape[1] - 1))
            mpr_slice = volume[:, idx, :]
            
        else:  # coronal
            # X plane (front-back)
            idx = int(request.position * (volume.shape[2] - 1))
            mpr_slice = volume[:, :, idx]
        
        # Convert to list for JSON
        mpr_list = mpr_slice.tolist()
        
        return MPRSliceResponse(
            plane=request.plane,
            position=request.position,
            data=mpr_list,
            width=mpr_slice.shape[1],
            height=mpr_slice.shape[0],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting MPR slice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thumbnail/{study_id}")
async def get_thumbnail(study_id: str):
    """
    Get thumbnail image for study preview
    
    Args:
        study_id: Study ID
        
    Returns:
        PNG image as bytes
        
    Example:
        GET /api/viewer/thumbnail/study_001
    """
    try:
        cached = get_cached_study(study_id)
        if not cached:
            raise HTTPException(status_code=404, detail=f"Study {study_id} not loaded")
        
        # TODO: Implement thumbnail image generation (PNG/JPEG)
        # For now, return placeholder
        raise HTTPException(
            status_code=501,
            detail="Thumbnail generation not yet implemented"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thumbnail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear-cache/{study_id}")
async def clear_cache(study_id: str):
    """
    Clear cached study from memory
    
    Args:
        study_id: Study ID to clear, or '*' to clear all
        
    Returns:
        Success message
        
    Example:
        DELETE /api/viewer/clear-cache/study_001
    """
    try:
        if study_id == "*":
            clear_study_cache()
            return {"status": "success", "message": "All studies cleared from cache"}
        else:
            clear_study_cache(study_id)
            return {"status": "success", "message": f"Study {study_id} cleared from cache"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache-status")
async def get_cache_status():
    """
    Get status of study cache
    
    Returns:
        Dictionary with cache statistics
        
    Example:
        GET /api/viewer/cache-status
    """
    try:
        studies = []
        total_size = 0
        
        for study_id, data in _loaded_studies.items():
            volume = data['volume']
            size_mb = (volume.nbytes / 1024 / 1024)
            total_size += size_mb
            
            studies.append({
                'study_id': study_id,
                'shape': volume.shape,
                'size_mb': round(size_mb, 2),
                'dtype': str(volume.dtype),
            })
        
        return {
            'status': 'success',
            'num_studies': len(studies),
            'total_size_mb': round(total_size, 2),
            'studies': studies,
        }
        
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Orthanc Integration Endpoints
# ============================================================================

from app.ml_models.orthanc_client import get_orthanc_client
from app.models import DicomStudy, Measurement
from sqlalchemy.orm import Session
from app.database import get_db
from fastapi import Depends


@router.get("/orthanc/health")
async def check_orthanc_health():
    """
    Check if Orthanc server is running
    
    Returns:
        Dictionary with Orthanc health status
        
    Example:
        GET /api/viewer/orthanc/health
    """
    try:
        client = get_orthanc_client()
        is_healthy = await client.health_check()
        
        if is_healthy:
            info = await client.get_server_info()
            return {
                "status": "healthy",
                "orthanc_available": True,
                "server_info": info,
            }
        else:
            return {
                "status": "unhealthy",
                "orthanc_available": False,
                "message": "Orthanc server is not reachable",
            }
    except Exception as e:
        logger.error(f"Orthanc health check failed: {e}")
        return {
            "status": "error",
            "orthanc_available": False,
            "error": str(e),
        }


@router.get("/orthanc/patients")
async def get_orthanc_patients():
    """
    Get list of all patients from Orthanc
    
    Returns:
        List of patients with basic info
        
    Example:
        GET /api/viewer/orthanc/patients
    """
    try:
        client = get_orthanc_client()
        patients = await client.get_all_patients()
        
        return {
            "status": "success",
            "count": len(patients),
            "patients": patients,
        }
    except Exception as e:
        logger.error(f"Error fetching Orthanc patients: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orthanc/studies")
async def get_orthanc_studies():
    """
    Get list of all studies from Orthanc
    
    Returns:
        List of studies with metadata
        
    Example:
        GET /api/viewer/orthanc/studies
    """
    try:
        client = get_orthanc_client()
        studies = await client.get_all_studies()
        
        return {
            "status": "success",
            "count": len(studies),
            "studies": studies,
        }
    except Exception as e:
        logger.error(f"Error fetching Orthanc studies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class LoadOrthancStudyRequest(BaseModel):
    """Request to load a study from Orthanc"""
    orthanc_study_id: str
    orthanc_series_id: str
    window_center: int = 40
    window_width: int = 400


@router.post("/orthanc/load-study")
async def load_orthanc_study(
    request: LoadOrthancStudyRequest,
    db: Session = Depends(get_db)
):
    """
    Load a DICOM study directly from Orthanc
    
    Steps:
    1. Fetch DICOM files from Orthanc
    2. Process with DICOM processor
    3. Store metadata in database
    4. Cache in memory for fast access
    
    Args:
        request: LoadOrthancStudyRequest with study IDs
        db: Database session
        
    Returns:
        Study metadata and availability status
        
    Example:
        POST /api/viewer/orthanc/load-study
        {
            "orthanc_study_id": "0123456789-abcdef",
            "orthanc_series_id": "fedcba9876543210",
            "window_center": 40,
            "window_width": 400
        }
    """
    try:
        client = get_orthanc_client()
        
        # Get series info from Orthanc
        series_info = await client.get_series(request.orthanc_series_id)
        if not series_info:
            raise HTTPException(status_code=404, detail="Series not found in Orthanc")
        
        # Get study info
        study_info = await client.get_study(request.orthanc_study_id)
        if not study_info:
            raise HTTPException(status_code=404, detail="Study not found in Orthanc")
        
        # Check if already in database
        db_study = db.query(DicomStudy).filter(
            DicomStudy.orthanc_study_id == request.orthanc_study_id
        ).first()
        
        if not db_study:
            # Create new study record
            db_study = DicomStudy(
                orthanc_study_id=request.orthanc_study_id,
                orthanc_patient_id=study_info.get("ParentPatient", "unknown"),
                patient_name=study_info.get("patient_name", "Unknown"),
                study_description=study_info.get("study_description", "Unnamed Study"),
                study_date=study_info.get("study_date"),
                study_time=study_info.get("study_time"),
                modality=study_info.get("modality", "UNKNOWN"),
                num_series=len(study_info.get("Series", [])),
                num_instances=len(series_info.get("Instances", [])),
            )
            db.add(db_study)
            db.commit()
            db.refresh(db_study)
            logger.info(f"Created new study record: {db_study.id}")
        
        # Download DICOM files from Orthanc
        logger.info(f"Downloading DICOM series {request.orthanc_series_id} from Orthanc...")
        dicom_files = await client.get_series_dicom_files(request.orthanc_series_id)
        
        if not dicom_files:
            raise HTTPException(status_code=500, detail="Failed to download DICOM files from Orthanc")
        
        # Process DICOM files
        processor = get_processor()
        
        # Save files temporarily and process
        import tempfile
        import os
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write DICOM files
            for idx, dicom_bytes in enumerate(dicom_files):
                filepath = os.path.join(temp_dir, f"slice_{idx:04d}.dcm")
                with open(filepath, 'wb') as f:
                    f.write(dicom_bytes)
            
            # Process the series
            result = processor.process_dicom_series(temp_dir)
            
            if not result:
                raise HTTPException(status_code=500, detail="Failed to process DICOM series")
            
            volume, metadata = result
            
            # Normalize Hounsfield values
            volume_normalized = processor.normalize_hounsfield(
                volume,
                window_center=request.window_center,
                window_width=request.window_width
            )
            
            # Cache the volume
            cache_study(request.orthanc_study_id, volume_normalized, metadata)
        
        return {
            "status": "success",
            "study_id": request.orthanc_study_id,
            "db_study_id": db_study.id,
            "volume_shape": volume.shape,
            "num_slices": volume.shape[0],
            "spacing": metadata.get("spacing", (1, 1, 1)),
            "modality": study_info.get("modality", "CT"),
            "patient_name": db_study.patient_name,
            "study_description": db_study.study_description,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading Orthanc study: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error loading study: {str(e)}")


@router.get("/orthanc/studies/{orthanc_study_id}")
async def get_orthanc_study_details(orthanc_study_id: str, db: Session = Depends(get_db)):
    """
    Get detailed info about a study from Orthanc
    
    Args:
        orthanc_study_id: Orthanc study ID
        db: Database session
        
    Returns:
        Study details with series and measurements count
        
    Example:
        GET /api/viewer/orthanc/studies/0123456789-abcdef
    """
    try:
        client = get_orthanc_client()
        
        study_info = await client.get_study(orthanc_study_id)
        if not study_info:
            raise HTTPException(status_code=404, detail="Study not found")
        
        # Get db study if exists
        db_study = db.query(DicomStudy).filter(
            DicomStudy.orthanc_study_id == orthanc_study_id
        ).first()
        
        # Get measurements if in database
        measurements_count = 0
        if db_study:
            measurements_count = db.query(Measurement).filter(
                Measurement.study_id == db_study.id
            ).count()
        
        return {
            "status": "success",
            "orthanc_study_id": orthanc_study_id,
            "in_database": db_study is not None,
            "db_id": db_study.id if db_study else None,
            "study_info": study_info,
            "measurements_count": measurements_count,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Orthanc study details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        processor = get_processor()
        return {
            "status": "healthy",
            "service": "3D Viewer API",
            "version": "1.0.0",
            "dicom_processor": "available",
        }
    except Exception as e:
        return {
            "status": "degraded",
            "service": "3D Viewer API",
            "error": str(e),
        }
