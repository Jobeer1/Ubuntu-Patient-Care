# Run Cloudflared tunnel + start the Medical Reporting Module app (Windows PowerShell)
# Usage: Open PowerShell as Administrator (if required) and run: .\run_cloudflared.ps1

# Explanation:
# - Starts the app with NO_SSL=1 so cloudflared can forward HTTP
# - Starts cloudflared tunnel and prints the public URL in the console

$ErrorActionPreference = 'Stop'

# Change to repository root (script location)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

# Prefer local cloudflared.exe (repo root) then PATH
$localCf = Join-Path $scriptDir 'cloudflared.exe'
if (Test-Path $localCf) {
    $cloudflaredCmd = $localCf
} elseif (Get-Command cloudflared -ErrorAction SilentlyContinue) {
    $cloudflaredCmd = (Get-Command cloudflared).Source
} else {
    Write-Host "cloudflared not found. Please download cloudflared.exe into this folder or install it system-wide." -ForegroundColor Yellow
    Write-Host "Download: https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -ForegroundColor Cyan
    exit 1
}

# Clean up any existing Python processes that might be holding log files
Get-Process python,py -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# Start the app in a background process (minimised window)
Write-Host "Starting Medical Reporting Module (HTTPS for STT support)..." -ForegroundColor Green
# Ensure environment variables are set for this PowerShell session so
# they are inherited by any child processes.
# Note: Keeping HTTPS since STT requires secure context

# Disable the Flask auto-reloader for the demo run to avoid the app restarting
# while the script probes for readiness. This makes the app start once and stay up.
$env:FLASK_ENV = 'production'
$env:PYTHONUNBUFFERED = '1'
$env:DATABASE_URL = 'sqlite:///medical_reporting.db'

# We will start the app via cmd.exe and redirect stdout/stderr to files.
# The child command does not need to set NO_SSL because it's already set in this session.
# Change to the app directory first so relative imports work correctly.
$appDir = Join-Path $scriptDir 'Orthanc\medical-reporting-module'
$childCmd = "cd /d `"$appDir`" && py app.py"
# Prepare separate stdout/stderr log files for the app and start the process.
$outLog = Join-Path $scriptDir 'app_stdout.log'
$errLog = Join-Path $scriptDir 'app_stderr.log'
# Try to remove old log files, ignore errors if they're in use
try { if (Test-Path $outLog) { Remove-Item $outLog -Force -ErrorAction Stop } } catch { }
try { if (Test-Path $errLog) { Remove-Item $errLog -Force -ErrorAction Stop } } catch { }

# Use cmd.exe redirection so Start-Process doesn't need -RedirectStandard* options.
# Build the cmd.exe command string using concatenation to avoid nested-quote parsing issues.
$childCmdRedirect = 'set NO_SSL=1 && py .\Orthanc\medical-reporting-module\app.py > "' + $outLog + '" 2> "' + $errLog + '"'
Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', $childCmdRedirect -WindowStyle Minimized -PassThru | Out-Null

# Wait until the app is responsive, then start cloudflared. This avoids creating a tunnel
# before the app is listening and helps pick HTTP vs HTTPS automatically.
Write-Host "Waiting for the app to be available on localhost:5443 (timeout 120s)..." -ForegroundColor Yellow
$maxAttempts = 120
$attempt = 0
$isHttp = $false
$isHttps = $false
while ($attempt -lt $maxAttempts) {
    $attempt++
    try {
    # Try HTTP first (try both 127.0.0.1 and localhost)
    $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:5443/' -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
            $isHttp = $true
            break
        }
    } catch {
        # ignore
    }

    try {
        # Try HTTPS while ignoring self-signed certs
        [Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
    $resp = Invoke-WebRequest -Uri 'https://127.0.0.1:5443/' -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
            $isHttps = $true
            break
        }
    } catch {
        # ignore
    } finally {
        [Net.ServicePointManager]::ServerCertificateValidationCallback = $null
    }

    Start-Sleep -Seconds 1
}

if ($isHttp) {
    Write-Host "App responded over HTTP on port 5443." -ForegroundColor Green
    $cfArgs = @('tunnel', '--url', 'http://127.0.0.1:5443', '--protocol', 'http2')
} elseif ($isHttps) {
    Write-Host "App responded over HTTPS on port 5443. Starting tunnel with --no-tls-verify." -ForegroundColor Green
    $cfArgs = @('tunnel', '--url', 'https://127.0.0.1:5443', '--no-tls-verify', '--protocol', 'http2')
} else {
    Write-Host "App did not respond within timeout. Trying HTTPS tunnel with --no-tls-verify." -ForegroundColor Yellow
    Write-Host "Check the app logs at $outLog and $errLog for errors." -ForegroundColor Yellow
    $cfArgs = @('tunnel', '--url', 'https://127.0.0.1:5443', '--no-tls-verify', '--protocol', 'http2')
}

Write-Host "Starting cloudflared with arguments: $($cfArgs -join ' ') using: $cloudflaredCmd" -ForegroundColor Green
Write-Host "If your app is still starting increase the timeout in this script." -ForegroundColor Yellow

& $cloudflaredCmd @cfArgs

Write-Host "cloudflared exited. When finished, press Enter to close this window." -ForegroundColor Cyan
Read-Host | Out-Null
