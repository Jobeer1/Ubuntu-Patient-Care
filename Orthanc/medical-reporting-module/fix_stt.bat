@echo off
echo ============================================
echo FIXING STT AND FFMPEG ISSUES
echo ============================================

echo Navigating to project directory...
cd /d "C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc\medical-reporting-module"

echo.
echo Installing ffmpeg-python...
python -m pip install ffmpeg-python

echo.
echo Installing additional audio libraries...
python -m pip install soundfile
python -m pip install librosa

echo.
echo Testing Python and pip...
python --version
python -m pip --version

echo.
echo Testing Whisper installation...
python -c "import whisper; print('Whisper version:', whisper.__version__ if hasattr(whisper, '__version__') else 'Available')"

echo.
echo ============================================
echo INSTALLATION COMPLETE!
echo ============================================
echo.
echo Next steps:
echo 1. Restart the application: python app.py
echo 2. Test voice dictation at: https://localhost:5001/voice-demo
echo.
pause
