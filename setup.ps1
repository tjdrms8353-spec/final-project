# dayribbon BI - 초기 설치 (Windows PowerShell)
# 다중 PC 모델: USB에는 소스만, 가상환경·node_modules는 각 PC 로컬 작업공간에 설치.
# 로컬 작업공간: %DAYRIBBON_LOCAL% 환경변수 또는 기본 C:\dayribbon-build
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$local = if ($env:DAYRIBBON_LOCAL) { $env:DAYRIBBON_LOCAL } else { "C:\dayribbon-build" }

Write-Host "== 1/3 소스 동기화: USB -> $local ==" -ForegroundColor Cyan
& "$root\scripts\sync-local.ps1" -Target $local

Write-Host "== 2/3 backend: python venv + pip install (로컬) ==" -ForegroundColor Cyan
python -m venv "$local\backend\.venv"
& "$local\backend\.venv\Scripts\python.exe" -m pip install --upgrade pip
& "$local\backend\.venv\Scripts\python.exe" -m pip install -r "$local\backend\requirements.txt"

Write-Host "== 3/3 frontend: npm install (로컬) ==" -ForegroundColor Cyan
Push-Location "$local\frontend"
npm install
Pop-Location

Write-Host "설치 완료. start.ps1을 실행하세요." -ForegroundColor Green
Write-Host "참고: .env·API 키는 USB 측에만 보관됩니다. 로컬 실행은 개발 기본값으로 동작합니다." -ForegroundColor Yellow
