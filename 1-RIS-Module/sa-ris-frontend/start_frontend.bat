@echo off
echo 🌐 Starting SA-RIS Frontend
echo ============================

cd /d "%~dp0"

echo 📦 Installing dependencies...
if not exist node_modules (
    npm install
) else (
    echo Dependencies already installed.
)

echo.
echo 🚀 Starting development server...
npm start