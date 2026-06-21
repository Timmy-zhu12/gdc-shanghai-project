@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" tools\submission_preflight.py
) else (
  python tools\submission_preflight.py
)
