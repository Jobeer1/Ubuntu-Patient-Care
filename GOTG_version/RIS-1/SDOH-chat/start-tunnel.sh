#!/bin/bash
# Cloudflare Tunnel Setup for SDOH Chat
# Run this to start the tunnel on chat.virons.uk

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "SDOH Chat - Cloudflare Tunnel Setup"
echo "============================================"
echo ""

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "Installing cloudflared..."
    curl -L --output cloudflared.tgz https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.tgz
    tar -xzf cloudflared.tgz
    chmod +x cloudflared
    export PATH="$SCRIPT_DIR:$PATH"
fi

# Start Flask server
echo "[1/2] Starting Flask server on https://localhost:5001..."
python run.py &
FLASK_PID=$!
echo "      Flask PID: $FLASK_PID"

# Wait for Flask to start
sleep 3

# Start Cloudflare tunnel
echo "[2/2] Starting Cloudflare tunnel to chat.virons.uk..."
cloudflared tunnel --no-autoupdate --url https://localhost:5001 chat.virons.uk &
TUNNEL_PID=$!
echo "      Tunnel PID: $TUNNEL_PID"

echo ""
echo "============================================"
echo "✅ SDOH Chat is now live!"
echo ""
echo "📱 Access at: https://chat.virons.uk"
echo ""
echo "Press Ctrl+C to stop both services"
echo "============================================"

# Wait for both processes
wait $FLASK_PID $TUNNEL_PID
