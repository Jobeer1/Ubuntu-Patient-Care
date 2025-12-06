@echo off
cd /d "C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\4-PACS-Module\Orthanc\medical-reporting-module"
setlocal enabledelayedexpansion
set "PORT=5000"
set "NO_SSL=1"
python app.py
