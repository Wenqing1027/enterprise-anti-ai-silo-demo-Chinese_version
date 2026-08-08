#!/usr/bin/env bash
# 确保 :8000 API 在跑。已健康则直接退出；否则用独立 Terminal/.command 常驻启动。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${QINGSHU_API_PORT:-8000}"
URL="http://127.0.0.1:${PORT}/health"
CMD_FILE="$ROOT/scripts/start_api.command"

if curl -fsS --max-time 2 "$URL" >/dev/null 2>&1; then
  echo "API already up: http://127.0.0.1:${PORT}/business"
  exit 0
fi

if command -v lsof >/dev/null 2>&1; then
  PIDS="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true)"
  if [[ -n "${PIDS}" ]]; then
    echo "Killing stale listeners on :$PORT: $PIDS"
    # shellcheck disable=SC2086
    kill $PIDS 2>/dev/null || true
    sleep 1
    # shellcheck disable=SC2086
    kill -9 $PIDS 2>/dev/null || true
  fi
fi

chmod +x "$CMD_FILE" "$ROOT/scripts/run_api.sh" 2>/dev/null || true

if [[ "$(uname -s)" == "Darwin" ]]; then
  echo "Opening stable Terminal via start_api.command ..."
  open "$CMD_FILE"
else
  nohup bash "$ROOT/scripts/run_api.sh" >>/tmp/qingshu-api.log 2>&1 &
  echo $! >/tmp/qingshu-api.pid
  disown || true
fi

for _ in $(seq 1 40); do
  if curl -fsS --max-time 1 "$URL" >/dev/null 2>&1; then
    echo "API ready: http://127.0.0.1:${PORT}/business"
    exit 0
  fi
  sleep 0.5
done

echo "API failed to become ready. Keep the Terminal window open; see its output." >&2
exit 1
