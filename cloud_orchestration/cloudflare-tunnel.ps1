# Cloudflare Tunnel Setup for AI Genesis Hackathon Demo
# Domain: virons.uk
# Subdomain: ubuntu-care (full URL: ubuntu-care.virons.uk)

Write-Host "========================================" -ForegroundColor Green
Write-Host "🏥 Ubuntu Patient Care - Cloudflare Tunnel" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Setting up public demo for hackathon judges..." -ForegroundColor Cyan
Write-Host ""

# Check if cloudflared is installed
$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue

if (-not $cloudflared) {
    Write-Host "❌ Cloudflared not found. Installing..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please install Cloudflared first:" -ForegroundColor Yellow
    Write-Host "  winget install --id Cloudflare.cloudflared" -ForegroundColor White
    Write-Host ""
    Write-Host "Or download from:" -ForegroundColor Yellow
    Write-Host "  https://github.com/cloudflare/cloudflared/releases" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "✓ Cloudflared found" -ForegroundColor Green
Write-Host ""

# Tunnel configuration
$TUNNEL_NAME = "ubuntu-care"
$SUBDOMAIN = "ubuntu-care"
$DOMAIN = "virons.uk"
$LOCAL_PORT = 8080
$PUBLIC_URL = "https://$SUBDOMAIN.$DOMAIN"

Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Tunnel Name: $TUNNEL_NAME" -ForegroundColor White
Write-Host "  Public URL:  $PUBLIC_URL" -ForegroundColor Green
Write-Host "  Local Port:  $LOCAL_PORT" -ForegroundColor White
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "🚀 Starting Cloudflare Tunnel..." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Judges can access the demo at:" -ForegroundColor Cyan
Write-Host "  $PUBLIC_URL" -ForegroundColor Green -BackgroundColor Black
Write-Host ""
Write-Host "Press Ctrl+C to stop the tunnel" -ForegroundColor Yellow
Write-Host ""

# Start the tunnel
cloudflared tunnel --url http://localhost:$LOCAL_PORT --hostname $SUBDOMAIN.$DOMAIN
