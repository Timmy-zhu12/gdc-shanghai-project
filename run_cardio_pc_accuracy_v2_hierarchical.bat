@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  call "%~dp0install_deps.bat"
)
".venv\Scripts\python.exe" -c "import numpy, PIL, pydicom, imageio" >nul 2>nul
if errorlevel 1 (
  call "%~dp0install_deps.bat"
)
if not exist "exports" mkdir exports
".venv\Scripts\python.exe" app.py
if errorlevel 1 (
  echo.
  echo CardioConsult V2 failed to start. See the error above.
  pause
)
endlocal
