# Medical Authorization Portal - PowerShell Startup Script
# =========================================================

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  Medical Authorization Portal" -ForegroundColor Cyan
Write-Host "  Starting Flask Application" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Check if dependencies are installed
Write-Host "Checking dependencies..." -ForegroundColor Yellow
$deps = @("flask", "flask_session", "werkzeug")
$missing = @()

foreach ($dep in $deps) {
    $check = pip show $dep 2>$null
    if (-not $check) {
        $missing += $dep
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Installing missing dependencies: $($missing -join ', ')" -ForegroundColor Yellow
    pip install -r requirements.txt
}

Write-Host ""
Write-Host "Starting Flask application..." -ForegroundColor Green
Write-Host "Access the portal at: http://localhost:5000" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

python app.py
