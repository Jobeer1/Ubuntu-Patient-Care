#!/usr/bin/env python3
"""
Test script to check if all critical imports work
"""

import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_database_imports():
    """Test database imports"""
    try:
        from models.database import init_db, db
        print("✓ Database imports successful")
        return True
    except Exception as e:
        print(f"✗ Database import failed: {e}")
        return False

def test_cache_service_imports():
    """Test cache service imports"""
    try:
        from services.cache_service import cache_service
        print("✓ Cache service imports successful")
        return True
    except Exception as e:
        print(f"✗ Cache service import failed: {e}")
        return False

def test_audit_service_imports():
    """Test audit service imports"""
    try:
        from services.audit_service import init_audit_service
        audit_service = init_audit_service()
        print("✓ Audit service imports successful")
        return True
    except Exception as e:
        print(f"✗ Audit service import failed: {e}")
        return False

def test_security_service_imports():
    """Test security service imports"""
    try:
        from services.security_service import security_service
        print("✓ Security service imports successful")
        return True
    except Exception as e:
        print(f"✗ Security service import failed: {e}")
        return False

def test_layout_manager_imports():
    """Test layout manager imports"""
    try:
        from services.layout_manager import layout_manager
        print("✓ Layout manager imports successful")
        return True
    except Exception as e:
        print(f"✗ Layout manager import failed: {e}")
        return False

def test_other_service_imports():
    """Test other service imports"""
    try:
        from services.template_manager import template_manager
        from services.offline_manager import offline_manager
        from core.reporting_engine import reporting_engine
        print("✓ Other service imports successful")
        return True
    except Exception as e:
        print(f"✗ Other service imports failed: {e}")
        return False

def main():
    """Run all import tests"""
    print("Testing critical imports...")
    print("-" * 40)
    
    tests = [
        test_database_imports,
        test_cache_service_imports,
        test_audit_service_imports,
        test_security_service_imports,
        test_layout_manager_imports,
        test_other_service_imports
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("-" * 40)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All critical imports working!")
        return True
    else:
        print("✗ Some imports still failing")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)