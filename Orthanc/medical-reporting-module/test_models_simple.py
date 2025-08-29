#!/usr/bin/env python3
"""
Simple test script for Medical Reporting Module data models
"""

from models.database import init_database, get_db_session, close_db_session
from models.report import Report, ReportStatus
from models.template import ReportTemplate
from models.layout import ScreenLayout
from models.voice_session import VoiceSession

def test_models():
    """Test basic model functionality"""
    print("🧪 Testing Medical Reporting Module Data Models")
    print("=" * 60)
    
    # Initialize database
    print("1. Initializing database...")
    success = init_database(create_sample=True)
    if not success:
        print("❌ Database initialization failed")
        return False
    print("✅ Database initialized successfully")
    
    # Get database session
    session = get_db_session()
    
    try:
        # Test Report model
        print("\n2. Testing Report model...")
        report = Report(
            study_id="TEST_STUDY_001",
            patient_id="TEST_PATIENT_001",
            doctor_id="TEST_DOCTOR_001",
            content={"findings": "Test findings", "impression": "Test impression"},
            created_by="TEST_DOCTOR_001",
            updated_by="TEST_DOCTOR_001"
        )
        
        session.add(report)
        session.commit()
        
        # Verify report creation
        saved_report = session.query(Report).filter_by(study_id="TEST_STUDY_001").first()
        assert saved_report is not None
        assert saved_report.status == ReportStatus.DRAFT.value
        assert saved_report.is_editable() == True
        print("✅ Report model working correctly")
        
        # Test Template model
        print("\n3. Testing Template model...")
        template = ReportTemplate(
            name="Test Template",
            category="test",
            specialty="general",
            voice_commands=["test template", "template test"],
            sections=[{"name": "test_section", "title": "Test Section"}],
            created_by="ADMIN",
            updated_by="ADMIN"
        )
        
        session.add(template)
        session.commit()
        
        # Verify template creation
        saved_template = session.query(ReportTemplate).filter_by(name="Test Template").first()
        assert saved_template is not None
        assert len(saved_template.voice_commands) == 2
        assert saved_template.usage_count == 0
        print("✅ Template model working correctly")
        
        # Test Layout model
        print("\n4. Testing Layout model...")
        layout = ScreenLayout(
            name="Test Layout",
            user_id="TEST_USER_001",
            viewport_config={"grid": {"rows": 2, "columns": 2}},
            panel_arrangement={"report_panel": {"position": "right"}},
            monitor_setup={"primary": {"width": 1920, "height": 1080}},
            created_by="TEST_USER_001",
            updated_by="TEST_USER_001"
        )
        
        session.add(layout)
        session.commit()
        
        # Verify layout creation
        saved_layout = session.query(ScreenLayout).filter_by(name="Test Layout").first()
        assert saved_layout is not None
        assert saved_layout.user_id == "TEST_USER_001"
        print("✅ Layout model working correctly")
        
        # Test VoiceSession model
        print("\n5. Testing VoiceSession model...")
        voice_session = VoiceSession(
            user_id="TEST_USER_001",
            session_name="Test Voice Session",
            audio_file_path="/test/path/audio.wav",
            audio_duration_seconds=120.5
        )
        
        session.add(voice_session)
        session.commit()
        
        # Verify voice session creation
        saved_session = session.query(VoiceSession).filter_by(session_name="Test Voice Session").first()
        assert saved_session is not None
        assert saved_session.audio_duration_seconds == 120.5
        print("✅ VoiceSession model working correctly")
        
        # Test relationships
        print("\n6. Testing model relationships...")
        
        # Link report to template
        report.template_id = template.id
        session.commit()
        
        # Verify relationship
        assert report.template is not None
        assert report.template.name == "Test Template"
        print("✅ Model relationships working correctly")
        
        # Test sample data
        print("\n7. Testing sample data...")
        sample_templates = session.query(ReportTemplate).filter_by(is_system_template=True).all()
        sample_layouts = session.query(ScreenLayout).filter_by(is_system_preset=True).all()
        
        print(f"   Found {len(sample_templates)} sample templates")
        print(f"   Found {len(sample_layouts)} sample layouts")
        
        if sample_templates:
            print(f"   Sample template: {sample_templates[0].name}")
        if sample_layouts:
            print(f"   Sample layout: {sample_layouts[0].name}")
        
        print("✅ Sample data created successfully")
        
        print("\n" + "=" * 60)
        print("🎉 All model tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        session.rollback()
        return False
        
    finally:
        close_db_session(session)

if __name__ == "__main__":
    success = test_models()
    exit(0 if success else 1)