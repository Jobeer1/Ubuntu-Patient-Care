#!/usr/bin/env python3
"""
Simple test for reporting engine
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_import():
    """Test basic import"""
    try:
        from core.reporting_engine import ReportingEngine, WorkflowState
        from models.report import ReportType
        print("✓ Imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_engine_creation():
    """Test engine creation"""
    try:
        from core.reporting_engine import ReportingEngine
        engine = ReportingEngine()
        print("✓ Engine created successfully")
        return True
    except Exception as e:
        print(f"✗ Engine creation failed: {e}")
        return False

def test_basic_session():
    """Test basic session creation"""
    try:
        from core.reporting_engine import ReportingEngine
        from models.report import ReportType
        
        engine = ReportingEngine()
        session = engine.create_report(
            user_id="doctor123",
            study_id="study456",
            report_type=ReportType.DIAGNOSTIC
        )
        
        print(f"✓ Session created: {session.session_id}")
        
        # End session
        engine.end_session(session.session_id)
        print("✓ Session ended")
        
        return True
    except Exception as e:
        print(f"✗ Basic session test failed: {e}")
        return False

if __name__ == "__main__":
    print("Simple Reporting Engine Test")
    print("=" * 40)
    
    tests = [
        test_basic_import,
        test_engine_creation,
        test_basic_session
    ]
    
    for test in tests:
        if not test():
            sys.exit(1)
    
    print("=" * 40)
    print("✓ All basic tests passed!")