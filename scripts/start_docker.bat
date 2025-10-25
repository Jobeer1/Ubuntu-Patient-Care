@echo off
echo 🐳 Starting SA-RIS Docker Services
echo =====================================

cd /d "%~dp0"

echo Starting MySQL database...
docker-compose up -d mysql_ris

echo Starting Redis cache...
docker-compose up -d redis_cache

echo Starting Orthanc PACS...
docker-compose up -d orthanc

echo Starting FHIR server...
docker-compose up -d fhir_server

echo.
echo ⏳ Waiting for services to be ready...
timeout /t 15 /nobreak > nul

echo.
echo ✅ Docker services started!
echo.
echo 🌐 Service URLs:
echo    MySQL: localhost:3306
echo    Redis: localhost:6379
echo    Orthanc PACS: http://localhost:8042
echo    FHIR Server: http://localhost:8080
echo.
echo 🔍 Check status: docker ps
echo 📋 View logs: docker logs [container_name]
echo 🛑 Stop all: docker-compose down
echo.
pause