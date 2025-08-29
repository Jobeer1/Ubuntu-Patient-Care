@echo off
REM Helper to run backend without Flask auto-reloader
SETLOCAL
echo Starting backend (no reloader)...
py -3 -c "import os; os.environ['FLASK_ENV']='production'; import app; app.run(debug=False, use_reloader=False)"
ENDLOCAL
