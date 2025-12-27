@echo off
REM Production Cloudflare Tunnel Setup for SDOH Chat
REM Uses named tunnel pointing to chat.virons.uk
REM Requires: cloudflared config file

cd /d "c:\Users\parkh\OneDrive\Desktop\05i_DEMO_Reinforcement\qubic-hackathon\GOTG_version\RIS-1\SDOH-chat"

echo.
echo ================================================
echo SDOH Chat - Production Tunnel Setup
echo ================================================
echo.

REM Start the Flask server in a new window
echo [1/2] Starting Flask server...
start "SDOH Chat Flask Server" cmd /k "python run.py"

REM Wait a moment for Flask to start
timeout /t 3 /nobreak

REM Start the Cloudflare tunnel with named config
echo [2/2] Starting Cloudflare tunnel...
start "Cloudflare Tunnel - Production" cmd /k "%USERPROFILE%\cloudflared.exe tunnel run SDOH-Chat"

echo.
echo ================================================
echo SDOH Chat is now LIVE!
echo.
echo URL: https://chat.virons.uk
echo.
echo Tunnel Config: cloudflared-config.yml
echo Tunnel Name: SDOH-Chat
echo Tunnel ID: 3b788567-25ba-4426-acbb-32229f6bd7e6
echo.
echo Both windows will stay open until you close them.
echo ================================================
echo.
