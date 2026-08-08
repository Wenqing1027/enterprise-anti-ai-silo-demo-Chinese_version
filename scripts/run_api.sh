#!/usr/bin/env bash
# 启动业务 API；默认剥离 IDE 注入的本地代理，避免 DeepSeek Connection error。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PID_FILE="${QINGSHU_API_PID_FILE:-/tmp/qingshu-api.pid}"
LOG_FILE="${QINGSHU_API_LOG_FILE:-/tmp/qingshu-api.log}"

# shellcheck disable=SC1091
source .venv/bin/activate

if [[ "${DEEPSEEK_TRUST_ENV:-0}" != "1" ]]; then
  unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
  unset SOCKS_PROXY SOCKS5_PROXY socks_proxy socks5_proxy
  unset GIT_HTTP_PROXY GIT_HTTPS_PROXY
fi

echo $$ >"$PID_FILE"
echo "[qingshu-api] starting pid=$$ root=$ROOT" | tee -a "$LOG_FILE"
exec python -m uvicorn apps.api:app --host 0.0.0.0 --port 8000 "$@"
