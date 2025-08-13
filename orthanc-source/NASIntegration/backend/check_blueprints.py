#!/usr/bin/env python3
"""
🇿🇦 Blueprint Registration Checker

Check which blueprints are registered in the Flask app.
"""

import requests
import json

def check_registered_blueprints():
    """Check which blueprints are registered"""
    try:
        # Try to access a simple endpoint to see what's available
        response = requests.get("http://localhost:5000/health")
        if response.status_code == 200:
            print("✅ Flask app is running")
        else:
            print("❌ Flask app not responding")
            return
        
        # Try to access the SA templates endpoints
        endpoints_to_test = [
            "/api/reporting/sa-templates/system/languages",
            "/api/reporting/sa-templates/system/status",
            "/api/reporting/templates",  # Regular reporting endpoint
            "/api/auth/login",  # Auth endpoint
        ]
        
        print("\n🔍 Testing endpoint availability:")
        for endpoint in endpoints_to_test:
            try:
                response = requests.get(f"http://localhost:5000{endpoint}")
                status = "✅ Available" if response.status_code != 404 else "❌ Not Found (404)"
                print(f"   {endpoint}: {status} (HTTP {response.status_code})")
            except Exception as e:
                print(f"   {endpoint}: ❌ Error - {e}")
        
        # Check if we can import the blueprint directly
        print("\n🔍 Testing blueprint import:")
        try:
            import sys
            import os
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
            
            from sa_templates_api import sa_templates_api_bp
            print("✅ SA Templates blueprint can be imported")
            print(f"   Blueprint name: {sa_templates_api_bp.name}")
            print(f"   URL prefix: {sa_templates_api_bp.url_prefix}")
            
            # List routes
            print("   Routes:")
            for rule in sa_templates_api_bp.url_map.iter_rules():
                print(f"     {rule.rule} -> {rule.endpoint}")
                
        except Exception as e:
            print(f"❌ Cannot import SA Templates blueprint: {e}")
    
    except Exception as e:
        print(f"❌ Error checking blueprints: {e}")

if __name__ == "__main__":
    check_registered_blueprints()