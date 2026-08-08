#!/usr/bin/env python3
"""从 data/knowledge/chunks.json 构建 TF-IDF 索引 → data/knowledge/tfidf_index.json。

用法（仓库根目录）:
  python scripts/build_kb_index.py
  python scripts/build_kb_index.py --title-boost 1.35
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.rag.tfidf_index import IndexParams, build_and_save_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Build TF-IDF index from chunks.json")
    parser.add_argument(
        "--chunks",
        type=Path,
        default=ROOT / "data" / "knowledge" / "chunks.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "knowledge" / "tfidf_index.json",
    )
    parser.add_argument("--title-boost", type=float, default=1.35)
    args = parser.parse_args()

    if not args.chunks.exists():
        print(f"缺少 {args.chunks}，请先运行 scripts/build_kb_chunks.py", file=sys.stderr)
        return 1

    params = IndexParams(title_boost=args.title_boost)
    idx = build_and_save_index(args.chunks, args.out, params=params)
    stats = idx.meta.get("stats") or {}
    print(f"wrote {args.out}")
    print(
        f"chunks={stats.get('chunks')} vocab={stats.get('vocab_size')} "
        f"by_domain={stats.get('by_domain')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
