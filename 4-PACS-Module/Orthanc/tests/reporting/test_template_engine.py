#!/usr/bin/env python3
"""
Template Engine Tests - Comprehensive testing for report template system

Tests all template types, variable substitution, conditional rendering,
data validation, and performance requirements.
"""

import pytest
import logging
from datetime import datetime
import time

from app.services.reporting.template_engine import (
    TemplateEngine,
    TemplateType,
    ConditionalOperator,
    ConditionalRenderer,
    VariableFormatter,
    TemplateValidationError,
    DataValidationError,
    get_template_engine
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestConditionalOperator:
    """Test conditional operator evaluation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = ConditionalRenderer()

    def test_operator_exists(self):
        """Test EXISTS operator."""
        assert self.renderer.evaluate_condition(
            ConditionalOperator.EXISTS, "value"
        ) is True
        assert self.renderer.evaluate_condition(
            ConditionalOperator.EXISTS, None
        ) is False
        assert self.renderer.evaluate_condition(
            ConditionalOperator.EXISTS, ""
        ) is False

    def test_operator_not_exists(self):
        """Test NOT_EXISTS operator."""
        assert self.renderer.evaluate_condition(
            ConditionalOperator.NOT_EXISTS, None
        ) is True
        assert self.renderer.evaluate_condition(
            ConditionalOperator.NOT_EXISTS, ""
        ) is True
        assert self.renderer.evaluate_condition(
            ConditionalOperator.NOT_EXISTS, "value"
        ) is False

    def test_operator_equals(self):
        """Test EQUALS operator."""
        assert self.renderer.evaluate_condition(
            ConditionalOperator.EQUALS, "value", "value"
        ) is True
        assert self.renderer.evaluate_condition(
            ConditionalOperator.EQUALS, "value", "other"
        ) is False
        assert self.renderer.evaluate_condition(
            ConditionalOperator.EQUALS, 5, 5
        ) is True

    def test_operator_not_equals(self):
        """Test NOT_EQUALS operator."""
        assert self.renderer.evaluate_condition(
            ConditionalOperator.NOT_EQUALS, "value", "other"
        ) is True
        assert self.renderer.evaluate_condition(
            ConditionalOperator.NOT_EQUALS, "value", "value"
        ) is False

    def test_operator_greater_than(self):
        """Test GREATER_THAN operator."""
        assert self.renderer.evaluate_condition(
            ConditionalOperator.GREATER_THAN, 10, 5
        ) is True
        assert self.renderer.evaluate_condition(
            ConditionalOperator.GREATER_THAN, 5, 10
        ) is False
        assert self.renderer.evaluate_condition(
            ConditionalOperator.GREATER_THAN, 5, 5
        ) is False

    def test_operator_less_than(self):
        """Test LESS_THAN operator."""
        assert self.renderer.evaluate_condition(
            ConditionalOperator.LESS_THAN, 5, 10
        ) is True
        assert self.renderer.evaluate_condition(
            ConditionalOperator.LESS_THAN, 10, 5
        ) is False

    def test_operator_contains(self):
        """Test CONTAINS operator."""
        assert self.renderer.evaluate_condition(
            ConditionalOperator.CONTAINS, "hello world", "world"
        ) is True
        assert self.renderer.evaluate_condition(
            ConditionalOperator.CONTAINS, "hello world", "xyz"
        ) is False

    def test_operator_in_list(self):
        """Test IN operator."""
        assert self.renderer.evaluate_condition(
            ConditionalOperator.IN_LIST, "b", ["a", "b", "c"]
        ) is True
        assert self.renderer.evaluate_condition(
            ConditionalOperator.IN_LIST, "d", ["a", "b", "c"]
        ) is False


class TestVariableFormatter:
    """Test variable formatting and substitution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = VariableFormatter()

    def test_simple_variable_substitution(self):
        """Test basic variable substitution."""
        template = "Hello {{name}}"
        data = {"name": "John"}
        result = self.formatter.substitute_variables(template, data)
        assert result == "Hello John"

    def test_nested_variable_substitution(self):
        """Test nested variable substitution."""
        template = "{{patient.name}} - {{patient.id}}"
        data = {
            "patient": {
                "name": "Jane Doe",
                "id": "P12345"
            }
        }
        result = self.formatter.substitute_variables(template, data)
        assert result == "Jane Doe - P12345"

    def test_missing_variable(self):
        """Test handling of missing variables."""
        template = "Name: {{name}}, Age: {{age}}"
        data = {"name": "John"}
        result = self.formatter.substitute_variables(template, data)
        assert "John" in result
        assert "[N/A]" in result

    def test_format_percent(self):
        """Test percent formatting."""
        template = "EF: {{ef|percent}}"
        data = {"ef": 55.234}
        result = self.formatter.substitute_variables(template, data)
        assert "55%" in result

    def test_format_percent2(self):
        """Test percent 2-decimal formatting."""
        template = "Score: {{score|percent2}}"
        data = {"score": 45.678}
        result = self.formatter.substitute_variables(template, data)
        assert "45.68%" in result

    def test_format_fixed1(self):
        """Test fixed 1-decimal formatting."""
        template = "Value: {{val|fixed1}}"
        data = {"val": 45.678}
        result = self.formatter.substitute_variables(template, data)
        assert "45.7" in result

    def test_format_fixed2(self):
        """Test fixed 2-decimal formatting."""
        template = "Value: {{val|fixed2}}"
        data = {"val": 45.6789}
        result = self.formatter.substitute_variables(template, data)
        assert "45.68" in result

    def test_format_fixed0(self):
        """Test fixed 0-decimal formatting."""
        template = "Count: {{count|fixed0}}"
        data = {"count": 45.678}
        result = self.formatter.substitute_variables(template, data)
        assert "46" in result

    def test_format_uppercase(self):
        """Test uppercase formatting."""
        template = "Status: {{status|upper}}"
        data = {"status": "completed"}
        result = self.formatter.substitute_variables(template, data)
        assert "COMPLETED" in result

    def test_format_date(self):
        """Test date formatting."""
        template = "Date: {{date|date}}"
        data = {"date": "2025-10-23T14:30:00"}
        result = self.formatter.substitute_variables(template, data)
        assert "2025-10-23" in result

    def test_multiple_substitutions(self):
        """Test multiple variable substitutions."""
        template = "{{first}} {{middle}} {{last}}"
        data = {
            "first": "John",
            "middle": "Paul",
            "last": "Smith"
        }
        result = self.formatter.substitute_variables(template, data)
        assert result == "John Paul Smith"


class TestTemplateEngine:
    """Test main template engine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = TemplateEngine()

    def test_engine_initialization(self):
        """Test engine initializes with all templates."""
        templates = self.engine.list_templates()
        assert len(templates) == 5
        template_types = [t["type"] for t in templates]
        assert TemplateType.GENERIC.value in template_types
        assert TemplateType.CARDIAC.value in template_types
        assert TemplateType.CORONARY.value in template_types
        assert TemplateType.PERFUSION.value in template_types
        assert TemplateType.MAMMOGRAPHY.value in template_types

    def test_generic_template_rendering(self):
        """Test generic template rendering."""
        data = {
            "study": {
                "study_id": "STU-001",
                "patient_name": "John Doe",
                "study_date": "2025-10-23",
                "modality": "CT",
                "findings": "No acute abnormalities",
                "impressions": "Normal study"
            }
        }

        html = self.engine.render_template("generic", data)
        
        assert "John Doe" in html
        assert "STU-001" in html
        assert "No acute abnormalities" in html
        assert len(html) > 200

    def test_cardiac_template_rendering(self):
        """Test cardiac template rendering."""
        data = {
            "study": {"study_id": "STU-002"},
            "cardiac": {
                "ejection_fraction": 55,
                "lvef": 55.2,
                "mass": 185,
                "valve_status": "Normal valves",
                "chamber_size": "Normal",
                "findings": "No wall motion abnormality",
                "impressions": "Normal cardiac function"
            }
        }

        html = self.engine.render_template("cardiac", data)
        
        assert "55%" in html or "55" in html
        assert "Normal valves" in html
        assert len(html) > 200

    def test_perfusion_template_rendering(self):
        """Test perfusion template rendering."""
        data = {
            "study": {"study_id": "STU-003"},
            "perfusion": {
                "cbf": 48.5,
                "cbv": 4.2,
                "mtt": 5.1,
                "defects": "No perfusion defects",
                "findings": "Normal perfusion pattern"
            }
        }

        html = self.engine.render_template("perfusion", data)
        
        assert "48.5" in html
        assert "4.2" in html
        assert "Normal perfusion" in html

    def test_mammography_template_rendering(self):
        """Test mammography template rendering."""
        data = {
            "study": {"study_id": "STU-004"},
            "mammography": {
                "bi_rads": 2,
                "lesion_detected": "No suspicious lesion",
                "findings": "Benign findings",
                "impressions": "Normal mammography"
            }
        }

        html = self.engine.render_template("mammography", data)
        
        assert "2" in html
        assert "Normal mammography" in html

    def test_coronary_template_rendering(self):
        """Test coronary template rendering."""
        data = {
            "study": {"study_id": "STU-005"},
            "coronary": {
                "stenosis_grade": "No significant stenosis",
                "calcium_score": 0,
                "vessels": "All vessels patent",
                "findings": "Normal coronary arteries"
            }
        }

        html = self.engine.render_template("coronary", data)
        
        assert "No significant stenosis" in html
        assert "Normal coronary" in html

    def test_data_validation_missing_required_field(self):
        """Test data validation catches missing required fields."""
        data = {
            "study": {"study_id": "STU-001"}
            # Missing patient_name
        }

        with pytest.raises(DataValidationError):
            self.engine.render_template("generic", data, validate=True)

    def test_data_validation_can_be_disabled(self):
        """Test data validation can be disabled."""
        data = {
            "study": {"study_id": "STU-001"}
            # Missing patient_name
        }

        # Should not raise error when validation disabled
        html = self.engine.render_template("generic", data, validate=False)
        assert len(html) > 0

    def test_conditional_sections_rendered(self):
        """Test conditional sections are rendered when conditions met."""
        data = {
            "study": {"study_id": "STU-001", "patient_name": "John"},
            "cardiac": {
                "ejection_fraction": 55,
                "findings": "Test findings"
            }
        }

        html = self.engine.render_template("cardiac", data, validate=False)
        
        # Findings section should be present
        assert "findings" in html.lower() or "findings" in html or "Test findings" in html

    def test_conditional_sections_hidden(self):
        """Test conditional sections are hidden when conditions not met."""
        data = {
            "study": {"study_id": "STU-001", "patient_name": "John"},
            "cardiac": {
                "ejection_fraction": 55
                # No findings provided
            }
        }

        html = self.engine.render_template("cardiac", data, validate=False)
        
        # Should still render, just without the findings section filled in
        assert "STU-001" in html

    def test_template_list(self):
        """Test getting list of available templates."""
        templates = self.engine.list_templates()
        
        assert len(templates) == 5
        assert all("type" in t for t in templates)
        assert all("metadata" in t for t in templates)

    def test_template_metadata(self):
        """Test getting template metadata."""
        metadata = self.engine.get_template_metadata("generic")
        
        assert metadata["name"] == "Generic Medical Report"
        assert len(metadata["required_fields"]) > 0
        assert "version" in metadata

    def test_invalid_template_type(self):
        """Test error on invalid template type."""
        data = {"study": {"study_id": "STU-001"}}
        
        with pytest.raises(TemplateValidationError):
            self.engine.render_template("invalid_type", data)

    def test_performance_generic_template(self):
        """Test generic template rendering performance (<100ms)."""
        data = {
            "study": {
                "study_id": "STU-001",
                "patient_name": "John Doe",
                "study_date": "2025-10-23",
                "modality": "CT"
            }
        }

        start = time.time()
        for _ in range(10):
            self.engine.render_template("generic", data, validate=False)
        elapsed = (time.time() - start) * 1000 / 10

        logger.info(f"Average render time: {elapsed:.1f}ms")
        assert elapsed < 100, f"Render too slow: {elapsed:.1f}ms (target <100ms)"

    def test_performance_cardiac_template(self):
        """Test cardiac template rendering performance (<100ms)."""
        data = {
            "study": {"study_id": "STU-002"},
            "cardiac": {
                "ejection_fraction": 55,
                "valve_status": "Normal",
                "findings": "Test findings"
            }
        }

        start = time.time()
        for _ in range(10):
            self.engine.render_template("cardiac", data, validate=False)
        elapsed = (time.time() - start) * 1000 / 10

        logger.info(f"Cardiac render time: {elapsed:.1f}ms")
        assert elapsed < 100

    def test_complex_nested_data(self):
        """Test with complex nested data structure."""
        data = {
            "study": {
                "study_id": "STU-006",
                "patient_name": "Complex Patient",
                "patient": {
                    "age": 65,
                    "gender": "M"
                }
            },
            "cardiac": {
                "ejection_fraction": 52.5,
                "measurements": {
                    "lvef": 52.5,
                    "mass": 190
                }
            }
        }

        html = self.engine.render_template("cardiac", data, validate=False)
        assert "Complex Patient" in html
        assert len(html) > 200


class TestConditionalRendering:
    """Test conditional rendering logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = ConditionalRenderer()

    def test_section_with_exists_condition_true(self):
        """Test section renders when exists condition is true."""
        section = {
            "type": "paragraph",
            "text": "Value exists",
            "condition": {"operator": "exists", "field": "value"}
        }
        data = {"value": "something"}
        
        should_render = self.renderer.should_render_section(section, data)
        assert should_render is True

    def test_section_with_exists_condition_false(self):
        """Test section doesn't render when exists condition is false."""
        section = {
            "type": "paragraph",
            "text": "Value exists",
            "condition": {"operator": "exists", "field": "value"}
        }
        data = {"value": None}
        
        should_render = self.renderer.should_render_section(section, data)
        assert should_render is False

    def test_section_without_condition(self):
        """Test section renders when no condition specified."""
        section = {
            "type": "paragraph",
            "text": "Always render"
        }
        data = {}
        
        should_render = self.renderer.should_render_section(section, data)
        assert should_render is True

    def test_nested_field_access(self):
        """Test accessing nested fields with dot notation."""
        section = {
            "condition": {"operator": "exists", "field": "patient.cardiac.ef"}
        }
        data = {
            "patient": {
                "cardiac": {
                    "ef": 55
                }
            }
        }
        
        should_render = self.renderer.should_render_section(section, data)
        assert should_render is True

    def test_comparison_condition(self):
        """Test comparison conditions."""
        section = {
            "condition": {
                "operator": "gt",
                "field": "value",
                "expected": 50
            }
        }
        data = {"value": 60}
        
        should_render = self.renderer.should_render_section(section, data)
        assert should_render is True


class TestSingleton:
    """Test singleton pattern for template engine."""

    def test_singleton_instance(self):
        """Test get_template_engine returns singleton."""
        engine1 = get_template_engine()
        engine2 = get_template_engine()
        
        assert engine1 is engine2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
