# 민감정보 Git 추적 여부 검사 (Windows PowerShell)
# - .env, 인증서, 키, secrets/ 가 git에 추적되고 있으면 실패 코드를 반환한다.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Push-Location $root
try {
  $tracked = git -c safe.directory='*' ls-files | Select-String -Pattern '(^|/)\.env$|\.pem$|\.key$|(^|/)secrets/'
  if ($tracked) {
    Write-Host "오류: 민감정보가 Git에 추적되고 있습니다:" -ForegroundColor Red
    $tracked | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    exit 1
  }
  if (-not (Test-Path "$root\.env")) {
    Write-Host "참고: .env가 아직 없습니다 (개발 기본값으로 동작). 필요 시 .env.example을 복사하세요." -ForegroundColor Yellow
  } else {
    Write-Host ".env 존재 — Git 미추적 확인 완료" -ForegroundColor Green
  }
  Write-Host "민감정보 Git 추적 없음" -ForegroundColor Green
} finally { Pop-Location }
