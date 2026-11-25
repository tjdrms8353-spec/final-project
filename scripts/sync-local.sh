#!/usr/bin/env bash
# USB 소스 → PC 로컬 작업공간 동기화 (Linux/macOS)
# - .env·인증서·비밀 파일은 로컬로 복제하지 않는다.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-${DAYRIBBON_LOCAL:-$HOME/dayribbon-local}}"

echo "동기화: $ROOT -> $TARGET"
mkdir -p "$TARGET"

rsync -a --delete \
  --exclude '.git' --exclude 'node_modules' --exclude '.venv' --exclude 'venv' \
  --exclude 'dist' --exclude 'dist-verify' --exclude 'runtime' \
  --exclude '__pycache__' --exclude 'secrets' --exclude 'data' --exclude '.pytest_cache' \
  --exclude '.env' --exclude '*.pem' --exclude '*.key' --exclude '*.log' \
  "$ROOT/" "$TARGET/"

echo "동기화 완료 → $TARGET"
