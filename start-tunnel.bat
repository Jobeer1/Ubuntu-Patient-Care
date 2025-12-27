@echo off
REM Cloudflare Tunnel Setup for SDOH Chat
REM Run this to start the tunnel on chat.virons.uk

cd /d "c:\Users\parkh\OneDrive\Desktop\05i_DEMO_Reinforcement\qubic-hackathon\GOTG_version\RIS-1\SDOH-chat"

REM Start the Flask server in a new window
start "SDOH Chat Flask Server" cmd /k "python run.py"

REM Wait a moment for Flask to start
timeout /t 3 /nobreak

REM Start the Cloudflare tunnel
start "Cloudflare Tunnel" cmd /k "%USERPROFILE%\cloudflared.exe tunnel --no-autoupdate --url https://localhost:5001 chat.virons.uk"

echo.
echo ============================================
echo SDOH Chat is now live!
echo.
echo URL: https://chat.virons.uk
echo.
echo Both windows will close when you close them.
echo ============================================
