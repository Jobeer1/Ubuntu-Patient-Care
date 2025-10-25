@echo off
echo Starting Medical Reporting Module WITHOUT SSL for Cloudflare Tunnel...
echo.
echo This will start the service on http://localhost:5443
echo Then run cloudflared in another terminal with:
echo   cloudflared tunnel --url http://localhost:5443
echo.

cd /d "%~dp0"

REM Set NO_SSL environment variable to disable HTTPS
set NO_SSL=true
set PORT=5443
set FLASK_ENV=production

python app.py

pause
