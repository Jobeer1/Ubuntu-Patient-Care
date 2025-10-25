"""
OneDrive Setup Verification Script
Checks if all configuration is correct before starting
"""
import os
import sys

def check_env_file():
    """Check if .env file exists and has required values"""
    env_path = "4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend/.env"
    
    if not os.path.exists(env_path):
        print("❌ .env file not found!")
        print(f"   Expected location: {env_path}")
        return False
    
    print("✅ .env file found")
    
    # Read and check contents
    with open(env_path, 'r') as f:
        content = f.read()
    
    required_vars = {
        'ONEDRIVE_CLIENT_ID': '42f0676f-4209-4be8-a72d-4102f5e260d8',
        'ONEDRIVE_CLIENT_SECRET': None,  # Should be set but we don't know the value
        'ONEDRIVE_REDIRECT_URI': 'http://localhost:5000/api/nas/onedrive/callback',
        'ONEDRIVE_TENANT_ID': 'fba55b68-1de1-4d10-a7cc-efa55942f829'
    }
    
    all_good = True
    for var, expected_value in required_vars.items():
        if var not in content:
            print(f"❌ {var} not found in .env file")
            all_good = False
        elif expected_value and expected_value not in content:
            print(f"⚠️  {var} found but value might be incorrect")
            print(f"   Expected: {expected_value}")
        elif var == 'ONEDRIVE_CLIENT_SECRET':
            if 'YOUR_CLIENT_SECRET_HERE' in content:
                print(f"❌ {var} not set - still has placeholder value")
                print(f"   You need to create a client secret in Azure Portal")
                all_good = False
            else:
                # Check if it looks like a real secret (contains ~ and .)
                import re
                secret_match = re.search(r'ONEDRIVE_CLIENT_SECRET=([^\s\n]+)', content)
                if secret_match and '~' in secret_match.group(1) and '.' in secret_match.group(1):
                    print(f"✅ {var} configured (secret looks valid)")
                else:
                    print(f"⚠️  {var} set but format looks unusual")
        else:
            print(f"✅ {var} configured")
    
    return all_good

def check_azure_setup():
    """Provide checklist for Azure AD setup"""
    print("\n" + "="*60)
    print("Azure AD Configuration Checklist")
    print("="*60)
    print("\nPlease verify these settings in Azure Portal:")
    print("https://portal.azure.com → Azure AD → App registrations → UPC PACS onedrive setup\n")
    
    checklist = [
        ("Redirect URI", "http://localhost:5000/api/nas/onedrive/callback"),
        ("API Permission", "Files.ReadWrite.All (Delegated)"),
        ("API Permission", "offline_access (Delegated)"),
        ("API Permission", "User.Read (Delegated)"),
        ("Admin Consent", "Granted (green checkmark)"),
        ("Client Secret", "Created and copied to .env file")
    ]
    
    for item, detail in checklist:
        print(f"  [ ] {item}: {detail}")
    
    print("\n" + "="*60)

def main():
    print("="*60)
    print("OneDrive Integration Setup Verification")
    print("="*60)
    print()
    
    # Check .env file
    env_ok = check_env_file()
    
    # Show Azure checklist
    check_azure_setup()
    
    print("\n" + "="*60)
    print("Next Steps:")
    print("="*60)
    
    if not env_ok:
        print("\n1. ❌ Fix the .env file issues above")
        print("2. Follow COMPLETE_ONEDRIVE_SETUP.md for detailed instructions")
        print("3. Run this script again to verify")
    else:
        print("\n1. ✅ .env file is configured")
        print("2. Verify Azure AD settings (checklist above)")
        print("3. Restart Flask backend:")
        print("   cd 4-PACS-Module\\Orthanc\\orthanc-source\\NASIntegration\\backend")
        print("   py app.py")
        print("4. Test the connection:")
        print("   py test_onedrive_endpoints.py")
        print("5. Go to http://localhost:5000/api/nas/onedrive/setup")
        print("6. Click 'Connect OneDrive'")
    
    print("\n" + "="*60)
    print("Documentation:")
    print("="*60)
    print("  • COMPLETE_ONEDRIVE_SETUP.md - Step-by-step guide")
    print("  • ONEDRIVE_SETUP_GUIDE.md - Detailed Azure AD setup")
    print("  • QUICK_FIX_ONEDRIVE.md - Quick reference")
    print("  • ONEDRIVE_FLOW_DIAGRAM.md - Visual flow diagram")
    print()

if __name__ == "__main__":
    main()
