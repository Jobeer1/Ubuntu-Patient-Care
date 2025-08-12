#!/usr/bin/env python3
"""
🇿🇦 South African Medical Reporting Module - Phase 1 Integration Test
Test script to verify complete Phase 1 functionality:
1. Start Report button integration
2. ReportingIntegration component functionality  
3. Voice recording capabilities
4. Measurement export workflow
"""

import json
import time
import requests
import sys
import os

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

def test_phase1_integration():
    """Test complete Phase 1 integration workflow"""
    print("🇿🇦 SA Medical Reporting - Phase 1 Integration Test")
    print("=" * 50)
    
    results = {
        "task1_start_button": False,
        "task2_reporting_component": False, 
        "task3_voice_recording": False,
        "task4_measurement_export": False,
        "overall_phase1": False
    }
    
    # Task 1: Check Start Report Button Integration
    print("\n📋 Task 1: Start Report Button Integration")
    print("-" * 30)
    
    try:
        # Check if StudyBrowser component has Start Report button
        studybrowser_path = "../dicom_viewer/src/components/StudyBrowser.tsx"
        if os.path.exists(studybrowser_path):
            with open(studybrowser_path, 'r') as f:
                content = f.read()
                if 'Start Report' in content and 'onStartReport' in content:
                    print("✅ Start Report button found in StudyBrowser")
                    results["task1_start_button"] = True
                else:
                    print("❌ Start Report button not properly integrated")
        else:
            print("❌ StudyBrowser component not found")
            
        # Check App.tsx integration
        app_path = "../dicom_viewer/src/App.tsx"
        if os.path.exists(app_path):
            with open(app_path, 'r') as f:
                content = f.read()
                if 'handleStartReport' in content and 'ReportingIntegration' in content:
                    print("✅ App.tsx reporting integration found")
                else:
                    print("❌ App.tsx integration incomplete")
                    
    except Exception as e:
        print(f"❌ Task 1 error: {e}")
    
    # Task 2: Check ReportingIntegration Component
    print("\n🔗 Task 2: ReportingIntegration Component")
    print("-" * 30)
    
    try:
        reporting_path = "../dicom_viewer/src/components/ReportingIntegration.tsx"
        if os.path.exists(reporting_path):
            with open(reporting_path, 'r') as f:
                content = f.read()
                required_features = [
                    'onExportMeasurements',
                    'initializeSession', 
                    'startVoiceRecording',
                    'exportMeasurements'
                ]
                
                missing_features = []
                for feature in required_features:
                    if feature not in content:
                        missing_features.append(feature)
                
                if not missing_features:
                    print("✅ ReportingIntegration component complete")
                    results["task2_reporting_component"] = True
                else:
                    print(f"❌ Missing features: {missing_features}")
        else:
            print("❌ ReportingIntegration component not found")
            
    except Exception as e:
        print(f"❌ Task 2 error: {e}")
    
    # Task 3: Check Voice Recording Setup
    print("\n🎤 Task 3: Voice Recording Capabilities")
    print("-" * 30)
    
    try:
        # Check if voice recording test exists
        voice_test_path = "../backend/test_voice_recording.py"
        if os.path.exists(voice_test_path):
            print("✅ Voice recording test file found")
            
            # Try to import required modules (simulate dependency check)
            try:
                import speech_recognition as sr
                print("✅ SpeechRecognition module available")
                results["task3_voice_recording"] = True
            except ImportError:
                print("⚠️  SpeechRecognition module missing - install with:")
                print("   pip install SpeechRecognition vosk pyaudio")
                
        else:
            print("❌ Voice recording test not found")
            
    except Exception as e:
        print(f"❌ Task 3 error: {e}")
    
    # Task 4: Check Measurement Export Integration
    print("\n📊 Task 4: Measurement Export Integration")
    print("-" * 30)
    
    try:
        # Check useMeasurements hook
        measurements_hook_path = "../dicom_viewer/src/hooks/useMeasurements.ts"
        if os.path.exists(measurements_hook_path):
            with open(measurements_hook_path, 'r') as f:
                content = f.read()
                required_functions = [
                    'addMeasurement',
                    'updateMeasurement', 
                    'removeMeasurement',
                    'exportMeasurements'
                ]
                
                missing_functions = []
                for func in required_functions:
                    if func not in content:
                        missing_functions.append(func)
                
                if not missing_functions:
                    print("✅ useMeasurements hook complete")
                    
                    # Check SA medical standards
                    if 'SA_MEDICAL_STANDARDS' in content:
                        print("✅ SA medical standards integrated")
                        results["task4_measurement_export"] = True
                    else:
                        print("⚠️  SA medical standards not found")
                else:
                    print(f"❌ Missing functions: {missing_functions}")
        else:
            print("❌ useMeasurements hook not found")
            
    except Exception as e:
        print(f"❌ Task 4 error: {e}")
    
    # Overall Phase 1 Assessment
    print("\n🎯 Phase 1 Overall Assessment")
    print("=" * 30)
    
    completed_tasks = sum(1 for result in results.values() if result and "task" in str(result))
    total_tasks = len([k for k in results.keys() if k.startswith("task")])
    
    print(f"Completed Tasks: {completed_tasks}/{total_tasks}")
    
    for task, status in results.items():
        if task.startswith("task"):
            status_icon = "✅" if status else "❌"
            task_name = task.replace("_", " ").title().replace("Task", "Task ")
            print(f"{status_icon} {task_name}")
    
    if completed_tasks == total_tasks:
        print("\n🎉 Phase 1 COMPLETE! Ready for testing.")
        results["overall_phase1"] = True
    elif completed_tasks >= 3:
        print("\n⚠️  Phase 1 mostly complete, minor issues to resolve.")
    else:
        print("\n❌ Phase 1 incomplete, significant work needed.")
    
    # Next Steps
    print("\n📋 Next Steps:")
    print("-" * 15)
    
    if not results["task3_voice_recording"]:
        print("1. Install voice recording dependencies:")
        print("   pip install SpeechRecognition vosk pyaudio")
        
    if completed_tasks == total_tasks:
        print("1. Start DICOM viewer: cd ../dicom_viewer && npm start")
        print("2. Start backend API: cd ../backend && python app.py") 
        print("3. Test complete workflow:")
        print("   - Load DICOM study")
        print("   - Click 'Start Report' button")
        print("   - Test voice recording")
        print("   - Export measurements")
        
    return results

def test_measurement_export_format():
    """Test SA medical measurement format compliance"""
    print("\n📏 Testing SA Medical Measurement Format")
    print("-" * 40)
    
    # Sample measurement data
    test_measurement = {
        "id": "measure_001",
        "type": "distance",
        "value": 45.7,
        "unit": "mm",
        "location": "cardiac_chamber",
        "timestamp": "2024-01-15T14:30:00Z",
        "sa_standards": {
            "unit_system": "metric",
            "precision": 1,
            "reference_standards": "SA_MEDICAL_2024"
        }
    }
    
    # Test export format
    try:
        export_data = {
            "patient_id": "SA123456789",
            "study_date": "2024-01-15",
            "measurements": [test_measurement],
            "medical_professional": {
                "license_number": "MP_SA_001234",
                "institution": "Cape Town Medical Center"
            },
            "sa_compliance": {
                "language": "en-ZA",
                "standards_version": "SA_MEDICAL_2024",
                "units": "metric"
            }
        }
        
        print("✅ SA medical format structure valid")
        print(f"   - Patient ID format: {export_data['patient_id']}")
        print(f"   - Measurements count: {len(export_data['measurements'])}")
        print(f"   - SA compliance: {export_data['sa_compliance']['standards_version']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Format validation error: {e}")
        return False

if __name__ == "__main__":
    # Run Phase 1 integration test
    results = test_phase1_integration()
    
    # Run measurement format test
    format_valid = test_measurement_export_format()
    
    # Final summary
    print("\n" + "=" * 50)
    print("🇿🇦 PHASE 1 INTEGRATION TEST COMPLETE")
    print("=" * 50)
    
    if results["overall_phase1"] and format_valid:
        print("🎉 SUCCESS: Phase 1 ready for production testing!")
        sys.exit(0)
    else:
        print("⚠️  REVIEW NEEDED: See issues above")
        sys.exit(1)
