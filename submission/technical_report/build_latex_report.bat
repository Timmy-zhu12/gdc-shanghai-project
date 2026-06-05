@echo off
setlocal
cd /d "%~dp0"

set "PY=%~dp0..\..\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

"%PY%" build_latex_report.py --compile
if errorlevel 1 (
  echo.
  echo LaTeX report source was generated, but PDF compilation did not complete.
  echo Install TeX Live or MiKTeX with xelatex, then run this script again.
  exit /b 1
)

echo.
echo Done.
