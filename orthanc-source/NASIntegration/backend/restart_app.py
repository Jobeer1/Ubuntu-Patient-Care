#!/usr/bin/env python3
"""
🇿🇦 Flask App Restart Helper

Helper script to restart the Flask application with proper blueprint registration.
"""

import os
import sys
import subprocess
import time
import requests

def check_app_running():
    """Check if Flask app is running"""
    try:
        response = requests.get("http://localhost:5000/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def restart_flask_app():
    """Restart the Flask application"""
    print("🔄 Restarting Flask application...")
    
    # Check if app is running
    if check_app_running():
        print("⚠️ Flask app is currently running")
        print("💡 Please stop the current Flask app (Ctrl+C) and run this script again")
        return False
    
    # Start the app
    print("🚀 Starting Flask application...")
    try:
        # Change to backend directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        # Start the Flask app
        subprocess.Popen([sys.executable, "app.py"])
        
        # Wait for app to start
        print("⏳ Waiting for app to start...")
        for i in range(10):
            time.sleep(1)
            if check_app_running():
                print("✅ Flask app started successfully!")
                return True
            print(f"   Waiting... ({i+1}/10)")
        
        print("❌ Flask app failed to start within 10 seconds")
        return False
        
    except Exception as e:
        print(f"❌ Error starting Flask app: {e}")
        return False

def test_sa_templates_endpoints():
    """Test SA templates endpoints after restart"""
    print("\n🧪 Testing SA Templates endpoints...")
    
    # Login first
    try:
        login_response = requests.post("http://localhost:5000/api/auth/login", 
                                     json={"username": "admin", "password": "admin123"})
        if login_response.status_code != 200:
            print("❌ Authentication failed")
            return False
        
        cookies = login_response.cookies
        
        # Test a simple endpoint
        response = requests.get("http://localhost:5000/api/reporting/sa-templates/system/languages", 
                              cookies=cookies)
        
        if response.status_code == 200:
            print("✅ SA Templates API is working!")
            return True
        else:
            print(f"❌ SA Templates API not working: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing endpoints: {e}")
        return False

if __name__ == "__main__":
    if restart_flask_app():
        time.sleep(2)  # Give it a moment
        test_sa_templates_endpoints()
    else:
        print("\n💡 Manual restart instructions:")
        print("1. Stop the current Flask app (Ctrl+C)")
        print("2. Run: python app.py")
        print("3. Test with: python test_sa_templates_direct.py")