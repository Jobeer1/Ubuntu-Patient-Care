#!/usr/bin/env python
"""
Run SDOH Chat Flask Server (HTTP or HTTPS) and SDOH OpenClaw Proxy
"""

import os
import sys
import threading

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from flask_app import app, db

# Import the SDOH proxy app
from sdoh_oc_proxy import APP as proxy_app


def run_proxy():
    """Run the SDOH OpenClaw proxy on HTTP port 5001"""
    print("[*] Starting SDOH OpenClaw Proxy on port 5001...")
    proxy_app.run(
        host='127.0.0.1',
        port=5001,
        debug=False,
        use_reloader=False,
        threaded=True
    )


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # Check for SSL certificates
    cert_file = 'cert.pem'
    key_file = 'key.pem'
    use_https = True  # Enable HTTPS for voice recording (browser requirement)
    
    # Start the SDOH proxy in a background thread
    proxy_thread = threading.Thread(target=run_proxy, daemon=True)
    proxy_thread.start()
    
    protocol = 'HTTPS' if use_https else 'HTTP'
    port = 5002
    base_url = f"{'https' if use_https else 'http'}://localhost:{port}"
    
    print("")
    print("====================================================")
    print("     SDOH Chat - Flask Server")
    print("     Privacy-First Healthcare Chat")
    print("====================================================")
    print("")
    print(f"[*] Starting {protocol} Server on port {port}...")
    print(f"[*] URL: {base_url}")
    print(f"[*] Chat: {base_url}/sdoh/index.html")
    print(f"[*] SDOH Proxy: http://localhost:5001/api/sdoh/oc")
    print(f"[*] Mode: {'HTTPS (Microphone enabled)' if use_https else 'HTTP (Voice recording disabled)'}")
    print("")
    
    if not use_https:
        print("[!] HTTPS disabled - voice recording requires HTTPS")
        print("[!] To enable HTTPS, run: python generate_cert.py")
        print("")
    else:
        print("[*] HTTPS enabled - microphone access available")
        print("[*] TTS Endpoint: Enabled")
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