@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Preparing local Python environment...
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

echo [2/3] Upgrading pip metadata with bounded network waits...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --timeout 60 --retries 2 --upgrade pip
if errorlevel 1 (
  echo.
  echo Pip upgrade failed or timed out. Check network/proxy settings, then rerun install_deps.bat.
  pause
  exit /b 1
)

echo [3/3] Installing CardioConsult dependencies with bounded network waits...
".venv\Scripts\python.exe" -m pip install -r requirements.txt --disable-pip-version-check --timeout 60 --retries 2
if errorlevel 1 (
  echo.
  echo Dependency installation failed or timed out. Check network/proxy settings, then rerun install_deps.bat.
  pause
  exit /b 1
)

echo.
echo Dependencies are ready. You can now run run_preflight.bat or run_ui.bat.
endlocal
