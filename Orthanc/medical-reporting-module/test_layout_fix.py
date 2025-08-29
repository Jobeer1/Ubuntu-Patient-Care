#!/usr/bin/env python3
"""
Quick test to verify layout manager fix
"""

import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    print("Testing layout manager import...")
    from services.layout_manager import layout_manager, LayoutManager
    print(f"✓ Layout manager imported successfully: {layout_manager}")
    
    print("Testing viewport manager import...")
    from services.viewport_manager import ViewportManager
    print("✓ Viewport manager imported successfully")
    
    print("Testing LayoutManager instantiation...")
    viewport_mgr = ViewportManager()
    layout_mgr = LayoutManager(viewport_mgr)
    print("✓ LayoutManager instantiated successfully")
    
    print("Testing app import...")
    import app
    print("✓ App module imported successfully")
    
    print("\n✓ All tests passed! The layout manager fix is working.")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)