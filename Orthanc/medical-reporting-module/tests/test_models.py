"""
Unit tests for Medical Reporting Module data models
"""

import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import models
from models.report import Report, OfflineChange, ReportStatus
from models.template import ReportTemplate, TemplateSection
from models.layout import ScreenLayout, ViewportConfiguration
from models.voice_session import VoiceSession, AudioSegment, VoiceCommand, VoiceSessionStatus
from models.database import DatabaseManager

class TestDatabaseSetup:
    """Test database setup and initialization"""
    
    @pytest.fixture
    def db_manager(self):
        """Create test database manager"""
        db_manager = DatabaseManager('sqlite:///:memory:')
        db_manager.initialize()
        yield db_manager
        # Cleanup is automatic with in-memory database
    
    @pytest.fixture
    def session(self, db_manager):
        """Create test database session"""
        session = db_manager.get_session()
        yield session
        session.close()
    
    def test_database_initialization(self, db_manager):
        """Test database initialization"""
        assert db_manager.engine is not None
        assert db_manager.Session is not None
        
        # Test table creation
        table_info = db_manager.get_table_info()
        expected_tables = ['reports', 'report_templates', 'screen_layouts', 'voice_sessions']
        
        for table in expected_tables:
            assert table in table_info

class TestReportModel:
    """Test Report model functionality"""
    
    @pytest.fixture
    def db_manager(self):
        db_manager = DatabaseManager('sqlite:///:memory:')
        db_manager.initialize()
        return db_manager
    
    @pytest.fixture
    def session(self, db_manager):
        session = db_manager.get_session()
        yield session
        session.close()
    
    def test_report_creation(self, session):
        """Test creating a new report"""
        report = Report(
            study_id="STUDY123",
            patient_id="PAT456",
            doctor_id="DOC789",
            content={"findings": "Normal study"},
            created_by="DOC789",
            updated_by="DOC789"
        )
        
        session.add(report)
        session.commit()
        
        # Verify report was created
        assert report.id is not None
        assert report.study_id == "STUDY123"
        assert report.status == ReportStatus.DRAFT.value
        assert report.created_at is not None
    
    def test_report_status_update(self, session):
        """Test updating report status"""
        report = Report(
            study_id="STUDY123",
            patient_id="PAT456",
            doctor_id="DOC789",
            created_by="DOC789",
            updated_by="DOC789"
        )
        
        session.add(report)
        session.commit()
        
        # Update status
        report.update_status(ReportStatus.TYPING.value, "DOC789")
        session.commit()
        
        assert report.status == ReportStatus.TYPING.value
        assert report.submitted_at is not None
    
    def test_report_to_dict(self, session):
        """Test report serialization"""
        report = Report(
            study_id="STUDY123",
            patient_id="PAT456",
            doctor_id="DOC789",
            content={"findings": "Normal study"},
            created_by="DOC789",
            updated_by="DOC789"
        )
        
        session.add(report)
        session.commit()
        
        report_dict = report.to_dict()
        
        assert report_dict['study_id'] == "STUDY123"
        assert report_dict['patient_id'] == "PAT456"
        assert report_dict['content'] == {"findings": "Normal study"}
        assert 'created_at' in report_dict
    
    def test_report_editability(self, session):
        """Test report editability logic"""
        report = Report(
            study_id="STUDY123",
            patient_id="PAT456",
            doctor_id="DOC789",
            created_by="DOC789",
            updated_by="DOC789"
        )
        
        # Draft reports should be editable
        assert report.is_editable() == True
        
        # Final reports should not be editable
        report.status = ReportStatus.FINAL.value
        assert report.is_editable() == False

class TestTemplateModel:
    """Test ReportTemplate model functionality"""
    
    @pytest.fixture
    def db_manager(self):
        db_manager = DatabaseManager('sqlite:///:memory:')
        db_manager.initialize()
        return db_manager
    
    @pytest.fixture
    def session(self, db_manager):
        session = db_manager.get_session()
        yield session
        session.close()
    
    def test_template_creation(self, session):
        """Test creating a new template"""
        template = ReportTemplate(
            name="CT Chest Template",
            category="radiology",
            specialty="thoracic",
            voice_commands=["chest ct", "ct chest"],
            sections=[
                {"name": "findings", "title": "Findings", "required": True}
            ],
            created_by="ADMIN",
            updated_by="ADMIN"
        )
        
        session.add(template)
        session.commit()
        
        assert template.id is not None
        assert template.name == "CT Chest Template"
        assert len(template.voice_commands) == 2
        assert template.usage_count == 0
    
    def test_template_voice_commands(self, session):
        """Test voice command management"""
        template = ReportTemplate(
            name="Test Template",
            category="radiology",
            specialty="general",
            created_by="ADMIN",
            updated_by="ADMIN"
        )
        
        # Add voice command
        template.add_voice_command("test command")
        assert "test command" in template.voice_commands
        assert template.primary_command == "test command"
        
        # Add another command
        template.add_voice_command("another command")
        assert len(template.voice_commands) == 2
        assert template.primary_command == "test command"  # Should remain the same
        
        # Remove command
        template.remove_voice_command("test command")
        assert "test command" not in template.voice_commands
        assert template.primary_command == "another command"  # Should update
    
    def test_template_usage_tracking(self, session):
        """Test template usage tracking"""
        template = ReportTemplate(
            name="Test Template",
            category="radiology",
            specialty="general",
            created_by="ADMIN",
            updated_by="ADMIN"
        )
        
        session.add(template)
        session.commit()
        
        initial_usage = template.usage_count
        initial_last_used = template.last_used_at
        
        # Increment usage
        template.increment_usage()
        session.commit()
        
        assert template.usage_count == initial_usage + 1
        assert template.last_used_at != initial_last_used

class TestLayoutModel:
    """Test ScreenLayout model functionality"""
    
    @pytest.fixture
    def db_manager(self):
        db_manager = DatabaseManager('sqlite:///:memory:')
        db_manager.initialize()
        return db_manager
    
    @pytest.fixture
    def session(self, db_manager):
        session = db_manager.get_session()
        yield session
        session.close()
    
    def test_layout_creation(self, session):
        """Test creating a new layout"""
        layout = ScreenLayout(
            name="Test Layout",
            user_id="USER123",
            viewport_config={"grid": {"rows": 2, "columns": 2}},
            panel_arrangement={"report_panel": {"position": "right"}},
            monitor_setup={"primary": {"width": 1920, "height": 1080}},
            created_by="USER123",
            updated_by="USER123"
        )
        
        session.add(layout)
        session.commit()
        
        assert layout.id is not None
        assert layout.name == "Test Layout"
        assert layout.grid_rows == 2
        assert layout.grid_columns == 2
    
    def test_layout_cloning(self, session):
        """Test layout cloning functionality"""
        original_layout = ScreenLayout(
            name="Original Layout",
            user_id="USER123",
            viewport_config={"test": "config"},
            created_by="USER123",
            updated_by="USER123"
        )
        
        session.add(original_layout)
        session.commit()
        
        # Clone layout
        clone_data = original_layout.clone_for_user("USER456", "Cloned Layout")
        
        assert clone_data['name'] == "Cloned Layout"
        assert clone_data['user_id'] == "USER456"
        assert clone_data['viewport_config'] == {"test": "config"}
        assert clone_data['usage_count'] == 0
        assert 'id' not in clone_data  # Should not include original ID

class TestVoiceSessionModel:
    """Test VoiceSession model functionality"""
    
    @pytest.fixture
    def db_manager(self):
        db_manager = DatabaseManager('sqlite:///:memory:')
        db_manager.initialize()
        return db_manager
    
    @pytest.fixture
    def session(self, db_manager):
        session = db_manager.get_session()
        yield session
        session.close()
    
    def test_voice_session_creation(self, session):
        """Test creating a new voice session"""
        voice_session = VoiceSession(
            user_id="USER123",
            session_name="Test Session",
            audio_file_path="/path/to/audio.wav",
            audio_duration_seconds=120.5
        )
        
        session.add(voice_session)
        session.commit()
        
        assert voice_session.id is not None
        assert voice_session.user_id == "USER123"
        assert voice_session.status == VoiceSessionStatus.ACTIVE.value
        assert voice_session.audio_duration_seconds == 120.5
    
    def test_voice_session_lifecycle(self, session):
        """Test voice session lifecycle methods"""
        voice_session = VoiceSession(user_id="USER123")
        
        # Test pause
        voice_session.pause_session()
        assert voice_session.status == VoiceSessionStatus.PAUSED.value
        
        # Test resume
        voice_session.resume_session()
        assert voice_session.status == VoiceSessionStatus.ACTIVE.value
        
        # Test end
        voice_session.end_session()
        assert voice_session.status == VoiceSessionStatus.COMPLETED.value
        assert voice_session.end_time is not None
    
    def test_voice_command_tracking(self, session):
        """Test voice command tracking"""
        voice_session = VoiceSession(user_id="USER123")
        
        # Add template command
        voice_session.add_command("template", "chest ct", {"template_id": "123"})
        assert len(voice_session.template_commands) == 1
        
        # Add navigation command
        voice_session.add_command("navigation", "next image", {"action": "next"})
        assert len(voice_session.navigation_commands) == 1
        
        # Add general command
        voice_session.add_command("action", "save report", {"saved": True})
        assert len(voice_session.commands_executed) == 1

def run_model_tests():
    """Run all model tests"""
    pytest.main([__file__, "-v"])

if __name__ == "__main__":
    run_model_tests()