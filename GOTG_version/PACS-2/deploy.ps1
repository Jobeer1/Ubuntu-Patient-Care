# GOTG PACS Deployment Script (Windows PowerShell)

Write-Host "🏥 GOTG PACS-2 Deployment Script" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker Compose is not installed. Please install Docker Compose first." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Docker and Docker Compose are installed" -ForegroundColor Green
Write-Host ""

# Create .env file if it doesn't exist
if (-not (Test-Path .env)) {
    Write-Host "Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "✅ .env file created. Please edit it with your configuration." -ForegroundColor Green
    Write-Host ""
}

# Create necessary directories
Write-Host "Creating data directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path data/dicom | Out-Null
New-Item -ItemType Directory -Force -Path data/sync-queue | Out-Null
New-Item -ItemType Directory -Force -Path data/sync-logs | Out-Null
New-Item -ItemType Directory -Force -Path data/ris-sync | Out-Null
New-Item -ItemType Directory -Force -Path data/backups | Out-Null
New-Item -ItemType Directory -Force -Path data/logs | Out-Null
Write-Host "✅ Directories created" -ForegroundColor Green
Write-Host ""

# Build and start containers
Write-Host "Building Docker containers..." -ForegroundColor Yellow
docker-compose build

Write-Host ""
Write-Host "Starting GOTG PACS services..." -ForegroundColor Yellow
docker-compose up -d

Write-Host ""
Write-Host "Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check service health
Write-Host ""
Write-Host "Checking service health..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8042/system" -UseBasicParsing -TimeoutSec 5
    Write-Host "✅ Orthanc PACS is running" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Orthanc PACS is not responding yet" -ForegroundColor Yellow
}

try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
    Write-Host "✅ DICOM Viewer is running" -ForegroundColor Green
} catch {
    Write-Host "⚠️  DICOM Viewer is not responding yet" -ForegroundColor Yellow
}

try {
    $response = Invoke-WebRequest -Uri "http://localhost:5001/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "✅ Sync Engine is running" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Sync Engine is not responding yet" -ForegroundColor Yellow
}

try {
    $response = Invoke-WebRequest -Uri "http://localhost:5002/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "✅ Health Monitor is running" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Health Monitor is not responding yet" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "🎉 GOTG PACS Deployment Complete!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access your PACS system:" -ForegroundColor Yellow
Write-Host "  📊 PACS Dashboard:    http://localhost:8042"
Write-Host "  🖼️  DICOM Viewer:      http://localhost:3000"
Write-Host "  🔄 Sync Monitor:      http://localhost:5001/status"
Write-Host "  💚 Health Monitor:    http://localhost:5002"
Write-Host ""
Write-Host "Default credentials:" -ForegroundColor Yellow
Write-Host "  Username: orthanc"
Write-Host "  Password: orthanc"
Write-Host ""
Write-Host "⚠️  IMPORTANT: Change the default password in .env file!" -ForegroundColor Red
Write-Host ""
Write-Host "To stop the system:" -ForegroundColor Yellow
Write-Host "  docker-compose down"
Write-Host ""
Write-Host "To view logs:" -ForegroundColor Yellow
Write-Host "  docker-compose logs -f"
Write-Host ""
Write-Host "For support, see README.md" -ForegroundColor Yellow
Write-Host ""
