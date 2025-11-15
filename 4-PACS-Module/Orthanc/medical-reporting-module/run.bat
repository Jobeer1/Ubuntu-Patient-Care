@echo off
REM Medical Reporting Module - HTTPS Launcher
REM This script ensures HTTPS is enabled on port 5443

cd /d "%~dp0"

REM Clear any existing NO_SSL variable
set NO_SSL=

REM Set HTTPS configuration
set PORT=5443
set HOST=0.0.0.0
set FLASK_ENV=development

echo ========================================
echo Medical Reporting Module - HTTPS Mode
echo ========================================
echo.
echo Starting on: https://localhost:5443
echo.
echo Note: Browser security warning is normal for self-signed certificates
echo Click 'Advanced' and 'Proceed to localhost' to continue
echo.
echo Press CTRL+C to stop the server
echo ========================================
echo.

python app.py

pause
