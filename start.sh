#!/usr/bin/env bash
# dayribbon BI 데모 - 실행 (Linux/macOS)
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
RUNTIME="$ROOT/runtime"
mkdir -p "$RUNTIME"

port_free() { ! (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
find_port() { local p=$1; while [ $p -le $2 ]; do port_free $p && { echo $p; return; }; p=$((p+1)); done; exit 1; }

BE_PORT=$(find_port 8000 8010)
FE_PORT=$(find_port 5173 5183)
[ "$FE_PORT" = "$BE_PORT" ] && FE_PORT=$(find_port 5184 5190)

echo "백엔드 포트: $BE_PORT / 프론트엔드 포트: $FE_PORT"

cd "$ROOT/backend"
PORT=$BE_PORT nohup ./.venv/bin/python run.py > "$RUNTIME/backend.log" 2>&1 &
BE_PID=$!

cd "$ROOT/frontend"
VITE_BACKEND_URL="http://localhost:$BE_PORT" nohup npm run dev -- --port "$FE_PORT" --host 127.0.0.1 > "$RUNTIME/frontend.log" 2>&1 &
FE_PID=$!

echo "{\"backend_pid\": $BE_PID, \"frontend_pid\": $FE_PID, \"backend_port\": $BE_PORT, \"frontend_port\": $FE_PORT}" > "$RUNTIME/pids.json"

echo ""
echo "실행 중:"
echo "  Frontend : http://localhost:$FE_PORT"
echo "  Backend  : http://localhost:$BE_PORT"
echo "  API Docs : http://localhost:$BE_PORT/docs"
echo "중지: stop.sh"
