# USB 소스 → PC 로컬 작업공간 동기화 (Windows PowerShell)
# - USB에는 소스·git·문서·.env만 보관, PC에는 재생성 가능한 파일만 둔다.
# - .env·인증서·비밀 파일은 로컬로 복제하지 않는다 (민감정보 로컬 복제 방지).
# - USB 드라이브 문자에 의존하지 않는다 (스크립트 위치 기준 경로).
param(
  [string]$Target = ""
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not $Target) {
  $Target = if ($env:DAYRIBBON_LOCAL) { $env:DAYRIBBON_LOCAL } else { "C:\dayribbon-build" }
}

Write-Host "동기화: $root -> $Target" -ForegroundColor Cyan

# 미러링 + 제외 규칙
#   디렉터리 제외: git 이력, PC별 산출물, 비밀 폴더, per-PC DB/런타임
#   파일 제외: .env·인증서·키·로그 (민감정보 로컬 복제 금지)
robocopy "$root" "$Target" /MIR `
  /XD .git node_modules .venv venv dist dist-verify runtime __pycache__ secrets data .pytest_cache `
  /XF .env *.pem *.key *.log `
  /NFL /NDL /NJH /NP

if ($LASTEXITCODE -gt 7) { throw "robocopy 동기화 실패 (코드 $LASTEXITCODE)" }
Write-Host "동기화 완료 → $Target" -ForegroundColor Green
