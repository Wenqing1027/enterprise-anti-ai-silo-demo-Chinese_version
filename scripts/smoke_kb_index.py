#!/usr/bin/env python3
"""R2 索引库冒烟：TF-IDF 落盘 + DataFetcher.search_kb 块级命中。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.datafetcher import DataFetcher, KbChunk  # noqa: E402
from shared.rag.tfidf_index import TfidfIndex  # noqa: E402


def main() -> None:
    index_path = ROOT / "data/knowledge/tfidf_index.json"
    assert index_path.exists(), "缺少 tfidf_index.json，请先 python scripts/build_kb_index.py"

    idx = TfidfIndex.load(index_path)
    assert idx.meta.get("index_id") == "tfidf_charngram_v1"
    assert (idx.meta.get("stats") or {}).get("chunks", 0) >= 15
    assert len(idx.vocab) > 50

    # 直接索引检索
    direct = idx.search("续航低于标称怎么排查", domain="repair", top_k=3)
    assert direct and direct[0].chunk.kb_domain == "repair"
    assert "续航" in (direct[0].chunk.content or "") or "续航" in direct[0].chunk.title

    policy = idx.search("2026Q3 提货返利档位", domain="policy", top_k=3)
    assert policy and policy[0].chunk.kb_domain == "policy"

    hr = idx.search("坐席质检 SOP 红线", domain="hr", top_k=3)
    assert hr and hr[0].chunk.kb_domain == "hr"

    # 域隔离：repair 问不应因 domain=hr 命中维修文
    cross = idx.search("续航异常排查", domain="hr", top_k=3)
    assert all(h.chunk.kb_domain == "hr" for h in cross)

    # DataFetcher 统一出口
    fetcher = DataFetcher()
    hits = fetcher.search_kb("续航低于标称怎么排查", domain="repair", top_k=3)
    assert hits and all(isinstance(h, KbChunk) for h in hits)
    assert hits[0].kb_chunk_id and "#c" in (hits[0].kb_chunk_id or "")
    assert hits[0].kb_score and hits[0].kb_score > 0
    assert hits[0].content and len(hits[0].content) > 20

    got = fetcher.get_kb_chunk(hits[0].kb_chunk_id or "")
    assert got is not None and got.kb_chunk_id == hits[0].kb_chunk_id

    print("OK kb index smoke")
    print(
        json.dumps(
            {
                "vocab_size": len(idx.vocab),
                "chunks": (idx.meta.get("stats") or {}).get("chunks"),
                "top_repair": {
                    "kb_chunk_id": hits[0].kb_chunk_id,
                    "score": hits[0].kb_score,
                    "title": hits[0].title,
                },
                "top_policy": {
                    "kb_chunk_id": policy[0].chunk.kb_chunk_id,
                    "score": policy[0].score,
                },
                "top_hr": {
                    "kb_chunk_id": hr[0].chunk.kb_chunk_id,
                    "score": hr[0].score,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
