@echo off
echo ==========================================
echo      Setting up Local Micro-Agent
echo           (Gemma 2B via Ollama)
echo ==========================================
echo.

REM Try to find Ollama in default user path
set "OLLAMA_PATH=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"

IF NOT EXIST "%OLLAMA_PATH%" (
    echo [ERROR] Ollama executable not found at:
    echo %OLLAMA_PATH%
    echo.
    echo Please ensure Ollama is installed.
    pause
    exit /b
)

echo [INFO] Ollama found. Pulling gemma:2b model...
echo.
"%OLLAMA_PATH%" pull gemma:2b

echo.
echo ==========================================
echo [SUCCESS] Model installed!
echo The Forge will now use this model if the internet goes down.
echo ==========================================
pause
