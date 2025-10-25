@echo off
echo Connecting to NAS...

REM Map the NAS drive
net use Z: "\\155.235.81.155\Image Archiving" /user:admin CH@R!$M@

if %errorlevel% neq 0 (
    echo FAILED: Could not connect to NAS
    goto :cleanup
)

echo SUCCESS: Connected to NAS
echo.
echo Scanning for DICOM files...

REM Count DICOM files
dir Z:\*.dcm /s /b | find /c ".dcm" > dicom_count.txt
set /p DICOM_COUNT=<dicom_count.txt

echo Found %DICOM_COUNT% .dcm files

REM List some sample files
echo.
echo Sample DICOM files:
dir Z:\*.dcm /b | head -10

REM Export full file list
echo.
echo Exporting full file list...
dir Z:\*.dcm /s /b > nas_dicom_files.txt

echo File list exported to nas_dicom_files.txt

:cleanup
REM Disconnect the drive
net use Z: /delete /y >nul 2>&1
echo Disconnected from NAS
