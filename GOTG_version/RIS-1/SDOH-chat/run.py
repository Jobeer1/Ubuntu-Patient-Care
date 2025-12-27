#!/usr/bin/env python
"""
Run SDOH Chat Flask Server (HTTP or HTTPS)
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from flask_app import app, db

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # Check for SSL certificates
    cert_file = 'cert.pem'
    key_file = 'key.pem'
    use_https = os.path.exists(cert_file) and os.path.exists(key_file)
    
    protocol = 'HTTPS' if use_https else 'HTTP'
    port = 5001
    base_url = f"{'https' if use_https else 'http'}://localhost:{port}"
    
    print("")
    print("====================================================")
    print("     SDOH Chat - Flask Server")
    print("     Privacy-First Healthcare Chat")
    print("====================================================")
    print("")
    print(f"[*] Starting {protocol} Server...")
    print(f"[*] URL: {base_url}")
    print(f"[*] Chat: {base_url}/sdoh/index.html")
    print(f"[*] Mode: {'HTTPS (Microphone enabled)' if use_https else 'HTTP (Voice recording disabled)'}")
    print("")
    
    if not use_https:
        print("[!] HTTPS disabled - voice recording requires HTTPS")
        print("[!] To enable HTTPS, run: python generate_cert.py")
        print("")
    else:
        print("[✓] HTTPS enabled - microphone access available")
        print("[✓] TTS Endpoint: Enabled")
        print("[!] Browser may show 'insecure' warning (normal for self-signed certs)")
        print("")
    
    print("Press CTRL+C to stop")
    print("")
    
    if use_https:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=True,
            ssl_context=(cert_file, key_file),
            use_reloader=False
        )
    else:
        app.run(host='0.0.0.0', port=port, debug=True)

