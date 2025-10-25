@echo off
echo 🇿🇦 South African Radiology Information System - Startup Script
echo ========================================================================

echo.
echo 🐳 Starting Docker containers...
cd /d "%~dp0sa-ris-backend"
docker-compose up -d

echo.
echo ⏳ Waiting for Docker containers to be ready...
timeout /t 10 /nobreak > nul

echo.
echo 📦 Installing backend dependencies...
if not exist node_modules (
    npm install
) else (
    echo Backend node modules already installed.
)

echo.
echo 🚀 Starting backend server...
start cmd /k "npm start"

echo.
echo 📦 Installing frontend dependencies...
cd /d "%~dp0sa-ris-frontend"
if not exist node_modules (
    npm install
) else (
    echo Frontend node modules already installed.
)

echo.
echo 🚀 Starting frontend development server...
start cmd /k "npm start"

echo.
echo ✅ System startup complete!
echo.
echo 🌐 Access your application at:
echo    Frontend: http://localhost:3000
echo    Backend API: http://localhost:3001
echo    Orthanc PACS: http://localhost:8042
echo    FHIR Server: https://fhir.sacoronavirus.co.za/r4
echo.
echo 📋 Test Instructions:
echo 1. Open http://localhost:3000 in your browser
echo 2. Check backend health: http://localhost:3001/health
echo 3. Test the South African UI theme and animations
echo 4. Try the language switcher (EN/AF/ZU)
echo 5. Check browser developer tools for FHIR API calls
echo 6. Upload DICOM files to test Orthanc integration
echo.
echo 🔍 To monitor logs:
echo    Backend: Check the backend terminal window
echo    Frontend: Check browser console (F12)
echo    Docker: docker logs sa-ris-backend
echo.
echo 🛑 To stop: docker-compose down (from sa-ris-backend directory)
echo.
pause