#!/usr/bin/env python3
"""
Comprehensive Diagnostic Tests for SA Medical Reporting Module
Tests all the fixes for dashboard, templates, and STT service
"""

import logging
import sys
import tempfile
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_flask_app_creation():
    """Test if Flask app can be created"""
    print("🔧 Testing Flask app creation...")
    try:
        from core.app_factory import create_app
        app = create_app('development')
        print("✅ Flask app created successfully")
        
        # Check template folder configuration
        print(f"   Template folder: {app.template_folder}")
        print(f"   Static folder: {app.static_folder}")
        return True
    except Exception as e:
        print(f"❌ Flask app creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_template_paths():
    """Test if template files exist"""
    print("🔧 Testing template file existence...")
    
    template_files = [
        'templates/dashboard_sa.html',
        'templates/voice_demo_sa.html'
    ]
    
    all_exist = True
    for template_file in template_files:
        if os.path.exists(template_file):
            print(f"✅ {template_file} exists")
        else:
            print(f"❌ {template_file} missing")
            all_exist = False
    
    return all_exist

def test_template_loading():
    """Test if templates can be loaded"""
    print("🔧 Testing template loading...")
    try:
        from core.app_factory import create_app
        
        app = create_app('development')
        
        with app.app_context():
            # Test dashboard template
            try:
                from flask import render_template
                result = render_template('dashboard_sa.html', 
                                      server_date_iso='2025-01-28T09:00:00', 
                                      doctor_name='Dr. Stoyanov')
                if 'Dr. Stoyanov' in result and 'SA Medical Reporting' in result:
                    print("✅ Dashboard template loaded successfully")
                    dashboard_ok = True
                else:
                    print("❌ Dashboard template content incorrect")
                    dashboard_ok = False
            except Exception as e:
                print(f"❌ Dashboard template loading failed: {e}")
                import traceback
                traceback.print_exc()
                dashboard_ok = False
                
            # Test voice demo template  
            try:
                result = render_template('voice_demo_sa.html')
                if 'SA Mediese Stem Demo' in result or 'Voice Demo' in result:
                    print("✅ Voice demo template loaded successfully")
                    voice_ok = True
                else:
                    print("❌ Voice demo template content incorrect")
                    voice_ok = False
            except Exception as e:
                print(f"❌ Voice demo template loading failed: {e}")
                import traceback
                traceback.print_exc()
                voice_ok = False
                
        return dashboard_ok and voice_ok
        
    except Exception as e:
        print(f"❌ Template loading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_stt_service():
    """Test if STT service is working"""
    print("🔧 Testing STT service...")
    try:
        from services.offline_stt_service import offline_stt_service
        
        # Test service initialization
        if offline_stt_service.initialize():
            print("✅ STT service initialized successfully")
            
            # Test temporary file creation and handling
            try:
                # Create proper temporary file with explicit close
                temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_file_path = temp_file.name
                
                # Write minimal WAV header for testing
                wav_header = b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x02\x00\x44\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00data\x00\x08\x00\x00'
                temp_file.write(wav_header)
                temp_file.flush()
                # IMPORTANT: Close file handle so Windows can access it
                temp_file.close()
                
                print(f"   Temp file created: {temp_file_path}")
                
                # Test if file exists and is readable
                if os.path.exists(temp_file_path):
                    print("✅ Temp file exists and is accessible")
                    
                    # Test transcription (should handle gracefully even with minimal data)
                    result = offline_stt_service.transcribe_audio_file(temp_file_path)
                    print(f"✅ STT transcription test completed (result: {result})")
                    
                    temp_ok = True
                else:
                    print("❌ Temp file not accessible")
                    temp_ok = False
                
                # Clean up
                try:
                    os.unlink(temp_file_path)
                    print("✅ Temp file cleaned up")
                except Exception as cleanup_e:
                    print(f"⚠️  Temp file cleanup warning: {cleanup_e}")
                
                return temp_ok
                
            except Exception as temp_e:
                print(f"❌ Temp file handling failed: {temp_e}")
                import traceback
                traceback.print_exc()
                return False
                
        else:
            print("❌ STT service initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ STT service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_service_manager():
    """Test if service manager can initialize services"""
    print("🔧 Testing service manager...")
    try:
        from core.service_manager import ServiceManager
        
        service_manager = ServiceManager()
        service_manager.initialize_all_services()
        
        # Check if key services are available
        stt_service = service_manager.get_service('stt_service')
        offline_stt = service_manager.get_service('offline_stt_service')
        
        services_ok = 0
        if stt_service:
            print("✅ STT service available in service manager")
            services_ok += 1
        else:
            print("❌ STT service not available in service manager")
            
        if offline_stt:
            print("✅ Offline STT service available in service manager")
            services_ok += 1
        else:
            print("❌ Offline STT service not available in service manager")
            
        return services_ok >= 1
        
    except Exception as e:
        print(f"❌ Service manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_voice_api_endpoint():
    """Test voice API endpoint functionality"""
    print("🔧 Testing voice API endpoint...")
    try:
        from core.app_factory import create_app
        
        app = create_app('development')
        
        with app.test_client() as client:
            # Test voice session start
            response = client.post('/api/voice/session/start')
            if response.status_code in [200, 201]:
                print("✅ Voice session start endpoint working")
                session_ok = True
            else:
                print(f"❌ Voice session start failed: {response.status_code}")
                session_ok = False
            
            # Test transcribe endpoint with empty data (should handle gracefully)
            response = client.post('/api/voice/transcribe')
            # Should return 400 for missing data, not crash
            if response.status_code in [400, 422]:
                print("✅ Voice transcribe endpoint handles empty data correctly")
                transcribe_ok = True
            else:
                print(f"❌ Voice transcribe endpoint unexpected response: {response.status_code}")
                transcribe_ok = False
            
        return session_ok and transcribe_ok
        
    except Exception as e:
        print(f"❌ Voice API endpoint test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all diagnostic tests"""
    print("🏥 SA Medical Reporting Module - Comprehensive Diagnostic Tests")
    print("=" * 70)
    
    tests = [
        ("Flask App Creation", test_flask_app_creation),
        ("Template File Paths", test_template_paths),
        ("Template Loading", test_template_loading),
        ("STT Service", test_stt_service),
        ("Service Manager", test_service_manager),
        ("Voice API Endpoints", test_voice_api_endpoint)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} Test...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} Test PASSED")
            else:
                print(f"❌ {test_name} Test FAILED")
        except Exception as e:
            print(f"❌ {test_name} Test ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(f"📊 Test Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! The fixes are working correctly.")
        return 0
    elif passed >= total * 0.8:
        print("⚠️  Most tests passed. Minor issues may need attention.")
        return 0
    else:
        print("⚠️  Several tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
