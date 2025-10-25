#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System Startup
World-class medical imaging for South African healthcare

Clean, modular startup script for the refactored application.
"""

import os
import sys
import platform

def main():
    print("🇿🇦 SOUTH AFRICAN MEDICAL IMAGING SYSTEM")
    print("🏥 Initializing World-Class Medical Platform...")
    
    # Change to backend directory
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    if os.path.exists(backend_dir):
        os.chdir(backend_dir)
    
    # Add current directory to Python path
    sys.path.insert(0, '.')
    
    try:
        # Import the Flask app from the modular structure
        from app import app
        
        print("\n🌐 System URLs:")
        print("   Main Interface: http://localhost:5000")
        print("   System Status: http://localhost:5000/system-status")
        print("   User Management: http://localhost:5000/user-management")
        print("   NAS Configuration: http://localhost:5000/nas-config")
        print("   Device Management: http://localhost:5000/device-management")
        print("   Reporting Dashboard: http://localhost:5000/reporting-dashboard")
        
        print("\n🔐 Demo Credentials:")
        print("   Admin: admin / admin123")
        print("   Doctor: doctor1 / doctor123")
        
        print("\n💡 Tips:")
        print("   • Press Ctrl+D on login page for demo credentials")
        print("   • Visit /system-status for comprehensive health check")
        print("   • Install optional packages: pip install -r requirements-optional.txt")
        
        print("\n⏹️  Press Ctrl+C to stop the system")
        print("🚀 Starting server...")
        
        # Start the Flask application
        app.run(
            debug=False,  # Clean production-like mode
            host='0.0.0.0', 
            port=5000,
            threaded=True
        )
        
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("Install core dependencies: pip install -r requirements-core.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 System stopped by user")
    except Exception as e:
        print(f"\n❌ Startup error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()