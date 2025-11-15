#!/bin/bash
#
# MCP Agent Installer - Linux/macOS
#
# Installs the per-subnet agent as a systemd service.
#
# Author: Kiro Team
# Task: K2.6
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AGENT_USER="mcp-agent"
INSTALL_DIR="/opt/mcp-agent"
CONFIG_DIR="/etc/mcp-agent"
DATA_DIR="/var/lib/mcp-agent"
LOG_DIR="/var/log/mcp-agent"
SYSTEMD_DIR="/etc/systemd/system"

echo -e "${GREEN}MCP Agent Installer${NC}"
echo "================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Please run: sudo bash install.sh"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    echo "Detected OS: $OS"
else
    echo -e "${RED}Error: Cannot detect OS${NC}"
    exit 1
fi

# Check Python version
echo ""
echo "Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo "Python version: $PYTHON_VERSION"
else
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Install dependencies
echo ""
echo "Installing dependencies..."
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    apt-get update
    apt-get install -y python3-pip python3-venv
elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
    yum install -y python3-pip
elif [ "$OS" = "fedora" ]; then
    dnf install -y python3-pip
else
    echo -e "${YELLOW}Warning: Unknown OS, skipping package installation${NC}"
fi

# Create agent user
echo ""
echo "Creating agent user..."
if id "$AGENT_USER" &>/dev/null; then
    echo "User $AGENT_USER already exists"
else
    useradd -r -s /bin/false -d "$DATA_DIR" "$AGENT_USER"
    echo "Created user: $AGENT_USER"
fi

# Create directories
echo ""
echo "Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR/certs"

# Copy files
echo ""
echo "Installing agent files..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"

# Install Python dependencies
echo ""
echo "Installing Python packages..."
pip install --upgrade pip
pip install flask cryptography paramiko pysmb requests pyyaml

# Copy config
echo ""
echo "Installing configuration..."
if [ -f "$CONFIG_DIR/config.json" ]; then
    echo "Config already exists, skipping"
else
    cp "$INSTALL_DIR/config.json" "$CONFIG_DIR/config.json"
    echo "Installed default config"
fi

# Generate agent ID
AGENT_ID="agent-$(openssl rand -hex 8)"
sed -i "s/agent-subnet-1/$AGENT_ID/" "$CONFIG_DIR/config.json"
echo "Generated agent ID: $AGENT_ID"

# Set permissions
echo ""
echo "Setting permissions..."
chown -R "$AGENT_USER:$AGENT_USER" "$INSTALL_DIR"
chown -R "$AGENT_USER:$AGENT_USER" "$CONFIG_DIR"
chown -R "$AGENT_USER:$AGENT_USER" "$DATA_DIR"
chown -R "$AGENT_USER:$AGENT_USER" "$LOG_DIR"
chmod 600 "$CONFIG_DIR/config.json"

# Create systemd service
echo ""
echo "Creating systemd service..."
cat > "$SYSTEMD_DIR/mcp-agent.service" << EOF
[Unit]
Description=MCP Agent Service
After=network.target

[Service]
Type=simple
User=$AGENT_USER
Group=$AGENT_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/service.py --config $CONFIG_DIR/config.json
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/agent.log
StandardError=append:$LOG_DIR/agent-error.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable and start service
echo ""
echo "Starting agent service..."
systemctl enable mcp-agent
systemctl start mcp-agent

# Wait for service to start
sleep 2

# Check status
if systemctl is-active --quiet mcp-agent; then
    echo -e "${GREEN}✓ Agent service is running${NC}"
else
    echo -e "${RED}✗ Agent service failed to start${NC}"
    echo "Check logs: journalctl -u mcp-agent -n 50"
    exit 1
fi

# Health check
echo ""
echo "Running health check..."
sleep 1
if curl -s http://localhost:8444/agent/health > /dev/null; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${YELLOW}⚠ Health check failed (service may still be starting)${NC}"
fi

# Print summary
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Agent ID: $AGENT_ID"
echo "Install directory: $INSTALL_DIR"
echo "Config directory: $CONFIG_DIR"
echo "Data directory: $DATA_DIR"
echo "Log directory: $LOG_DIR"
echo ""
echo "Service commands:"
echo "  Start:   systemctl start mcp-agent"
echo "  Stop:    systemctl stop mcp-agent"
echo "  Status:  systemctl status mcp-agent"
echo "  Logs:    journalctl -u mcp-agent -f"
echo ""
echo "Health check: curl http://localhost:8444/agent/health"
echo ""
echo "Next steps:"
echo "1. Edit config: $CONFIG_DIR/config.json"
echo "2. Configure adapters for your environment"
echo "3. Restart service: systemctl restart mcp-agent"
echo ""
