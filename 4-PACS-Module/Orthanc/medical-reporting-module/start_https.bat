@echo off
REM Start Medical Reporting Module on HTTPS port 5443
cd /d "%~dp0"

REM Ensure NO_SSL is NOT set (or set to 0)
set NO_SSL=0
set PORT=5443
set FLASK_ENV=development

echo Starting Medical Reporting Module on HTTPS port 5443...
echo.
echo Note: You may see a browser security warning for the self-signed certificate.
echo This is normal for development. Click 'Advanced' and 'Proceed' to continue.
echo.

python app.py

pause
