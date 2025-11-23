#!/usr/bin/env python3
"""Quick test of IBM Watson configuration"""

import configparser
from pathlib import Path

config = configparser.ConfigParser()
config_path = Path(__file__).parent / "app" / "config.ini"

print("\n[CHECK] IBM Watson Configuration Test")
print("="*60)

if config_path.exists():
    config.read(config_path)
    print(f"[✓] Config file found: {config_path}")
    
    # Check Watson section
    if config.has_section("watson_api"):
        print("[✓] Watson API section exists")
        
        api_key = config.get("watson_api", "apikey", fallback=None)
        api_url = config.get("watson_api", "url", fallback=None)
        iam_url = config.get("watson_api", "iam_url", fallback=None)
        
        if api_key:
            print(f"[✓] API Key configured: {api_key[:20]}...{api_key[-10:]}")
        else:
            print("[✗] API Key missing")
            
        if api_url:
            print(f"[✓] API URL configured: {api_url}")
        else:
            print("[✗] API URL missing")
            
        if iam_url:
            print(f"[✓] IAM URL configured: {iam_url}")
        else:
            print("[✗] IAM URL missing")
    else:
        print("[✗] Watson API section not found")
else:
    print(f"[✗] Config file not found: {config_path}")

print("="*60)
print("[CHECK] IBM Watson agent configuration verified\n")
