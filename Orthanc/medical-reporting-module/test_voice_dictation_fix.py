#!/usr/bin/env python3
"""
Test Voice Dictation Functionality
Verify that voice dictation is working and writing to text areas properly
"""

import os
import sys
import requests
import json
import tempfile
import wave
import numpy as np
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_audio():
    """Create a simple test audio file"""
    # Create a simple sine wave audio file for testing
    sample_rate = 16000
    duration = 2  # seconds
    frequency = 440  # Hz
    
    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(2 * np.pi * frequency * t)
    
    # Convert to 16-bit integers
    audio_data = (audio_data * 32767).astype(np.int16)
    
    # Create temporary WAV file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    
    with wave.open(temp_file.name, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    return temp_file.name

def test_voice_session_start():
    """Test starting a voice session"""
    print("🎤 Testing voice session start...")
    
    try:
        response = requests.post('https://localhost:5001/api/demo/voice/start', 
                               json={'language': 'en-ZA', 'medical_mode': True},
                               verify=False)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Voice session started: {data.get('session_id')}")
            return data.get('session_id')
        else:
            print(f"❌ Voice session start failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Voice session start error: {e}")
        return None

def test_voice_transcription():
    """Test voice transcription with audio file"""
    print("🎤 Testing voice transcription...")
    
    try:
        # Create test audio file
        audio_file = create_test_audio()
        
        try:
            with open(audio_file, 'rb') as f:
                files = {'audio': ('test.wav', f, 'audio/wav')}
                data = {'session_id': 'test_session', 'language': 'en-ZA'}
                
                response = requests.post('https://localhost:5001/api/voice/transcribe',
                                       files=files,
                                       data=data,
                                       verify=False)
            
            if response.status_code == 200:
                result = response.json()
                transcription = result.get('transcription', '')
                print(f"✅ Transcription received: {transcription[:100]}...")
                print(f"   SA Enhanced: {result.get('sa_enhanced', False)}")
                print(f"   Confidence: {result.get('confidence', 0)}")
                return transcription
            else:
                print(f"❌ Transcription failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        finally:
            # Clean up temp file
            try:
                os.unlink(audio_file)
            except:
                pass
            
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return None

def test_report_saving():
    """Test saving a report"""
    print("💾 Testing report saving...")
    
    try:
        report_data = {
            'content': '''CONSULTATION NOTE

Date: 25/08/2025
Patient: Test Patient
ID Number: 1234567890123

CHIEF COMPLAINT:
Patient presents with chest pain and shortness of breath.

PHYSICAL EXAMINATION:
Blood pressure is elevated at 160 over 90 mmHg.
Heart rate is regular at 72 beats per minute.
Lungs are clear to auscultation bilaterally.

ASSESSMENT:
Hypertension with possible cardiac involvement.

PLAN:
Prescribed medication for hypertension.
Recommend follow-up in two weeks.

Dr. Test Doctor
HPCSA Registration: MP123456''',
            'timestamp': datetime.utcnow().isoformat(),
            'session_id': 'test_session',
            'word_count': 85,
            'char_count': 650
        }
        
        response = requests.post('https://localhost:5001/api/reports/save',
                               json=report_data,
                               verify=False)
        
        if response.status_code == 201:
            result = response.json()
            report_id = result.get('report_id')
            print(f"✅ Report saved successfully: {report_id}")
            return report_id
        else:
            print(f"❌ Report save failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Report save error: {e}")
        return None

def test_report_retrieval(report_id):
    """Test retrieving a saved report"""
    print("📄 Testing report retrieval...")
    
    try:
        response = requests.get(f'https://localhost:5001/api/reports/{report_id}',
                              verify=False)
        
        if response.status_code == 200:
            result = response.json()
            report = result.get('report', {})
            print(f"✅ Report retrieved successfully")
            print(f"   Content length: {len(report.get('content', ''))}")
            print(f"   Word count: {report.get('word_count', 0)}")
            return True
        else:
            print(f"❌ Report retrieval failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Report retrieval error: {e}")
        return False

def test_sa_medical_enhancement():
    """Test South African medical terminology enhancement"""
    print("🇿🇦 Testing SA medical terminology enhancement...")
    
    test_cases = [
        ("Patient has tb and hiv", "tuberculosis", "HIV"),
        ("mva with gsw to chest", "motor vehicle accident", "gunshot wound"),
        ("chest xray shows pcp", "chest X-ray", "Pneumocystis pneumonia"),
        ("bp is 160/90, hr 72", "blood pressure", "heart rate"),
        ("ecg shows normal rhythm", "ECG", "rhythm")
    ]
    
    enhanced_count = 0
    
    for original, expected1, expected2 in test_cases:
        try:
            response = requests.post('https://localhost:5001/api/demo/voice/simulate',
                                   json={'text': original},
                                   verify=False)
            
            if response.status_code == 200:
                result = response.json()
                enhanced = result.get('enhanced_text', '').lower()
                
                if expected1.lower() in enhanced and expected2.lower() in enhanced:
                    print(f"✅ '{original}' → Enhanced correctly")
                    enhanced_count += 1
                else:
                    print(f"❌ '{original}' → Enhancement incomplete")
                    print(f"   Expected: {expected1}, {expected2}")
                    print(f"   Got: {enhanced}")
            else:
                print(f"❌ Enhancement test failed for: {original}")
                
        except Exception as e:
            print(f"❌ Enhancement error for '{original}': {e}")
    
    print(f"🇿🇦 SA Enhancement Results: {enhanced_count}/{len(test_cases)} passed")
    return enhanced_count == len(test_cases)

def test_voice_demo_page():
    """Test that the voice demo page loads correctly"""
    print("🌐 Testing voice demo page...")
    
    try:
        response = requests.get('https://localhost:5001/voice-demo', verify=False)
        
        if response.status_code == 200:
            content = response.text
            
            # Check for key elements
            checks = [
                ('SA Medical Voice Demo' in content, 'Title'),
                ('microphone-btn' in content, 'Microphone button'),
                ('transcription-area' in content, 'Transcription area'),
                ('South African' in content, 'SA branding'),
                ('voice-demo.js' in content, 'JavaScript file'),
                ('template-btn' in content, 'Template buttons')
            ]
            
            passed = 0
            for check, name in checks:
                if check:
                    print(f"✅ {name} found")
                    passed += 1
                else:
                    print(f"❌ {name} missing")
            
            print(f"🌐 Voice demo page: {passed}/{len(checks)} checks passed")
            return passed == len(checks)
        else:
            print(f"❌ Voice demo page failed to load: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Voice demo page error: {e}")
        return False

def main():
    """Run all voice dictation tests"""
    print("🇿🇦 SA Medical Voice Dictation Test Suite")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get('https://localhost:5001/health', verify=False, timeout=5)
        if response.status_code != 200:
            print("❌ Server is not running or not healthy")
            return
    except:
        print("❌ Cannot connect to server at https://localhost:5001")
        print("   Please start the server with: python app.py")
        return
    
    print("✅ Server is running")
    print()
    
    # Run tests
    tests = [
        ("Voice Session Start", test_voice_session_start),
        ("Voice Transcription", test_voice_transcription),
        ("Report Saving", test_report_saving),
        ("SA Medical Enhancement", test_sa_medical_enhancement),
        ("Voice Demo Page", test_voice_demo_page)
    ]
    
    results = []
    report_id = None
    
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        try:
            if test_name == "Report Saving":
                result = test_func()
                if result:
                    report_id = result
                    results.append(True)
                else:
                    results.append(False)
            elif test_name == "Report Retrieval" and report_id:
                result = test_report_retrieval(report_id)
                results.append(result)
            else:
                result = test_func()
                results.append(bool(result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append(False)
        print()
    
    # Test report retrieval if we have a report ID
    if report_id:
        print("Running Report Retrieval...")
        try:
            result = test_report_retrieval(report_id)
            results.append(result)
        except Exception as e:
            print(f"❌ Report Retrieval failed with error: {e}")
            results.append(False)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"🇿🇦 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All voice dictation functionality is working correctly!")
        print("✅ SA medical terminology enhancement is active")
        print("✅ Reports can be saved and retrieved")
        print("✅ Voice demo page is properly configured")
    else:
        print("❌ Some tests failed - voice dictation needs attention")
        
        # Specific recommendations
        if not results[0]:  # Voice session
            print("   - Check voice session API endpoints")
        if not results[1]:  # Transcription
            print("   - Check Whisper model integration")
        if not results[2]:  # Report saving
            print("   - Check reports API and database")
        if not results[3]:  # SA enhancement
            print("   - Check SA medical terminology processing")
        if not results[4]:  # Voice demo page
            print("   - Check voice demo template and routes")

if __name__ == '__main__':
    main()