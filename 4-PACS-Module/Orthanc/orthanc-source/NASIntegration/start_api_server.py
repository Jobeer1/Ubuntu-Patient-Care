#!/usr/bin/env python3
"""
Orthanc Management API - Server Startup Script
Simple script to start the FastAPI development server
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    import uvicorn
    from orthanc_management.api.app import app
    
    if __name__ == "__main__":
        print("🚀 Starting Orthanc Management API Server")
        print("=" * 50)
        print("📍 API Documentation: http://localhost:8000/api/docs")
        print("📍 Redoc Documentation: http://localhost:8000/api/redoc")
        print("📍 Health Check: http://localhost:8000/health")
        print("=" * 50)
        
        # Start the server
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000, 
            reload=True,
            reload_dirs=[str(current_dir)],
            log_level="info"
        )

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install fastapi uvicorn sqlalchemy pydantic python-jose[cryptography] python-multipart bcrypt python-dateutil email-validator")
    sys.exit(1)
except Exception as e:
    print(f"❌ Failed to start server: {e}")
    sys.exit(1)
