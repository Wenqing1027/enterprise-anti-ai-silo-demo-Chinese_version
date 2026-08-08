"""本地 JSON 持久化（Demo 级；非生产数据库）。"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


_lock = threading.RLock()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_list(path: Path) -> list[dict[str, Any]]:
    with _lock:
        if not path.exists():
            return []
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError(f"store file must be a JSON list: {path}")
        return data


def save_list(path: Path, rows: list[dict[str, Any]]) -> None:
    with _lock:
        ensure_parent(path)
        path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )


def load_json(path: Path, default: Any = None) -> Any:
    with _lock:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
