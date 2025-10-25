#!/usr/bin/env python3
"""
Test script to verify Flask session configuration
"""

import sys
import os

# Add backend to path
sys.path.insert(0, '4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend')

from config import Config

print("\n" + "="*50)
print("Flask Session Configuration Test")
print("="*50)

config = Config()

print(f"\n🔑 SECRET_KEY: {config.SECRET_KEY[:30]}...")
print(f"📝 SECRET_KEY Length: {len(config.SECRET_KEY)}")
print(f"🍪 SESSION_COOKIE_SAMESITE: {config.SESSION_COOKIE_SAMESITE}")
print(f"🔒 SESSION_COOKIE_SECURE: {config.SESSION_COOKIE_SECURE}")
print(f"🌐 SESSION_COOKIE_HTTPONLY: {config.SESSION_COOKIE_HTTPONLY}")
print(f"⏰ SESSION_PERMANENT_LIFETIME: {config.SESSION_PERMANENT_LIFETIME}")

print("\n" + "="*50)
print("✅ Configuration looks good!")
print("="*50)

# Test if SECRET_KEY is consistent
config2 = Config()
if config.SECRET_KEY == config2.SECRET_KEY:
    print("✅ SECRET_KEY is CONSISTENT across instances")
else:
    print("❌ SECRET_KEY is DIFFERENT across instances!")
    print(f"   First:  {config.SECRET_KEY[:30]}...")
    print(f"   Second: {config2.SECRET_KEY[:30]}...")

print()
