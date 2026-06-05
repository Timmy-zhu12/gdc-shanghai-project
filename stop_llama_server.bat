@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_llama_server.ps1" -Port 8088
if errorlevel 1 (
  echo.
  echo Failed to stop CardioConsult llama-server. See the message above.
  pause
)
endlocal
