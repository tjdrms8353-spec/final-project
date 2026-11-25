# dayribbon BI 데모 - 실행 중인 프로세스 종료 (Windows PowerShell)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = "$root\runtime\pids.json"
if (-not (Test-Path $pidFile)) { Write-Host "실행 정보가 없습니다."; exit 0 }
$info = Get-Content $pidFile -Raw | ConvertFrom-Json
foreach ($p in @($info.backend_pid, $info.frontend_pid)) {
  if ($p) {
    try { Stop-Process -Id $p -Force -ErrorAction Stop; Write-Host "PID $p 종료" } catch { Write-Host "PID $p 이미 종료됨" }
  }
}
# cmd.exe 래퍼로 띄운 npm 자식 프로세스 정리
Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
  Where-Object { $_.CommandLine -match 'dayribbon-bi-demo' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
Write-Host "중지 완료."
