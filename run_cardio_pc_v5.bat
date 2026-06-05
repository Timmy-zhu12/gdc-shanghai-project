@echo off
setlocal
cd /d "%~dp0"

echo [1/4] Preparing local Python environment...
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>nul
  if %errorlevel%==0 (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
)
if errorlevel 1 (
  echo.
  echo Failed to create the local Python environment. Install Python 3.10 or newer, then retry.
  pause
  exit /b 1
)

if not exist "config.json" (
  copy /Y "config.example.json" "config.json" >nul
)

echo [2/4] Checking installed dependencies...
".venv\Scripts\python.exe" -c "import numpy, PIL, pydicom, imageio, pandas, sklearn, joblib" >nul 2>nul
if errorlevel 1 (
  echo.
  echo Missing Python dependencies.
  echo Run install_deps.bat once, then start this app again.
  echo This launcher does not run pip silently, so it will not appear stuck during package installation.
  pause
  exit /b 1
)

echo [3/4] Starting CardioConsult PC V5 in anti-hang default mode...
echo [4/4] The UI should open shortly. Default inference mode skips GGUF unless you choose Gemma4 enhancement.
".venv\Scripts\python.exe" app.py
if errorlevel 1 (
  echo.
  echo CardioConsult PC V5 failed to start. See the error above.
  pause
  exit /b 1
)
endlocal
