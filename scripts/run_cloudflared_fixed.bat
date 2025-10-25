@echo off
echo Starting Cloudflare Tunnel for Medical Reporting Module...
echo.
echo Your service is running on https://localhost:5443
echo Cloudflare will create a public URL that proxies to your local service
echo.

cd /d "C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\4-PACS-Module\Orthanc\medical-reporting-module"

REM Use http://localhost:5443 instead of https://localhost:5443
REM This avoids TLS handshake issues between cloudflared and your self-signed cert
cloudflared tunnel --url http://localhost:5443

pause
