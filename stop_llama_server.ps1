param(
  [int]$Port = 8088
)

$ErrorActionPreference = "SilentlyContinue"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$targets = @()

$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
foreach ($listener in $listeners) {
  $process = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
  if ($process -and $process.ProcessName -like "llama-server*") {
    $targets += $process
  }
}

$targets += Get-Process -Name "llama-server" -ErrorAction SilentlyContinue | Where-Object {
  -not $_.Path -or $_.Path.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)
}

$targets = $targets | Sort-Object Id -Unique

if (-not $targets -or $targets.Count -eq 0) {
  Write-Host "No CardioConsult llama-server process found on port $Port."
  exit 0
}

foreach ($process in $targets) {
  Write-Host "Stopping llama-server pid=$($process.Id) path=$($process.Path)"
  Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Milliseconds 500

$remaining = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($remaining) {
  Write-Host "Port $Port is still listening. Please check Task Manager if another service owns it."
  exit 1
}

Write-Host "CardioConsult llama-server stopped."
