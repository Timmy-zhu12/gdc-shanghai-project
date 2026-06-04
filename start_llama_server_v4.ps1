param(
  [switch]$Visible
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$server = Join-Path $root "tools\llama_cpp\llama-b9469-bin-win-cpu-x64\llama-server.exe"
$model = Join-Path $root "models\gemma-4-4b-it-Q4_K_M.gguf"
$legacyModel = "D:\cardioconsult_PC_runbook\models\gemma-4-4b-it-Q4_K_M.gguf"
$hostName = "127.0.0.1"
$port = 8088

function Test-PortOpen {
  param([string]$HostName, [int]$Port)
  $client = New-Object System.Net.Sockets.TcpClient
  try {
    $async = $client.BeginConnect($HostName, $Port, $null, $null)
    if (-not $async.AsyncWaitHandle.WaitOne(300)) {
      return $false
    }
    $client.EndConnect($async)
    return $true
  } catch {
    return $false
  } finally {
    $client.Close()
  }
}

if (-not (Test-Path $server)) {
  throw "llama-server.exe not found: $server"
}
if (-not (Test-Path $model)) {
  if (Test-Path $legacyModel) {
    $model = $legacyModel
  } else {
    throw "Gemma4 GGUF model not found. Put gemma-4-4b-it-Q4_K_M.gguf in: $(Join-Path $root 'models')"
  }
}

if (Test-PortOpen -HostName $hostName -Port $port) {
  Write-Host "CardioConsult Gemma4 server already listening at http://$hostName`:$port"
  exit 0
}

$args = @(
  "-m", $model,
  "--host", $hostName,
  "--port", "$port",
  "-c", "4096",
  "-b", "1024",
  "-ub", "256",
  "-np", "1",
  "--offline",
  "-a", "cardioconsult-gemma4"
)

$windowStyle = "Hidden"
if ($Visible) {
  $windowStyle = "Normal"
}

Start-Process `
  -FilePath $server `
  -ArgumentList $args `
  -WorkingDirectory (Split-Path -Parent $server) `
  -WindowStyle $windowStyle

Write-Host "Starting CardioConsult Gemma4 server at http://$hostName`:$port"
Write-Host "First model load can take a while; later diagnoses reuse the loaded model."
