# Ubuntu Patient Care - Medical Authorization System Startup Script
# Starts all required services in the correct order

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Ubuntu Patient Care - Medical Authorization System" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
Write-Host "Checking prerequisites..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.10+" -ForegroundColor Red
    exit 1
}

# Check if Node.js is installed
try {
    $nodeVersion = node --version 2>&1
    Write-Host "✅ Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Starting services..." -ForegroundColor Yellow
Write-Host ""

# Get current directory
$currentDir = Get-Location

# Start MCP Server
Write-Host "1️⃣  Starting MCP Medical Authorization Server..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$currentDir\mcp-medical-server'; python server.py" -WindowStyle Normal

Start-Sleep -Seconds 3

# Start Backend
Write-Host "2️⃣  Starting SA-RIS Backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$currentDir\sa-ris-backend'; npm start" -WindowStyle Normal

Start-Sleep -Seconds 5

# Start Frontend (React Dev Server)
Write-Host "3️⃣  Starting SA-RIS Frontend (React Dev Server)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$currentDir\sa-ris-frontend'; npm start" -WindowStyle Normal

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  ✅ All services started!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services running:" -ForegroundColor Yellow
Write-Host "  • MCP Server:     Running in separate window" -ForegroundColor White
Write-Host "  • Backend API:    http://localhost:3001" -ForegroundColor White
Write-Host "  • Frontend UI:    http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Browser will open automatically" -ForegroundColor White
Write-Host "  2. Click 'Medical Authorization' in sidebar" -ForegroundColor White
Write-Host "  3. Start testing with sample data" -ForegroundColor White
Write-Host ""
Write-Host "Sample test data:" -ForegroundColor Yellow
Write-Host "  Medical Scheme: DISCOVERY" -ForegroundColor White
Write-Host "  Member Number:  1234567890" -ForegroundColor White
Write-Host "  Patient ID:     TEST-001" -ForegroundColor White
Write-Host "  Procedure:      3011 (CT Head)" -ForegroundColor White
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Yellow
Write-Host "  • Quick Start:  QUICK_START_MCP_AUTH.md" -ForegroundColor White
Write-Host "  • Testing:      TEST_MEDICAL_AUTH_UI.md" -ForegroundColor White
Write-Host "  • Integration:  INTEGRATION_COMPLETE.md" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C in each window to stop services" -ForegroundColor Gray
Write-Host ""
