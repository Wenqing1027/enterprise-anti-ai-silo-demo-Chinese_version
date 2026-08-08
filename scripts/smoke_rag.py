#!/usr/bin/env python3
"""R5 RAG 冒烟：金标 core + 1 条越域；快路径不跑全量评测。

全量金标请用：python scripts/eval_rag.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

from agents.rag.agent import run_rag  # noqa: E402
from apps.skill_dispatch import peek_skill_kind  # noqa: E402

GOLD_PATH = ROOT / "data/eval/rag/gold_qa.json"


def _doc_ids(citations: list[dict[str, Any]], contexts: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for row in list(citations or []) + list(contexts or []):
        did = row.get("kb_doc_id")
        if did:
            out.add(str(did))
        cid = row.get("kb_chunk_id") or ""
        if "#" in cid:
            out.add(cid.split("#", 1)[0])
    return out


def _keyword_hit(answer: str, must_any: list[str]) -> bool:
    if not must_any:
        return True
    text = answer or ""
    return any(k in text for k in must_any)


def _load_smoke_cases() -> list[dict]:
    raw = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    cases = list(raw.get("cases") or [])
    core = [c for c in cases if c.get("suite") == "core"]
    xdom = [c for c in cases if c.get("id") == "RAG-XDOM-001"]
    selected = core + xdom
    if len(selected) < 4:
        raise RuntimeError("金标缺少 core/越域用例")
    return selected


def main() -> None:
    rows = []
    for case in _load_smoke_cases():
        sid = case["skill_id"]
        assert peek_skill_kind(sid) == "rag", sid
        gold = case["gold"]
        result = run_rag(sid, {"query": case["query"]})
        assert result.ok, (case["id"], result.stop_reason, result.final_answer[:200])

        docs = _doc_ids(result.citations, result.contexts)
        if gold.get("expect_hit"):
            accept = set(gold.get("doc_id_any_of") or [])
            assert accept & docs, (case["id"], docs, accept)
            assert result.citations, case["id"]
            assert _keyword_hit(
                result.final_answer or "",
                list(gold.get("must_contain_any") or []),
            ), (case["id"], result.final_answer[:200])
        if gold.get("cross_domain"):
            forbid = set(gold.get("forbid_doc_id_any_of") or [])
            assert not (forbid & docs), (case["id"], "leaked", docs)
            assert _keyword_hit(
                result.final_answer or "",
                list(gold.get("must_contain_any") or []),
            ), (case["id"], result.final_answer[:200])

        rows.append(
            {
                "id": case["id"],
                "skill_id": sid,
                "stop_reason": result.stop_reason,
                "docs": sorted(docs),
            }
        )

    print("OK rag smoke (core+xdom)")
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
