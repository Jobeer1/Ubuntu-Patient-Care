# Clinical DICOM Viewer - Installation Script
# For Windows systems

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Clinical DICOM Viewer - Installation" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check Node.js
try {
    $nodeVersion = node --version
    Write-Host "✅ Node.js found: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js not found." -ForegroundColor Red
    Write-Host "Please install Node.js from: https://nodejs.org/" -ForegroundColor Yellow
    Write-Host "Download the LTS version (16.x or higher)" -ForegroundColor Yellow
    exit 1
}

# Check npm
try {
    $npmVersion = npm --version
    Write-Host "✅ npm found: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ npm not found." -ForegroundColor Red
    Write-Host "npm should be installed with Node.js" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Yellow
npm install

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "✅ Installation complete!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Quick Start:" -ForegroundColor Yellow
    Write-Host "  npm run dev          # Start development server"
    Write-Host "  npm run build        # Build for production"
    Write-Host ""
    Write-Host "Documentation:" -ForegroundColor Yellow
    Write-Host "  QUICK_START.md       # 5-minute setup guide"
    Write-Host "  README.md            # Full documentation"
    Write-Host "  DEPLOYMENT_GUIDE.md  # Production deployment"
    Write-Host ""
    Write-Host "The viewer will be available at:" -ForegroundColor Yellow
    Write-Host "  http://localhost:3000"
    Write-Host ""
    Write-Host "Ready to save lives! 🏥" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ Installation failed!" -ForegroundColor Red
    Write-Host "Please check the error messages above." -ForegroundColor Yellow
    exit 1
}
