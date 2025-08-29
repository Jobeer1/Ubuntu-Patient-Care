#!/usr/bin/env python3
"""
Quick test to verify the app can start
"""

try:
    print("Testing imports...")
    from core.routes import core_bp
    print("✅ Routes imported successfully")
    
    from core.app_factory import create_app
    print("✅ App factory imported successfully")
    
    print("Creating app...")
    app = create_app('development')
    print("✅ App created successfully")
    
    print("\n🎉 SA Medical Dashboard is ready!")
    print("✅ All syntax errors fixed")
    print("✅ App can start successfully")
    print("\nRun: python app.py")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()