@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" tools\gemma_emergency_stop_smoke.py
) else (
  python tools\gemma_emergency_stop_smoke.py
)
