@echo off
echo ========================================
echo Restarting Flask Backend with OneDrive
echo ========================================
echo.
echo Press Ctrl+C in the backend terminal to stop it first!
echo Then run this script.
echo.
pause

cd 4-PACS-Module\Orthanc\orthanc-source\NASIntegration\backend
echo Starting Flask backend with OneDrive integration...
py app.py
