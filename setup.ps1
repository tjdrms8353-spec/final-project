# dayribbon BI 데모 - 초기 설치 (Windows PowerShell)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "== backend: python venv + pip install ==" -ForegroundColor Cyan
python -m venv "$root\backend\.venv"
& "$root\backend\.venv\Scripts\python.exe" -m pip install --upgrade pip
& "$root\backend\.venv\Scripts\python.exe" -m pip install -r "$root\backend\requirements.txt"
Write-Host "== frontend: npm install ==" -ForegroundColor Cyan
Push-Location "$root\frontend"
npm install
Pop-Location
Write-Host "설치 완료. start.ps1을 실행하세요." -ForegroundColor Green
