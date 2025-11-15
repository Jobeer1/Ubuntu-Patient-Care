"""
Tests for P1-MAP-002: Patient ID Mapping Adapter

Tests verify:
1. Bidirectional mapping (OpenEMR ↔ FHIR UUID)
2. External ID registration and retrieval
3. UUID generation and validation
4. External ID lookup by type
5. Patient merging for duplicates
6. Complete mapping retrieval
7. FHIR identifier conversion
"""

import pytest
import uuid as uuid_module
from patient_id_adapter import (
    PatientIDAdapter,
    ExternalID,
    ExternalIDType,
    PatientIDMapping
)


@pytest.fixture
def adapter():
    """Create adapter instance for testing"""
    return PatientIDAdapter(auto_generate_uuid=True)


@pytest.fixture
def adapter_no_auto():
    """Create adapter without auto-generation"""
    return PatientIDAdapter(auto_generate_uuid=False)


class TestBasicMapping:
    """Test basic ID mapping functionality"""
    
    def test_register_mapping_generates_uuid(self, adapter):
        """Registering mapping without UUID generates one"""
        fhir_uuid = adapter.register_mapping("PAT-001")
        
        assert fhir_uuid
        assert len(fhir_uuid) == 36  # UUID format
    
    def test_register_mapping_with_uuid(self, adapter):
        """Registering with provided UUID uses it"""
        test_uuid = str(uuid_module.uuid4())
        result_uuid = adapter.register_mapping("PAT-002", test_uuid)
        
        assert result_uuid == test_uuid
    
    def test_forward_mapping(self, adapter):
        """OpenEMR ID → FHIR UUID mapping works"""
        fhir_uuid = adapter.register_mapping("PAT-003")
        
        result = adapter.get_fhir_id("PAT-003")
        assert result == fhir_uuid
    
    def test_reverse_mapping(self, adapter):
        """FHIR UUID → OpenEMR ID mapping works"""
        fhir_uuid = adapter.register_mapping("PAT-004")
        
        result = adapter.get_openemr_id(fhir_uuid)
        assert result == "PAT-004"
    
    def test_get_nonexistent_forward(self, adapter):
        """Getting nonexistent OpenEMR ID returns None"""
        result = adapter.get_fhir_id("PAT-999")
        assert result is None
    
    def test_get_nonexistent_reverse(self, adapter):
        """Getting nonexistent UUID returns None"""
        fake_uuid = str(uuid_module.uuid4())
        result = adapter.get_openemr_id(fake_uuid)
        assert result is None


class TestValidation:
    """Test input validation"""
    
    def test_invalid_openemr_id_empty(self, adapter):
        """Empty OpenEMR ID is rejected"""
        with pytest.raises(ValueError):
            adapter.register_mapping("")
    
    def test_invalid_openemr_id_none(self, adapter):
        """None OpenEMR ID is rejected"""
        with pytest.raises(ValueError):
            adapter.register_mapping(None)
    
    def test_invalid_uuid_format(self, adapter):
        """Invalid UUID format is rejected"""
        with pytest.raises(ValueError):
            adapter.register_mapping("PAT-005", "not-a-uuid")
    
    def test_duplicate_mapping_different_uuid(self, adapter):
        """Remapping to different UUID is rejected"""
        uuid1 = adapter.register_mapping("PAT-006")
        uuid2 = str(uuid_module.uuid4())
        
        with pytest.raises(ValueError):
            adapter.register_mapping("PAT-006", uuid2)
    
    def test_auto_generate_disabled(self, adapter_no_auto):
        """Without auto-generation, must provide UUID"""
        with pytest.raises(ValueError):
            adapter_no_auto.register_mapping("PAT-007")
    
    def test_auto_generate_works(self, adapter_no_auto):
        """With UUID provided, auto-generation disabled works"""
        test_uuid = str(uuid_module.uuid4())
        result = adapter_no_auto.register_mapping("PAT-008", test_uuid)
        assert result == test_uuid


class TestExternalIDs:
    """Test external ID functionality"""
    
    def test_register_with_external_ids(self, adapter):
        """Registering with external IDs stores them"""
        ext_ids = [
            ExternalID(ExternalIDType.SSN, "123-45-6789"),
            ExternalID(ExternalIDType.INSURANCE, "INS-123-456")
        ]
        fhir_uuid = adapter.register_mapping("PAT-010", external_ids=ext_ids)
        
        result = adapter.get_external_ids(fhir_uuid)
        assert len(result) == 2
    
    def test_find_by_ssn(self, adapter):
        """Finding patient by SSN works"""
        ext_ids = [ExternalID(ExternalIDType.SSN, "987-65-4321")]
        fhir_uuid = adapter.register_mapping("PAT-011", external_ids=ext_ids)
        
        found_uuid = adapter.find_by_external_id(ExternalIDType.SSN, "987-65-4321")
        assert found_uuid == fhir_uuid
    
    def test_find_by_insurance(self, adapter):
        """Finding patient by insurance ID works"""
        ext_ids = [ExternalID(ExternalIDType.INSURANCE, "BCBS-999")]
        fhir_uuid = adapter.register_mapping("PAT-012", external_ids=ext_ids)
        
        found_uuid = adapter.find_by_external_id(ExternalIDType.INSURANCE, "BCBS-999")
        assert found_uuid == fhir_uuid
    
    def test_find_nonexistent_external_id(self, adapter):
        """Finding nonexistent external ID returns None"""
        result = adapter.find_by_external_id(ExternalIDType.SSN, "000-00-0000")
        assert result is None
    
    def test_add_external_id(self, adapter):
        """Adding external ID to existing mapping works"""
        fhir_uuid = adapter.register_mapping("PAT-013")
        ext_id = ExternalID(ExternalIDType.MEDICARE, "1234567890")
        
        success = adapter.add_external_id(fhir_uuid, ext_id)
        
        assert success is True
        retrieved = adapter.get_external_ids(fhir_uuid)
        assert len(retrieved) == 1
    
    def test_add_external_id_to_nonexistent(self, adapter):
        """Adding external ID to nonexistent UUID fails"""
        fake_uuid = str(uuid_module.uuid4())
        ext_id = ExternalID(ExternalIDType.SSN, "111-11-1111")
        
        success = adapter.add_external_id(fake_uuid, ext_id)
        
        assert success is False
    
    def test_add_duplicate_external_id(self, adapter):
        """Adding duplicate external ID is idempotent"""
        fhir_uuid = adapter.register_mapping("PAT-014")
        ext_id = ExternalID(ExternalIDType.SSN, "222-22-2222")
        
        success1 = adapter.add_external_id(fhir_uuid, ext_id)
        success2 = adapter.add_external_id(fhir_uuid, ext_id)
        
        assert success1 is True
        assert success2 is True
        retrieved = adapter.get_external_ids(fhir_uuid)
        assert len(retrieved) == 1


class TestMappingRetrieval:
    """Test retrieving complete mappings"""
    
    def test_get_mapping(self, adapter):
        """Getting complete mapping works"""
        ext_ids = [
            ExternalID(ExternalIDType.SSN, "333-33-3333"),
            ExternalID(ExternalIDType.INSURANCE, "INS-888")
        ]
        fhir_uuid = adapter.register_mapping("PAT-015", external_ids=ext_ids)
        
        mapping = adapter.get_mapping("PAT-015")
        
        assert mapping is not None
        assert mapping.openemr_id == "PAT-015"
        assert mapping.fhir_uuid == fhir_uuid
        assert len(mapping.external_ids) == 2
    
    def test_get_nonexistent_mapping(self, adapter):
        """Getting nonexistent mapping returns None"""
        result = adapter.get_mapping("PAT-999")
        assert result is None
    
    def test_list_all_mappings(self, adapter):
        """Listing all mappings works"""
        adapter.register_mapping("PAT-020")
        adapter.register_mapping("PAT-021")
        adapter.register_mapping("PAT-022")
        
        all_mappings = adapter.list_all_mappings()
        
        assert len(all_mappings) >= 3
        assert all(isinstance(m, PatientIDMapping) for m in all_mappings)


class TestFHIRConversion:
    """Test conversion to FHIR format"""
    
    def test_to_fhir_identifier(self, adapter):
        """Converting to FHIR Identifier works"""
        adapter.register_mapping("PAT-025")
        
        fhir_id = adapter.to_fhir_identifier("PAT-025")
        
        assert fhir_id is not None
        assert fhir_id["system"] == "urn:openemr-patient-id"
        assert fhir_id["value"] == "PAT-025"
        assert "type" in fhir_id
    
    def test_fhir_identifier_nonexistent(self, adapter):
        """Converting nonexistent patient returns None"""
        result = adapter.to_fhir_identifier("PAT-999")
        assert result is None
    
    def test_external_id_to_fhir(self):
        """External ID converts to FHIR Identifier"""
        ext_id = ExternalID(ExternalIDType.SSN, "444-44-4444")
        fhir_id = ext_id.to_fhir_identifier()
        
        assert fhir_id["value"] == "444-44-4444"
        assert "system" in fhir_id
        assert "type" in fhir_id


class TestPatientMerging:
    """Test patient record merging for duplicates"""
    
    def test_merge_patients(self, adapter):
        """Merging patient records works"""
        # Create two records
        uuid1 = adapter.register_mapping("PAT-030")
        uuid2 = adapter.register_mapping("PAT-031")
        
        # Add external IDs to both
        adapter.add_external_id(uuid1, ExternalID(ExternalIDType.SSN, "555-55-5555"))
        adapter.add_external_id(uuid2, ExternalID(ExternalIDType.INSURANCE, "INS-555"))
        
        # Merge
        success = adapter.merge_patients(uuid1, uuid2)
        
        assert success is True
        
        # uuid1 should have both external IDs now
        external_ids = adapter.get_external_ids(uuid1)
        assert len(external_ids) == 2
    
    def test_merge_nonexistent_primary(self, adapter):
        """Merging with nonexistent primary fails"""
        fake_uuid = str(uuid_module.uuid4())
        uuid2 = adapter.register_mapping("PAT-032")
        
        success = adapter.merge_patients(fake_uuid, uuid2)
        assert success is False
    
    def test_merge_nonexistent_duplicate(self, adapter):
        """Merging with nonexistent duplicate fails"""
        uuid1 = adapter.register_mapping("PAT-033")
        fake_uuid = str(uuid_module.uuid4())
        
        success = adapter.merge_patients(uuid1, fake_uuid)
        assert success is False


class TestStatistics:
    """Test adapter statistics"""
    
    def test_stats_empty(self, adapter):
        """Empty adapter has zero mappings"""
        stats = adapter.stats()
        
        assert stats["total_mappings"] == 0
        assert stats["total_external_ids"] == 0
    
    def test_stats_after_registrations(self, adapter):
        """Stats update after registrations"""
        adapter.register_mapping("PAT-040", external_ids=[
            ExternalID(ExternalIDType.SSN, "666-66-6666")
        ])
        adapter.register_mapping("PAT-041")
        
        stats = adapter.stats()
        
        assert stats["total_mappings"] >= 2
        assert stats["total_external_ids"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
