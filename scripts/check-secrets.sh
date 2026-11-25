#!/usr/bin/env bash
# 민감정보 Git 추적 여부 검사 (Linux/macOS)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if git -c safe.directory='*' ls-files | grep -E '(^|/)\.env$|\.pem$|\.key$|(^|/)secrets/'; then
  echo "오류: 위 민감정보 파일이 Git에 추적되고 있습니다." >&2
  exit 1
fi
[ -f .env ] && echo ".env 존재 — Git 미추적 확인 완료" || echo "참고: .env 없음 (개발 기본값으로 동작)"
echo "민감정보 Git 추적 없음"
