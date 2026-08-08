#!/bin/bash
# 双击或 open 本文件即可在独立 Terminal 中常驻 API
cd "$(dirname "$0")/.." || exit 1
exec bash scripts/run_api.sh
