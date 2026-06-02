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
".venv\Scripts\python.exe" -m pip install -r requirements.txt --disable-pip-version-check
if errorlevel 1 (
  echo.
  echo Dependency installation failed.
  pause
)
endlocal
