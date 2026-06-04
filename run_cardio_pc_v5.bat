@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>nul
  if %errorlevel%==0 (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
)
if not exist "config.json" (
  copy /Y "config.example.json" "config.json" >nul
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt >nul
".venv\Scripts\python.exe" app.py
if errorlevel 1 (
  echo.
  echo CardioConsult PC V5 failed to start. See the error above.
  pause
)
endlocal
