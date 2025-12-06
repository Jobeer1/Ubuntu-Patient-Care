#!/bin/bash
# Clinical DICOM Viewer - Installation Script
# For Ubuntu/Linux systems

set -e

echo "=========================================="
echo "Clinical DICOM Viewer - Installation"
echo "=========================================="
echo ""

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Installing..."
    curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
    sudo apt-get install -y nodejs
else
    echo "✅ Node.js found: $(node --version)"
fi

# Check npm
if ! command -v npm &> /dev/null; then
    echo "❌ npm not found. Installing..."
    sudo apt-get install -y npm
else
    echo "✅ npm found: $(npm --version)"
fi

echo ""
echo "Installing dependencies..."
npm install

echo ""
echo "=========================================="
echo "✅ Installation complete!"
echo "=========================================="
echo ""
echo "Quick Start:"
echo "  npm run dev          # Start development server"
echo "  npm run build        # Build for production"
echo ""
echo "Documentation:"
echo "  QUICK_START.md       # 5-minute setup guide"
echo "  README.md            # Full documentation"
echo "  DEPLOYMENT_GUIDE.md  # Production deployment"
echo ""
echo "The viewer will be available at:"
echo "  http://localhost:3000"
echo ""
echo "Ready to save lives! 🏥"
