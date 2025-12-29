@echo off
echo Stopping any running python processes...
taskkill /F /IM python.exe /T
echo.
echo Starting SDOH Chat Server...
start cmd /k "python run.py"
echo.
echo Server started in a new window.
pause
