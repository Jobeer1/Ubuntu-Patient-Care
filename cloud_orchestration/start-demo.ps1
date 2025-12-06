# Start Ubuntu Care Demo with Cloudflare Tunnel

Write-Host "🚀 Starting Ubuntu Care Demo..." -ForegroundColor Green

# Start the demo app in background
Write-Host "Starting Flask app on port 8080..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python app.py"

# Wait for app to start
Start-Sleep -Seconds 3

# Start Cloudflare tunnel
Write-Host "Starting Cloudflare tunnel..." -ForegroundColor Cyan
Write-Host "Your demo will be live at: https://ubuntu-care.virons.uk" -ForegroundColor Yellow
cloudflared tunnel run ubuntu-patient-care
