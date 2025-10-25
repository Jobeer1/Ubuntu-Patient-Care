@echo off
echo Starting Medical Reporting Module on HTTP port 5000 for Cloudflare...
echo.
echo Your HTTPS service can still run on port 5443
echo This HTTP version on port 5000 is for cloudflared tunnel only
echo.
echo After this starts, run in another terminal:
echo   cloudflared tunnel --url http://localhost:5000
echo.

cd /d "%~dp0"

set NO_SSL=true
set PORT=5000
set FLASK_ENV=production

python app.py

pause
