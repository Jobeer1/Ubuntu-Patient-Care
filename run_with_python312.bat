@echo off
REM SDOH Chat - Flask Server Launcher (Python 3.12)
cd /d "%~dp0"
echo Activating Python 3.12 virtual environment...
call venv312\Scripts\activate.bat
echo Starting SDOH Chat Flask Server...
python run.py
pause
