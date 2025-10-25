#!/usr/bin/env python3
"""
Verify Microsoft OAuth Configuration for MCP Server
This script checks that your configuration is correct
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Found .env file at {env_path}")
else:
    print(f"✗ .env file not found at {env_path}")
    print(f"  Create it by copying .env.example: copy .env.example .env")
    sys.exit(1)

print("\n" + "="*60)
print("Microsoft OAuth Configuration Verification")
print("="*60 + "\n")

# Check required variables
required_vars = {
    'MICROSOFT_CLIENT_ID': '60271c16-3fcb-4ba7-972b-9f075200a567',
    'MICROSOFT_CLIENT_SECRET': 'your-client-secret',
    'MICROSOFT_TENANT_ID': 'fba55b68-1de1-4d10-a7cc-efa55942f829',
    'MICROSOFT_REDIRECT_URI': 'http://localhost:8080/auth/microsoft/callback'
}

all_ok = True

for var_name, expected_value in required_vars.items():
    value = os.getenv(var_name, '')
    
    if not value:
        print(f"✗ {var_name}")
        print(f"  └─ Missing or empty!")
        all_ok = False
        continue
    
    if var_name == 'MICROSOFT_CLIENT_SECRET':
        if value == 'your-client-secret' or len(value) < 10:
            print(f"✗ {var_name}")
            print(f"  └─ Placeholder value detected!")
            print(f"  └─ Get real secret from: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Credentials/appId/60271c16-3fcb-4ba7-972b-9f075200a567")
            all_ok = False
        else:
            print(f"✓ {var_name}")
            print(f"  └─ Set (secret hidden for security)")
    else:
        if value == expected_value:
            print(f"✓ {var_name}")
            print(f"  └─ {value}")
        else:
            print(f"⚠ {var_name}")
            print(f"  └─ Current: {value}")
            print(f"  └─ Expected: {expected_value}")
            if var_name != 'MICROSOFT_REDIRECT_URI':
                all_ok = False

print("\n" + "="*60)
print("Next Steps:")
print("="*60 + "\n")

if all_ok:
    print("✓ All configuration looks good!")
    print("\nNow:")
    print("1. Verify redirect URI is added in Azure Portal")
    print("   https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Authentication/appId/60271c16-3fcb-4ba7-972b-9f075200a567")
    print("\n2. Under 'Web' section, confirm redirect URI exists:")
    print("   http://localhost:8080/auth/microsoft/callback")
    print("\n3. Start the MCP server:")
    print("   python run.py")
    print("\n4. Test login:")
    print("   http://localhost:8080/test")
else:
    print("✗ Configuration incomplete!")
    print("\nFix these issues:")
    print("1. Edit .env file")
    print("2. Add missing values from Azure Portal")
    print("3. Save the file")
    print("4. Restart MCP server")

print("\n" + "="*60 + "\n")
