#!/usr/bin/env bash
# dayribbon BI 데모 - 초기 설치 (Linux/macOS)
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "== backend: python venv + pip install =="
python3 -m venv "$ROOT/backend/.venv"
"$ROOT/backend/.venv/bin/pip" install --upgrade pip
"$ROOT/backend/.venv/bin/pip" install -r "$ROOT/backend/requirements.txt"

echo "== frontend: npm install =="
cd "$ROOT/frontend" && npm install

echo "설치 완료. start.sh를 실행하세요."
