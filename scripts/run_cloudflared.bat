@echo off
REM Run Cloudflared tunnel + start the Medical Reporting Module app (Windows batch)
REM Usage: Open cmd.exe and run: run_cloudflared.bat

SETLOCAL
SET NO_SSL=1

REM Start the Python app in a new window so it keeps running
start "MedicalReportingApp" cmd /k "py Orthanc\medical-reporting-module\app.py"

REM Wait a few seconds for the app to start
ping -n 4 127.0.0.1 >nul

REM Prefer local cloudflared.exe in repo root
IF EXIST "%~dp0cloudflared.exe" (
	"%~dp0cloudflared.exe" tunnel --url http://localhost:5443
) ELSE (
	ECHO cloudflared.exe not found in repo root or on PATH.
	ECHO Download cloudflared for Windows and place cloudflared.exe in this folder:
	ECHO https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
	ECHO Running cloudflared from PATH (if available)...
	cloudflared tunnel --url http://localhost:5443
)

ENDLOCAL
