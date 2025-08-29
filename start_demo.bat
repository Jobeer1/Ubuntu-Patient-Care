@echo off
echo 🏥 Ubuntu Patient Care - Hackathon Demo Launcher
echo.
echo Setting up the system for demo...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.8+ first.
    pause
    exit /b 1
)

REM Install basic requirements
echo 📦 Installing requirements...
pip install flask flask-cors sqlite3

REM Create necessary directories
mkdir "Orthanc\medical-reporting-module\models\whisper\cache" 2>nul

REM Start the system
echo 🚀 Starting Ubuntu Patient Care System...
echo.
echo 🌐 The system will start on http://localhost:5000
echo 📋 Demo credentials will be displayed in the console
echo.
cd Orthanc
python medical-reporting-module\core\app_factory.py

pause
