@echo off
REM Temporary Cloudflare Tunnel Setup for SDOH Chat
REM Uses temporary trycloudflare.com URL (for testing)

cd /d "c:\Users\parkh\OneDrive\Desktop\05i_DEMO_Reinforcement\qubic-hackathon\GOTG_version\RIS-1\SDOH-chat"

echo.
echo ================================================
echo SDOH Chat - Temporary Tunnel Setup
echo ================================================
echo.

REM Start the Flask server in a new window
echo [1/2] Starting Flask server...
start "SDOH Chat Flask Server" cmd /k "python run.py"

REM Wait a moment for Flask to start
timeout /t 3 /nobreak

REM Start the Cloudflare tunnel (temporary)
echo [2/2] Starting temporary Cloudflare tunnel...
echo.
echo Note: A new URL will be generated. Share it with judges.
echo.
start "Cloudflare Tunnel - Temporary" cmd /k "%USERPROFILE%\cloudflared.exe tunnel --no-autoupdate --url https://localhost:5001"

echo.
echo ================================================
echo SDOH Chat is starting...
echo.
echo Check the tunnel window for your temporary URL:
echo  https://*.trycloudflare.com
echo.
echo This URL changes on each restart - that's normal!
echo ================================================
echo.
