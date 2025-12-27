# Ubuntu Patient Care - Complete Package Setup Script (Windows PowerShell)
# This script deploys weight files and configuration to the correct locations
# Run this AFTER extracting the Ubuntu-Patient-Care-Complete-Package folder

$ErrorActionPreference = "Stop"

Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     Ubuntu Patient Care - Complete Package Setup               ║" -ForegroundColor Cyan
Write-Host "║     Deploying weights and configuration files                  ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Get the directory where this script is located
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PACKAGE_DIR = Split-Path -Parent $SCRIPT_DIR
$PROJECT_ROOT = Split-Path -Parent $PACKAGE_DIR

Write-Host "📁 Detected paths:" -ForegroundColor Yellow
Write-Host "   Package directory: $PACKAGE_DIR"
Write-Host "   Project root: $PROJECT_ROOT`n"

# Function to copy files with verification
function Copy-WithCheck {
    param(
        [string]$Source,
        [string]$Dest
    )
    
    if (-not (Test-Path $Source)) {
        Write-Host "❌ ERROR: Source file not found: $Source" -ForegroundColor Red
        return $false
    }
    
    $FileName = Split-Path -Leaf $Source
    $DestDir = Split-Path -Parent $Dest
    
    # Create destination directory if it doesn't exist
    if (-not (Test-Path $DestDir)) {
        New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
    }
    
    Write-Host "📦 Copying: $FileName"
    Copy-Item -Path $Source -Destination $Dest -Force
    
    $FileSize = (Get-Item $Dest).Length / 1MB
    Write-Host "✅ Deployed to: $Dest ($([Math]::Round($FileSize, 2)) MB)`n"
    
    return $true
}

# 1. Deploy Whisper model weights
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "1️⃣  DEPLOYING MODEL WEIGHTS" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

$WEIGHTS_DIR = Join-Path $PACKAGE_DIR "weights"
if (Test-Path $WEIGHTS_DIR) {
    $WEIGHTS_FILE = Join-Path $WEIGHTS_DIR "base.pt"
    if (Test-Path $WEIGHTS_FILE) {
        $DEST_WEIGHTS = Join-Path $PROJECT_ROOT "4-PACS-Module\Orthanc\medical-reporting-module\models\whisper\base.pt"
        Copy-WithCheck $WEIGHTS_FILE $DEST_WEIGHTS
    } else {
        Write-Host "⚠️  Warning: base.pt not found in $WEIGHTS_DIR`n" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Warning: Weights directory not found`n" -ForegroundColor Yellow
}

# 2. Deploy configuration files
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "2️⃣  DEPLOYING CONFIGURATION FILES" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

$SECRETS_DIR = Join-Path $PACKAGE_DIR "secrets"
if (Test-Path $SECRETS_DIR) {
    $ENV_TEMPLATE = Join-Path $SECRETS_DIR ".env.template"
    if (Test-Path $ENV_TEMPLATE) {
        $DEST_TEMPLATE = Join-Path $PROJECT_ROOT ".env.template"
        Copy-WithCheck $ENV_TEMPLATE $DEST_TEMPLATE
        
        # Create actual .env if it doesn't exist
        $ENV_FILE = Join-Path $PROJECT_ROOT ".env"
        if (-not (Test-Path $ENV_FILE)) {
            Write-Host "📝 Creating .env file from template..."
            Copy-Item $DEST_TEMPLATE $ENV_FILE -Force
            Write-Host "✅ .env file created - EDIT WITH YOUR CREDENTIALS!`n" -ForegroundColor Green
        } else {
            Write-Host "ℹ️  .env file already exists - skipping creation`n" -ForegroundColor Blue
        }
    }
} else {
    Write-Host "ℹ️  Secrets directory not found - configuration will use defaults`n" -ForegroundColor Blue
}

# 3. Verify deployment
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "3️⃣  VERIFYING DEPLOYMENT" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

$DEPLOYMENT_SUCCESS = $true

# Check Whisper weights
$WHISPER_PATH = Join-Path $PROJECT_ROOT "4-PACS-Module\Orthanc\medical-reporting-module\models\whisper\base.pt"
if (Test-Path $WHISPER_PATH) {
    $FILESIZE = [Math]::Round((Get-Item $WHISPER_PATH).Length / 1MB, 2)
    Write-Host "✅ Whisper model deployed: $FILESIZE MB" -ForegroundColor Green
} else {
    Write-Host "❌ Whisper model NOT found" -ForegroundColor Red
    $DEPLOYMENT_SUCCESS = $false
}

# Check .env
$ENV_FILE = Join-Path $PROJECT_ROOT ".env"
if (Test-Path $ENV_FILE) {
    Write-Host "✅ Configuration file deployed" -ForegroundColor Green
} else {
    Write-Host "⚠️  Configuration file not found" -ForegroundColor Yellow
}

Write-Host ""

if ($DEPLOYMENT_SUCCESS) {
    Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║                    ✅ SETUP COMPLETE!                          ║" -ForegroundColor Green
    Write-Host "║                                                                ║" -ForegroundColor Green
    Write-Host "║  Next steps:                                                   ║" -ForegroundColor Green
    Write-Host "║  1. Edit .env file with your OAuth credentials                ║" -ForegroundColor Green
    Write-Host "║  2. Run: python 4-PACS-Module/Orthanc/mcp-server/run.py       ║" -ForegroundColor Green
    Write-Host "║  3. Access at: http://localhost:5000/login                    ║" -ForegroundColor Green
    Write-Host "║                                                                ║" -ForegroundColor Green
    Write-Host "║  📖 See README.md for detailed instructions                    ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some files could not be verified. Please check manually." -ForegroundColor Yellow
}

Write-Host ""
