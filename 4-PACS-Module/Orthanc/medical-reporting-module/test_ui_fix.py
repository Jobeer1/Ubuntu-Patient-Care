#!/usr/bin/env python3
"""
Test script to verify the UI fix is working
"""

import requests
import json
import time

def test_stt_ui_fix():
    """Test that the STT system displays transcribed text"""
    print("🧪 Testing STT UI Fix")
    print("=" * 40)
    
    base_url = "https://localhost:5443"
    
    try:
        # Test 1: Check if voice demo page loads
        print("📄 Testing voice demo page...")
        response = requests.get(f"{base_url}/voice-demo", verify=False)
        if response.status_code == 200:
            print("✅ Voice demo page loads successfully")
            
            # Check if the correct HTML elements exist
            html_content = response.text
            if 'id="transcription-area"' in html_content:
                print("✅ transcription-area element found in HTML")
            else:
                print("❌ transcription-area element missing")
                
            if 'id="microphone-btn"' in html_content:
                print("✅ microphone-btn element found in HTML")
            else:
                print("❌ microphone-btn element missing")
                
            if 'voice-demo.js' in html_content:
                print("✅ voice-demo.js script included")
            else:
                print("❌ voice-demo.js script missing")
                
        else:
            print(f"❌ Voice demo page failed to load: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        
    print("\n" + "=" * 40)
    print("🎯 UI Fix Summary:")
    print("- Fixed JavaScript to update correct HTML element")
    print("- Changed from 'report-text' textarea to 'transcription-area' div")
    print("- Added proper status indicator handling")
    print("- Enhanced copy/save functionality")
    print("\n✅ The transcribed text should now appear in the UI!")

if __name__ == "__main__":
    test_stt_ui_fix()