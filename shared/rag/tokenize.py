"""中英混合轻量分词：供切块检索与 TF-IDF 共用。"""

from __future__ import annotations

import re

_SPLIT_RE = re.compile(r"[\s，。；、！？,.!?/|：:（）()【】\[\]\"'“”‘’·•\-_=+*]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def tokenize(text: str, *, ngram_ns: tuple[int, ...] = (2, 3)) -> list[str]:
    """空白切分 + CJK n-gram；保留英文/数字 token。"""
    q = (text or "").strip().lower()
    if not q:
        return []
    parts = [t for t in _SPLIT_RE.split(q) if t]
    tokens: list[str] = []
    for p in parts:
        tokens.append(p)
        if _CJK_RE.search(p):
            for n in ngram_ns:
                if len(p) >= n:
                    tokens.extend(p[i : i + n] for i in range(0, len(p) - n + 1))
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if len(t) < 2 and not t.isascii():
            # 单汉字噪声大，跳过；ascii 单字母也跳过
            continue
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out
