#!/usr/bin/env bash
# dayribbon BI - 종료 (Linux/macOS)
LOCAL="${DAYRIBBON_LOCAL:-$HOME/dayribbon-local}"
PIDFILE="$LOCAL/runtime/pids.json"
[ -f "$PIDFILE" ] || { echo "실행 정보가 없습니다."; exit 0; }

python3 - "$PIDFILE" <<'EOF'
import json, os, signal, sys
info = json.load(open(sys.argv[1]))
for key in ("backend_pid", "frontend_pid"):
    pid = info.get(key)
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"PID {pid} 종료")
        except ProcessLookupError:
            print(f"PID {pid} 이미 종료됨")
EOF

pkill -f "$LOCAL/frontend" 2>/dev/null || true
rm -f "$PIDFILE"
echo "중지 완료."
