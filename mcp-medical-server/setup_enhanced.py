#!/usr/bin/env python3
"""
Enhanced MCP Medical Server Setup Script
Sets up web scraping capabilities with Chrome automation
"""

import os
import sys
import subprocess
import platform
import zipfile
import urllib.request
import json
import shutil
from pathlib import Path

def run_command(command, check=True):
    """Run a shell command and return result"""
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        if check:
            sys.exit(1)
        return e

def install_chrome_driver():
    """Install Chrome and ChromeDriver for Selenium automation"""
    system = platform.system().lower()
    print(f"Setting up Chrome automation for {system}...")
    
    if system == "windows":
        # Windows Chrome installation
        print("Installing Chrome on Windows...")
        chrome_installer_url = "https://dl.google.com/chrome/install/375.126/chrome_installer.exe"
        
        try:
            print("Downloading Chrome installer...")
            urllib.request.urlretrieve(chrome_installer_url, "chrome_installer.exe")
            
            print("Installing Chrome...")
            run_command("chrome_installer.exe /silent /install", check=False)
            
            # Clean up
            if os.path.exists("chrome_installer.exe"):
                os.remove("chrome_installer.exe")
                
        except Exception as e:
            print(f"Chrome installation may have failed: {e}")
            print("Please install Chrome manually from https://www.google.com/chrome/")
    
    elif system == "linux":
        # Linux Chrome installation
        print("Installing Chrome on Linux...")
        commands = [
            "wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -",
            "sudo sh -c 'echo \"deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main\" >> /etc/apt/sources.list.d/google-chrome.list'",
            "sudo apt-get update",
            "sudo apt-get install -y google-chrome-stable"
        ]
        
        for cmd in commands:
            run_command(cmd, check=False)
    
    elif system == "darwin":  # macOS
        print("Installing Chrome on macOS...")
        run_command("brew install --cask google-chrome", check=False)
    
    print("✅ Chrome setup completed")

def setup_python_environment():
    """Set up Python virtual environment and install dependencies"""
    print("Setting up Python environment...")
    
    # Create virtual environment
    venv_path = Path("venv")
    if not venv_path.exists():
        print("Creating virtual environment...")
        run_command(f"{sys.executable} -m venv venv")
    
    # Determine activation script
    if platform.system() == "Windows":
        activate_script = "venv\\Scripts\\activate.bat"
        pip_path = "venv\\Scripts\\pip"
    else:
        activate_script = "source venv/bin/activate"
        pip_path = "venv/bin/pip"
    
    # Install requirements
    print("Installing Python dependencies...")
    run_command(f"{pip_path} install --upgrade pip")
    run_command(f"{pip_path} install -r requirements.txt")
    
    print("✅ Python environment setup completed")

def setup_aws_credentials():
    """Setup AWS credentials for Bedrock access"""
    print("Setting up AWS credentials...")
    
    aws_dir = Path.home() / ".aws"
    aws_dir.mkdir(exist_ok=True)
    
    credentials_file = aws_dir / "credentials"
    config_file = aws_dir / "config"
    
    if not credentials_file.exists():
        print("Creating AWS credentials template...")
        credentials_content = """[default]
aws_access_key_id = YOUR_ACCESS_KEY_HERE
aws_secret_access_key = YOUR_SECRET_KEY_HERE
region = us-east-1

# Add your AWS credentials above
# Get them from: https://console.aws.amazon.com/iam/home#/security_credentials
"""
        credentials_file.write_text(credentials_content)
        print(f"📝 Please edit {credentials_file} with your AWS credentials")
    
    if not config_file.exists():
        print("Creating AWS config...")
        config_content = """[default]
region = us-east-1
output = json

[profile bedrock]  
region = us-east-1
"""
        config_file.write_text(config_content)
    
    print("✅ AWS configuration setup completed")

def setup_database():
    """Initialize SQLite database for caching and credentials"""
    print("Setting up database...")
    
    db_dir = Path("data")
    db_dir.mkdir(exist_ok=True)
    
    # Database will be created automatically by the application
    print("✅ Database directory created")

def setup_react_ui():
    """Setup React UI components"""
    print("Setting up React UI...")
    
    ui_dir = Path("ui")
    if ui_dir.exists():
        print("Installing Node.js dependencies...")
        original_dir = os.getcwd()
        try:
            os.chdir("ui")
            
            # Check if npm is available
            npm_check = run_command("npm --version", check=False)
            if npm_check.returncode != 0:
                print("⚠️  npm not found. Please install Node.js from https://nodejs.org/")
                return
            
            # Install dependencies
            run_command("npm install")
            print("✅ React UI setup completed")
            
        finally:
            os.chdir(original_dir)
    else:
        print("⚠️  UI directory not found, skipping React setup")

def create_startup_scripts():
    """Create convenient startup scripts"""
    print("Creating startup scripts...")
    
    if platform.system() == "Windows":
        # Windows batch file
        startup_script = """@echo off
echo Starting Enhanced MCP Medical Server...
echo.

REM Activate virtual environment
call venv\\Scripts\\activate.bat

REM Start the server
echo Starting FastAPI server with MCP integration...
python server.py

pause
"""
        with open("start_server.bat", "w") as f:
            f.write(startup_script)
        
        # React UI startup
        ui_script = """@echo off
echo Starting React UI...
cd ui
npm start
pause
"""
        with open("start_ui.bat", "w") as f:
            f.write(ui_script)
    
    else:
        # Unix shell script
        startup_script = """#!/bin/bash
echo "Starting Enhanced MCP Medical Server..."
echo

# Activate virtual environment
source venv/bin/activate

# Start the server
echo "Starting FastAPI server with MCP integration..."
python server.py
"""
        with open("start_server.sh", "w") as f:
            f.write(startup_script)
        os.chmod("start_server.sh", 0o755)
        
        # React UI startup
        ui_script = """#!/bin/bash
echo "Starting React UI..."
cd ui
npm start
"""
        with open("start_ui.sh", "w") as f:
            f.write(ui_script)
        os.chmod("start_ui.sh", 0o755)
    
    print("✅ Startup scripts created")

def create_environment_file():
    """Create .env file with default configuration"""
    print("Creating environment configuration...")
    
    env_content = """# Enhanced MCP Medical Server Configuration

# Server Configuration
HOST=localhost
PORT=8000
DEBUG=true

# Database
DATABASE_URL=sqlite:///./data/medical_schemes.db

# AWS Bedrock Configuration
AWS_REGION=us-east-1
AWS_PROFILE=default
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0

# Web Scraping Configuration
CHROME_HEADLESS=true
SCRAPING_DELAY_MIN=1
SCRAPING_DELAY_MAX=3
MAX_RETRY_ATTEMPTS=3
CAPTCHA_SERVICE=2captcha
CAPTCHA_API_KEY=your_2captcha_api_key_here

# Security
SECRET_KEY=your-secret-key-here-change-this-in-production
FERNET_KEY=auto-generated-on-first-run

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/mcp_server.log

# CORS Origins (for React UI)
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]

# Rate Limiting
MAX_REQUESTS_PER_MINUTE=60
MAX_CONCURRENT_SCRAPING=3

# Cache Configuration
CACHE_TTL_MINUTES=60
CACHE_MAX_SIZE=1000
"""
    
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write(env_content)
        print("✅ Environment file created")
    else:
        print("ℹ️  Environment file already exists")

def verify_installation():
    """Verify that all components are properly installed"""
    print("Verifying installation...")
    
    checks = [
        ("Python", sys.executable + " --version"),
        ("Chrome", "google-chrome --version" if platform.system() != "Windows" else "chrome --version"),
        ("Node.js", "node --version"),
        ("npm", "npm --version")
    ]
    
    results = {}
    for name, command in checks:
        result = run_command(command, check=False)
        results[name] = result.returncode == 0
        status = "✅" if results[name] else "❌"
        print(f"{status} {name}: {'OK' if results[name] else 'Not found'}")
    
    print("\nInstallation Summary:")
    print("=" * 50)
    
    if results.get("Python", False):
        print("✅ Python environment ready")
    else:
        print("❌ Python not properly configured")
    
    if results.get("Chrome", False):
        print("✅ Chrome browser ready for automation")
    else:
        print("⚠️  Chrome not found - web scraping may not work")
    
    if results.get("Node.js", False) and results.get("npm", False):
        print("✅ Node.js environment ready for React UI")
    else:
        print("⚠️  Node.js not found - React UI may not work")
    
    print("\nNext Steps:")
    print("1. Edit .env file with your configurations")
    print("2. Add AWS credentials to ~/.aws/credentials")
    print("3. Run startup scripts to test the server")
    print("4. Access UI at http://localhost:3000")

def main():
    """Main setup function"""
    print("🏥 Enhanced MCP Medical Server Setup")
    print("=" * 50)
    print("This script will set up:")
    print("• Python virtual environment")
    print("• Web scraping with Chrome automation")
    print("• AWS Bedrock integration")
    print("• React UI components")
    print("• Database and caching")
    print()
    
    try:
        # Setup steps
        setup_python_environment()
        install_chrome_driver()
        setup_aws_credentials()
        setup_database()
        setup_react_ui()
        create_environment_file()
        create_startup_scripts()
        
        print("\n🎉 Setup completed successfully!")
        print()
        
        verify_installation()
        
    except KeyboardInterrupt:
        print("\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()