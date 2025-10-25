@echo off
echo ========================================
echo Starting Flask Backend with Cloud Storage
echo ========================================
echo.
echo Configuration Status:
echo.
echo OneDrive:
echo   Client ID: 42f0676f-4209-4be8-a72d-4102f5e260d8
echo   Status: READY
echo.
echo Google Drive:
echo   Client ID: 807845595525-sl5078kmp1kd22v9aohudukkhsqi3rrn
echo   Status: READY
echo.
echo ========================================
echo.
echo After backend starts:
echo   1. OneDrive Setup: http://localhost:5000/api/nas/onedrive/setup
echo   2. Google Drive Setup: http://localhost:5000/api/nas/gdrive/setup
echo.
echo ========================================
echo.

cd 4-PACS-Module\Orthanc\orthanc-source\NASIntegration\backend

echo Starting Flask backend...
echo Look for:
echo   - OneDrive integration registered
echo   - Google Drive integration registered
echo.
py app.py
