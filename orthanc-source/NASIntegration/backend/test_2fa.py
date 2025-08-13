#!/usr/bin/env python3
"""
Test script for Orthanc 2FA Integration
Demonstrates the 2FA functionality and API endpoints
"""

import requests
import json
import time
import pyotp
from typing import Dict, Any

class OrthancTwoFactorTester:
    """Test class for 2FA functionality"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.totp_secret = None
        
    def test_login(self, username: str = "admin", password: str = "admin_password") -> Dict[str, Any]:
        """Test login functionality"""
        print(f"\n=== Testing Login for {username} ===")
        
        response = self.session.post(f"{self.base_url}/api/login", json={
            "username": username,
            "password": password
        })
        
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        return data
    
    def test_2fa_config(self, enable_2fa: bool = True) -> Dict[str, Any]:
        """Test 2FA configuration (admin only)"""
        print(f"\n=== Testing 2FA Configuration (Enable: {enable_2fa}) ===")
        
        config = {
            "enabled": enable_2fa,
            "required_for_admin": True,
            "required_for_users": False,
            "allowed_methods": ["totp", "backup_codes"],
            "totp_issuer": "Orthanc NAS Test"
        }
        
        response = self.session.post(f"{self.base_url}/api/2fa/config", json=config)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        return data
    
    def test_get_2fa_config(self) -> Dict[str, Any]:
        """Test getting 2FA configuration"""
        print(f"\n=== Getting 2FA Configuration ===")
        
        response = self.session.get(f"{self.base_url}/api/2fa/config")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        return data
    
    def test_totp_setup(self) -> Dict[str, Any]:
        """Test TOTP setup"""
        print(f"\n=== Testing TOTP Setup ===")
        
        response = self.session.post(f"{self.base_url}/api/2fa/setup/totp")
        print(f"Status: {response.status_code}")
        data = response.json()
        
        if response.status_code == 200 and 'setup_data' in data:
            self.totp_secret = data['setup_data']['manual_entry_key']
            print(f"TOTP Secret: {self.totp_secret}")
            print("QR Code available in response (base64 encoded)")
        else:
            print(f"Response: {json.dumps(data, indent=2)}")
        
        return data
    
    def test_totp_verification(self) -> Dict[str, Any]:
        """Test TOTP verification during setup"""
        print(f"\n=== Testing TOTP Verification ===")
        
        if not self.totp_secret:
            print("Error: No TOTP secret available. Run setup first.")
            return {}
        
        # Generate TOTP code
        totp = pyotp.TOTP(self.totp_secret)
        code = totp.now()
        print(f"Generated TOTP code: {code}")
        
        response = self.session.post(f"{self.base_url}/api/2fa/setup/totp/verify", json={
            "code": code
        })
        
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        return data
    
    def test_backup_codes_generation(self) -> Dict[str, Any]:
        """Test backup codes generation"""
        print(f"\n=== Testing Backup Codes Generation ===")
        
        response = self.session.post(f"{self.base_url}/api/2fa/backup-codes/generate")
        print(f"Status: {response.status_code}")
        data = response.json()
        
        if response.status_code == 200 and 'backup_codes' in data:
            print(f"Generated {len(data['backup_codes'])} backup codes:")
            for i, code in enumerate(data['backup_codes'][:3], 1):  # Show first 3
                print(f"  {i}. {code}")
            print("  ... (showing first 3 codes only)")
        else:
            print(f"Response: {json.dumps(data, indent=2)}")
        
        return data
    
    def test_2fa_status(self) -> Dict[str, Any]:
        """Test getting user 2FA status"""
        print(f"\n=== Testing 2FA Status ===")
        
        response = self.session.get(f"{self.base_url}/api/2fa/status")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        return data
    
    def test_2fa_authentication(self) -> Dict[str, Any]:
        """Test 2FA authentication"""
        print(f"\n=== Testing 2FA Authentication ===")
        
        if not self.totp_secret:
            print("Error: No TOTP secret available. Complete setup first.")
            return {}
        
        # Generate TOTP code
        totp = pyotp.TOTP(self.totp_secret)
        code = totp.now()
        print(f"Generated TOTP code: {code}")
        
        response = self.session.post(f"{self.base_url}/api/2fa/verify", json={
            "code": code,
            "method": "totp"
        })
        
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        return data
    
    def test_protected_endpoint(self) -> Dict[str, Any]:
        """Test accessing a protected endpoint"""
        print(f"\n=== Testing Protected Endpoint ===")
        
        response = self.session.get(f"{self.base_url}/api/admin/users")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        return data
    
    def test_2fa_stats(self) -> Dict[str, Any]:
        """Test 2FA statistics endpoint"""
        print(f"\n=== Testing 2FA Statistics ===")
        
        response = self.session.get(f"{self.base_url}/api/2fa/admin/stats")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        return data
    
    def run_full_test_suite(self):
        """Run the complete test suite"""
        print("=" * 60)
        print("ORTHANC 2FA INTEGRATION TEST SUITE")
        print("=" * 60)
        
        try:
            # 1. Login as admin
            login_result = self.test_login("admin", "admin_password")
            if not login_result.get('success'):
                print("❌ Login failed. Cannot continue tests.")
                return
            
            # 2. Enable 2FA
            config_result = self.test_2fa_config(True)
            if not config_result.get('success'):
                print("❌ Failed to enable 2FA. Some tests may fail.")
            
            # 3. Get current config
            self.test_get_2fa_config()
            
            # 4. Setup TOTP
            setup_result = self.test_totp_setup()
            if not setup_result.get('success'):
                print("❌ TOTP setup failed. Cannot continue 2FA tests.")
                return
            
            # 5. Verify TOTP setup
            verify_result = self.test_totp_verification()
            if not verify_result.get('success'):
                print("❌ TOTP verification failed. Cannot continue.")
                return
            
            # 6. Generate backup codes
            self.test_backup_codes_generation()
            
            # 7. Check 2FA status
            self.test_2fa_status()
            
            # 8. Test 2FA authentication
            auth_result = self.test_2fa_authentication()
            if not auth_result.get('success'):
                print("❌ 2FA authentication failed.")
                return
            
            # 9. Test protected endpoint (should work now)
            self.test_protected_endpoint()
            
            # 10. Test 2FA statistics
            self.test_2fa_stats()
            
            print("\n" + "=" * 60)
            print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ Test suite failed with error: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Main test function"""
    print("Starting Orthanc 2FA Integration Tests...")
    print("Make sure the Flask application is running on http://localhost:5000")
    
    # Wait a moment for user to read
    time.sleep(2)
    
    tester = OrthancTwoFactorTester()
    tester.run_full_test_suite()

if __name__ == "__main__":
    main()