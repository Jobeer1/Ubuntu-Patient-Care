@echo off
echo ========================================
echo Starting Complete SA RIS System
echo ========================================
echo.

echo [1/5] Starting OpenEMR (EHR/EMR)...
start "OpenEMR" cmd /k "cd 1-RIS-Module\openemr && docker-compose up"
timeout /t 5 /nobreak >nul

echo [2/5] Starting MCP Medical Server...
start "MCP Server" cmd /k "cd mcp-medical-server && py server.py"
timeout /t 3 /nobreak >nul

echo [3/5] Starting RIS Backend...
start "RIS Backend" cmd /k "cd 1-RIS-Module\sa-ris-backend && npm start"
timeout /t 5 /nobreak >nul

echo [4/5] Starting RIS Frontend...
start "RIS Frontend" cmd /k "cd 1-RIS-Module\sa-ris-frontend && npm start"
timeout /t 3 /nobreak >nul

echo [5/5] Note: Start Orthanc manually if needed
echo.
echo ========================================
echo All Services Starting!
echo ========================================
echo.
echo Access Points:
echo   RIS Frontend:  http://localhost:3000
echo   RIS Backend:   http://localhost:3001
echo   OpenEMR:       http://localhost:8080
echo   Orthanc:       http://localhost:8042 (manual start)
echo.
echo Check the opened windows for status.
echo.
pause
