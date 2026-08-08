#!/usr/bin/env bash
# Story 2：跨类型消费并阻断（与 Story A 同一地基冒烟脚本内完成）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "[demo] Story B — read_ai_outputs / check_outreach_block（青枢出行）"
echo "[demo] 说明：Story B 已包含在 smoke_foundation.py 端到端链路中"
python3 "$ROOT/scripts/smoke_foundation.py"
