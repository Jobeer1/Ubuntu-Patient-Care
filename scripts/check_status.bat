@echo off
echo 🔍 SA-RIS System Status Check
echo ==============================

echo.
echo 🐳 Checking Docker services...
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo.
echo 🌐 Checking service availability...
echo.

echo Testing Backend API (port 3001):
curl -s --max-time 5 http://localhost:3001/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Backend API: RUNNING
) else (
    echo ❌ Backend API: NOT RESPONDING
)

echo.
echo Testing Orthanc PACS (port 8042):
curl -s --max-time 5 http://localhost:8042/system >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Orthanc PACS: RUNNING
) else (
    echo ❌ Orthanc PACS: NOT RESPONDING
)

echo.
echo Testing MySQL Database (port 3306):
docker exec sa_ris_mysql mysqladmin ping -u sa_ris_user -psa_ris_pass_2025 >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ MySQL Database: RUNNING
) else (
    echo ❌ MySQL Database: NOT RESPONDING
)

echo.
echo Testing Redis Cache (port 6379):
docker exec sa_ris_redis redis-cli ping >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Redis Cache: RUNNING
) else (
    echo ❌ Redis Cache: NOT RESPONDING
)

echo.
echo 📋 Service URLs:
echo    Frontend:     http://localhost:3000
echo    Backend API:  http://localhost:3001
echo    Orthanc PACS: http://localhost:8042
echo    MySQL:        localhost:3306
echo    Redis:        localhost:6379
echo.
echo 💡 Tips:
echo    - Start services: start_system.bat
echo    - View logs: docker logs [container_name]
echo    - Restart service: docker-compose restart [service_name]
echo.
pause