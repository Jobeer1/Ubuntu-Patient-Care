@echo off
echo 🧪 Testing SA-RIS Backend Server
echo ================================

cd /d "%~dp0"

echo 📦 Installing dependencies if needed...
if not exist node_modules (
    npm install
)

echo.
echo 🚀 Starting backend server for testing...
start cmd /k "npm start"

echo.
echo ⏳ Waiting for server to start...
timeout /t 5 /nobreak > nul

echo.
echo 🔍 Testing backend endpoints...
echo.

echo Testing health endpoint:
curl -s http://localhost:3001/health | findstr "healthy" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Health check: PASS
) else (
    echo ❌ Health check: FAIL
)

echo.
echo Testing DICOM endpoint:
curl -s http://localhost:3001/api/dicom/studies >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ DICOM endpoint: PASS
) else (
    echo ❌ DICOM endpoint: FAIL
)

echo.
echo Testing FHIR endpoint:
curl -s http://localhost:3001/api/fhir/patients >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ FHIR endpoint: PASS
) else (
    echo ❌ FHIR endpoint: FAIL
)

echo.
echo 🎉 Backend testing complete!
echo.
echo 🌐 Backend should be running at: http://localhost:3001
echo 📊 Check the server terminal window for detailed logs
echo 🛑 Close the server terminal window to stop the backend
echo.
pause