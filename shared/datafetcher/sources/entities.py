"""来源 A：结构化实体 JSON（假 CRM / 工单 / 订单 / 库存…）。只读。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable


class EntitySource:
    """从 data/entities/*.json 加载；对上层不暴露路径与 IO。"""

    def __init__(self, entities_dir: Path) -> None:
        self._dir = entities_dir
        self._cache: dict[str, list[dict[str, Any]]] = {}

    def _load(self, name: str) -> list[dict[str, Any]]:
        if name not in self._cache:
            path = self._dir / f"{name}.json"
            if not path.exists():
                self._cache[name] = []
            else:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    raise ValueError(f"entity file must be a list: {path}")
                self._cache[name] = data
        return self._cache[name]

    def reload(self) -> None:
        self._cache.clear()

    def all(self, name: str) -> list[dict[str, Any]]:
        return list(self._load(name))

    def find_one(
        self,
        name: str,
        predicate: Callable[[dict[str, Any]], bool],
    ) -> dict[str, Any] | None:
        for row in self._load(name):
            if predicate(row):
                return dict(row)
        return None

    def find_many(
        self,
        name: str,
        predicate: Callable[[dict[str, Any]], bool] | None = None,
        *,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        rows: Iterable[dict[str, Any]] = self._load(name)
        out: list[dict[str, Any]] = []
        for row in rows:
            if predicate is None or predicate(row):
                out.append(dict(row))
                if limit is not None and len(out) >= limit:
                    break
        return out

    def by_key(self, name: str, key: str, value: Any) -> dict[str, Any] | None:
        return self.find_one(name, lambda r: r.get(key) == value)

    def by_keys(
        self,
        name: str,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        def pred(r: dict[str, Any]) -> bool:
            return all(r.get(k) == v for k, v in kwargs.items())

        return self.find_one(name, pred)
