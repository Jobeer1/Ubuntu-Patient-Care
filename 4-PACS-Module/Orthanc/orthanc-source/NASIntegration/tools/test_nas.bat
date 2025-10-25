@echo off
echo Testing NAS connection...
echo.

REM Test NAS connection
net use Z: \\155.235.81.155\Image Archiving /user:admin CH@R!$M@

if %errorlevel% equ 0 (
    echo SUCCESS: NAS connection established!
    echo.
    echo Listing files in the share:
    dir Z:\
    echo.
    echo Disconnecting...
    net use Z: /delete
) else (
    echo FAILED: Could not connect to NAS
    echo Error code: %errorlevel%
)
