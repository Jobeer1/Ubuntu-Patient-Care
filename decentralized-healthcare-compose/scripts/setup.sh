#!/bin/bash

# Healthcare Compute Platform Setup Script
# This script sets up the development environment

set -e

echo "🏥 Setting up Healthcare Compute Platform..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/{datasets,models,jobs,results}
mkdir -p logs
mkdir -p grafana/{dashboards,datasources}

# Copy environment file
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration"
fi

# Generate JWT secret
if grep -q "your-super-secret-jwt-key" .env; then
    echo "🔐 Generating JWT secret..."
    JWT_SECRET=$(openssl rand -base64 64)
    sed -i "s/your-super-secret-jwt-key-change-this-in-production/$JWT_SECRET/" .env
fi

# Create Docker network
echo "🐳 Creating Docker network..."
docker network create healthcare-compute-network 2>/dev/null || true

# Clone public medical datasets (optional)
echo "📊 Checking for medical datasets..."
if [ ! -d "data/datasets/covidx" ]; then
    echo "💡 Tip: Download COVIDx dataset from https://github.com/lindawangg/COVID-Net"
    echo "   and extract to data/datasets/covidx/"
fi

if [ ! -d "data/datasets/brats" ]; then
    echo "💡 Tip: Download BraTS dataset from https://www.med.upenn.edu/sbia/brats2020.html"
    echo "   and extract to data/datasets/brats/"
fi

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install -r requirements.txt

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
cd dashboard && npm install && cd ..

# Build and start services
echo "🚀 Starting services..."
docker-compose up -d db redis

# Wait for database to be ready
echo "⏳ Waiting for database..."
sleep 10

# Run database migrations
echo "🗄️ Running database migrations..."
docker-compose exec -T db psql -U postgres -d healthcare_compute -c "\dt" || \
docker-compose up -d coordinator && sleep 5

# Initialize smart contracts (if needed)
echo "⛓️ Checking smart contracts..."
if [ ! -f "contracts/.deployed" ]; then
    echo "💡 Run 'npm run deploy:contracts' to deploy smart contracts"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌐 Next steps:"
echo "   1. Edit .env with your configuration"
echo "   2. Run 'docker-compose up' to start all services"
echo "   3. Visit http://localhost:3000 for the dashboard"
echo "   4. Visit http://localhost:8000/docs for API documentation"
echo "   5. Visit http://localhost:3001 for Grafana monitoring"
echo ""
echo "📚 For development:"
echo "   - Coordinator API: http://localhost:8000"
echo "   - Frontend: http://localhost:3000"
echo "   - Grafana: http://localhost:3001 (admin/admin)"
echo "   - Prometheus: http://localhost:9090"
echo ""
echo "🧪 To run tests:"
echo "   npm run test:backend"
echo "   npm run test:frontend"
echo ""