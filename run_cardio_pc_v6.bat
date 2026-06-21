@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" app.py
) else (
  python app.py
)
endlocal
