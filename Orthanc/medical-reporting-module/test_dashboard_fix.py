#!/usr/bin/env python3
"""
Test script to verify dashboard fix
"""

import requests
import sys

def test_dashboard():
    """Test if dashboard loads without blank screen"""
    try:
        # Test the dashboard endpoint
        response = requests.get('https://localhost:5001/', verify=False, timeout=10)
        
        if response.status_code == 200:
            content = response.text
            
            # Check for key elements that should be present
            checks = [
                'SA Medical Reporting Module' in content,
                'DASHBOARD FIXED' in content,
                'New Report' in content,
                'DICOM Viewer' in content,
                'Orthanc PACS' in content,
                'Voice Dictation' in content
            ]
            
            if all(checks):
                print("✅ DASHBOARD FIX SUCCESSFUL!")
                print("✅ All required elements found")
                print("✅ No more blank screen")
                return True
            else:
                print("⚠️ Dashboard loads but missing some elements")
                print(f"Checks passed: {sum(checks)}/{len(checks)}")
                return False
        else:
            print(f"❌ Dashboard returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        print("Make sure the server is running on https://localhost:5001")
        return False

if __name__ == "__main__":
    print("🔧 Testing SA Medical Dashboard Fix...")
    print("=" * 50)
    
    success = test_dashboard()
    
    if success:
        print("\n🎉 DASHBOARD IS NOW WORKING!")
        print("🇿🇦 SA Medical System ready for use")
        sys.exit(0)
    else:
        print("\n❌ Dashboard still has issues")
        sys.exit(1)