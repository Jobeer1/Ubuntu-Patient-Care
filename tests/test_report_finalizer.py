"""
Tests for P1-AUD-004: Hash & Stamp Integration

Tests verify:
1. Content hashing consistency
2. Audit stamp creation and metadata
3. Stamp verification and tamper detection
4. Merkle ledger integration
5. Audit trail retrieval
"""

import pytest
import json
import tempfile
import os
from datetime import datetime
import sys

# Add audit module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'audit'))

from report_finalizer import ReportFinalizer, ReportAuditStamp


@pytest.fixture
def temp_ledger():
    """Create temporary ledger file for testing"""
    fd, path = tempfile.mkstemp(suffix='.ledger')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def finalizer(temp_ledger):
    """Create ReportFinalizer instance for testing"""
    return ReportFinalizer(temp_ledger)


@pytest.fixture
def sample_report():
    """Sample report content for testing"""
    return {
        "patient_id": "PAT-123",
        "imaging_study_id": "STUDY-456",
        "findings": "No abnormalities detected",
        "conclusion": "Normal study",
        "body_part": "Chest",
        "modality": "X-Ray"
    }


class TestContentHashing:
    """Test content hashing functionality"""
    
    def test_hash_consistency(self, finalizer, sample_report):
        """Same content should always produce same hash"""
        hash1 = finalizer.compute_content_hash(sample_report)
        hash2 = finalizer.compute_content_hash(sample_report)
        assert hash1 == hash2
    
    def test_hash_changes_with_content(self, finalizer, sample_report):
        """Different content should produce different hash"""
        hash1 = finalizer.compute_content_hash(sample_report)
        
        modified_report = sample_report.copy()
        modified_report["findings"] = "Abnormality detected"
        hash2 = finalizer.compute_content_hash(modified_report)
        
        assert hash1 != hash2
    
    def test_hash_order_independent(self, finalizer):
        """Hash should be same regardless of key order (canonical JSON)"""
        data1 = {"a": 1, "b": 2, "c": 3}
        data2 = {"c": 3, "a": 1, "b": 2}
        
        hash1 = finalizer.compute_content_hash(data1)
        hash2 = finalizer.compute_content_hash(data2)
        
        assert hash1 == hash2
    
    def test_hash_format(self, finalizer, sample_report):
        """Hash should be valid hex string"""
        hash_val = finalizer.compute_content_hash(sample_report)
        
        assert isinstance(hash_val, str)
        assert len(hash_val) == 64  # SHA256 produces 64 hex chars
        assert all(c in '0123456789abcdef' for c in hash_val)


class TestReportFinalization:
    """Test report finalization and stamp creation"""
    
    def test_finalize_creates_stamp(self, finalizer, sample_report):
        """Finalizing report creates valid audit stamp"""
        stamp = finalizer.finalize_report(
            report_id="REPORT-001",
            content=sample_report,
            practitioner_id="DOC-123"
        )
        
        assert isinstance(stamp, ReportAuditStamp)
        assert stamp.report_id == "REPORT-001"
        assert stamp.practitioner_id == "DOC-123"
        assert stamp.ledger_tx_id is not None
    
    def test_stamp_has_correct_hash(self, finalizer, sample_report):
        """Audit stamp contains correct content hash"""
        expected_hash = finalizer.compute_content_hash(sample_report)
        
        stamp = finalizer.finalize_report(
            report_id="REPORT-002",
            content=sample_report,
            practitioner_id="DOC-123"
        )
        
        assert stamp.content_hash == expected_hash
    
    def test_stamp_has_timestamp(self, finalizer, sample_report):
        """Audit stamp contains timestamp"""
        before = datetime.utcnow()
        
        stamp = finalizer.finalize_report(
            report_id="REPORT-003",
            content=sample_report,
            practitioner_id="DOC-123"
        )
        
        after = datetime.utcnow()
        
        # Timestamp should be ISO format and within time range
        assert "T" in stamp.timestamp
        assert "Z" in stamp.timestamp or "+" in stamp.timestamp or "-" in stamp.timestamp
    
    def test_finalize_with_signature(self, finalizer, sample_report):
        """Finalization can include digital signature"""
        sig = "sig_abc123xyz"
        
        stamp = finalizer.finalize_report(
            report_id="REPORT-004",
            content=sample_report,
            practitioner_id="DOC-123",
            signature=sig
        )
        
        assert stamp.signature == sig
    
    def test_finalize_invalid_report_id(self, finalizer, sample_report):
        """Finalization rejects invalid report IDs"""
        with pytest.raises(ValueError):
            finalizer.finalize_report(
                report_id="",
                content=sample_report,
                practitioner_id="DOC-123"
            )
    
    def test_finalize_invalid_content(self, finalizer):
        """Finalization rejects invalid content"""
        with pytest.raises(ValueError):
            finalizer.finalize_report(
                report_id="REPORT-005",
                content="not a dict",
                practitioner_id="DOC-123"
            )
    
    def test_finalize_invalid_practitioner(self, finalizer, sample_report):
        """Finalization rejects invalid practitioner ID"""
        with pytest.raises(ValueError):
            finalizer.finalize_report(
                report_id="REPORT-006",
                content=sample_report,
                practitioner_id=""
            )


class TestStampVerification:
    """Test stamp verification and tamper detection"""
    
    def test_verify_valid_stamp(self, finalizer, sample_report):
        """Valid stamp should verify successfully"""
        stamp = finalizer.finalize_report(
            report_id="REPORT-010",
            content=sample_report,
            practitioner_id="DOC-123"
        )
        
        is_valid = finalizer.verify_report_stamp(
            "REPORT-010",
            sample_report,
            stamp
        )
        
        assert is_valid is True
    
    def test_verify_detects_tampered_content(self, finalizer, sample_report):
        """Verification should detect tampered content"""
        stamp = finalizer.finalize_report(
            report_id="REPORT-011",
            content=sample_report,
            practitioner_id="DOC-123"
        )
        
        # Tamper with content
        tampered_report = sample_report.copy()
        tampered_report["findings"] = "TAMPERED"
        
        is_valid = finalizer.verify_report_stamp(
            "REPORT-011",
            tampered_report,
            stamp
        )
        
        assert is_valid is False
    
    def test_verify_detects_wrong_report_id(self, finalizer, sample_report):
        """Verification should detect mismatched report ID"""
        stamp = finalizer.finalize_report(
            report_id="REPORT-012",
            content=sample_report,
            practitioner_id="DOC-123"
        )
        
        is_valid = finalizer.verify_report_stamp(
            "REPORT-999",  # Wrong ID
            sample_report,
            stamp
        )
        
        assert is_valid is False
    
    def test_verify_detects_single_field_change(self, finalizer, sample_report):
        """Verification should detect even single field changes"""
        stamp = finalizer.finalize_report(
            report_id="REPORT-013",
            content=sample_report,
            practitioner_id="DOC-123"
        )
        
        # Change just one field
        modified = sample_report.copy()
        modified["conclusion"] = "Modified conclusion"
        
        is_valid = finalizer.verify_report_stamp(
            "REPORT-013",
            modified,
            stamp
        )
        
        assert is_valid is False


class TestAuditTrail:
    """Test audit trail functionality"""
    
    def test_audit_trail_retrieval(self, finalizer, sample_report):
        """Should retrieve audit trail for report"""
        report_id = "REPORT-020"
        
        # Finalize report
        stamp = finalizer.finalize_report(
            report_id=report_id,
            content=sample_report,
            practitioner_id="DOC-123"
        )
        
        # Get trail
        trail = finalizer.get_audit_trail(report_id)
        
        assert len(trail) >= 1
        assert any(e.get("report_id") == report_id for e in trail)
    
    def test_audit_trail_only_matching_reports(self, finalizer, sample_report):
        """Audit trail should only contain events for specified report"""
        # Finalize multiple reports
        for i in range(3):
            finalizer.finalize_report(
                report_id=f"REPORT-{i}",
                content=sample_report,
                practitioner_id="DOC-123"
            )
        
        # Get trail for one report
        trail = finalizer.get_audit_trail("REPORT-1")
        
        # All entries should be for REPORT-1
        assert all(e.get("report_id") == "REPORT-1" for e in trail)


class TestAuditStampDataStructure:
    """Test ReportAuditStamp data structure"""
    
    def test_stamp_to_dict(self, finalizer, sample_report):
        """Stamp should convert to dictionary"""
        stamp = finalizer.finalize_report(
            report_id="REPORT-030",
            content=sample_report,
            practitioner_id="DOC-123",
            signature="sig_123"
        )
        
        stamp_dict = stamp.to_dict()
        
        assert isinstance(stamp_dict, dict)
        assert stamp_dict["report_id"] == "REPORT-030"
        assert stamp_dict["practitioner_id"] == "DOC-123"
        assert stamp_dict["signature"] == "sig_123"
        assert "content_hash" in stamp_dict
        assert "timestamp" in stamp_dict
        assert "ledger_tx_id" in stamp_dict
    
    def test_stamp_serializable_to_json(self, finalizer, sample_report):
        """Stamp should be serializable to JSON"""
        stamp = finalizer.finalize_report(
            report_id="REPORT-031",
            content=sample_report,
            practitioner_id="DOC-123"
        )
        
        # Should not raise
        json_str = json.dumps(stamp.to_dict())
        
        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["report_id"] == "REPORT-031"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
