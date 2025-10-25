@echo off
REM MCP Server Installation Script for Windows
REM Ubuntu Patient Care System

echo ===============================================================
echo.
echo            MCP Server Installation
echo            Ubuntu Patient Care System
echo.
echo ===============================================================
echo.

REM Check Python
echo Checking Python version...
python --version
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)
echo.

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv
echo Virtual environment created
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Install dependencies
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo Dependencies installed
echo.

REM Generate secret keys
echo Generating secret keys...
python scripts\generate_secrets.py > .secrets.txt
echo Secret keys generated (saved to .secrets.txt)
echo.

REM Create .env file
if not exist .env (
    echo Creating .env file...
    copy .env.example .env
    echo .env file created
    echo.
    echo WARNING: Please edit .env file and add your OAuth credentials
) else (
    echo .env file already exists
)
echo.

REM Create logs directory
echo Creating logs directory...
if not exist logs mkdir logs
echo Logs directory created
echo.

REM Setup database
echo Setting up database...
python scripts\setup_database.py
echo Database setup complete
echo.

echo ===============================================================
echo.
echo            Installation Complete!
echo.
echo ===============================================================
echo.
echo Next steps:
echo 1. Edit .env file with your OAuth credentials
echo 2. Run: python run.py
echo 3. Visit: http://localhost:8080
echo 4. Test: http://localhost:8080/test
echo.
echo For quick start guide, see: QUICKSTART.md
echo.
pause
