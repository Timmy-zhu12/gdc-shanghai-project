@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_llama_server_v4.ps1"
if errorlevel 1 (
  echo.
  echo Fast server mode could not start. The app will still open and use CLI or rule fallback.
)
call "%~dp0run_cardio_pc_v4.bat"
endlocal
