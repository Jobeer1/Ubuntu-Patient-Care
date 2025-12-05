"""
Unit tests for AI Triage MCP Tool

Tests cover:
- Model initialization and configuration
- Model selection logic
- Triage triggering and status tracking
- Error handling and edge cases
- MCP tool functions

Author: AI Teleradiology Team
Date: 2025-11-27
"""

import pytest
import json
from typing import Dict, Any

# Import the module being tested
from tools.ai_triage import (
    AITriageEngine,
    ModelType,
    TriageStatus,
    Severity,
    TriageRequest,
    TriageResult,
    ModelConfig,
    initialize_engine,
    get_engine,
    mcp_list_models,
    mcp_select_model,
    mcp_trigger_triage,
    mcp_get_triage_status,
    mcp_get_model_config,
    mcp_update_model_threshold,
    mcp_toggle_model
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def engine():
    """Create a fresh engine for testing"""
    # Use a new instance for each test
    engine = AITriageEngine()
    return engine


@pytest.fixture
def triage_request():
    """Create a standard triage request"""
    return TriageRequest(
        study_id="TEST-STUDY-001",
        modality="CT",
        body_part="Chest",
        metadata={"test": True}
    )


# ============================================================================
# Model Configuration Tests
# ============================================================================

class TestModelConfiguration:
    """Test model initialization and configuration"""

    def test_engine_initialization(self, engine):
        """Test that engine initializes with default models"""
        assert engine is not None
        assert len(engine.models) == 4

    def test_default_models_loaded(self, engine):
        """Test that all default models are loaded"""
        model_types = [m.value for m in ModelType]
        assert len(model_types) == 4
        
        for model_type in model_types:
            assert model_type in engine.models or any(
                m.model_type.value == model_type for m in engine.models.values()
            )

    def test_list_models(self, engine):
        """Test listing available models"""
        models = engine.list_models()
        
        assert isinstance(models, dict)
        assert len(models) == 4
        
        for key, model in models.items():
            assert 'type' in model
            assert 'version' in model
            assert 'threshold' in model
            assert 'enabled' in model
            assert 'metadata' in model

    def test_get_model_config(self, engine):
        """Test retrieving model configuration"""
        config = engine.get_model_config(ModelType.CHEST_CT_NODULE.value)
        
        assert config is not None
        assert config['type'] == ModelType.CHEST_CT_NODULE.value
        assert config['version'] == "1.0"
        assert 0.0 <= config['threshold'] <= 1.0

    def test_get_nonexistent_model_config(self, engine):
        """Test getting config for nonexistent model"""
        config = engine.get_model_config("invalid_model")
        assert config is None

    def test_model_metadata_ct_chest(self, engine):
        """Test chest CT model has correct metadata"""
        config = engine.get_model_config(ModelType.CHEST_CT_NODULE.value)
        
        assert config['metadata']['modality'] == 'CT'
        assert config['metadata']['body_part'] == 'Chest'
        assert config['metadata']['sensitivity'] == 0.90
        assert config['metadata']['specificity'] == 0.85


# ============================================================================
# Model Selection Tests
# ============================================================================

class TestModelSelection:
    """Test model selection logic"""

    def test_select_chest_ct_model(self, engine):
        """Test selecting chest CT nodule model"""
        success, msg, model = engine.select_model("CT", "Chest")
        
        assert success is True
        assert model == ModelType.CHEST_CT_NODULE
        assert "Selected model" in msg

    def test_select_abdomen_mr_model(self, engine):
        """Test selecting abdomen MR bleed model"""
        success, msg, model = engine.select_model("MR", "Abdomen")
        
        assert success is True
        assert model == ModelType.ABDOMEN_MR_BLEED

    def test_select_brain_ct_model(self, engine):
        """Test selecting brain CT stroke model"""
        success, msg, model = engine.select_model("CT", "Brain")
        
        assert success is True
        assert model == ModelType.BRAIN_CT_STROKE

    def test_select_bone_xray_model(self, engine):
        """Test selecting bone X-ray fracture model"""
        success, msg, model = engine.select_model("XR", "Bone")
        
        assert success is True
        assert model == ModelType.BONE_XRAY_FRACTURE

    def test_select_unsupported_combination(self, engine):
        """Test selecting unsupported modality/body_part"""
        success, msg, model = engine.select_model("US", "Liver")
        
        assert success is False
        assert model is None
        assert "No model available" in msg

    def test_select_disabled_model(self, engine):
        """Test selecting a disabled model"""
        # Disable the model first
        engine.toggle_model(ModelType.CHEST_CT_NODULE.value, False)
        
        success, msg, model = engine.select_model("CT", "Chest")
        
        assert success is False
        assert "disabled" in msg.lower()

    def test_case_insensitive_selection(self, engine):
        """Test that model selection is case insensitive"""
        success, msg, model = engine.select_model("ct", "chest")
        
        assert success is True
        assert model == ModelType.CHEST_CT_NODULE


# ============================================================================
# Triage Triggering Tests
# ============================================================================

class TestTriageTrigger:
    """Test triage pipeline triggering"""

    def test_trigger_basic_triage(self, engine, triage_request):
        """Test basic triage triggering"""
        result = engine.trigger_triage(triage_request)
        
        assert result.study_id == triage_request.study_id
        assert result.model == ModelType.CHEST_CT_NODULE
        assert result.status in TriageStatus
        assert result.severity in Severity
        assert 0.0 <= result.confidence <= 1.0
        assert result.error is None

    def test_trigger_triage_queue_status(self, engine, triage_request):
        """Test that triage updates queue status"""
        engine.trigger_triage(triage_request)
        
        # Status should be in queue (either still processing or completed)
        assert triage_request.study_id in engine.triage_queue

    def test_trigger_triage_result_cached(self, engine, triage_request):
        """Test that triage result is cached"""
        result = engine.trigger_triage(triage_request)
        
        # Result should be in cache
        cached = engine.results_cache.get(triage_request.study_id)
        assert cached is not None
        assert cached.study_id == result.study_id

    def test_trigger_triage_with_explicit_model(self, engine):
        """Test triggering triage with explicit model"""
        request = TriageRequest(
            study_id="TEST-002",
            modality="CT",
            body_part="Brain",
            model_type=ModelType.BRAIN_CT_STROKE
        )
        
        result = engine.trigger_triage(request)
        
        assert result.model == ModelType.BRAIN_CT_STROKE
        assert result.error is None

    def test_trigger_triage_invalid_model_selection(self, engine):
        """Test triage fails gracefully with invalid model"""
        request = TriageRequest(
            study_id="TEST-003",
            modality="INVALID",
            body_part="INVALID"
        )
        
        result = engine.trigger_triage(request)
        
        assert result.status == TriageStatus.FAILED
        assert result.error is not None


# ============================================================================
# Triage Status Tests
# ============================================================================

class TestTriageStatus:
    """Test triage status monitoring"""

    def test_get_triage_status_pending(self, engine):
        """Test getting status of non-existent study"""
        status_info = engine.get_triage_status("NONEXISTENT")
        
        assert status_info['study_id'] == "NONEXISTENT"
        assert status_info['status'] == TriageStatus.PENDING.value
        assert status_info['result'] is None

    def test_get_triage_status_completed(self, engine, triage_request):
        """Test getting status of completed study"""
        engine.trigger_triage(triage_request)
        status_info = engine.get_triage_status(triage_request.study_id)
        
        assert status_info['study_id'] == triage_request.study_id
        assert status_info['status'] in [s.value for s in TriageStatus]
        assert status_info['result'] is not None

    def test_multiple_studies_tracking(self, engine):
        """Test tracking multiple studies simultaneously"""
        studies = ["STUDY-001", "STUDY-002", "STUDY-003"]
        
        for study_id in studies:
            request = TriageRequest(study_id=study_id, modality="CT", body_part="Chest")
            engine.trigger_triage(request)
        
        # All studies should be in queue
        for study_id in studies:
            assert study_id in engine.triage_queue


# ============================================================================
# Model Configuration Update Tests
# ============================================================================

class TestModelConfigurationUpdates:
    """Test updating model configurations"""

    def test_update_model_threshold(self, engine):
        """Test updating model threshold"""
        model_type = ModelType.CHEST_CT_NODULE.value
        success, msg = engine.update_model_threshold(model_type, 0.85)
        
        assert success is True
        assert engine.models[model_type].threshold == 0.85

    def test_update_threshold_invalid_range(self, engine):
        """Test updating threshold with invalid value"""
        model_type = ModelType.CHEST_CT_NODULE.value
        
        # Test below range
        success, msg = engine.update_model_threshold(model_type, -0.1)
        assert success is False
        
        # Test above range
        success, msg = engine.update_model_threshold(model_type, 1.1)
        assert success is False

    def test_update_threshold_nonexistent_model(self, engine):
        """Test updating threshold for nonexistent model"""
        success, msg = engine.update_model_threshold("invalid_model", 0.5)
        assert success is False

    def test_toggle_model_disable(self, engine):
        """Test disabling a model"""
        model_type = ModelType.CHEST_CT_NODULE.value
        success, msg = engine.toggle_model(model_type, False)
        
        assert success is True
        assert engine.models[model_type].enabled is False

    def test_toggle_model_enable(self, engine):
        """Test enabling a model"""
        model_type = ModelType.CHEST_CT_NODULE.value
        engine.toggle_model(model_type, False)
        
        success, msg = engine.toggle_model(model_type, True)
        
        assert success is True
        assert engine.models[model_type].enabled is True

    def test_toggle_nonexistent_model(self, engine):
        """Test toggling nonexistent model"""
        success, msg = engine.toggle_model("invalid_model", False)
        assert success is False


# ============================================================================
# Triage Result Tests
# ============================================================================

class TestTriageResult:
    """Test TriageResult data class"""

    def test_triage_result_to_dict(self):
        """Test converting TriageResult to dictionary"""
        result = TriageResult(
            study_id="TEST-001",
            model=ModelType.CHEST_CT_NODULE,
            status=TriageStatus.CRITICAL,
            severity=Severity.CRITICAL,
            confidence=0.95,
            message="Critical finding detected",
            critical_slices=[10, 15, 20],
            roi_coordinates={"x": 100, "y": 200}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['study_id'] == "TEST-001"
        assert result_dict['model'] == ModelType.CHEST_CT_NODULE.value
        assert result_dict['status'] == TriageStatus.CRITICAL.value
        assert result_dict['severity'] == Severity.CRITICAL.value
        assert result_dict['confidence'] == 0.95

    def test_triage_result_timestamp(self):
        """Test that TriageResult includes timestamp"""
        result = TriageResult(
            study_id="TEST-001",
            model=ModelType.CHEST_CT_NODULE,
            status=TriageStatus.NORMAL,
            severity=Severity.NORMAL,
            confidence=0.5,
            message="No findings"
        )
        
        assert result.timestamp is not None
        assert len(result.timestamp) > 0


# ============================================================================
# MCP Tool Function Tests
# ============================================================================

class TestMCPTools:
    """Test MCP tool functions"""

    def test_mcp_list_models(self):
        """Test MCP list_models tool"""
        result = mcp_list_models()
        
        assert result['success'] is True
        assert 'models' in result
        assert len(result['models']) > 0

    def test_mcp_select_model_success(self):
        """Test MCP select_model tool success"""
        result = mcp_select_model("CT", "Chest")
        
        assert result['success'] is True
        assert result['model'] is not None
        assert result['config'] is not None

    def test_mcp_select_model_failure(self):
        """Test MCP select_model tool failure"""
        result = mcp_select_model("INVALID", "INVALID")
        
        assert result['success'] is False
        assert result['model'] is None

    def test_mcp_trigger_triage(self):
        """Test MCP trigger_triage tool"""
        result = mcp_trigger_triage(
            study_id="MCP-TEST-001",
            modality="CT",
            body_part="Chest"
        )
        
        assert result['success'] is True
        assert 'result' in result
        assert result['result']['study_id'] == "MCP-TEST-001"

    def test_mcp_trigger_triage_with_model(self):
        """Test MCP trigger_triage with explicit model"""
        result = mcp_trigger_triage(
            study_id="MCP-TEST-002",
            modality="CT",
            body_part="Brain",
            model_type="brain_ct_mobilenet"
        )
        
        assert result['success'] is True

    def test_mcp_get_triage_status(self):
        """Test MCP get_triage_status tool"""
        # First trigger triage
        mcp_trigger_triage(
            study_id="MCP-STATUS-001",
            modality="CT",
            body_part="Chest"
        )
        
        # Then get status
        result = mcp_get_triage_status("MCP-STATUS-001")
        
        assert result['success'] is True
        assert 'status_info' in result

    def test_mcp_get_model_config(self):
        """Test MCP get_model_config tool"""
        result = mcp_get_model_config("chest_ct_squeezenet")
        
        assert result['success'] is True
        assert result['config'] is not None
        assert result['config']['type'] == "chest_ct_squeezenet"

    def test_mcp_update_model_threshold(self):
        """Test MCP update_model_threshold tool"""
        result = mcp_update_model_threshold("chest_ct_squeezenet", 0.8)
        
        assert result['success'] is True

    def test_mcp_toggle_model(self):
        """Test MCP toggle_model tool"""
        result = mcp_toggle_model("chest_ct_squeezenet", False)
        
        assert result['success'] is True


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_empty_study_id(self, engine):
        """Test triage with empty study ID"""
        request = TriageRequest(
            study_id="",
            modality="CT",
            body_part="Chest"
        )
        
        # Should still process but with empty ID
        result = engine.trigger_triage(request)
        assert result.study_id == ""

    def test_special_characters_in_study_id(self, engine):
        """Test triage with special characters"""
        request = TriageRequest(
            study_id="STUDY-@#$%",
            modality="CT",
            body_part="Chest"
        )
        
        result = engine.trigger_triage(request)
        assert result.study_id == "STUDY-@#$%"

    def test_multiple_rapid_requests(self, engine):
        """Test handling multiple rapid triage requests"""
        for i in range(10):
            request = TriageRequest(
                study_id=f"RAPID-{i}",
                modality="CT",
                body_part="Chest"
            )
            result = engine.trigger_triage(request)
            assert result.error is None

    def test_thread_safe_queue_updates(self, engine):
        """Test queue is properly updated for multiple studies"""
        studies = [f"THREAD-{i}" for i in range(5)]
        
        for study_id in studies:
            request = TriageRequest(
                study_id=study_id,
                modality="CT",
                body_part="Chest"
            )
            engine.trigger_triage(request)
        
        # All should be queued
        for study_id in studies:
            assert study_id in engine.triage_queue


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
