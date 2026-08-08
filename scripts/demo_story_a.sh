#!/usr/bin/env bash
# Story 1：产出资产化（绕过 Agent，走地基冒烟）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "[demo] Story A — fetcher → write_ai_output（青枢出行）"
python3 "$ROOT/scripts/smoke_foundation.py"
