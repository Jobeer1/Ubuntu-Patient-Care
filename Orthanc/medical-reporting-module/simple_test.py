"""
Simple test to check viewport manager import
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Testing basic imports...")
    
    # Test enum imports
    from enum import Enum
    print("✓ Enum import works")
    
    # Test dataclass imports
    from dataclasses import dataclass
    print("✓ Dataclass import works")
    
    # Test typing imports
    from typing import Dict, List, Any, Optional
    print("✓ Typing imports work")
    
    # Test datetime import
    from datetime import datetime
    print("✓ Datetime import works")
    
    # Try to import the viewport manager file directly
    print("\nTesting viewport_manager.py...")
    
    # First check if file exists and is readable
    with open('services/viewport_manager.py', 'r') as f:
        content = f.read()
        print(f"✓ File exists and is readable ({len(content)} characters)")
    
    # Try to compile the file
    compile(content, 'services/viewport_manager.py', 'exec')
    print("✓ File compiles successfully")
    
    # Try to execute the file
    exec(content)
    print("✓ File executes successfully")
    
    # Check if ViewportManager is in the executed namespace
    if 'ViewportManager' in locals():
        print("✓ ViewportManager class found")
    else:
        print("❌ ViewportManager class not found in locals")
        print("Available names:", [name for name in locals() if not name.startswith('_')])
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()