# Install Node dependencies and start the backend server (sa-ris-backend)
# Usage: .\start_backend.ps1

$backendPath = Join-Path $PSScriptRoot 'sa-ris-backend'
if (-not (Test-Path $backendPath)) {
    Write-Error "Backend folder not found at $backendPath"
    exit 1
}

Push-Location $backendPath
try {
    if (-not (Test-Path 'node_modules')) {
        Write-Host "Installing Node dependencies..."
        npm install
    } else {
        Write-Host "node_modules already present; skipping npm install"
    }

    Write-Host "Starting backend: npm start"
    npm start
} finally {
    Pop-Location
}
