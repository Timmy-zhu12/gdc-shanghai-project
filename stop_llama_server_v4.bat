@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'llama-server.exe' -and $_.CommandLine -like '*cardioconsult-gemma4*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('Stopped llama-server PID ' + $_.ProcessId) }"
endlocal
