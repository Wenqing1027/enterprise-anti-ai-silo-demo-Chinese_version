"""来源 C：共享语义字典（标签 / 字段释义）。只读。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class VocabSource:
    def __init__(self, vocab_dir: Path) -> None:
        self._dir = vocab_dir
        self._tags: list[dict[str, Any]] | None = None
        self._glossary: list[dict[str, Any]] | None = None

    def reload(self) -> None:
        self._tags = None
        self._glossary = None

    def tags(self) -> list[dict[str, Any]]:
        if self._tags is None:
            path = self._dir / "tag_vocabulary.json"
            if not path.exists():
                self._tags = []
            else:
                raw = json.loads(path.read_text(encoding="utf-8"))
                self._tags = list(raw.get("tags", [])) if isinstance(raw, dict) else list(raw)
        return list(self._tags)

    def tag_by_id(self, tag_id: str) -> dict[str, Any] | None:
        for t in self.tags():
            if t.get("tag_id") == tag_id:
                return dict(t)
        return None

    def glossary_fields(self) -> list[dict[str, Any]]:
        if self._glossary is None:
            path = self._dir / "field_glossary.json"
            if not path.exists():
                self._glossary = []
            else:
                raw = json.loads(path.read_text(encoding="utf-8"))
                self._glossary = list(raw.get("fields", []))
        return list(self._glossary)
