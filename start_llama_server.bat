@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_llama_server_v4.ps1" -Visible
if errorlevel 1 (
  echo.
  echo Failed to start CardioConsult Gemma4 server. See the error above.
  pause
)
endlocal
