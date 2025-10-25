@echo off
echo ========================================
echo Cleanup Old Duplicate Folders
echo ========================================
echo.
echo This will remove the old duplicate folders:
echo   - RIS\
echo   - Medical-Billing\
echo.
echo The correct folders are:
echo   - 1-RIS-Module\
echo   - 2-Medical-Billing\
echo.
echo IMPORTANT: Close all terminals and processes first!
echo.
pause

echo.
echo Attempting to remove old folders...
echo.

if exist "RIS" (
    echo Removing RIS folder...
    rmdir /s /q "RIS" 2>nul
    if exist "RIS" (
        echo WARNING: Could not remove RIS folder - it may be in use
        echo Please close all processes and try again
    ) else (
        echo SUCCESS: RIS folder removed
    )
)

if exist "Medical-Billing" (
    echo Removing Medical-Billing folder...
    rmdir /s /q "Medical-Billing" 2>nul
    if exist "Medical-Billing" (
        echo WARNING: Could not remove Medical-Billing folder - it may be in use
        echo Please close all processes and try again
    ) else (
        echo SUCCESS: Medical-Billing folder removed
    )
)

echo.
echo ========================================
echo Cleanup Complete
echo ========================================
echo.
echo If folders could not be removed:
echo 1. Close all terminals and command prompts
echo 2. Stop all Node.js processes
echo 3. Close VS Code or any IDE
echo 4. Run this script again
echo.
echo Or simply use the correct paths going forward:
echo   - 1-RIS-Module\
echo   - 2-Medical-Billing\
echo.
pause
