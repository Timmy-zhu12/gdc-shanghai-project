@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_llama_server_v4.ps1"
if errorlevel 1 (
  echo.
  echo Failed to start CardioConsult Gemma4 llama-server. Check models\gemma-4-4b-it-Q4_K_M.gguf or the legacy model path.
  pause
)
endlocal
