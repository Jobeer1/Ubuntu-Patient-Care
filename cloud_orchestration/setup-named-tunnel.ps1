# Setup Named Cloudflare Tunnel for ubuntu-care.virons.uk
# Run this script to create a stable, persistent tunnel

Write-Host "========================================" -ForegroundColor Green
Write-Host "🏥 Ubuntu Patient Care - Named Tunnel Setup" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

$TUNNEL_NAME = "ubuntu-care"
$HOSTNAME = "ubuntu-care.virons.uk"
$LOCAL_URL = "http://localhost:8080"

# Step 1: Login to Cloudflare
Write-Host "Step 1: Logging into Cloudflare..." -ForegroundColor Cyan
Write-Host "  A browser window will open. Select 'virons.uk' domain." -ForegroundColor Yellow
Write-Host ""
cloudflared tunnel login

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Login failed. Please try again." -ForegroundColor Red
    exit 1
}

Write-Host "✓ Login successful" -ForegroundColor Green
Write-Host ""

# Step 2: Create named tunnel
Write-Host "Step 2: Creating named tunnel '$TUNNEL_NAME'..." -ForegroundColor Cyan
cloudflared tunnel create $TUNNEL_NAME

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠ Tunnel may already exist. Continuing..." -ForegroundColor Yellow
}

Write-Host "✓ Tunnel created" -ForegroundColor Green
Write-Host ""

# Step 3: Get tunnel ID
Write-Host "Step 3: Getting tunnel ID..." -ForegroundColor Cyan
$tunnelInfo = cloudflared tunnel list | Select-String $TUNNEL_NAME
if ($tunnelInfo) {
    $tunnelId = ($tunnelInfo -split '\s+')[0]
    Write-Host "✓ Tunnel ID: $tunnelId" -ForegroundColor Green
} else {
    Write-Host "✗ Could not find tunnel. Please check 'cloudflared tunnel list'" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 4: Create config file
Write-Host "Step 4: Creating config file..." -ForegroundColor Cyan
$configPath = "$env:USERPROFILE\.cloudflared\config.yml"
$credentialsPath = "$env:USERPROFILE\.cloudflared\$tunnelId.json"

$configContent = @"
tunnel: $tunnelId
credentials-file: $credentialsPath

ingress:
  - hostname: $HOSTNAME
    service: $LOCAL_URL
  - service: http_status:404
"@

$configContent | Out-File -FilePath $configPath -Encoding UTF8
Write-Host "✓ Config file created at: $configPath" -ForegroundColor Green
Write-Host ""

# Step 5: Route DNS
Write-Host "Step 5: Routing DNS..." -ForegroundColor Cyan
cloudflared tunnel route dns $TUNNEL_NAME $HOSTNAME

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠ DNS route may already exist. Continuing..." -ForegroundColor Yellow
}

Write-Host "✓ DNS routed" -ForegroundColor Green
Write-Host ""

# Done
Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Your stable URL is ready:" -ForegroundColor Cyan
Write-Host "  https://$HOSTNAME" -ForegroundColor Green -BackgroundColor Black
Write-Host ""
Write-Host "To start the tunnel, run:" -ForegroundColor Cyan
Write-Host "  cloudflared tunnel run $TUNNEL_NAME" -ForegroundColor White
Write-Host ""
Write-Host "Or use the start script:" -ForegroundColor Cyan
Write-Host "  .\start-tunnel.ps1" -ForegroundColor White
Write-Host ""
