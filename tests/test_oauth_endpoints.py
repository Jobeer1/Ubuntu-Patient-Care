#!/usr/bin/env python3
"""
Test script to verify OAuth endpoints are properly configured
Run this to check if OAuth routes are accessible
"""

import requests
import sys

BASE_URL = "http://localhost:5000"

def test_endpoint(url, description):
    """Test if an endpoint is accessible"""
    try:
        response = requests.get(url, allow_redirects=False)
        if response.status_code in [302, 301]:  # Redirect is expected for OAuth
            print(f"✅ {description}: OK (redirects to OAuth provider)")
            return True
        elif response.status_code == 200:
            print(f"✅ {description}: OK")
            return True
        else:
            print(f"⚠️  {description}: Unexpected status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ {description}: Cannot connect to server")
        return False
    except Exception as e:
        print(f"❌ {description}: Error - {e}")
        return False

def main():
    print("🔍 Testing OAuth Endpoints")
    print("=" * 50)
    print(f"Base URL: {BASE_URL}")
    print()
    
    # Check if server is running
    print("1. Checking if backend server is running...")
    if not test_endpoint(f"{BASE_URL}/api/health", "Health check"):
        print("\n❌ Backend server is not running!")
        print("Start it with: python app.py")
        sys.exit(1)
    
    print()
    print("2. Testing OAuth endpoints...")
    
    # Test Microsoft OAuth
    microsoft_ok = test_endpoint(
        f"{BASE_URL}/api/auth/microsoft",
        "Microsoft OAuth endpoint"
    )
    
    # Test Google OAuth
    google_ok = test_endpoint(
        f"{BASE_URL}/api/auth/google",
        "Google OAuth endpoint"
    )
    
    print()
    print("3. Testing login page...")
    login_ok = test_endpoint(
        f"{BASE_URL}/login",
        "Login page"
    )
    
    print()
    print("=" * 50)
    print("📊 Test Results:")
    print()
    
    if microsoft_ok and google_ok and login_ok:
        print("✅ All OAuth endpoints are accessible!")
        print()
        print("Next steps:")
        print("1. Configure OAuth credentials in .env file")
        print("2. Restart the backend server")
        print("3. Visit http://localhost:5000/login")
        print("4. Click 'Sign in with Microsoft' or 'Sign in with Google'")
        print()
        print("See OAUTH_SETUP_GUIDE.md for configuration instructions")
    else:
        print("⚠️  Some endpoints are not accessible")
        print("Make sure the backend server is running")
    
    print()

if __name__ == "__main__":
    main()
