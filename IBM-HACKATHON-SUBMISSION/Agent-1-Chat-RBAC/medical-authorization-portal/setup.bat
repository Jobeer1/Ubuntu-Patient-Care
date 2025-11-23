@echo off
REM Medical Authorization Portal - Setup Script
REM ============================================

echo.
echo Installing dependencies...
echo.

pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install dependencies
    exit /b 1
)

echo.
echo SUCCESS: All dependencies installed!
echo.
echo To start the application, run:
echo   python app.py
echo.
echo Then open your browser to: http://localhost:5000
echo.
pause
