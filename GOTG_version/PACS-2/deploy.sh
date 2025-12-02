#!/bin/bash
# GOTG PACS Deployment Script (Linux/Mac)

set -e

echo "🏥 GOTG PACS-2 Deployment Script"
echo "=================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created. Please edit it with your configuration."
    echo ""
fi

# Create necessary directories
echo "Creating data directories..."
mkdir -p data/dicom
mkdir -p data/sync-queue
mkdir -p data/sync-logs
mkdir -p data/ris-sync
mkdir -p data/backups
mkdir -p data/logs
echo "✅ Directories created"
echo ""

# Build and start containers
echo "Building Docker containers..."
docker-compose build

echo ""
echo "Starting GOTG PACS services..."
docker-compose up -d

echo ""
echo "Waiting for services to start..."
sleep 10

# Check service health
echo ""
echo "Checking service health..."

if curl -f -s http://localhost:8042/system > /dev/null 2>&1; then
    echo "✅ Orthanc PACS is running"
else
    echo "⚠️  Orthanc PACS is not responding yet"
fi

if curl -f -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ DICOM Viewer is running"
else
    echo "⚠️  DICOM Viewer is not responding yet"
fi

if curl -f -s http://localhost:5001/health > /dev/null 2>&1; then
    echo "✅ Sync Engine is running"
else
    echo "⚠️  Sync Engine is not responding yet"
fi

if curl -f -s http://localhost:5002/health > /dev/null 2>&1; then
    echo "✅ Health Monitor is running"
else
    echo "⚠️  Health Monitor is not responding yet"
fi

echo ""
echo "=================================="
echo "🎉 GOTG PACS Deployment Complete!"
echo "=================================="
echo ""
echo "Access your PACS system:"
echo "  📊 PACS Dashboard:    http://localhost:8042"
echo "  🖼️  DICOM Viewer:      http://localhost:3000"
echo "  🔄 Sync Monitor:      http://localhost:5001/status"
echo "  💚 Health Monitor:    http://localhost:5002"
echo ""
echo "Default credentials:"
echo "  Username: orthanc"
echo "  Password: orthanc"
echo ""
echo "⚠️  IMPORTANT: Change the default password in .env file!"
echo ""
echo "To stop the system:"
echo "  docker-compose down"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "For support, see README.md"
echo ""
