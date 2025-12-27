# Cloudflare Tunnel Setup Guide

## Overview
This guide sets up a secure Cloudflare Tunnel that exposes your SDOH Chat application to the internet at `chat.virons.uk`.

## What is a Cloudflare Tunnel?
Cloudflare Tunnel creates a secure, encrypted connection from your local machine to Cloudflare's global network. This allows you to:
- ✅ Expose localhost to the internet without port forwarding
- ✅ Get instant SSL/TLS encryption
- ✅ Avoid DDoS attacks with Cloudflare's protection
- ✅ Use a custom domain (chat.virons.uk)

## Prerequisites
- `cloudflared` executable (automatically downloaded on first run)
- Python Flask server running on `https://localhost:5001`
- Cloudflare account with `chat.virons.uk` domain configured

## Quick Start

### Windows
```powershell
# Navigate to the SDOH-chat directory
cd c:\Users\parkh\OneDrive\Desktop\05i_DEMO_Reinforcement\qubic-hackathon\GOTG_version\RIS-1\SDOH-chat

# Run the tunnel startup script
.\start-tunnel.bat
```

### Linux/Mac
```bash
# Navigate to the SDOH-chat directory
cd ~/SDOH-chat

# Make the script executable
chmod +x start-tunnel.sh

# Run the tunnel startup script
./start-tunnel.sh
```

## What Happens
1. **Flask Server Starts**: Runs on `https://localhost:5001` with HTTPS enabled
2. **Cloudflare Tunnel Starts**: Creates secure tunnel to Cloudflare's network
3. **Domain Routing**: Traffic to `chat.virons.uk` is routed to `https://localhost:5001`
4. **Live Demo**: App becomes accessible at `https://chat.virons.uk`

## Manual Setup (Advanced)

If you prefer to manage the processes separately:

### Terminal 1: Start Flask
```bash
python run.py
# Runs on https://localhost:5001
```

### Terminal 2: Start Tunnel
```bash
cloudflared tunnel --no-autoupdate --url https://localhost:5001 chat.virons.uk
```

## Verification
1. Open https://chat.virons.uk in your browser
2. You should see the SDOH Chat dashboard
3. Check the console for any errors
4. Microphone access should work without HTTPS warnings

## Troubleshooting

### Tunnel Connection Failed
```
Error: Failed to connect to Cloudflare
```
**Solution**: Verify that `chat.virons.uk` is configured in your Cloudflare DNS settings.

### Port 5001 Already in Use
```
Error: Address already in use
```
**Solution**: Kill the existing Flask process:
```powershell
# Windows
Get-Process python | Stop-Process -Force

# Linux/Mac
pkill -f "python run.py"
```

### HTTPS Certificate Warning
The Flask server uses a self-signed certificate (normal). Cloudflare's tunnel encrypts the connection end-to-end.

### Silero TTS Not Loading
If you see "No module named 'omegaconf'":
```bash
pip install omegaconf
```

## Security Notes
- ⚠️ This tunnel exposes your local machine to the internet
- ✅ All traffic is encrypted end-to-end (local → Cloudflare → user)
- ✅ Cloudflare protects against DDoS and other attacks
- ✅ The tunnel terminates when the process stops
- 🔒 API keys are NOT exposed (config.ini is in .gitignore)

## For Judges
Share this link: **https://chat.virons.uk**

The demo will be live as long as:
1. The Flask server is running
2. The Cloudflare tunnel is active
3. Both are running on the same machine

---

*Last Updated: December 27, 2025*
