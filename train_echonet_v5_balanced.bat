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
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt >nul
".venv\Scripts\python.exe" tools\train_echonet_v5.py --train-limit 600 --val-limit 160 --test-limit 160 --max-frames 16
if errorlevel 1 (
  echo.
  echo V5 EchoNet balanced training failed. See the error above.
  pause
)
endlocal
