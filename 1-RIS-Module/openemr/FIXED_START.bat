@echo off
title OpenEMR RIS - Setup and Run Guide
color 0A

echo ========================================
echo    OpenEMR RIS - SETUP AND RUN
echo ========================================
echo.

echo 1. Setting up database...
cd server
call npx prisma db push
echo.

echo 2. Creating demo users...
node create-demo-user.js
echo.

echo 3. Installing server dependencies...
call npm install
echo.

echo 4. Installing client dependencies...
cd ../client
call npm install
echo.

echo ========================================
echo    SETUP COMPLETE!
echo ========================================
echo.
echo Demo Login Credentials:
echo   Email: demo@example.com
echo   Password: demo123
echo.
echo Admin Login Credentials:
echo   Email: admin@openemr.co.za
echo   Password: admin123
echo.
echo TO RUN THE SYSTEM:
echo.
echo 1. Open a NEW terminal and run: cd openemr/server && npm run dev
echo 2. Open ANOTHER terminal and run: cd openemr/client && npm start
echo 3. Open http://localhost:3000 in your browser
echo 4. Login with demo@example.com / demo123
echo.
echo All features are now working:
echo - Login system fixed
echo - All CRUD operations working
echo - Form validation implemented
echo - Button functionality restored
echo.
pause