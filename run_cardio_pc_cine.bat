@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  call "%~dp0install_deps.bat"
)
if not exist "exports" mkdir exports
".venv\Scripts\python.exe" app.py
endlocal
