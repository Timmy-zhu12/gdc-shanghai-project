@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if exist "%~dp0.venv\Scripts\python.exe" (
  set PY="%~dp0.venv\Scripts\python.exe"
) else (
  set PY=python
)
%PY% src\analyze_media_cli.py --input "%~dp0samples\A4C_ED_synthetic.png" --input "%~dp0samples\A4C_ES_synthetic.png" --max-loaded-frames 48 --decode-timeout 6 --max-input-files 12 --decode-workers 4 --out outputs\media_smoke_result.json
