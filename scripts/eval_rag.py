#!/usr/bin/env python3
"""RAG 金标评测（R5）：命中文档 / 引用 / 关键词 / 域隔离 / 越域安全。"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

from agents.rag.agent import run_rag
from agents.rag.skill_loader import load_rag_skill

GOLD_PATH = ROOT / "data/eval/rag/gold_qa.json"
REPORT_DIR = ROOT / "docs/rag/eval_reports"


def _rate(n_ok: int, n: int) -> float:
    return (n_ok / n) if n else 1.0


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


def _domains(citations: list[dict[str, Any]], contexts: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for row in list(citations or []) + list(contexts or []):
        d = row.get("kb_domain")
        if d:
            out.add(str(d))
    return out


def _keyword_hit(answer: str, must_any: list[str]) -> bool:
    if not must_any:
        return True
    text = answer or ""
    return any(k in text for k in must_any)


def eval_cases(
    cases: list[dict[str, Any]],
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    selected = cases[: limit or len(cases)]
    rows: list[dict[str, Any]] = []

    run_ok = hit_ok = hit_n = cite_ok = cite_n = 0
    kw_ok = kw_n = dom_ok = xdom_ok = xdom_n = 0

    for case in selected:
        skill_id = case["skill_id"]
        query = case["query"]
        gold = case["gold"]
        skill = load_rag_skill(skill_id)
        allow_domains = set(skill.kb_domains_allow)

        t0 = time.time()
        result = run_rag(skill_id, {"query": query})
        elapsed = time.time() - t0

        answer = result.final_answer or ""
        citations = result.citations or []
        contexts = result.contexts or []
        docs = _doc_ids(citations, contexts)
        domains = _domains(citations, contexts)

        ok_run = bool(result.ok)
        if ok_run:
            run_ok += 1

        expect_hit = bool(gold.get("expect_hit"))
        doc_hit = None
        if expect_hit:
            hit_n += 1
            accept = set(gold.get("doc_id_any_of") or [])
            doc_hit = bool(accept & docs)
            if doc_hit:
                hit_ok += 1
            cite_n += 1
            if citations:
                cite_ok += 1

        must_any = list(gold.get("must_contain_any") or [])
        if must_any:
            kw_n += 1
            if _keyword_hit(answer, must_any):
                kw_ok += 1

        # 域隔离：引用域 ⊆ Skill 白名单
        isolation_ok = domains.issubset(allow_domains) if domains else True
        if isolation_ok:
            dom_ok += 1

        # 越域安全
        cross_ok = None
        if gold.get("cross_domain"):
            xdom_n += 1
            forbid = set(gold.get("forbid_doc_id_any_of") or [])
            leaked = bool(forbid & docs)
            # 允许弱检索噪声，但答案须承认未覆盖/引导换域
            ack = _keyword_hit(answer, list(gold.get("must_contain_any") or []))
            cross_ok = (not leaked) and ack and isolation_ok
            if cross_ok:
                xdom_ok += 1

        rows.append(
            {
                "id": case["id"],
                "skill_id": skill_id,
                "suite": case.get("suite"),
                "ok": result.ok,
                "stop_reason": result.stop_reason,
                "elapsed_s": round(elapsed, 2),
                "expect_hit": expect_hit,
                "doc_hit": doc_hit,
                "cited_docs": sorted(docs),
                "cited_domains": sorted(domains),
                "keyword_hit": _keyword_hit(answer, must_any) if must_any else None,
                "domain_isolation_ok": isolation_ok,
                "cross_domain_ok": cross_ok,
                "answer_preview": answer[:180].replace("\n", " "),
            }
        )

    n = len(selected)
    metrics = {
        "n": n,
        "run_ok_rate": round(_rate(run_ok, n), 4),
        "hit_doc_recall": round(_rate(hit_ok, hit_n), 4) if hit_n else None,
        "hit_n": hit_n,
        "cite_present_rate": round(_rate(cite_ok, cite_n), 4) if cite_n else None,
        "cite_n": cite_n,
        "keyword_hit_rate": round(_rate(kw_ok, kw_n), 4) if kw_n else None,
        "keyword_n": kw_n,
        "domain_isolation_rate": round(_rate(dom_ok, n), 4),
        "cross_domain_safe_rate": round(_rate(xdom_ok, xdom_n), 4) if xdom_n else None,
        "cross_domain_n": xdom_n,
    }
    return {"metrics": metrics, "rows": rows}


def _pass_thresholds(metrics: dict[str, Any], thresholds: dict[str, Any]) -> tuple[bool, list[str]]:
    fails: list[str] = []

    def check(key: str, actual: float | None) -> None:
        need = thresholds.get(key)
        if need is None or actual is None:
            return
        if actual + 1e-9 < float(need):
            fails.append(f"{key}: {actual} < {need}")

    check("run_ok_rate", metrics.get("run_ok_rate"))
    check("hit_doc_recall", metrics.get("hit_doc_recall"))
    check("cite_present_rate", metrics.get("cite_present_rate"))
    check("keyword_hit_rate", metrics.get("keyword_hit_rate"))
    check("domain_isolation_rate", metrics.get("domain_isolation_rate"))
    check("cross_domain_safe_rate", metrics.get("cross_domain_safe_rate"))
    return (len(fails) == 0), fails


def _write_reports(payload: dict[str, Any]) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    stamp_json = REPORT_DIR / f"eval-{ts}.json"
    stamp_md = REPORT_DIR / f"eval-{ts}.md"
    latest_json = REPORT_DIR / "latest.json"
    latest_md = REPORT_DIR / "latest.md"

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    stamp_json.write_text(text, encoding="utf-8")
    latest_json.write_text(text, encoding="utf-8")

    m = payload["metrics"]
    lines = [
        f"# RAG 金标评测报告 · {payload['built_at']}",
        "",
        f"- **结果**: `{'PASS' if payload['passed'] else 'FAIL'}`",
        f"- **用例数**: {m.get('n')}",
        f"- **耗时**: {payload.get('elapsed_s')}s",
        "",
        "## 指标",
        "",
        f"| 指标 | 值 | 门槛 |",
        f"|------|----|------|",
    ]
    th = payload["thresholds"]
    for key, label in (
        ("run_ok_rate", "运行成功率"),
        ("hit_doc_recall", "金标文档召回"),
        ("cite_present_rate", "引用可见率"),
        ("keyword_hit_rate", "关键词覆盖"),
        ("domain_isolation_rate", "域隔离"),
        ("cross_domain_safe_rate", "越域安全"),
    ):
        val = m.get(key)
        need = th.get(key)
        lines.append(
            f"| {label} (`{key}`) | {val if val is not None else '—'} | {need if need is not None else '—'} |"
        )

    if payload.get("failures"):
        lines += ["", "## 未达门槛", ""]
        for f in payload["failures"]:
            lines.append(f"- {f}")

    lines += ["", "## 逐条", "", "| id | skill | ok | doc_hit | kw | xdom | stop |", "|----|-------|----|---------|----|------|------|"]
    for r in payload["rows"]:
        lines.append(
            f"| {r['id']} | {r['skill_id']} | {r['ok']} | {r.get('doc_hit')} | "
            f"{r.get('keyword_hit')} | {r.get('cross_domain_ok')} | {r.get('stop_reason')} |"
        )
    lines.append("")
    md = "\n".join(lines)
    stamp_md.write_text(md, encoding="utf-8")
    latest_md.write_text(md, encoding="utf-8")
    return latest_md, latest_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RAG gold QA")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--suite",
        choices=["all", "core", "extended", "cross_domain"],
        default="all",
    )
    parser.add_argument(
        "--gold",
        type=Path,
        default=GOLD_PATH,
    )
    args = parser.parse_args()

    raw = json.loads(args.gold.read_text(encoding="utf-8"))
    cases = list(raw.get("cases") or [])
    if args.suite != "all":
        cases = [c for c in cases if c.get("suite") == args.suite]
    thresholds = dict(raw.get("thresholds") or {})

    t0 = time.time()
    result = eval_cases(cases, limit=args.limit)
    elapsed = round(time.time() - t0, 2)
    passed, fails = _pass_thresholds(result["metrics"], thresholds)

    payload = {
        "version": raw.get("version", "v1"),
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "suite": args.suite,
        "elapsed_s": elapsed,
        "passed": passed,
        "failures": fails,
        "thresholds": thresholds,
        "metrics": result["metrics"],
        "rows": result["rows"],
    }
    md_path, json_path = _write_reports(payload)
    print(f"wrote {md_path}")
    print(f"wrote {json_path}")
    print(json.dumps({"passed": passed, "metrics": result["metrics"], "failures": fails}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
