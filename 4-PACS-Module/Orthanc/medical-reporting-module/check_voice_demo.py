#!/usr/bin/env python3
"""
Check the voice demo page content
"""

import requests
import urllib3

# Disable SSL warnings for self-signed certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    response = requests.get('https://localhost:5443/voice-demo', verify=False, timeout=10)
    if response.status_code == 200:
        content = response.text
        
        print("🔍 Checking voice demo content...")
        
        # Check for key phrases
        checks = [
            ("How to Use", "How to Use" in content),
            ("SA Medical Terms Recognition", "SA Medical Terms Recognition" in content),
            ("Hoe om te gebruik", "Hoe om te gebruik" in content),
            ("SA Mediese Terme", "SA Mediese Terme" in content),
            ("Click the microphone", "Click the microphone" in content),
            ("Klik die mikrofoon", "Klik die mikrofoon" in content)
        ]
        
        for phrase, found in checks:
            status = "✅" if found else "❌"
            print(f"{status} '{phrase}': {found}")
        
        # Show a snippet of the content around instructions
        if "How to Use" in content:
            start = content.find("How to Use")
            snippet = content[start:start+500]
            print(f"\n📝 Content snippet:\n{snippet}")
        elif "Hoe om te gebruik" in content:
            start = content.find("Hoe om te gebruik")
            snippet = content[start:start+500]
            print(f"\n📝 Content snippet:\n{snippet}")
        
    else:
        print(f"❌ Failed to load page: {response.status_code}")
        
except Exception as e:
    print(f"❌ Error: {e}")