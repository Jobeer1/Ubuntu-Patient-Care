# ===============================================
# SA Offline DICOM Viewer - Installation Script (Windows)
# Ubuntu Patient Care System
# ===============================================

Write-Host "🇿🇦 Ubuntu Patient Care - SA Offline DICOM Viewer" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host "Installing production-ready offline DICOM viewer..." -ForegroundColor White
Write-Host ""

# Check if Node.js is installed
try {
    $nodeVersion = node --version
    Write-Host "✅ Node.js $nodeVersion detected" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js is not installed. Please install Node.js 16+ first." -ForegroundColor Red
    Write-Host "Visit: https://nodejs.org/en/download/" -ForegroundColor Yellow
    exit 1
}

# Check Node.js version
$versionNumber = [int]($nodeVersion -replace "v(\d+)\..*", '$1')
if ($versionNumber -lt 16) {
    Write-Host "❌ Node.js version 16 or higher is required. Current version: $nodeVersion" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Navigate to the offline DICOM viewer directory
Set-Location $PSScriptRoot

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Cyan
npm install

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Dependencies installed successfully" -ForegroundColor Green
Write-Host ""

# Build the application
Write-Host "🔨 Building application..." -ForegroundColor Cyan
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to build application" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Application built successfully" -ForegroundColor Green
Write-Host ""

# Create start script
Write-Host "📜 Creating start script..." -ForegroundColor Cyan

$startScript = @'
@echo off
echo 🇿🇦 Starting SA Offline DICOM Viewer...
echo Opening browser at http://localhost:8080
echo Press Ctrl+C to stop the server
echo.
npm run serve
pause
'@

$startScript | Out-File -FilePath "start-dicom-viewer.bat" -Encoding ASCII
Write-Host "✅ Start script created" -ForegroundColor Green
Write-Host ""

# Create desktop shortcut
Write-Host "🖥️ Creating desktop shortcut..." -ForegroundColor Cyan
try {
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\SA DICOM Viewer.lnk")
    $Shortcut.TargetPath = Join-Path $PSScriptRoot "start-dicom-viewer.bat"
    $Shortcut.WorkingDirectory = $PSScriptRoot
    $Shortcut.IconLocation = Join-Path $PSScriptRoot "assets\icon.ico"
    $Shortcut.Description = "Ubuntu Patient Care - SA Offline DICOM Viewer"
    $Shortcut.Save()
    Write-Host "✅ Desktop shortcut created" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Could not create desktop shortcut" -ForegroundColor Yellow
}

# Installation complete
Write-Host ""
Write-Host "🎉 Installation Complete!" -ForegroundColor Green -BackgroundColor DarkGreen
Write-Host ""
Write-Host "To start the SA Offline DICOM Viewer:" -ForegroundColor White
Write-Host "1. Double-click: start-dicom-viewer.bat" -ForegroundColor Yellow
Write-Host "2. Or run: npm run serve" -ForegroundColor Yellow
Write-Host "3. Open browser to http://localhost:8080" -ForegroundColor Yellow
Write-Host ""
Write-Host "Features included:" -ForegroundColor White
Write-Host "✅ Complete DICOM support (CT, MRI, X-Ray, etc.)" -ForegroundColor Green
Write-Host "✅ POPI Act compliance for South Africa" -ForegroundColor Green
Write-Host "✅ Offline-first architecture" -ForegroundColor Green
Write-Host "✅ Medical aid export formats" -ForegroundColor Green
Write-Host "✅ Advanced measurement tools" -ForegroundColor Green
Write-Host "✅ Secure data handling" -ForegroundColor Green
Write-Host "✅ Multi-format export (DICOM, PDF, Images)" -ForegroundColor Green
Write-Host ""
Write-Host "For support: support@ubuntu-patient-care.co.za" -ForegroundColor Cyan
Write-Host "Documentation: README.md" -ForegroundColor Cyan
Write-Host ""
Write-Host "🇿🇦 Ubuntu Philosophy: 'I am because we are'" -ForegroundColor Green

Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
