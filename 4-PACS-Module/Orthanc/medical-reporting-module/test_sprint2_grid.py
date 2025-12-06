#!/usr/bin/env python3
"""
Quick test for Sprint 2 grid manager implementation
Tests the enhanced DICOM viewer with drag/drop and layout management
"""

import requests
import time

def test_grid_manager():
    """Test the enhanced find-studies page with grid manager"""
    base_url = "https://127.0.0.1:5443"
    
    print("🧪 Testing Sprint 2 DICOM Grid Manager...")
    
    try:
        # Test 1: Find studies page loads
        print("1️⃣ Testing find-studies page...")
        response = requests.get(f"{base_url}/find-studies", verify=False, timeout=10)
        assert response.status_code == 200
        assert "find-studies.js" in response.text
        assert "Layout:" in response.text or "Drag series" in response.text
        print("   ✅ Find studies page loads with grid manager UI")
        
        # Test 2: DICOM search API
        print("2️⃣ Testing DICOM search API...")
        response = requests.get(f"{base_url}/api/dicom/qido", 
                              params={"PatientName": "demo"}, 
                              verify=False, timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "studies" in data
        assert len(data["studies"]) > 0
        print(f"   ✅ DICOM search returns {len(data['studies'])} demo studies")
        
        # Test 3: Series metadata API
        print("3️⃣ Testing series metadata API...")
        study = data["studies"][0]
        study_uid = study["studyInstanceUID"]
        response = requests.get(f"{base_url}/api/dicom/study/{study_uid}/metadata", 
                              verify=False, timeout=10)
        assert response.status_code == 200
        metadata = response.json()
        assert "series" in metadata
        assert len(metadata["series"]) > 0
        print(f"   ✅ Study metadata returns {len(metadata['series'])} series")
        
        # Test 4: WADO image streaming
        print("4️⃣ Testing WADO image streaming...")
        series = metadata["series"][0]
        series_uid = series["seriesInstanceUID"]
        response = requests.get(f"{base_url}/api/dicom/wado", 
                              params={
                                  "study": study_uid,
                                  "series": series_uid,
                                  "instance": 0
                              }, 
                              verify=False, timeout=10)
        # Should return image data or demo placeholder
        assert response.status_code == 200
        print("   ✅ WADO endpoint streams image data")
        
        print("\n🎉 All Sprint 2 Grid Manager tests passed!")
        print("\n📋 Manual testing checklist:")
        print("   □ Visit /find-studies page")
        print("   □ Search returns demo studies")
        print("   □ Click study opens enhanced viewer modal")
        print("   □ Layout selector shows grid options (1x1, 2x1, 2x2, etc.)")
        print("   □ Series in left panel are draggable (cursor changes to move)")
        print("   □ Grid slots show drop zones and accept dragged series")
        print("   □ Dropped series show images with navigation controls")
        print("   □ Save/Load preset functionality works")
        print("   □ Multiple viewports can show different series simultaneously")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        print("💡 Make sure the server is running: py app.py")
        return False
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_grid_manager()
    exit(0 if success else 1)
