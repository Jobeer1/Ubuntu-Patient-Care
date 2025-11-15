#!/usr/bin/env python3
"""
Verification script to test NAS Configuration Frontend Fix
Tests both backend API and frontend integration
"""

import requests
import json
import sys
import time

BASE_URL = 'http://localhost:5000'

def print_header(text):
    print("\n" + "="*60)
    print("  " + text)
    print("="*60 + "\n")

def test_api_endpoint():
    """Test the NAS configuration API endpoint"""
    print_header("Testing Backend API Endpoint")
    
    try:
        url = f'{BASE_URL}/api/nas/indexing/config/active'
        print("[*] Testing: " + url)
        
        response = requests.get(url, timeout=5)
        
        print("[OK] Status Code: " + str(response.status_code))
        
        if response.status_code == 200:
            data = response.json()
            print("[OK] Response is valid JSON")
            
            # Check required fields
            required_fields = ['success', 'path', 'modalities', 'description']
            for field in required_fields:
                if field in data:
                    print("[OK] Field '" + field + "' present")
                    if field == 'modalities' and isinstance(data[field], list):
                        print("     Value: " + ', '.join(data[field]))
                    elif field == 'path':
                        print("     Value: " + data[field])
                else:
                    print("[FAIL] Missing field: " + field)
            
            return data
        else:
            print("[FAIL] Unexpected status code: " + str(response.status_code))
            return None
            
    except requests.exceptions.ConnectionError:
        print("[FAIL] Connection failed - is Flask server running on port 5000?")
        return None
    except Exception as e:
        print("[FAIL] Error: " + str(e))
        return None

def test_html_page():
    """Test that HTML page loads correctly"""
    print_header("Testing HTML Page Load")
    
    try:
        url = f'{BASE_URL}/nas-integration'
        print("[*] Testing: " + url)
        
        response = requests.get(url, timeout=5)
        
        print("[OK] Status Code: " + str(response.status_code))
        
        if response.status_code == 200:
            html = response.text
            
            # Check for required elements
            checks = {
                'dashboardNasDevices': 'id="dashboardNasDevices"',
                'dashboardNasDetails': 'id="dashboardNasDetails"',
                'nas-config-modal.js': 'nas-config-modal.js',
                'test-nas-loading.js': 'test-nas-loading.js',
                'orthanc-integration.js': 'orthanc-integration.js',
            }
            
            for check_name, check_string in checks.items():
                if check_string in html:
                    print("[OK] Found: " + check_name)
                else:
                    print("[FAIL] Missing: " + check_name)
            
            return True
        else:
            print("[FAIL] Unexpected status code: " + str(response.status_code))
            return False
            
    except requests.exceptions.ConnectionError:
        print("[FAIL] Connection failed")
        return False
    except Exception as e:
        print("[FAIL] Error: " + str(e))
        return False

def test_static_files():
    """Test that all required static files load"""
    print_header("Testing Static Files")
    
    files_to_test = [
        'js/orthanc-integration.js',
        'js/nas-config-modal.js',
        'js/test-nas-loading.js',
        'css/nas_integration.css',
    ]
    
    all_ok = True
    for file_path in files_to_test:
        try:
            url = f'{BASE_URL}/static/{file_path}'
            response = requests.head(url, timeout=5)
            
            if response.status_code in [200, 304]:  # 304 is "Not Modified" (cached)
                print("[OK] " + file_path + " - Status " + str(response.status_code))
            else:
                print("[FAIL] " + file_path + " - Status " + str(response.status_code))
                all_ok = False
                
        except Exception as e:
            print("[FAIL] " + file_path + " - Error: " + str(e))
            all_ok = False
    
    return all_ok

def test_modal_functions():
    """Test that modal functions are properly defined"""
    print_header("Testing Modal Function Definitions")
    
    try:
        url = f'{BASE_URL}/static/js/nas-config-modal.js'
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            js_code = response.text
            
            functions = [
                'function showNASConfigurationModal()',
                'function loadCurrentNASConfig()',
                'function loadNASConfigurations()',
                'window.showNASConfigurationModal',
                'window.loadCurrentNASConfig',
            ]
            
            for func in functions:
                if func in js_code:
                    print("[OK] Found: " + func)
                else:
                    print("[FAIL] Missing: " + func)
            
            return True
        else:
            print("[FAIL] Could not load nas-config-modal.js")
            return False
            
    except Exception as e:
        print("[FAIL] Error: " + str(e))
        return False

def test_click_handler():
    """Test that click handler is defined in orthanc-integration.js"""
    print_header("Testing Click Handler Definition")
    
    try:
        url = f'{BASE_URL}/static/js/orthanc-integration.js'
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            js_code = response.text
            
            checks = [
                'nasCard.addEventListener(\'click\'',
                'window.showNASConfigurationModal',
                'dashboardNasDevices',
                'updateNasDashboard',
            ]
            
            for check in checks:
                if check in js_code:
                    print("[OK] Found: " + check)
                else:
                    print("[FAIL] Missing: " + check)
            
            return True
        else:
            print("[FAIL] Could not load orthanc-integration.js")
            return False
            
    except Exception as e:
        print("[FAIL] Error: " + str(e))
        return False

def main():
    print("\n" + "="*60)
    print("  NAS CONFIGURATION FRONTEND FIX VERIFICATION")
    print("="*60)
    
    results = {
        'API Endpoint': test_api_endpoint(),
        'HTML Page': test_html_page(),
        'Static Files': test_static_files(),
        'Modal Functions': test_modal_functions(),
        'Click Handler': test_click_handler(),
    }
    
    print_header("VERIFICATION SUMMARY")
    
    all_passed = True
    for test_name, result in results.items():
        if result is None or result is False:
            status = "[FAIL]"
            all_passed = False
        else:
            status = "[PASS]"
        print(status + " - " + test_name)
    
    print("\n" + "="*60)
    if all_passed:
        print("  ALL TESTS PASSED!")
        print("  The NAS Configuration Frontend Fix is complete.")
        print("\n  NEXT STEPS:")
        print("  1. Open http://localhost:5000/nas-integration in browser")
        print("  2. Look at the NAS Devices status card (2nd card)")
        print("  3. Should show: 'Configured NAS' instead of '0 Found'")
        print("  4. Click the card to open configuration modal")
        print("  5. Check browser console (F12) for debug output")
    else:
        print("  SOME TESTS FAILED")
        print("  Please review the failures above")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
