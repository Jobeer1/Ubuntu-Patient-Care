#!/bin/bash

# ===============================================
# SA Offline DICOM Viewer - Installation Script
# Ubuntu Patient Care System
# ===============================================

echo "🇿🇦 Ubuntu Patient Care - SA Offline DICOM Viewer"
echo "==================================================="
echo "Installing production-ready offline DICOM viewer..."
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ first."
    echo "Visit: https://nodejs.org/en/download/"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 16 ]; then
    echo "❌ Node.js version 16 or higher is required. Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js $(node -v) detected"
echo ""

# Navigate to the offline DICOM viewer directory
cd "$(dirname "$0")"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed successfully"
echo ""

# Build the application
echo "🔨 Building application..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Failed to build application"
    exit 1
fi

echo "✅ Application built successfully"
echo ""

# Create desktop shortcut (Linux)
if command -v xdg-desktop-menu &> /dev/null; then
    echo "🖥️ Creating desktop shortcut..."
    
    cat > sa-dicom-viewer.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=SA Offline DICOM Viewer
Comment=Ubuntu Patient Care - Offline DICOM Viewer
Exec=npm run serve
Icon=$(pwd)/assets/icon.png
Terminal=false
StartupNotify=true
Categories=Office;Medical;
EOF

    xdg-desktop-menu install sa-dicom-viewer.desktop
    echo "✅ Desktop shortcut created"
fi

# Create start script
echo "📜 Creating start script..."
cat > start-dicom-viewer.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "🇿🇦 Starting SA Offline DICOM Viewer..."
echo "Opening browser at http://localhost:8080"
echo "Press Ctrl+C to stop the server"
echo ""
npm run serve
EOF

chmod +x start-dicom-viewer.sh
echo "✅ Start script created"
echo ""

# Installation complete
echo "🎉 Installation Complete!"
echo ""
echo "To start the SA Offline DICOM Viewer:"
echo "1. Run: ./start-dicom-viewer.sh"
echo "2. Or run: npm run serve"
echo "3. Open browser to http://localhost:8080"
echo ""
echo "Features included:"
echo "✅ Complete DICOM support (CT, MRI, X-Ray, etc.)"
echo "✅ POPI Act compliance for South Africa"
echo "✅ Offline-first architecture"
echo "✅ Medical aid export formats"
echo "✅ Advanced measurement tools"
echo "✅ Secure data handling"
echo "✅ Multi-format export (DICOM, PDF, Images)"
echo ""
echo "For support: support@ubuntu-patient-care.co.za"
echo "Documentation: ./README.md"
echo ""
echo "🇿🇦 Ubuntu Philosophy: 'I am because we are'"
