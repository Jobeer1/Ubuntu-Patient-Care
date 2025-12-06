"""
Measurement Tools API Routes
Phase 1.2: DICOM Measurements and Analysis
Endpoints for creating, retrieving, and managing measurements
"""

import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Measurement, DicomStudy, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/measurements", tags=["Measurements"])


# ============================================================================
# Pydantic Models for Request/Response Validation
# ============================================================================

class MeasurementBase(BaseModel):
    """Base measurement model"""
    measurement_type: str  # 'distance', 'area', 'angle', 'volume', 'hu'
    label: Optional[str] = None
    description: Optional[str] = None
    value: str  # e.g., "45.2 mm", "1250 cm³", "340 HU"


class DistanceMeasurement(MeasurementBase):
    """Distance measurement between two points"""
    measurement_type: str = "distance"
    point1: tuple  # (x, y, z)
    point2: tuple  # (x, y, z)
    distance_mm: float


class AreaMeasurement(MeasurementBase):
    """Area measurement of ROI"""
    measurement_type: str = "area"
    polygon_points: List[tuple]  # List of (x, y) points
    area_mm2: float


class AngleMeasurement(MeasurementBase):
    """Angle measurement between three points"""
    measurement_type: str = "angle"
    point1: tuple  # (x, y, z)
    vertex: tuple  # (x, y, z)
    point3: tuple  # (x, y, z)
    angle_degrees: float


class VolumeMeasurement(MeasurementBase):
    """Volume measurement of segmented region"""
    measurement_type: str = "volume"
    volume_mm3: float
    num_voxels: int
    hu_min: Optional[int] = None
    hu_max: Optional[int] = None


class HUMeasurement(MeasurementBase):
    """Hounsfield Unit point measurement"""
    measurement_type: str = "hu"
    point: tuple  # (x, y, z)
    hu_value: int
    window_center: int = 40
    window_width: int = 400


class CreateMeasurementRequest(BaseModel):
    """Request to create a new measurement"""
    study_id: int
    measurement_type: str
    label: Optional[str] = None
    description: Optional[str] = None
    value: str
    measurement_data: Dict[str, Any]  # Type-specific data
    series_index: Optional[int] = None
    slice_index: Optional[int] = None


class MeasurementResponse(BaseModel):
    """Response with measurement data"""
    id: int
    study_id: int
    measurement_type: str
    label: Optional[str]
    description: Optional[str]
    value: str
    measurement_data: Dict[str, Any]
    series_index: Optional[int]
    slice_index: Optional[int]
    created_at: datetime
    created_by_user_id: int
    
    class Config:
        from_attributes = True


class StudyMeasurementsResponse(BaseModel):
    """Response with all measurements for a study"""
    study_id: int
    orthanc_study_id: str
    total_measurements: int
    measurements: List[MeasurementResponse]


# ============================================================================
# Measurement CRUD Endpoints
# ============================================================================

@router.post("/create", response_model=MeasurementResponse)
async def create_measurement(
    request: CreateMeasurementRequest,
    user_id: int,  # Would come from auth token in production
    db: Session = Depends(get_db)
):
    """
    Create a new measurement for a study
    
    Args:
        request: CreateMeasurementRequest with measurement details
        user_id: User ID creating the measurement
        db: Database session
        
    Returns:
        Created measurement
        
    Example:
        POST /api/measurements/create
        {
            "study_id": 1,
            "measurement_type": "distance",
            "label": "Tumor Size",
            "value": "45.2 mm",
            "measurement_data": {
                "point1": [100, 200, 50],
                "point2": [145, 200, 50],
                "distance_mm": 45.2,
                "unit": "mm"
            },
            "slice_index": 50
        }
    """
    try:
        # Verify study exists
        study = db.query(DicomStudy).filter(DicomStudy.id == request.study_id).first()
        if not study:
            raise HTTPException(status_code=404, detail="Study not found")
        
        # Create measurement
        measurement = Measurement(
            study_id=request.study_id,
            user_id=user_id,
            measurement_type=request.measurement_type,
            label=request.label,
            description=request.description,
            value=request.value,
            measurement_data=request.measurement_data,
            series_index=request.series_index,
            slice_index=request.slice_index,
        )
        
        db.add(measurement)
        db.commit()
        db.refresh(measurement)
        
        logger.info(f"Created {request.measurement_type} measurement: {measurement.id}")
        
        return MeasurementResponse(
            id=measurement.id,
            study_id=measurement.study_id,
            measurement_type=measurement.measurement_type,
            label=measurement.label,
            description=measurement.description,
            value=measurement.value,
            measurement_data=measurement.measurement_data,
            series_index=measurement.series_index,
            slice_index=measurement.slice_index,
            created_at=measurement.created_at,
            created_by_user_id=measurement.user_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating measurement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/study/{study_id}", response_model=StudyMeasurementsResponse)
async def get_study_measurements(
    study_id: int,
    measurement_type: Optional[str] = Query(None, description="Filter by type: distance, area, volume, angle, hu"),
    db: Session = Depends(get_db)
):
    """
    Get all measurements for a study
    
    Args:
        study_id: Database study ID
        measurement_type: Optional filter by measurement type
        db: Database session
        
    Returns:
        All measurements for the study
        
    Example:
        GET /api/measurements/study/1
        GET /api/measurements/study/1?measurement_type=distance
    """
    try:
        # Verify study exists
        study = db.query(DicomStudy).filter(DicomStudy.id == study_id).first()
        if not study:
            raise HTTPException(status_code=404, detail="Study not found")
        
        # Get measurements
        query = db.query(Measurement).filter(Measurement.study_id == study_id)
        
        if measurement_type:
            query = query.filter(Measurement.measurement_type == measurement_type)
        
        measurements = query.order_by(Measurement.created_at.desc()).all()
        
        return StudyMeasurementsResponse(
            study_id=study.id,
            orthanc_study_id=study.orthanc_study_id,
            total_measurements=len(measurements),
            measurements=[
                MeasurementResponse(
                    id=m.id,
                    study_id=m.study_id,
                    measurement_type=m.measurement_type,
                    label=m.label,
                    description=m.description,
                    value=m.value,
                    measurement_data=m.measurement_data,
                    series_index=m.series_index,
                    slice_index=m.slice_index,
                    created_at=m.created_at,
                    created_by_user_id=m.user_id,
                )
                for m in measurements
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching measurements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{measurement_id}", response_model=MeasurementResponse)
async def get_measurement(measurement_id: int, db: Session = Depends(get_db)):
    """
    Get a single measurement by ID
    
    Args:
        measurement_id: Measurement ID
        db: Database session
        
    Returns:
        Measurement data
        
    Example:
        GET /api/measurements/42
    """
    try:
        measurement = db.query(Measurement).filter(Measurement.id == measurement_id).first()
        
        if not measurement:
            raise HTTPException(status_code=404, detail="Measurement not found")
        
        return MeasurementResponse(
            id=measurement.id,
            study_id=measurement.study_id,
            measurement_type=measurement.measurement_type,
            label=measurement.label,
            description=measurement.description,
            value=measurement.value,
            measurement_data=measurement.measurement_data,
            series_index=measurement.series_index,
            slice_index=measurement.slice_index,
            created_at=measurement.created_at,
            created_by_user_id=measurement.user_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching measurement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{measurement_id}", response_model=MeasurementResponse)
async def update_measurement(
    measurement_id: int,
    request: CreateMeasurementRequest,
    db: Session = Depends(get_db)
):
    """
    Update an existing measurement
    
    Args:
        measurement_id: Measurement ID
        request: Updated measurement data
        db: Database session
        
    Returns:
        Updated measurement
        
    Example:
        PUT /api/measurements/42
        {
            "study_id": 1,
            "measurement_type": "distance",
            "label": "Updated Label",
            "value": "46.5 mm",
            "measurement_data": {...}
        }
    """
    try:
        measurement = db.query(Measurement).filter(Measurement.id == measurement_id).first()
        
        if not measurement:
            raise HTTPException(status_code=404, detail="Measurement not found")
        
        # Update fields
        measurement.label = request.label
        measurement.description = request.description
        measurement.value = request.value
        measurement.measurement_data = request.measurement_data
        measurement.series_index = request.series_index
        measurement.slice_index = request.slice_index
        measurement.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(measurement)
        
        logger.info(f"Updated measurement: {measurement.id}")
        
        return MeasurementResponse(
            id=measurement.id,
            study_id=measurement.study_id,
            measurement_type=measurement.measurement_type,
            label=measurement.label,
            description=measurement.description,
            value=measurement.value,
            measurement_data=measurement.measurement_data,
            series_index=measurement.series_index,
            slice_index=measurement.slice_index,
            created_at=measurement.created_at,
            created_by_user_id=measurement.user_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating measurement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{measurement_id}")
async def delete_measurement(measurement_id: int, db: Session = Depends(get_db)):
    """
    Delete a measurement
    
    Args:
        measurement_id: Measurement ID
        db: Database session
        
    Returns:
        Success status
        
    Example:
        DELETE /api/measurements/42
    """
    try:
        measurement = db.query(Measurement).filter(Measurement.id == measurement_id).first()
        
        if not measurement:
            raise HTTPException(status_code=404, detail="Measurement not found")
        
        db.delete(measurement)
        db.commit()
        
        logger.info(f"Deleted measurement: {measurement_id}")
        
        return {
            "status": "success",
            "message": f"Measurement {measurement_id} deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting measurement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Measurement Analytics
# ============================================================================

@router.get("/study/{study_id}/summary")
async def get_measurement_summary(study_id: int, db: Session = Depends(get_db)):
    """
    Get summary statistics of measurements for a study
    
    Args:
        study_id: Database study ID
        db: Database session
        
    Returns:
        Summary with counts by measurement type
        
    Example:
        GET /api/measurements/study/1/summary
    """
    try:
        study = db.query(DicomStudy).filter(DicomStudy.id == study_id).first()
        if not study:
            raise HTTPException(status_code=404, detail="Study not found")
        
        measurements = db.query(Measurement).filter(Measurement.study_id == study_id).all()
        
        # Group by type
        summary = {}
        for m in measurements:
            if m.measurement_type not in summary:
                summary[m.measurement_type] = 0
            summary[m.measurement_type] += 1
        
        return {
            "status": "success",
            "study_id": study_id,
            "total_measurements": len(measurements),
            "by_type": summary,
            "latest_measurement": measurements[0].created_at if measurements else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting measurement summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Measurement Export
# ============================================================================

@router.get("/study/{study_id}/export")
async def export_measurements(
    study_id: int,
    format: str = Query("json", regex="^(json|csv|excel)$"),
    db: Session = Depends(get_db)
):
    """
    Export measurements in specified format
    
    Args:
        study_id: Database study ID
        format: Export format (json, csv, or excel)
        db: Database session
        
    Returns:
        Exported measurements data
        
    Example:
        GET /api/measurements/study/1/export?format=json
        GET /api/measurements/study/1/export?format=csv
    """
    try:
        study = db.query(DicomStudy).filter(DicomStudy.id == study_id).first()
        if not study:
            raise HTTPException(status_code=404, detail="Study not found")
        
        measurements = db.query(Measurement).filter(Measurement.study_id == study_id).all()
        
        if format == "json":
            return {
                "status": "success",
                "study": {
                    "id": study.id,
                    "orthanc_study_id": study.orthanc_study_id,
                    "patient_name": study.patient_name,
                    "study_description": study.study_description,
                    "study_date": study.study_date,
                },
                "measurements": [
                    {
                        "id": m.id,
                        "type": m.measurement_type,
                        "label": m.label,
                        "value": m.value,
                        "data": m.measurement_data,
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in measurements
                ]
            }
        
        elif format == "csv":
            # CSV format
            rows = ["id,type,label,value,created_at"]
            for m in measurements:
                rows.append(f'{m.id},"{m.measurement_type}","{m.label or ""}","{m.value}","{m.created_at}"')
            return {"data": "\n".join(rows), "content_type": "text/csv"}
        
        elif format == "excel":
            # Return instructions for Excel export
            return {
                "status": "success",
                "message": "Use JSON export and convert with pandas/openpyxl",
                "json_url": f"/api/measurements/study/{study_id}/export?format=json"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting measurements: {e}")
        raise HTTPException(status_code=500, detail=str(e))
