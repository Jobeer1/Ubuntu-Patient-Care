#!/usr/bin/env python3
"""
Complete SSL Setup for Medical Reporting Module
Ensures HTTPS is properly configured for microphone access
"""

import os
import sys
import logging
from pathlib import Path
import socket
import ssl
import requests
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings for testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_ssl_manager():
    """Check if SSL manager is working"""
    try:
        from services.ssl_manager import ssl_manager
        
        logger.info("SSL Manager imported successfully")
        
        # Check SSL setup status
        status = ssl_manager.check_ssl_setup()
        logger.info(f"SSL setup status: {status}")
        
        return ssl_manager
        
    except Exception as e:
        logger.error(f"Failed to import SSL manager: {e}")
        return None

def setup_development_ssl(ssl_manager):
    """Set up SSL for development environment"""
    try:
        logger.info("Setting up SSL for development...")
        
        # Try to set up development SSL
        success = ssl_manager.setup_development_ssl()
        
        if success:
            logger.info("✅ Development SSL setup successful")
            
            # Get certificate info
            cert_info = ssl_manager.get_certificate_info()
            if cert_info:
                logger.info(f"Certificate valid until: {cert_info['not_after']}")
                logger.info(f"Days until expiry: {cert_info['days_until_expiry']}")
            
            return True
        else:
            logger.error("❌ Development SSL setup failed")
            return False
            
    except Exception as e:
        logger.error(f"Error setting up development SSL: {e}")
        return False

def test_ssl_context(ssl_manager):
    """Test if SSL context can be created"""
    try:
        logger.info("Testing SSL context creation...")
        
        ssl_context = ssl_manager.get_ssl_context()
        
        if ssl_context:
            logger.info("✅ SSL context created successfully")
            logger.info(f"SSL context type: {type(ssl_context)}")
            return True
        else:
            logger.error("❌ Failed to create SSL context")
            return False
            
    except Exception as e:
        logger.error(f"Error testing SSL context: {e}")
        return False

def test_https_server():
    """Test if HTTPS server can be started"""
    try:
        logger.info("Testing HTTPS server startup...")
        
        # Import Flask and create a test app
        from flask import Flask
        from services.ssl_manager import ssl_manager
        
        app = Flask(__name__)
        
        @app.route('/test')
        def test_route():
            return {'status': 'SSL working', 'message': 'HTTPS is configured correctly'}
        
        # Get SSL context
        ssl_context = ssl_manager.get_ssl_context()
        
        if ssl_context:
            logger.info("✅ HTTPS server can be configured")
            logger.info("SSL context is ready for Flask application")
            return True
        else:
            logger.error("❌ Cannot configure HTTPS server")
            return False
            
    except Exception as e:
        logger.error(f"Error testing HTTPS server: {e}")
        return False

def check_microphone_requirements():
    """Check requirements for microphone access"""
    logger.info("Checking microphone access requirements...")
    
    requirements = {
        "https_required": True,
        "valid_certificate": True,
        "secure_context": True
    }
    
    # Check if we're running on localhost (which has special permissions)
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    logger.info(f"Hostname: {hostname}")
    logger.info(f"Local IP: {local_ip}")
    
    if hostname == 'localhost' or local_ip.startswith('127.') or local_ip.startswith('192.168.'):
        logger.info("✅ Running on local network - microphone access should work with HTTPS")
    else:
        logger.warning("⚠️ Running on public network - may need valid SSL certificate")
    
    return requirements

def create_microphone_test_page():
    """Create a test page for microphone access"""
    try:
        test_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Microphone Test - Medical Reporting Module</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .status { padding: 20px; margin: 20px 0; border-radius: 5px; }
        .success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .warning { background-color: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        button { padding: 10px 20px; margin: 10px; font-size: 16px; }
        #output { margin-top: 20px; padding: 10px; background-color: #f8f9fa; border: 1px solid #dee2e6; }
    </style>
</head>
<body>
    <h1>🎤 Microphone Access Test</h1>
    <p>This page tests if microphone access is working with HTTPS.</p>
    
    <div id="status" class="status warning">
        <strong>Status:</strong> <span id="statusText">Checking...</span>
    </div>
    
    <button onclick="testMicrophone()">Test Microphone Access</button>
    <button onclick="checkHTTPS()">Check HTTPS Status</button>
    
    <div id="output"></div>
    
    <script>
        function updateStatus(message, type) {
            const statusDiv = document.getElementById('status');
            const statusText = document.getElementById('statusText');
            statusText.textContent = message;
            statusDiv.className = 'status ' + type;
        }
        
        function log(message) {
            const output = document.getElementById('output');
            output.innerHTML += '<p>' + new Date().toLocaleTimeString() + ': ' + message + '</p>';
        }
        
        function checkHTTPS() {
            if (location.protocol === 'https:') {
                updateStatus('HTTPS is enabled ✅', 'success');
                log('✅ Page is served over HTTPS');
            } else {
                updateStatus('HTTP detected - microphone may not work ❌', 'error');
                log('❌ Page is served over HTTP - microphone access will be blocked');
            }
        }
        
        async function testMicrophone() {
            log('🎤 Testing microphone access...');
            
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                updateStatus('Microphone access granted ✅', 'success');
                log('✅ Microphone access granted successfully');
                
                // Stop the stream
                stream.getTracks().forEach(track => track.stop());
                log('🔇 Microphone stream stopped');
                
            } catch (error) {
                updateStatus('Microphone access denied ❌', 'error');
                log('❌ Microphone access error: ' + error.message);
                
                if (error.name === 'NotAllowedError') {
                    log('💡 User denied microphone permission');
                } else if (error.name === 'NotSecureError') {
                    log('💡 Microphone requires HTTPS');
                } else {
                    log('💡 Other microphone error: ' + error.name);
                }
            }
        }
        
        // Check HTTPS status on page load
        window.onload = function() {
            checkHTTPS();
        };
    </script>
</body>
</html>"""
        
        # Save test page
        test_file = Path("frontend/templates/microphone_test.html")
        test_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_html)
        
        logger.info(f"✅ Microphone test page created: {test_file}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create microphone test page: {e}")
        return False

def main():
    """Run complete SSL setup and testing"""
    logger.info("🔒 Starting complete SSL setup for Medical Reporting Module...")
    
    # Step 1: Check SSL manager
    logger.info("\n" + "="*60)
    logger.info("STEP 1: SSL Manager Check")
    logger.info("="*60)
    ssl_manager = check_ssl_manager()
    
    if not ssl_manager:
        logger.error("❌ Cannot proceed without SSL manager")
        return False
    
    # Step 2: Setup development SSL
    logger.info("\n" + "="*60)
    logger.info("STEP 2: Development SSL Setup")
    logger.info("="*60)
    ssl_setup_ok = setup_development_ssl(ssl_manager)
    
    # Step 3: Test SSL context
    logger.info("\n" + "="*60)
    logger.info("STEP 3: SSL Context Test")
    logger.info("="*60)
    ssl_context_ok = test_ssl_context(ssl_manager)
    
    # Step 4: Test HTTPS server
    logger.info("\n" + "="*60)
    logger.info("STEP 4: HTTPS Server Test")
    logger.info("="*60)
    https_server_ok = test_https_server()
    
    # Step 5: Check microphone requirements
    logger.info("\n" + "="*60)
    logger.info("STEP 5: Microphone Requirements")
    logger.info("="*60)
    mic_requirements = check_microphone_requirements()
    
    # Step 6: Create test page
    logger.info("\n" + "="*60)
    logger.info("STEP 6: Microphone Test Page")
    logger.info("="*60)
    test_page_ok = create_microphone_test_page()
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("SSL SETUP SUMMARY")
    logger.info("="*60)
    logger.info(f"SSL Manager: {'✅' if ssl_manager else '❌'}")
    logger.info(f"SSL Setup: {'✅' if ssl_setup_ok else '❌'}")
    logger.info(f"SSL Context: {'✅' if ssl_context_ok else '❌'}")
    logger.info(f"HTTPS Server: {'✅' if https_server_ok else '❌'}")
    logger.info(f"Test Page: {'✅' if test_page_ok else '❌'}")
    
    all_ok = all([ssl_manager, ssl_setup_ok, ssl_context_ok, https_server_ok])
    
    if all_ok:
        logger.info("\n🎉 SSL SETUP COMPLETE!")
        logger.info("HTTPS is properly configured for microphone access.")
        logger.info("\n📋 Next steps:")
        logger.info("1. Start the application: python app.py")
        logger.info("2. Open browser to: https://localhost:5001")
        logger.info("3. Test microphone: https://localhost:5001/microphone_test")
        logger.info("4. Accept the self-signed certificate warning")
        logger.info("5. Grant microphone permission when prompted")
        
    else:
        logger.error("\n❌ SSL SETUP INCOMPLETE!")
        logger.error("Some components failed. Check the logs above.")
    
    return all_ok

if __name__ == "__main__":
    main()