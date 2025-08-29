#!/usr/bin/env python3
"""
Quick syntax test for routes.py
"""

import sys
import os

def test_syntax():
    """Test Python syntax of routes.py"""
    try:
        # Add the current directory to Python path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Try to compile the routes file
        with open('core/routes.py', 'r') as f:
            code = f.read()
        
        compile(code, 'core/routes.py', 'exec')
        print("✅ routes.py syntax is valid")
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error in routes.py: {e}")
        print(f"   Line {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print(f"❌ Error testing routes.py: {e}")
        return False

if __name__ == "__main__":
    if test_syntax():
        print("🎉 Syntax test passed - app should start now!")
        sys.exit(0)
    else:
        print("⚠️  Syntax errors found - need to fix before starting app")
        sys.exit(1)