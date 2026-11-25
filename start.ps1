# dayribbon BI - 백엔드/프론트엔드 실행 (Windows PowerShell)
# 로컬 작업공간(DAYRIBBON_LOCAL 또는 C:\dayribbon-build)에서 실행한다.
# 최신 소스 반영이 필요하면 먼저 scripts\sync-local.ps1을 실행하세요.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$local = if ($env:DAYRIBBON_LOCAL) { $env:DAYRIBBON_LOCAL } else { "C:\dayribbon-build" }

if (-not (Test-Path "$local\backend\.venv\Scripts\python.exe")) {
  throw "로컬 작업공간이 없습니다: $local — setup.ps1을 먼저 실행하세요."
}

$runtime = "$local\runtime"
New-Item -ItemType Directory -Force -Path $runtime | Out-Null

function Test-PortFree($port) {
  try {
    $c = New-Object Net.Sockets.TcpClient
    $c.Connect('127.0.0.1', $port); $c.Close(); return $false
  } catch { return $true }
}
function Find-Port($start, $end) {
  foreach ($p in $start..$end) { if (Test-PortFree $p) { return $p } }
  throw "사용 가능한 포트가 없습니다 ($start-$end)"
}

# 포트 결정 (기본 8000/5173, 사용 중이면 다음 포트)
$bePort = Find-Port 8000 8010
$fePort = Find-Port 5173 5183
if ($fePort -eq $bePort) { $fePort = Find-Port 5184 5190 }

$env:PORT = "$bePort"
$env:VITE_BACKEND_URL = "http://localhost:$bePort"

Write-Host "백엔드 포트: $bePort / 프론트엔드 포트: $fePort" -ForegroundColor Cyan

$be = Start-Process -PassThru -FilePath "$local\backend\.venv\Scripts\python.exe" `
  -ArgumentList 'run.py' -WorkingDirectory "$local\backend"
$fe = Start-Process -PassThru -FilePath 'cmd.exe' `
  -ArgumentList '/c', "npm run dev -- --port $fePort --host 127.0.0.1" `
  -WorkingDirectory "$local\frontend"

@{ backend_pid = $be.Id; frontend_pid = $fe.Id; backend_port = $bePort; frontend_port = $fePort } |
  ConvertTo-Json | Out-File "$runtime\pids.json" -Encoding utf8

Write-Host ""
Write-Host "실행 중:" -ForegroundColor Green
Write-Host "  Frontend : http://localhost:$fePort"
Write-Host "  Backend  : http://localhost:$bePort"
Write-Host "  API Docs : http://localhost:$bePort/docs"
Write-Host ""
Write-Host "중지하려면 stop.ps1을 실행하세요." -ForegroundColor Yellow
