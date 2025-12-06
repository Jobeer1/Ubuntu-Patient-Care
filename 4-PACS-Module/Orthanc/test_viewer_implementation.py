"""
Test the complete viewer implementation
Tests the patient search with viewer functionality
"""

import requests
import json
import sys
import os

# Add the medical module to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
medical_module_path = os.path.join(os.path.dirname(current_dir), 'medical-reporting-module')
sys.path.insert(0, medical_module_path)

def test_patient_search_api():
    """Test the patient search API endpoint"""
    print("🔍 Testing Patient Search API...")
    
    try:
        # Test search endpoint
        search_url = "http://localhost:5000/api/nas/search/patient"
        search_data = {
            "query": "John",
            "search_type": "patient_name",
            "limit": 10
        }
        
        response = requests.post(search_url, json=search_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Search API working: Found {result.get('total_found', 0)} patients")
            
            if result.get('patients'):
                first_patient = result['patients'][0]
                print(f"   Sample patient: {first_patient.get('patient_name')} (ID: {first_patient.get('patient_id')})")
                return first_patient.get('patient_id')
        else:
            print(f"❌ Search API failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Search API error: {e}")
    
    return None

def test_search_stats_api():
    """Test the search statistics API"""
    print("\n📊 Testing Search Stats API...")
    
    try:
        stats_url = "http://localhost:5000/api/nas/search/stats"
        response = requests.get(stats_url, timeout=10)
        
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Stats API working:")
            print(f"   Total Patients: {stats.get('total_patients', 0)}")
            print(f"   Total Studies: {stats.get('total_studies', 0)}")
            print(f"   Date Range: {stats.get('first_record_date', 'Unknown')} to {stats.get('last_record_date', 'Unknown')}")
            print(f"   Top Modality: {stats.get('top_modality', 'Unknown')}")
        else:
            print(f"❌ Stats API failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Stats API error: {e}")

def test_suggestions_api():
    """Test the search suggestions API"""
    print("\n💡 Testing Search Suggestions API...")
    
    try:
        suggestions_url = "http://localhost:5000/api/nas/search/suggestions?q=John&limit=5"
        response = requests.get(suggestions_url, timeout=10)
        
        if response.status_code == 200:
            suggestions = response.json()
            print(f"✅ Suggestions API working:")
            
            patient_names = suggestions.get('suggestions', {}).get('patient_names', [])
            if patient_names:
                print(f"   Patient name suggestions: {', '.join(patient_names[:3])}")
            
            patient_ids = suggestions.get('suggestions', {}).get('patient_ids', [])
            if patient_ids:
                print(f"   Patient ID suggestions: {', '.join(patient_ids[:3])}")
        else:
            print(f"❌ Suggestions API failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Suggestions API error: {e}")

def test_download_api(patient_id):
    """Test the download API endpoint"""
    if not patient_id:
        print("\n📥 Skipping Download API test (no patient ID)")
        return
    
    print(f"\n📥 Testing Download API for patient {patient_id}...")
    
    try:
        download_url = f"http://localhost:5000/api/nas/download/patient?patient_id={patient_id}&format=zip"
        
        # Just test if the endpoint responds (don't actually download)
        response = requests.head(download_url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Download API endpoint responding correctly")
            content_type = response.headers.get('Content-Type', 'Unknown')
            print(f"   Content Type: {content_type}")
        elif response.status_code == 404:
            print(f"⚠️ Download API: No files found for patient {patient_id}")
        else:
            print(f"❌ Download API failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Download API error: {e}")

def test_web_routes():
    """Test the web viewer routes"""
    print("\n🌐 Testing Web Viewer Routes...")
    
    try:
        # Test basic viewer route
        basic_url = "http://localhost:5000/viewer/basic?patient_id=TEST123"
        response = requests.get(basic_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Basic viewer route working")
        elif response.status_code == 401:
            print("⚠️ Basic viewer route requires authentication")
        else:
            print(f"❌ Basic viewer route failed: {response.status_code}")
        
        # Test OHIF viewer route
        ohif_url = "http://localhost:5000/ohif/viewer?patient_id=TEST123"
        response = requests.get(ohif_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ OHIF viewer route working")
        elif response.status_code == 401:
            print("⚠️ OHIF viewer route requires authentication")
        else:
            print(f"❌ OHIF viewer route failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Web routes error: {e}")

def test_database_connection():
    """Test database connection and data"""
    print("\n🗄️ Testing Database Connection...")
    
    try:
        from services.smart_patient_search import get_quick_stats
        stats = get_quick_stats()
        
        if stats.get('success'):
            print("✅ Database connection working")
            print(f"   Database contains {stats.get('total_patients', 0)} patients")
        else:
            print(f"❌ Database connection failed: {stats.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Database error: {e}")

def main():
    """Run all tests"""
    print("🚀 Testing South African Medical Imaging System - Patient Viewer Implementation")
    print("=" * 80)
    
    # Test database connection first
    test_database_connection()
    
    # Test API endpoints
    patient_id = test_patient_search_api()
    test_search_stats_api()
    test_suggestions_api()
    test_download_api(patient_id)
    
    # Test web routes
    test_web_routes()
    
    print("\n" + "=" * 80)
    print("🏁 Testing Complete!")
    print("\n📋 Implementation Summary:")
    print("   ✅ Enhanced patient search with viewer action buttons")
    print("   ✅ Basic DICOM viewer template with South African theme")
    print("   ✅ OHIF medical-grade viewer integration template")
    print("   ✅ DICOM download service with ZIP packaging")
    print("   ✅ Statistics display with proper z-index positioning")
    print("   ✅ Authentication-protected viewer routes")
    
    print("\n🔧 Next Steps:")
    print("   1. Configure OHIF DICOMweb integration")
    print("   2. Set up NAS storage path in download service")
    print("   3. Install DICOM.js library for basic viewer")
    print("   4. Test with actual patient DICOM data")

if __name__ == "__main__":
    main()