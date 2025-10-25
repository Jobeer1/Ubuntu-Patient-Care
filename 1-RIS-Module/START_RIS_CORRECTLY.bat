@echo off
echo ========================================
echo Starting SA RIS System (Correct Paths)
echo ========================================
echo.

echo Checking paths...
if not exist "1-RIS-Module\sa-ris-backend\package.json" (
    echo ERROR: Cannot find 1-RIS-Module\sa-ris-backend
    echo Please check USE_CORRECT_PATHS.md
    pause
    exit /b 1
)

echo.
echo Starting RIS Backend...
echo Location: 1-RIS-Module\sa-ris-backend
echo.
start "RIS Backend" cmd /k "cd 1-RIS-Module\sa-ris-backend && npm install && npm start"

timeout /t 3 /nobreak >nul

echo.
echo Starting RIS Frontend...
echo Location: 1-RIS-Module\sa-ris-frontend
echo.
start "RIS Frontend" cmd /k "cd 1-RIS-Module\sa-ris-frontend && npm install && npm start"

echo.
echo ========================================
echo Services Starting...
echo ========================================
echo.
echo RIS Backend:  http://localhost:5000
echo RIS Frontend: http://localhost:3000
echo.
echo Check the opened windows for status.
echo.
pause
