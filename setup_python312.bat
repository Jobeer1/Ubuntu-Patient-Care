@echo off
cd /d "C:\Users\User\Desktop\Joleen USB\SDOH-chat"
echo Installing Python 3.12 dependencies...
call venv312\Scripts\activate.bat
pip install -r requirements.txt
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install openai-whisper
pause
