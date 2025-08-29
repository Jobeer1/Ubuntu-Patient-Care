#!/usr/bin/env python3
"""
Simple FastAPI Server Runner
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from orthanc_management.api.app import app

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Orthanc Management API on http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/api/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000)
