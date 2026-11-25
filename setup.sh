#!/usr/bin/env bash
# dayribbon BI - 초기 설치 (Linux/macOS)
# 다중 PC 모델: USB에는 소스만, 가상환경·node_modules는 각 PC 로컬 작업공간에 설치.
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
LOCAL="${DAYRIBBON_LOCAL:-$HOME/dayribbon-local}"

echo "== 1/3 소스 동기화: USB -> $LOCAL =="
"$ROOT/scripts/sync-local.sh" "$LOCAL"

echo "== 2/3 backend: python venv + pip install (로컬) =="
python3 -m venv "$LOCAL/backend/.venv"
"$LOCAL/backend/.venv/bin/pip" install --upgrade pip
"$LOCAL/backend/.venv/bin/pip" install -r "$LOCAL/backend/requirements.txt"

echo "== 3/3 frontend: npm install (로컬) =="
cd "$LOCAL/frontend" && npm install

echo "설치 완료. start.sh를 실행하세요."
echo "참고: .env·API 키는 USB 측에만 보관됩니다."
