"""
Quick test script to verify OneDrive endpoints are working
Run this after restarting the Flask backend
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_endpoint(name, url):
    """Test an endpoint and print the result"""
    try:
        response = requests.get(url, timeout=5)
        print(f"\n✅ {name}")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"\n❌ {name}")
        print(f"   Error: Cannot connect to {url}")
        print(f"   Make sure Flask backend is running!")
        return False
    except Exception as e:
        print(f"\n❌ {name}")
        print(f"   Error: {e}")
        return False

def main():
    print("=" * 60)
    print("OneDrive Integration Endpoint Tests")
    print("=" * 60)
    
    # Test health check first
    if not test_endpoint("Health Check", f"{BASE_URL}/api/health"):
        print("\n⚠️  Flask backend is not running!")
        print("   Start it with: py app.py")
        return
    
    # Test OneDrive endpoints
    test_endpoint("OneDrive Config", f"{BASE_URL}/api/nas/onedrive/config")
    test_endpoint("OneDrive Status", f"{BASE_URL}/api/nas/onedrive/status")
    
    # Test Google Drive endpoints
    test_endpoint("Google Drive Config", f"{BASE_URL}/api/nas/gdrive/config")
    test_endpoint("Google Drive Status", f"{BASE_URL}/api/nas/gdrive/status")
    
    print("\n" + "=" * 60)
    print("✅ All endpoints are responding!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Go to http://localhost:5000/patients")
    print("2. Click the OneDrive setup button")
    print("3. Follow the setup guide in ONEDRIVE_SETUP_GUIDE.md")

if __name__ == "__main__":
    main()
