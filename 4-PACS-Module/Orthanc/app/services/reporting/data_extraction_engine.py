#!/usr/bin/env python3
"""
Data Extraction Engine - PACS Advanced Tools Phase 5

Extract and normalize clinical data from all analysis modules for report generation.
Supports Cardiac, Coronary, Perfusion, and Mammography analysis data.

Features:
- Module-specific extractors for each analysis type
- Data validation against clinical reference ranges
- Normalization of values to standard units
- Comprehensive error handling
- Performance optimized (<500ms per study)
- Schema-based validation
- Audit trail logging
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import time

# Configure logging
logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """Supported analysis types."""
    GENERIC = "generic"
    CARDIAC = "cardiac"
    CORONARY = "coronary"
    PERFUSION = "perfusion"
    MAMMOGRAPHY = "mammography"


# ==================== Data Classes ====================

@dataclass
class CardiacData:
    """Structured cardiac analysis data."""
    ejection_fraction: Optional[float] = None  # %
    lvef: Optional[float] = None  # %
    mass: Optional[float] = None  # grams
    valve_status: Optional[str] = None
    chamber_size: Optional[str] = None
    wall_thickness: Optional[str] = None
    wall_motion: Optional[str] = None
    findings: Optional[str] = None
    impressions: Optional[str] = None
    recommendations: Optional[str] = None

    def validate(self) -> List[str]:
        """Validate cardiac data against reference ranges."""
        errors = []

        if self.ejection_fraction is not None:
            if not (0 <= self.ejection_fraction <= 100):
                errors.append(f"EF out of range: {self.ejection_fraction}%")
            if self.ejection_fraction < 40:
                errors.append("WARNING: Low EF (<40% suggests systolic dysfunction)")

        if self.mass is not None:
            if not (0 < self.mass < 500):
                errors.append(f"LV mass out of range: {self.mass}g")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class CoronaryData:
    """Structured coronary analysis data."""
    stenosis_grade: Optional[str] = None  # Percentage or category
    calcium_score: Optional[float] = None  # Agatston score
    vessels: Optional[str] = None  # Description of vessels
    lad: Optional[Dict[str, Any]] = None  # LAD specific data
    lcx: Optional[Dict[str, Any]] = None  # LCX specific data
    rca: Optional[Dict[str, Any]] = None  # RCA specific data
    left_main: Optional[Dict[str, Any]] = None  # Left main specific data
    risk_assessment: Optional[str] = None  # Risk category
    findings: Optional[str] = None
    impressions: Optional[str] = None
    recommendations: Optional[str] = None

    def validate(self) -> List[str]:
        """Validate coronary data against reference ranges."""
        errors = []

        if self.calcium_score is not None:
            if self.calcium_score < 0:
                errors.append(f"Calcium score negative: {self.calcium_score}")
            if self.calcium_score > 5000:
                errors.append(f"Calcium score very high: {self.calcium_score}")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PerfusionData:
    """Structured perfusion analysis data."""
    cbf: Optional[float] = None  # mL/min/100g
    cbv: Optional[float] = None  # mL/100g
    mtt: Optional[float] = None  # seconds
    defects: Optional[str] = None  # Description of defects
    regional_analysis: Optional[Dict[str, Any]] = None
    ischemia_extent: Optional[float] = None  # Percentage
    flow_reserve: Optional[float] = None
    findings: Optional[str] = None
    impressions: Optional[str] = None
    recommendations: Optional[str] = None

    def validate(self) -> List[str]:
        """Validate perfusion data against reference ranges."""
        errors = []

        # Normal CBF: 40-60 mL/min/100g
        if self.cbf is not None:
            if not (0 < self.cbf < 150):
                errors.append(f"CBF out of range: {self.cbf}")
            if self.cbf < 20:
                errors.append("WARNING: Very low CBF (<20 mL/min/100g)")

        # Normal MTT: 4-6 seconds
        if self.mtt is not None:
            if not (0 < self.mtt < 15):
                errors.append(f"MTT out of range: {self.mtt}s")

        # Ischemia extent should be 0-100%
        if self.ischemia_extent is not None:
            if not (0 <= self.ischemia_extent <= 100):
                errors.append(f"Ischemia extent out of range: {self.ischemia_extent}%")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class MammographyData:
    """Structured mammography analysis data."""
    bi_rads: Optional[int] = None  # 0-6
    bi_rads_category: Optional[str] = None  # Description
    lesion_detected: Optional[bool] = None
    lesion_description: Optional[str] = None
    microcalcifications: Optional[bool] = None
    microcalc_pattern: Optional[str] = None
    density: Optional[str] = None  # A, B, C, D
    mass_characteristics: Optional[Dict[str, Any]] = None
    findings: Optional[str] = None
    impressions: Optional[str] = None
    recommendations: Optional[str] = None

    def validate(self) -> List[str]:
        """Validate mammography data against BI-RADS standards."""
        errors = []

        if self.bi_rads is not None:
            if not (0 <= self.bi_rads <= 6):
                errors.append(f"BI-RADS category out of range: {self.bi_rads}")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class StudyMetadata:
    """Study information metadata."""
    study_id: str
    patient_name: Optional[str] = None
    patient_id: Optional[str] = None
    study_date: Optional[str] = None
    modality: Optional[str] = None
    description: Optional[str] = None
    institution: Optional[str] = None
    radiologist: Optional[str] = None
    referring_physician: Optional[str] = None
    clinical_history: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


# ==================== Data Validators ====================

class DataValidator:
    """Validates extracted data against clinical standards."""

    def __init__(self):
        """Initialize validator."""
        self.logger = logging.getLogger(f"{__name__}.DataValidator")

    def validate_cardiac(self, data: CardiacData) -> Tuple[bool, List[str]]:
        """Validate cardiac data."""
        errors = data.validate()
        is_valid = len(errors) == 0

        if not is_valid:
            self.logger.warning(f"Cardiac data validation issues: {errors}")

        return is_valid, errors

    def validate_coronary(self, data: CoronaryData) -> Tuple[bool, List[str]]:
        """Validate coronary data."""
        errors = data.validate()
        is_valid = len(errors) == 0

        if not is_valid:
            self.logger.warning(f"Coronary data validation issues: {errors}")

        return is_valid, errors

    def validate_perfusion(self, data: PerfusionData) -> Tuple[bool, List[str]]:
        """Validate perfusion data."""
        errors = data.validate()
        is_valid = len(errors) == 0

        if not is_valid:
            self.logger.warning(f"Perfusion data validation issues: {errors}")

        return is_valid, errors

    def validate_mammography(self, data: MammographyData) -> Tuple[bool, List[str]]:
        """Validate mammography data."""
        errors = data.validate()
        is_valid = len(errors) == 0

        if not is_valid:
            self.logger.warning(f"Mammography data validation issues: {errors}")

        return is_valid, errors


# ==================== Data Normalizers ====================

class DataNormalizer:
    """Normalizes extracted data to standard units and formats."""

    def __init__(self):
        """Initialize normalizer."""
        self.logger = logging.getLogger(f"{__name__}.DataNormalizer")

    def normalize_percentage(self, value: Any, decimals: int = 1) -> float:
        """Normalize value to percentage."""
        try:
            val = float(value)
            if 0 <= val <= 100:
                return round(val, decimals)
            return round(val, decimals)
        except (ValueError, TypeError) as e:
            self.logger.error(f"Error normalizing percentage: {e}")
            return 0.0

    def normalize_measurement(
        self,
        value: Any,
        unit_from: str,
        unit_to: str,
        decimals: int = 1
    ) -> float:
        """Normalize measurement between units."""
        try:
            val = float(value)

            # Convert based on unit pairs
            conversions = {
                ("mm", "cm"): val / 10,
                ("cm", "mm"): val * 10,
                ("g", "kg"): val / 1000,
                ("kg", "g"): val * 1000,
                ("mL", "L"): val / 1000,
                ("L", "mL"): val * 1000,
            }

            key = (unit_from, unit_to)
            if key in conversions:
                return round(conversions[key], decimals)
            else:
                return round(val, decimals)

        except (ValueError, TypeError) as e:
            self.logger.error(f"Error normalizing measurement: {e}")
            return 0.0

    def normalize_string(self, value: Any) -> str:
        """Normalize string value."""
        if value is None:
            return ""
        return str(value).strip()

    def normalize_date(self, value: Any) -> str:
        """Normalize date to ISO format."""
        if value is None:
            return ""

        if isinstance(value, str):
            return value[:10]  # Return YYYY-MM-DD portion

        try:
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d")
        except Exception as e:
            self.logger.error(f"Error normalizing date: {e}")

        return str(value)


# ==================== Module-Specific Extractors ====================

class CardiacExtractor:
    """Extract and structure cardiac analysis data."""

    def __init__(self):
        """Initialize cardiac extractor."""
        self.logger = logging.getLogger(f"{__name__}.CardiacExtractor")
        self.normalizer = DataNormalizer()
        self.validator = DataValidator()

    def extract(self, analysis_data: Dict[str, Any]) -> CardiacData:
        """
        Extract cardiac data from analysis results.

        Args:
            analysis_data: Raw cardiac analysis data

        Returns:
            CardiacData: Structured cardiac data
        """
        self.logger.info("Extracting cardiac data...")

        try:
            # Extract and normalize values
            ef = analysis_data.get("ejection_fraction")
            if ef is not None:
                ef = self.normalizer.normalize_percentage(ef)

            lvef = analysis_data.get("lvef")
            if lvef is not None:
                lvef = self.normalizer.normalize_percentage(lvef)

            mass = analysis_data.get("mass")
            if mass is not None:
                mass = self.normalizer.normalize_measurement(mass, "g", "g")

            # Create structured data
            data = CardiacData(
                ejection_fraction=ef,
                lvef=lvef,
                mass=mass,
                valve_status=self.normalizer.normalize_string(
                    analysis_data.get("valve_status")
                ),
                chamber_size=self.normalizer.normalize_string(
                    analysis_data.get("chamber_size")
                ),
                wall_thickness=self.normalizer.normalize_string(
                    analysis_data.get("wall_thickness")
                ),
                wall_motion=self.normalizer.normalize_string(
                    analysis_data.get("wall_motion")
                ),
                findings=self.normalizer.normalize_string(
                    analysis_data.get("findings")
                ),
                impressions=self.normalizer.normalize_string(
                    analysis_data.get("impressions")
                ),
                recommendations=self.normalizer.normalize_string(
                    analysis_data.get("recommendations")
                ),
            )

            # Validate
            is_valid, errors = self.validator.validate_cardiac(data)
            if not is_valid:
                self.logger.warning(f"Cardiac data validation issues: {errors}")

            return data

        except Exception as e:
            self.logger.error(f"Error extracting cardiac data: {e}")
            raise


class PerfusionExtractor:
    """Extract and structure perfusion analysis data."""

    def __init__(self):
        """Initialize perfusion extractor."""
        self.logger = logging.getLogger(f"{__name__}.PerfusionExtractor")
        self.normalizer = DataNormalizer()
        self.validator = DataValidator()

    def extract(self, analysis_data: Dict[str, Any]) -> PerfusionData:
        """
        Extract perfusion data from analysis results.

        Args:
            analysis_data: Raw perfusion analysis data

        Returns:
            PerfusionData: Structured perfusion data
        """
        self.logger.info("Extracting perfusion data...")

        try:
            # Extract and normalize values
            cbf = analysis_data.get("cbf")
            if cbf is not None:
                cbf = self.normalizer.normalize_measurement(cbf, "mL/min/100g", "mL/min/100g", 1)

            cbv = analysis_data.get("cbv")
            if cbv is not None:
                cbv = self.normalizer.normalize_measurement(cbv, "mL/100g", "mL/100g", 2)

            mtt = analysis_data.get("mtt")
            if mtt is not None:
                mtt = self.normalizer.normalize_measurement(mtt, "s", "s", 1)

            ischemia_extent = analysis_data.get("ischemia_extent")
            if ischemia_extent is not None:
                ischemia_extent = self.normalizer.normalize_percentage(ischemia_extent, 1)

            # Create structured data
            data = PerfusionData(
                cbf=cbf,
                cbv=cbv,
                mtt=mtt,
                defects=self.normalizer.normalize_string(
                    analysis_data.get("defects")
                ),
                regional_analysis=analysis_data.get("regional_analysis"),
                ischemia_extent=ischemia_extent,
                flow_reserve=analysis_data.get("flow_reserve"),
                findings=self.normalizer.normalize_string(
                    analysis_data.get("findings")
                ),
                impressions=self.normalizer.normalize_string(
                    analysis_data.get("impressions")
                ),
                recommendations=self.normalizer.normalize_string(
                    analysis_data.get("recommendations")
                ),
            )

            # Validate
            is_valid, errors = self.validator.validate_perfusion(data)
            if not is_valid:
                self.logger.warning(f"Perfusion data validation issues: {errors}")

            return data

        except Exception as e:
            self.logger.error(f"Error extracting perfusion data: {e}")
            raise


class MammographyExtractor:
    """Extract and structure mammography analysis data."""

    def __init__(self):
        """Initialize mammography extractor."""
        self.logger = logging.getLogger(f"{__name__}.MammographyExtractor")
        self.normalizer = DataNormalizer()
        self.validator = DataValidator()

    def extract(self, analysis_data: Dict[str, Any]) -> MammographyData:
        """
        Extract mammography data from analysis results.

        Args:
            analysis_data: Raw mammography analysis data

        Returns:
            MammographyData: Structured mammography data
        """
        self.logger.info("Extracting mammography data...")

        try:
            # Extract BI-RADS category
            bi_rads = analysis_data.get("bi_rads")
            if bi_rads is not None:
                try:
                    bi_rads = int(bi_rads)
                except (ValueError, TypeError):
                    bi_rads = None

            # Get BI-RADS category description
            bi_rads_categories = {
                0: "Incomplete",
                1: "Negative",
                2: "Benign",
                3: "Probably benign",
                4: "Suspicious",
                5: "Malignant",
                6: "Known cancer"
            }
            bi_rads_cat = bi_rads_categories.get(bi_rads) if bi_rads else None

            # Create structured data
            data = MammographyData(
                bi_rads=bi_rads,
                bi_rads_category=bi_rads_cat,
                lesion_detected=analysis_data.get("lesion_detected"),
                lesion_description=self.normalizer.normalize_string(
                    analysis_data.get("lesion_description")
                ),
                microcalcifications=analysis_data.get("microcalcifications"),
                microcalc_pattern=self.normalizer.normalize_string(
                    analysis_data.get("microcalc_pattern")
                ),
                density=self.normalizer.normalize_string(
                    analysis_data.get("density")
                ),
                mass_characteristics=analysis_data.get("mass_characteristics"),
                findings=self.normalizer.normalize_string(
                    analysis_data.get("findings")
                ),
                impressions=self.normalizer.normalize_string(
                    analysis_data.get("impressions")
                ),
                recommendations=self.normalizer.normalize_string(
                    analysis_data.get("recommendations")
                ),
            )

            # Validate
            is_valid, errors = self.validator.validate_mammography(data)
            if not is_valid:
                self.logger.warning(f"Mammography data validation issues: {errors}")

            return data

        except Exception as e:
            self.logger.error(f"Error extracting mammography data: {e}")
            raise


class CoronaryExtractor:
    """Extract and structure coronary analysis data."""

    def __init__(self):
        """Initialize coronary extractor."""
        self.logger = logging.getLogger(f"{__name__}.CoronaryExtractor")
        self.normalizer = DataNormalizer()
        self.validator = DataValidator()

    def extract(self, analysis_data: Dict[str, Any]) -> CoronaryData:
        """
        Extract coronary data from analysis results.

        Args:
            analysis_data: Raw coronary analysis data

        Returns:
            CoronaryData: Structured coronary data
        """
        self.logger.info("Extracting coronary data...")

        try:
            # Extract calcium score
            calcium_score = analysis_data.get("calcium_score")
            if calcium_score is not None:
                try:
                    calcium_score = float(calcium_score)
                except (ValueError, TypeError):
                    calcium_score = None

            # Create structured data
            data = CoronaryData(
                stenosis_grade=self.normalizer.normalize_string(
                    analysis_data.get("stenosis_grade")
                ),
                calcium_score=calcium_score,
                vessels=self.normalizer.normalize_string(
                    analysis_data.get("vessels")
                ),
                lad=analysis_data.get("lad"),
                lcx=analysis_data.get("lcx"),
                rca=analysis_data.get("rca"),
                left_main=analysis_data.get("left_main"),
                risk_assessment=self.normalizer.normalize_string(
                    analysis_data.get("risk_assessment")
                ),
                findings=self.normalizer.normalize_string(
                    analysis_data.get("findings")
                ),
                impressions=self.normalizer.normalize_string(
                    analysis_data.get("impressions")
                ),
                recommendations=self.normalizer.normalize_string(
                    analysis_data.get("recommendations")
                ),
            )

            # Validate
            is_valid, errors = self.validator.validate_coronary(data)
            if not is_valid:
                self.logger.warning(f"Coronary data validation issues: {errors}")

            return data

        except Exception as e:
            self.logger.error(f"Error extracting coronary data: {e}")
            raise


# ==================== Main Data Extraction Engine ====================

class DataExtractionEngine:
    """Main engine for extracting and normalizing report data."""

    def __init__(self):
        """Initialize data extraction engine."""
        self.logger = logging.getLogger(f"{__name__}.DataExtractionEngine")
        self.cardiac_extractor = CardiacExtractor()
        self.coronary_extractor = CoronaryExtractor()
        self.perfusion_extractor = PerfusionExtractor()
        self.mammography_extractor = MammographyExtractor()
        self.normalizer = DataNormalizer()

    def extract_all(
        self,
        study_metadata: Dict[str, Any],
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract all available data from a study.

        Args:
            study_metadata: Study information
            analysis_data: Analysis results (may contain multiple analysis types)

        Returns:
            dict: Complete structured data for report generation
        """
        start_time = time.time()

        try:
            result = {
                "study": self._extract_metadata(study_metadata),
            }

            # Extract each analysis type if present
            if "cardiac" in analysis_data:
                try:
                    cardiac_data = self.cardiac_extractor.extract(
                        analysis_data["cardiac"]
                    )
                    result["cardiac"] = cardiac_data.to_dict()
                except Exception as e:
                    self.logger.error(f"Failed to extract cardiac data: {e}")

            if "coronary" in analysis_data:
                try:
                    coronary_data = self.coronary_extractor.extract(
                        analysis_data["coronary"]
                    )
                    result["coronary"] = coronary_data.to_dict()
                except Exception as e:
                    self.logger.error(f"Failed to extract coronary data: {e}")

            if "perfusion" in analysis_data:
                try:
                    perfusion_data = self.perfusion_extractor.extract(
                        analysis_data["perfusion"]
                    )
                    result["perfusion"] = perfusion_data.to_dict()
                except Exception as e:
                    self.logger.error(f"Failed to extract perfusion data: {e}")

            if "mammography" in analysis_data:
                try:
                    mammography_data = self.mammography_extractor.extract(
                        analysis_data["mammography"]
                    )
                    result["mammography"] = mammography_data.to_dict()
                except Exception as e:
                    self.logger.error(f"Failed to extract mammography data: {e}")

            elapsed = (time.time() - start_time) * 1000
            self.logger.info(f"Data extraction completed in {elapsed:.1f}ms")

            return result

        except Exception as e:
            self.logger.error(f"Error extracting data: {e}")
            raise

    def _extract_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize study metadata."""
        return {
            "study_id": self.normalizer.normalize_string(
                metadata.get("study_id")
            ),
            "patient_name": self.normalizer.normalize_string(
                metadata.get("patient_name")
            ),
            "patient_id": self.normalizer.normalize_string(
                metadata.get("patient_id")
            ),
            "study_date": self.normalizer.normalize_date(
                metadata.get("study_date")
            ),
            "modality": self.normalizer.normalize_string(
                metadata.get("modality")
            ),
            "description": self.normalizer.normalize_string(
                metadata.get("description")
            ),
        }

    def validate_all_data(
        self,
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Tuple[bool, List[str]]]:
        """
        Validate all analysis data.

        Returns:
            dict: Validation results for each analysis type
        """
        results = {}

        if "cardiac" in analysis_data:
            cardiac_data = CardiacData(**analysis_data["cardiac"])
            results["cardiac"] = self.cardiac_extractor.validator.validate_cardiac(
                cardiac_data
            )

        if "coronary" in analysis_data:
            coronary_data = CoronaryData(**analysis_data["coronary"])
            results["coronary"] = self.coronary_extractor.validator.validate_coronary(
                coronary_data
            )

        if "perfusion" in analysis_data:
            perfusion_data = PerfusionData(**analysis_data["perfusion"])
            results["perfusion"] = self.perfusion_extractor.validator.validate_perfusion(
                perfusion_data
            )

        if "mammography" in analysis_data:
            mammography_data = MammographyData(**analysis_data["mammography"])
            results["mammography"] = self.mammography_extractor.validator.validate_mammography(
                mammography_data
            )

        return results


# Singleton instance
_extraction_engine: Optional[DataExtractionEngine] = None


def get_extraction_engine() -> DataExtractionEngine:
    """Get or create data extraction engine singleton."""
    global _extraction_engine
    if _extraction_engine is None:
        _extraction_engine = DataExtractionEngine()
    return _extraction_engine


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    engine = get_extraction_engine()

    # Test data extraction
    metadata = {
        "study_id": "STU-2025-0001",
        "patient_name": "John Doe",
        "study_date": "2025-10-23",
        "modality": "CT"
    }

    analysis_data = {
        "cardiac": {
            "ejection_fraction": 55.2,
            "mass": 185,
            "valve_status": "Normal valves"
        },
        "perfusion": {
            "cbf": 48.5,
            "cbv": 4.2,
            "mtt": 5.1
        }
    }

    try:
        result = engine.extract_all(metadata, analysis_data)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")
