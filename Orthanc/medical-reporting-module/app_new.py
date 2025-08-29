#!/usr/bin/env python3
"""
Medical Reporting Module - Clean, Modular Flask Application
Refactored for maintainability, upgradability, and troubleshooting
"""

import os
import sys
import logging
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    
    logger.info("Starting Medical Reporting Module...")
    
    try:
        # Create Flask application
        from core.app_factory import create_app, socketio
        
        # Determine environment
        config_name = 'production' if os.environ.get('FLASK_ENV') == 'production' else 'development'
        
        # Create app
        app = create_app(config_name)
        
        # Get configuration
        port = int(os.environ.get('PORT', 5001))
        debug = config_name == 'development'
        host = '0.0.0.0'
        
        # Setup SSL context
        ssl_context = None
        try:
            ssl_manager = app.service_manager.get_service('ssl_manager')
            if ssl_manager:
                ssl_context = ssl_manager.get_ssl_context()
                if ssl_context:
                    logger.info(f"Starting with HTTPS on port {port}")
                    logger.info("SSL certificates configured - microphone access available")
                else:
                    logger.info(f"Starting with HTTP on port {port}")
                    logger.warning("No SSL certificates - microphone access may be blocked")
        except Exception as e:
            logger.error(f"SSL setup error: {e}")
        
        # Start application
        logger.info("="*60)
        logger.info("MEDICAL REPORTING MODULE READY")
        logger.info("="*60)
        logger.info(f"Environment: {config_name}")
        logger.info(f"Port: {port}")
        logger.info(f"SSL: {'Enabled' if ssl_context else 'Disabled'}")
        logger.info(f"Access URL: {'https' if ssl_context else 'http'}://localhost:{port}")
        logger.info(f"Microphone Test: {'https' if ssl_context else 'http'}://localhost:{port}/microphone-test")
        logger.info("="*60)
        
        # Run application
        if ssl_context:
            socketio.run(app, host=host, port=port, debug=debug, ssl_context=ssl_context)
        else:
            socketio.run(app, host=host, port=port, debug=debug)
            
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()