#!/bin/bash
# Ubuntu Patient Care - Complete Package Setup Script
# This script deploys weight files and configuration to the correct locations
# Run this AFTER extracting the Ubuntu-Patient-Care-Complete-Package folder

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     Ubuntu Patient Care - Complete Package Setup               ║"
echo "║     Deploying weights and configuration files                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$PACKAGE_DIR")"

echo "📁 Detected paths:"
echo "   Package directory: $PACKAGE_DIR"
echo "   Project root: $PROJECT_ROOT"
echo ""

# Function to copy files with verification
copy_with_check() {
    local source=$1
    local dest=$2
    local file_name=$(basename "$source")
    
    if [ ! -f "$source" ]; then
        echo "❌ ERROR: Source file not found: $source"
        return 1
    fi
    
    # Create destination directory if it doesn't exist
    mkdir -p "$(dirname "$dest")"
    
    echo "📦 Copying: $file_name"
    cp -v "$source" "$dest"
    echo "✅ Deployed to: $dest"
    echo ""
}

# 1. Deploy Whisper model weights
echo "═══════════════════════════════════════════════════════════════════"
echo "1️⃣  DEPLOYING MODEL WEIGHTS"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

WEIGHTS_DIR="$PACKAGE_DIR/weights"
if [ -d "$WEIGHTS_DIR" ]; then
    if [ -f "$WEIGHTS_DIR/base.pt" ]; then
        copy_with_check "$WEIGHTS_DIR/base.pt" \
            "$PROJECT_ROOT/4-PACS-Module/Orthanc/medical-reporting-module/models/whisper/base.pt"
    else
        echo "⚠️  Warning: base.pt not found in $WEIGHTS_DIR"
    fi
else
    echo "⚠️  Warning: Weights directory not found"
fi

# 2. Deploy configuration files
echo "═══════════════════════════════════════════════════════════════════"
echo "2️⃣  DEPLOYING CONFIGURATION FILES"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

SECRETS_DIR="$PACKAGE_DIR/secrets"
if [ -d "$SECRETS_DIR" ]; then
    if [ -f "$SECRETS_DIR/.env.template" ]; then
        copy_with_check "$SECRETS_DIR/.env.template" \
            "$PROJECT_ROOT/.env.template"
        
        # Create actual .env if it doesn't exist
        if [ ! -f "$PROJECT_ROOT/.env" ]; then
            echo "📝 Creating .env file from template..."
            cp "$PROJECT_ROOT/.env.template" "$PROJECT_ROOT/.env"
            echo "✅ .env file created - EDIT WITH YOUR CREDENTIALS!"
            echo ""
        else
            echo "ℹ️  .env file already exists - skipping creation"
            echo ""
        fi
    fi
else
    echo "ℹ️  Secrets directory not found - configuration will use defaults"
fi

# 3. Verify deployment
echo "═══════════════════════════════════════════════════════════════════"
echo "3️⃣  VERIFYING DEPLOYMENT"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

DEPLOYMENT_SUCCESS=true

# Check Whisper weights
if [ -f "$PROJECT_ROOT/4-PACS-Module/Orthanc/medical-reporting-module/models/whisper/base.pt" ]; then
    FILESIZE=$(du -h "$PROJECT_ROOT/4-PACS-Module/Orthanc/medical-reporting-module/models/whisper/base.pt" | cut -f1)
    echo "✅ Whisper model deployed: $FILESIZE"
else
    echo "❌ Whisper model NOT found"
    DEPLOYMENT_SUCCESS=false
fi

# Check .env
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "✅ Configuration file deployed"
else
    echo "⚠️  Configuration file not found"
fi

echo ""

if [ "$DEPLOYMENT_SUCCESS" = true ]; then
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                    ✅ SETUP COMPLETE!                          ║"
    echo "║                                                                ║"
    echo "║  Next steps:                                                   ║"
    echo "║  1. Edit .env file with your OAuth credentials                ║"
    echo "║  2. Run: python 4-PACS-Module/Orthanc/mcp-server/run.py       ║"
    echo "║  3. Access at: http://localhost:5000/login                    ║"
    echo "║                                                                ║"
    echo "║  📖 See README.md for detailed instructions                    ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
else
    echo "⚠️  Some files could not be verified. Please check manually."
fi
