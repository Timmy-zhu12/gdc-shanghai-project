@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" app.py --self-test-rule-only
) else (
  python app.py --self-test-rule-only
)
