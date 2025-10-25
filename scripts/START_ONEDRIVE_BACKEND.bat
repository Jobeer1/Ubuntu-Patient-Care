@echo off
echo ========================================
echo Starting Flask Backend with OneDrive
echo ========================================
echo.
echo Configuration Status:
echo   Client ID: 42f0676f-4209-4be8-a72d-4102f5e260d8
echo   Client Secret: Ok28Q~encB43... (configured)
echo   Tenant ID: fba55b68-1de1-4d10-a7cc-efa55942f829
echo   Redirect URI: http://localhost:5000/api/nas/onedrive/callback
echo.
echo ========================================
echo.

cd 4-PACS-Module\Orthanc\orthanc-source\NASIntegration\backend

echo Starting Flask backend...
echo Look for: "OneDrive integration registered"
echo.
py app.py
