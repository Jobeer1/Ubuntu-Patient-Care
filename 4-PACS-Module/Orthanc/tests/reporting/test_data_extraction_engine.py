#!/usr/bin/env python3
"""
Data Extraction Engine Tests - Comprehensive testing for report data extraction

Tests data validation, normalization, extraction from all analysis types,
and performance requirements.
"""

import pytest
import logging
import time
from datetime import datetime

from app.services.reporting.data_extraction_engine import (
    DataExtractionEngine,
    CardiacData,
    CoronaryData,
    PerfusionData,
    MammographyData,
    CardiacExtractor,
    CoronaryExtractor,
    PerfusionExtractor,
    MammographyExtractor,
    DataValidator,
    DataNormalizer,
    get_extraction_engine
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDataNormalizer:
    """Test data normalization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.normalizer = DataNormalizer()

    def test_normalize_percentage(self):
        """Test percentage normalization."""
        assert self.normalizer.normalize_percentage(55.234) == 55.2
        assert self.normalizer.normalize_percentage(100) == 100.0
        assert self.normalizer.normalize_percentage(0) == 0.0

    def test_normalize_percentage_decimals(self):
        """Test percentage normalization with custom decimals."""
        assert self.normalizer.normalize_percentage(45.678, decimals=2) == 45.68
        assert self.normalizer.normalize_percentage(45.678, decimals=0) == 46.0

    def test_normalize_measurement(self):
        """Test measurement unit conversion."""
        assert self.normalizer.normalize_measurement(10, "mm", "cm") == 1.0
        assert self.normalizer.normalize_measurement(1, "cm", "mm") == 10.0
        assert self.normalizer.normalize_measurement(1000, "g", "kg") == 1.0

    def test_normalize_string(self):
        """Test string normalization."""
        assert self.normalizer.normalize_string("  test  ") == "test"
        assert self.normalizer.normalize_string(None) == ""
        assert self.normalizer.normalize_string("NORMAL") == "NORMAL"

    def test_normalize_date(self):
        """Test date normalization."""
        assert self.normalizer.normalize_date("2025-10-23T14:30:00") == "2025-10-23"
        assert self.normalizer.normalize_date(None) == ""


class TestDataValidator:
    """Test data validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DataValidator()

    def test_validate_cardiac_normal(self):
        """Test validation of normal cardiac data."""
        data = CardiacData(
            ejection_fraction=55.0,
            mass=185.0
        )
        is_valid, errors = self.validator.validate_cardiac(data)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_cardiac_low_ef(self):
        """Test validation catches low ejection fraction."""
        data = CardiacData(ejection_fraction=35.0)
        is_valid, errors = self.validator.validate_cardiac(data)
        assert is_valid is False
        assert any("low" in str(e).lower() for e in errors)

    def test_validate_cardiac_out_of_range(self):
        """Test validation catches out of range values."""
        data = CardiacData(ejection_fraction=150.0)
        is_valid, errors = self.validator.validate_cardiac(data)
        assert is_valid is False

    def test_validate_perfusion_normal(self):
        """Test validation of normal perfusion data."""
        data = PerfusionData(
            cbf=48.5,
            mtt=5.1
        )
        is_valid, errors = self.validator.validate_perfusion(data)
        assert is_valid is True

    def test_validate_perfusion_low_cbf(self):
        """Test validation catches low CBF."""
        data = PerfusionData(cbf=15.0)
        is_valid, errors = self.validator.validate_perfusion(data)
        assert is_valid is False
        assert any("low" in str(e).lower() for e in errors)

    def test_validate_mammography_valid_bi_rads(self):
        """Test validation of valid BI-RADS."""
        data = MammographyData(bi_rads=2)
        is_valid, errors = self.validator.validate_mammography(data)
        assert is_valid is True

    def test_validate_mammography_invalid_bi_rads(self):
        """Test validation catches invalid BI-RADS."""
        data = MammographyData(bi_rads=7)
        is_valid, errors = self.validator.validate_mammography(data)
        assert is_valid is False


class TestCardiacExtractor:
    """Test cardiac data extraction."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = CardiacExtractor()

    def test_extract_cardiac_basic(self):
        """Test basic cardiac data extraction."""
        analysis_data = {
            "ejection_fraction": 55.0,
            "mass": 185.0,
            "valve_status": "Normal valves"
        }

        data = self.extractor.extract(analysis_data)

        assert data.ejection_fraction == 55.0
        assert data.mass == 185.0
        assert data.valve_status == "Normal valves"

    def test_extract_cardiac_with_normalization(self):
        """Test cardiac extraction with value normalization."""
        analysis_data = {
            "ejection_fraction": 55.234,
            "mass": 185.678
        }

        data = self.extractor.extract(analysis_data)

        assert data.ejection_fraction == 55.2  # Normalized to 1 decimal
        assert data.mass == 185.7

    def test_extract_cardiac_complete(self):
        """Test extraction of complete cardiac data."""
        analysis_data = {
            "ejection_fraction": 55.0,
            "lvef": 55.0,
            "mass": 185.0,
            "valve_status": "Normal aortic, mitral, tricuspid valves",
            "chamber_size": "Normal LV cavity",
            "findings": "No wall motion abnormalities",
            "impressions": "Normal cardiac function"
        }

        data = self.extractor.extract(analysis_data)

        assert data.ejection_fraction == 55.0
        assert data.findings == "No wall motion abnormalities"
        assert data.impressions == "Normal cardiac function"

    def test_extract_cardiac_to_dict(self):
        """Test conversion of cardiac data to dictionary."""
        analysis_data = {
            "ejection_fraction": 55.0,
            "valve_status": "Normal"
        }

        data = self.extractor.extract(analysis_data)
        data_dict = data.to_dict()

        assert "ejection_fraction" in data_dict
        assert data_dict["ejection_fraction"] == 55.0
        assert "valve_status" in data_dict
        # None values should be excluded
        assert "recommendations" not in data_dict


class TestPerfusionExtractor:
    """Test perfusion data extraction."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PerfusionExtractor()

    def test_extract_perfusion_basic(self):
        """Test basic perfusion data extraction."""
        analysis_data = {
            "cbf": 48.5,
            "cbv": 4.2,
            "mtt": 5.1
        }

        data = self.extractor.extract(analysis_data)

        assert data.cbf == 48.5
        assert data.cbv == 4.2
        assert data.mtt == 5.1

    def test_extract_perfusion_with_defects(self):
        """Test perfusion extraction with defect information."""
        analysis_data = {
            "cbf": 35.0,  # Low CBF
            "defects": "Perfusion defect in left MCA territory",
            "ischemia_extent": 25.5,
            "findings": "Evidence of acute ischemia"
        }

        data = self.extractor.extract(analysis_data)

        assert data.cbf == 35.0
        assert data.defects == "Perfusion defect in left MCA territory"
        assert data.ischemia_extent == 25.5

    def test_extract_perfusion_normalization(self):
        """Test perfusion value normalization."""
        analysis_data = {
            "cbf": 48.567,
            "cbv": 4.234,
            "mtt": 5.123,
            "ischemia_extent": 25.678
        }

        data = self.extractor.extract(analysis_data)

        assert data.cbf == 48.6
        assert data.cbv == 4.23
        assert data.mtt == 5.1
        assert data.ischemia_extent == 25.7


class TestMammographyExtractor:
    """Test mammography data extraction."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = MammographyExtractor()

    def test_extract_mammography_bi_rads_2(self):
        """Test mammography extraction with BI-RADS 2."""
        analysis_data = {
            "bi_rads": 2,
            "lesion_detected": False,
            "findings": "Benign findings"
        }

        data = self.extractor.extract(analysis_data)

        assert data.bi_rads == 2
        assert data.bi_rads_category == "Benign"
        assert data.lesion_detected is False

    def test_extract_mammography_bi_rads_4(self):
        """Test mammography extraction with BI-RADS 4."""
        analysis_data = {
            "bi_rads": 4,
            "lesion_detected": True,
            "lesion_description": "Irregular mass with spiculated margins",
            "findings": "Suspicious finding requiring biopsy"
        }

        data = self.extractor.extract(analysis_data)

        assert data.bi_rads == 4
        assert data.bi_rads_category == "Suspicious"
        assert data.lesion_detected is True

    def test_extract_mammography_microcalc(self):
        """Test mammography extraction with microcalcifications."""
        analysis_data = {
            "bi_rads": 3,
            "microcalcifications": True,
            "microcalc_pattern": "Clustered",
            "findings": "Clustered microcalcifications"
        }

        data = self.extractor.extract(analysis_data)

        assert data.microcalcifications is True
        assert data.microcalc_pattern == "Clustered"

    def test_extract_mammography_all_bi_rads(self):
        """Test BI-RADS category mapping."""
        bi_rads_map = {
            0: "Incomplete",
            1: "Negative",
            2: "Benign",
            3: "Probably benign",
            4: "Suspicious",
            5: "Malignant",
            6: "Known cancer"
        }

        for bi_rads, category in bi_rads_map.items():
            data = self.extractor.extract({"bi_rads": bi_rads})
            assert data.bi_rads_category == category


class TestCoronaryExtractor:
    """Test coronary data extraction."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = CoronaryExtractor()

    def test_extract_coronary_basic(self):
        """Test basic coronary data extraction."""
        analysis_data = {
            "stenosis_grade": "No significant stenosis",
            "calcium_score": 0,
            "vessels": "All vessels patent"
        }

        data = self.extractor.extract(analysis_data)

        assert data.stenosis_grade == "No significant stenosis"
        assert data.calcium_score == 0
        assert data.vessels == "All vessels patent"

    def test_extract_coronary_with_stenosis(self):
        """Test coronary extraction with stenosis."""
        analysis_data = {
            "stenosis_grade": "75% LAD",
            "vessels": "LAD: 75% stenosis, LCX: patent, RCA: patent",
            "findings": "Significant LAD stenosis"
        }

        data = self.extractor.extract(analysis_data)

        assert "75%" in data.stenosis_grade
        assert "LAD" in data.vessels

    def test_extract_coronary_calcium_score(self):
        """Test coronary calcium score extraction."""
        analysis_data = {
            "calcium_score": 245.5,
            "risk_assessment": "Moderate risk"
        }

        data = self.extractor.extract(analysis_data)

        assert data.calcium_score == 245.5


class TestDataExtractionEngine:
    """Test main data extraction engine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = DataExtractionEngine()

    def test_extract_all_single_modality(self):
        """Test extraction with single analysis type."""
        metadata = {
            "study_id": "STU-001",
            "patient_name": "John Doe",
            "study_date": "2025-10-23"
        }

        analysis_data = {
            "cardiac": {
                "ejection_fraction": 55.0,
                "mass": 185.0
            }
        }

        result = self.engine.extract_all(metadata, analysis_data)

        assert "study" in result
        assert "cardiac" in result
        assert result["study"]["study_id"] == "STU-001"
        assert result["cardiac"]["ejection_fraction"] == 55.0

    def test_extract_all_multiple_modalities(self):
        """Test extraction with multiple analysis types."""
        metadata = {
            "study_id": "STU-002",
            "patient_name": "Jane Smith"
        }

        analysis_data = {
            "cardiac": {"ejection_fraction": 55.0},
            "coronary": {"calcium_score": 0},
            "perfusion": {"cbf": 48.5},
            "mammography": {"bi_rads": 2}
        }

        result = self.engine.extract_all(metadata, analysis_data)

        assert "cardiac" in result
        assert "coronary" in result
        assert "perfusion" in result
        assert "mammography" in result

    def test_extract_all_performance(self):
        """Test extraction performance (<500ms for complete study)."""
        metadata = {
            "study_id": "STU-003",
            "patient_name": "Test Patient"
        }

        analysis_data = {
            "cardiac": {
                "ejection_fraction": 55.0,
                "mass": 185.0,
                "valve_status": "Normal"
            },
            "perfusion": {
                "cbf": 48.5,
                "cbv": 4.2,
                "mtt": 5.1
            },
            "mammography": {
                "bi_rads": 2,
                "lesion_detected": False
            }
        }

        start = time.time()
        for _ in range(10):
            result = self.engine.extract_all(metadata, analysis_data)
        elapsed = (time.time() - start) * 1000 / 10

        logger.info(f"Average extraction time: {elapsed:.1f}ms")
        assert elapsed < 500, f"Extraction too slow: {elapsed:.1f}ms (target <500ms)"

    def test_extract_all_empty_data(self):
        """Test extraction with minimal data."""
        metadata = {
            "study_id": "STU-004",
            "patient_name": "Minimal Patient"
        }

        analysis_data = {}

        result = self.engine.extract_all(metadata, analysis_data)

        assert "study" in result
        assert result["study"]["study_id"] == "STU-004"

    def test_validate_all_data(self):
        """Test data validation."""
        analysis_data = {
            "cardiac": {
                "ejection_fraction": 55.0,
                "mass": 185.0
            },
            "perfusion": {
                "cbf": 48.5,
                "mtt": 5.1
            }
        }

        # Convert to structured data
        cardiac_data = CardiacData(**analysis_data["cardiac"])
        perfusion_data = PerfusionData(**analysis_data["perfusion"])

        # Validate
        cardiac_valid, cardiac_errors = self.engine.cardiac_extractor.validator.validate_cardiac(cardiac_data)
        perfusion_valid, perfusion_errors = self.engine.perfusion_extractor.validator.validate_perfusion(perfusion_data)

        assert cardiac_valid is True
        assert perfusion_valid is True

    def test_singleton_pattern(self):
        """Test singleton pattern."""
        engine1 = get_extraction_engine()
        engine2 = get_extraction_engine()

        assert engine1 is engine2


class TestDataSerialization:
    """Test data serialization to dictionary."""

    def test_cardiac_to_dict(self):
        """Test cardiac data to dictionary conversion."""
        data = CardiacData(
            ejection_fraction=55.0,
            mass=185.0
        )
        data_dict = data.to_dict()

        assert "ejection_fraction" in data_dict
        assert data_dict["ejection_fraction"] == 55.0
        assert "recommendations" not in data_dict  # None values excluded

    def test_perfusion_to_dict(self):
        """Test perfusion data to dictionary conversion."""
        data = PerfusionData(
            cbf=48.5,
            cbv=4.2,
            mtt=5.1
        )
        data_dict = data.to_dict()

        assert data_dict["cbf"] == 48.5
        assert data_dict["cbv"] == 4.2
        assert len(data_dict) == 3  # Only 3 fields set


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
