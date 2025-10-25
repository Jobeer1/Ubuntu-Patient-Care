@echo off
echo 🚀 Starting SA-RIS Backend Server
echo ===================================

cd /d "%~dp0"

echo 📦 Installing dependencies...
if not exist node_modules (
    npm install
) else (
    echo Dependencies already installed.
)

echo.
echo 🔧 Checking environment configuration...
if not exist .env (
    echo ⚠️  .env file not found. Copying from .env.example...
    copy .env.example .env
    echo ✅ Created .env file. Please update with your configuration.
    echo.
    echo Press any key to continue with default settings...
    pause > nul
)

echo.
echo 🚀 Starting backend server...
npm start