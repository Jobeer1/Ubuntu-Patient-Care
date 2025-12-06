#!/bin/bash

# MCP Server Installation Script
# Ubuntu Patient Care System

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║           MCP Server Installation                         ║"
echo "║           Ubuntu Patient Care System                      ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $python_version found"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
echo "✓ Virtual environment created"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Generate secret keys
echo "Generating secret keys..."
python scripts/generate_secrets.py > .secrets.txt
echo "✓ Secret keys generated (saved to .secrets.txt)"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  Please edit .env file and add your OAuth credentials"
else
    echo "✓ .env file already exists"
fi
echo ""

# Create logs directory
echo "Creating logs directory..."
mkdir -p logs
echo "✓ Logs directory created"
echo ""

# Setup database
echo "Setting up database..."
python scripts/setup_database.py
echo "✓ Database setup complete"
echo ""

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║           Installation Complete!                          ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your OAuth credentials"
echo "2. Run: python run.py"
echo "3. Visit: http://localhost:8080"
echo "4. Test: http://localhost:8080/test"
echo ""
echo "For quick start guide, see: QUICKSTART.md"
echo ""
