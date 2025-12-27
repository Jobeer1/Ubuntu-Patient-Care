# GOTG SDOH Chat - Production Deployment Guide

## ✅ Your Domain is Live!

**Production URL**: https://chat.virons.uk

This uses a **named Cloudflare Tunnel** connected to your `virons.uk` domain.

---

## 🚀 Quick Start (30 seconds)

### Option 1: One-Click Launch (Windows)
```powershell
cd "c:\Users\parkh\OneDrive\Desktop\05i_DEMO_Reinforcement\qubic-hackathon\GOTG_version\RIS-1\SDOH-chat"
.\start-tunnel-named.bat
```

This will:
1. Start Flask server on `https://localhost:5001`
2. Activate Cloudflare tunnel to `chat.virons.uk`
3. App is live at `https://chat.virons.uk`

### Option 2: Manual Launch (Two Terminals)

**Terminal 1**: Start Flask
```powershell
cd "c:\Users\parkh\OneDrive\Desktop\05i_DEMO_Reinforcement\qubic-hackathon\GOTG_version\RIS-1\SDOH-chat"
python run.py
```

**Terminal 2**: Start Tunnel
```powershell
& "$env:USERPROFILE\cloudflared.exe" tunnel run SDOH-Chat
```

---

## 🔧 Configuration

### Tunnel Details
- **Tunnel Name**: SDOH-Chat
- **Tunnel ID**: 3b788567-25ba-4426-acbb-32229f6bd7e6
- **Domain**: chat.virons.uk
- **Target**: https://localhost:5001
- **Config File**: `~/.cloudflared/config.yml`

### Config File Location
```
C:\Users\parkh\.cloudflared\config.yml
```

### Current Config
```yaml
tunnel: 3b788567-25ba-4426-acbb-32229f6bd7e6
credentials-file: ~/.cloudflared/3b788567-25ba-4426-acbb-32229f6bd7e6.json

ingress:
  - hostname: chat.virons.uk
    service: https://localhost:5001
    tlsSkipVerify: true
  - service: http_status:404
```

---

## 📋 What's Setup

### ✅ Completed
- [x] Cloudflare account linked to virons.uk
- [x] Named tunnel created (SDOH-Chat)
- [x] DNS CNAME record added (chat.virons.uk)
- [x] Tunnel credentials downloaded
- [x] Config file created
- [x] Startup scripts created

### Status Check
```powershell
# List all tunnels
& "$env:USERPROFILE\cloudflared.exe" tunnel list

# Check tunnel status
& "$env:USERPROFILE\cloudflared.exe" tunnel info SDOH-Chat

# View logs
& "$env:USERPROFILE\cloudflared.exe" tunnel logs SDOH-Chat
```

---

## 🌐 For Judges

### Share This Link
```
https://chat.virons.uk
```

The app is live whenever both:
1. Flask server is running (`python run.py`)
2. Cloudflare tunnel is active (`.\start-tunnel-named.bat`)

---

## ⚠️ Important Notes

### Self-Signed Certificate Warning
- The Flask server uses a self-signed certificate
- **This is normal and safe** - Cloudflare's tunnel encrypts the entire connection
- Judges see HTTPS://chat.virons.uk with valid SSL (provided by Cloudflare)
- No certificate warnings when accessing via the domain

### Uptime
- The tunnel is **active only when the scripts are running**
- Stopping the batch file stops the tunnel
- This is fine for demo purposes

### Bandwidth
- Cloudflare Tunnel free tier is rate-limited
- Fine for hackathon demo and judging
- For production, upgrade Cloudflare plan

---

## 🔐 Security

Your setup includes:
- ✅ End-to-end encryption (local → Cloudflare → users)
- ✅ DDoS protection (Cloudflare)
- ✅ WAF protection (Cloudflare)
- ✅ API keys NOT exposed (.gitignore protects config.ini)
- ✅ Zero port forwarding needed

---

## 📞 Troubleshooting

### Tunnel Not Connecting
```powershell
# Check credentials file exists
Test-Path "$env:USERPROFILE\.cloudflared\3b788567-25ba-4426-acbb-32229f6bd7e6.json"

# Verify config is valid
& "$env:USERPROFILE\cloudflared.exe" --version
```

### Flask Server Won't Start
```powershell
# Kill any existing processes
Get-Process python | Stop-Process -Force

# Check port 5001 is free
netstat -ano | findstr :5001
```

### DNS Not Resolving
- DNS changes can take 5-10 minutes to propagate
- Try accessing with `.cloudflare-ipfs.com` URL from Cloudflare dashboard
- Check Cloudflare DNS settings at https://dash.cloudflare.com

---

## 📚 References

- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Cloudflare Dashboard](https://dash.cloudflare.com)
- [Your Domain DNS](https://dash.cloudflare.com/profile/domains)

---

*Last Updated: December 27, 2025*  
*Ready for Hackathon Judging ✅*
