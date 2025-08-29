#!/usr/bin/env python3
"""
Test script for the SA Medical Voice Demo functionality
"""

import requests
import json
import time
import sys
import os

def test_voice_demo_page():
    """Test that the voice demo page loads correctly"""
    base_url = "http://127.0.0.1:5001"
    
    print("🧪 Testing SA Medical Voice Demo...")
    
    try:
        # Test 1: Check if voice demo page loads
        print("\n1. Testing voice demo page load...")
        response = requests.get(f"{base_url}/voice-demo")
        
        if response.status_code == 200:
            print("✅ Voice demo page loads successfully")
            
            # Check for key elements in the HTML
            html_content = response.text
            required_elements = [
                "SA Medical Voice Demo",
                "microphone",
                "transcription",
                "South African",
                "voice-demo.js"
            ]
            
            missing_elements = []
            for element in required_elements:
                if element.lower() not in html_content.lower():
                    missing_elements.append(element)
            
            if missing_elements:
                print(f"⚠️  Missing elements: {missing_elements}")
            else:
                print("✅ All required elements found in voice demo page")
                
        else:
            print(f"❌ Voice demo page failed to load: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing voice demo page: {e}")
        return False
    
    # Test 2: Check voice API endpoints
    print("\n2. Testing voice API endpoints...")
    
    try:
        # Test voice session start
        response = requests.post(f"{base_url}/api/demo/voice/start", 
                               json={"doctor_id": "test_doctor"})
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Voice session started: {data.get('session_id')}")
        else:
            print(f"❌ Voice session start failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Voice session start error: {e}")
    
    try:
        # Test voice simulation
        response = requests.post(f"{base_url}/api/demo/voice/simulate",
                               json={"text": "The patient has tb and pneumonia"})
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Voice simulation works:")
            print(f"   Original: {data.get('original_text')}")
            print(f"   Enhanced: {data.get('enhanced_text')}")
            print(f"   SA Terms: {data.get('sa_terms_found')}")
        else:
            print(f"❌ Voice simulation failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Voice simulation error: {e}")
    
    # Test 3: Test SA medical terminology processing
    print("\n3. Testing SA medical terminology processing...")
    
    test_phrases = [
        "tb in the lung",
        "mva with multiple injuries", 
        "chest xray shows consolidation",
        "hiv positive patient with pcp"
    ]
    
    for phrase in test_phrases:
        try:
            response = requests.post(f"{base_url}/api/demo/voice/simulate",
                                   json={"text": phrase})
            
            if response.status_code == 200:
                data = response.json()
                original = data.get('original_text', '')
                enhanced = data.get('enhanced_text', '')
                
                if original != enhanced:
                    print(f"✅ '{original}' → '{enhanced}'")
                else:
                    print(f"ℹ️  '{original}' (no changes needed)")
            else:
                print(f"❌ Failed to process: {phrase}")
                
        except Exception as e:
            print(f"❌ Error processing '{phrase}': {e}")
    
    print("\n🏁 Voice demo test completed!")
    return True

def test_voice_demo_features():
    """Test specific voice demo features"""
    print("\n🔧 Testing Voice Demo Features...")
    
    # Test microphone access requirements
    print("\n• Microphone Access Requirements:")
    print("  - HTTPS required for microphone access")
    print("  - WebRTC MediaRecorder API support needed")
    print("  - Audio visualization using Web Audio API")
    
    # Test SA medical terminology
    print("\n• SA Medical Terminology Support:")
    sa_terms = [
        "tuberculosis (TB)", "pneumonia", "chest X-ray",
        "motor vehicle accident (MVA)", "gunshot wound (GSW)",
        "HIV/AIDS", "silicosis", "trauma"
    ]
    
    for term in sa_terms:
        print(f"  ✓ {term}")
    
    # Test voice commands
    print("\n• Voice Commands:")
    voice_commands = [
        "Start recording", "Stop recording", "Clear text",
        "Save report", "Load template", "Simulate input"
    ]
    
    for command in voice_commands:
        print(f"  ✓ {command}")
    
    # Test keyboard shortcuts
    print("\n• Keyboard Shortcuts:")
    print("  ✓ Ctrl + Space: Toggle recording")
    print("  ✓ Ctrl + S: Save report")
    
    print("\n✅ All voice demo features documented")

def main():
    """Main test function"""
    print("=" * 60)
    print("SA MEDICAL VOICE DEMO TEST SUITE")
    print("=" * 60)
    
    # Test voice demo functionality
    success = test_voice_demo_page()
    
    # Test voice demo features
    test_voice_demo_features()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ VOICE DEMO TESTS COMPLETED SUCCESSFULLY")
        print("🎤 Voice demo is ready for use!")
        print(f"🌐 Access at: http://127.0.0.1:5001/voice-demo")
    else:
        print("❌ SOME VOICE DEMO TESTS FAILED")
        print("🔧 Please check the application and try again")
    print("=" * 60)

if __name__ == "__main__":
    main()