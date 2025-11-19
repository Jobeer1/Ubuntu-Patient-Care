# Start the Named Cloudflare Tunnel
# Run this after setup-named-tunnel.ps1

Write-Host "========================================" -ForegroundColor Green
Write-Host "🏥 Ubuntu Patient Care - Starting Tunnel" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Public URL: https://ubuntu-care.virons.uk" -ForegroundColor Green -BackgroundColor Black
Write-Host ""
Write-Host "Press Ctrl+C to stop the tunnel" -ForegroundColor Yellow
Write-Host ""

cloudflared tunnel run ubuntu-care
