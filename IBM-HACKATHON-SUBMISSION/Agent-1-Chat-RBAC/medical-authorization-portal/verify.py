#!/usr/bin/env python
"""
Medical Authorization Portal - App Verification Script
Verifies that all components are working correctly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_app():
    """Verify the Flask app is working correctly"""
    
    print("\n" + "="*60)
    print("[SYSTEM] Medical Authorization Portal - Verification")
    print("="*60 + "\n")
    
    # Test 1: Import Flask app
    print("[TEST 1] Loading Flask app...")
    try:
        from app import app
        print("[PASS] Flask app loaded successfully\n")
    except Exception as e:
        print(f"[FAIL] Could not load Flask app: {e}\n")
        return False
    
    # Test 2: Check database
    print("[TEST 2] Checking database...")
    try:
        import sqlite3
        from app import init_db
        init_db()
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in c.fetchall()]
        
        expected_tables = {'users', 'chat_history', 'authorizations'}
        if expected_tables.issubset(set(tables)):
            print(f"[PASS] Database has all required tables: {', '.join(tables)}\n")
        else:
            print(f"[FAIL] Missing tables. Found: {tables}\n")
            return False
        
        conn.close()
    except Exception as e:
        print(f"[FAIL] Database error: {e}\n")
        return False
    
    # Test 3: Check routes
    print("[TEST 3] Checking routes...")
    try:
        client = app.test_client()
        
        test_routes = {
            '/': 302,
            '/login': 200,
            '/register': 200,
            '/nonexistent': 404
        }
        
        all_passed = True
        for route, expected_code in test_routes.items():
            response = client.get(route)
            if response.status_code == expected_code:
                print(f"[PASS] {route:20} -> {response.status_code}")
            else:
                print(f"[FAIL] {route:20} -> {response.status_code} (expected {expected_code})")
                all_passed = False
        
        print()
        if not all_passed:
            return False
    except Exception as e:
        print(f"[FAIL] Route test error: {e}\n")
        return False
    
    # Test 4: Check session configuration
    print("[TEST 4] Checking session configuration...")
    try:
        from app import app
        config_checks = {
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
        }
        
        all_passed = True
        for key, expected_value in config_checks.items():
            actual_value = app.config.get(key)
            if actual_value == expected_value:
                print(f"[PASS] {key:30} = {actual_value}")
            else:
                print(f"[FAIL] {key:30} = {actual_value} (expected {expected_value})")
                all_passed = False
        
        print()
        if not all_passed:
            return False
    except Exception as e:
        print(f"[FAIL] Configuration check error: {e}\n")
        return False
    
    # Test 5: Check templates
    print("[TEST 5] Checking template files...")
    try:
        templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
        required_templates = [
            'base.html', 'login.html', 'register.html',
            'dashboard.html', 'chat.html', 'patients.html',
            'authorizations.html', '404.html', '500.html'
        ]
        
        missing_templates = []
        for template in required_templates:
            template_path = os.path.join(templates_dir, template)
            if not os.path.exists(template_path):
                missing_templates.append(template)
            else:
                print(f"[PASS] {template}")
        
        if missing_templates:
            print(f"\n[FAIL] Missing templates: {', '.join(missing_templates)}\n")
            return False
        print()
    except Exception as e:
        print(f"[FAIL] Template check error: {e}\n")
        return False
    
    # Test 6: Check static files
    print("[TEST 6] Checking static files...")
    try:
        static_css = os.path.join(os.path.dirname(__file__), 'static', 'css', 'style.css')
        if os.path.exists(static_css):
            print(f"[PASS] static/css/style.css exists\n")
        else:
            print(f"[FAIL] static/css/style.css not found\n")
            return False
    except Exception as e:
        print(f"[FAIL] Static files check error: {e}\n")
        return False
    
    # Summary
    print("="*60)
    print("[SUCCESS] All verifications passed!")
    print("="*60)
    print("\nYour Medical Authorization Portal is ready!")
    print("\nTo start the app, run:")
    print("  python app.py")
    print("\nThen open your browser to:")
    print("  http://localhost:5000")
    print("\n" + "="*60 + "\n")
    
    return True

if __name__ == '__main__':
    success = verify_app()
    sys.exit(0 if success else 1)
