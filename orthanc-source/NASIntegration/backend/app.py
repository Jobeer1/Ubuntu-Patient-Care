#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - Main Application

Clean, modular Flask application entry point.
All functionality is organized into separate modules for maintainability.
"""

from flask import Flask
import os
import sys
import logging

# Setup clean logging first
logging.basicConfig(
    level=logging.WARNING,  # Reduce log noise
    format='%(levelname)s: %(message)s'
)

from core.warning_manager import warning_manager
from core.app_factory import create_app
from core.system_initializer import SystemInitializer

def main():
    """Main application entry point"""
    # Setup warning management
    warning_manager.setup_warning_filters()
    warning_manager.check_dependencies()
    
    # Suppress warnings during startup
    sys.stderr = warning_manager.suppress_startup_warnings()
    
    try:
        # Create Flask application
        app = create_app()
        
        # Initialize system components
        initializer = SystemInitializer(app)
        initializer.initialize_all()
        
        # Restore stderr
        sys.stderr = sys.__stderr__
        
        # Print clean startup summary
        warning_manager.print_startup_summary()
        
        return app
        
    except Exception as e:
        # Restore stderr for error reporting
        sys.stderr = sys.__stderr__
        print(f"❌ Failed to start application: {e}")
        raise

# Create the Flask app instance
app = main()

if __name__ == '__main__':
    # Development server
    app.run(
        debug=False,  # Disable debug mode for cleaner output
        host='0.0.0.0', 
        port=5000,
        threaded=True
    )