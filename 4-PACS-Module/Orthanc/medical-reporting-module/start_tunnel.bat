@echo off
echo ========================================
echo Medical Reporting Module - Cloudflare Tunnel Setup
echo ========================================
echo.
echo This will start an HTTP version on port 8080 for Cloudflare tunnel
echo Your HTTPS version will continue running on port 5443
echo.

cd /d "%~dp0"

REM Start HTTP version on port 8080 for cloudflared
start "Medical Reporting HTTP" cmd /k "set NO_SSL=true && set PORT=8080 && set FLASK_ENV=production && python app.py"

REM Wait for server to start
timeout /t 5 /nobreak

REM Start cloudflared tunnel
echo.
echo Starting Cloudflare tunnel...
echo.
cloudflared tunnel --url http://localhost:8080

pause
