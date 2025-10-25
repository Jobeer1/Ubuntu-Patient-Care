#!/usr/bin/env python3
"""
Simple server launcher for testing
"""

from app import app
import logging

if __name__ == '__main__':
    # Set logging level for debugging
    logging.basicConfig(level=logging.INFO)
    
    print("🇿🇦 Starting South African Medical Imaging System")
    print("=" * 50)
    print("Server will be available at: http://localhost:5000")
    print("Admin interface: http://localhost:5000/admin/users")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    # Run the development server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )
