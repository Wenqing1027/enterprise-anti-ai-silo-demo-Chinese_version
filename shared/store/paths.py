"""共享 Store 路径约定。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RUNTIME_DIR = DATA_DIR / "runtime"

AI_OUTPUTS_FILE = RUNTIME_DIR / "ai_outputs.json"
RUN_LOGS_FILE = RUNTIME_DIR / "run_logs.json"
TAG_VOCAB_FILE = DATA_DIR / "vocab" / "tag_vocabulary.json"
