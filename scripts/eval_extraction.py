"""Extraction 金标评测（阶段四）：对齐 docs/extraction 阶段一门槛。"""

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

from agents.extraction.agent import run_extraction
from shared.tools.guards import BLOCKING_TAGS

GOLD_TICKET = ROOT / "data/eval/extraction/gold_ticket_fields.json"
GOLD_VOC = ROOT / "data/eval/extraction/gold_voc_entities.json"
REPORT_DIR = ROOT / "docs/extraction/eval_reports"


def _rate(n_ok: int, n: int) -> float:
    return (n_ok / n) if n else 1.0


def _tag_hit(pred: str | None, gold: dict[str, Any]) -> bool:
    accept = list(gold.get("tag_id_accept") or [])
    primary = gold.get("tag_id")
    if primary and primary not in accept:
        accept = [primary, *accept]
    return bool(pred) and pred in accept


def _blocking_hit(payload: dict[str, Any], gold: dict[str, Any]) -> bool:
    if not gold.get("blocking_required"):
        return True
    tags = {payload.get("tag_id"), *(payload.get("secondary_tag_ids") or [])}
    tags.discard(None)
    required = set(gold.get("blocking_any_of") or list(BLOCKING_TAGS))
    return bool(tags & required)


def _sentiment_hit(pred: str | None, gold: dict[str, Any], *, tolerant: bool) -> bool:
    g = gold.get("sentiment")
    if pred == g:
        return True
    if not tolerant:
        return False
    # 非投诉句允许 neu↔neg 一档
    if not gold.get("is_complaint") and {pred, g} <= {"neu", "neg"}:
        return True
    return False


def eval_ticket(cases: list[dict[str, Any]], *, limit: int | None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    schema_ok = type_ok = fault_ok = fault_n = tag_ok = sent_ok = sent_tol = 0
    id_need = id_hit = 0
    blocking_miss = 0
    selected = cases[: limit or len(cases)]

    for case in selected:
        t0 = time.time()
        result = run_extraction(
            "ticket_fields",
            case["input"],
            write_output=False,
        )
        elapsed = time.time() - t0
        gold = case["gold"]
        payload = result.payload or {}
        ok_schema = bool(result.ok)
        if ok_schema:
            schema_ok += 1

        type_hit = ok_schema and payload.get("ticket_type") == gold.get("ticket_type")
        if type_hit:
            type_ok += 1

        # fault 子集
        if gold.get("ticket_type") == "fault" and gold.get("fault_category") is not None:
            fault_n += 1
            pred_f = payload.get("fault_category")
            accept_f = list(gold.get("fault_category_accept") or [])
            if gold.get("fault_category") and gold["fault_category"] not in accept_f:
                accept_f = [gold["fault_category"], *accept_f]
            if gold.get("accept_fault_other") and pred_f == "other":
                fault_ok += 1
            elif pred_f in accept_f:
                fault_ok += 1

        tag_hit = ok_schema and _tag_hit(payload.get("tag_id"), gold)
        if tag_hit:
            tag_ok += 1

        if gold.get("blocking_required") and not _blocking_hit(payload, gold):
            blocking_miss += 1

        if ok_schema and _sentiment_hit(payload.get("sentiment"), gold, tolerant=False):
            sent_ok += 1
        if ok_schema and _sentiment_hit(payload.get("sentiment"), gold, tolerant=True):
            sent_tol += 1

        if gold.get("expect_ids"):
            id_need += 1
            cid_ok = True
            vin_ok = True
            if gold.get("customer_id"):
                cid_ok = payload.get("customer_id") == gold["customer_id"]
            if gold.get("vin"):
                vin_ok = payload.get("vin") == gold["vin"]
            if cid_ok and vin_ok:
                id_hit += 1

        rows.append(
            {
                "id": case["id"],
                "ok": result.ok,
                "stop_reason": result.stop_reason,
                "elapsed_s": round(elapsed, 2),
                "ticket_type_hit": type_hit,
                "tag_hit": tag_hit,
                "sentiment_pred": payload.get("sentiment"),
                "tag_id_pred": payload.get("tag_id"),
                "blocking_ok": _blocking_hit(payload, gold) if gold.get("blocking_required") else None,
            }
        )

    n = len(selected)
    metrics = {
        "n": n,
        "schema_ok_rate": round(_rate(schema_ok, n), 4),
        "ticket_type_acc": round(_rate(type_ok, n), 4),
        "fault_category_acc": round(_rate(fault_ok, fault_n), 4),
        "fault_n": fault_n,
        "tag_id_acc": round(_rate(tag_ok, n), 4),
        "blocking_miss": blocking_miss,
        "sentiment_acc": round(_rate(sent_ok, n), 4),
        "sentiment_acc_tolerant": round(_rate(sent_tol, n), 4),
        "id_recall": round(_rate(id_hit, id_need), 4) if id_need else None,
        "id_need": id_need,
    }
    return {"metrics": metrics, "rows": rows}


def eval_voc(cases: list[dict[str, Any]], *, limit: int | None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    schema_ok = tag_ok = sent_ok = domain_ok = 0
    blocking_miss = oov = 0
    selected = cases[: limit or len(cases)]

    # leaf tags for OOV
    vocab = json.loads((ROOT / "data/vocab/tag_vocabulary.json").read_text(encoding="utf-8"))
    allowed = {
        t["tag_id"]
        for t in vocab.get("tags", [])
        if t.get("tag_id") and not str(t["tag_id"]).startswith("TAG-ROOT-")
    }

    for case in selected:
        t0 = time.time()
        result = run_extraction(
            "voc_entities",
            case["input"],
            write_output=False,
        )
        elapsed = time.time() - t0
        gold = case["gold"]
        payload = result.payload or {}
        ok_schema = bool(result.ok)
        if ok_schema:
            schema_ok += 1
        else:
            # schema fail already counted; still check oov on raw if any
            pass

        tag_hit = ok_schema and _tag_hit(payload.get("tag_id"), gold)
        if tag_hit:
            tag_ok += 1

        if gold.get("blocking_required") and not _blocking_hit(payload, gold):
            blocking_miss += 1

        if ok_schema and payload.get("sentiment") == gold.get("sentiment"):
            sent_ok += 1

        domain_accept = list(gold.get("tag_domain_accept") or [])
        gdom = gold.get("tag_domain")
        if gdom and gdom not in domain_accept:
            domain_accept = [gdom, *domain_accept]
        if ok_schema and payload.get("tag_domain") in domain_accept:
            domain_ok += 1

        tid = payload.get("tag_id")
        if tid and tid not in allowed:
            oov += 1

        rows.append(
            {
                "id": case["id"],
                "ok": result.ok,
                "stop_reason": result.stop_reason,
                "elapsed_s": round(elapsed, 2),
                "tag_hit": tag_hit,
                "tag_id_pred": tid,
                "sentiment_pred": payload.get("sentiment"),
                "tag_domain_pred": payload.get("tag_domain"),
                "blocking_ok": _blocking_hit(payload, gold) if gold.get("blocking_required") else None,
            }
        )

    n = len(selected)
    metrics = {
        "n": n,
        "schema_ok_rate": round(_rate(schema_ok, n), 4),
        "tag_id_acc": round(_rate(tag_ok, n), 4),
        "blocking_miss": blocking_miss,
        "sentiment_acc": round(_rate(sent_ok, n), 4),
        "tag_domain_acc": round(_rate(domain_ok, n), 4),
        "oov_tag_rate": round(_rate(oov, n), 4),
    }
    return {"metrics": metrics, "rows": rows}


def _pass_ticket(m: dict[str, Any], th: dict[str, Any]) -> dict[str, bool]:
    # 阶段一：非投诉句 neu↔neg 可容忍一档 → 验收用 tolerant
    sentiment_for_gate = m.get("sentiment_acc_tolerant", m.get("sentiment_acc"))
    return {
        "schema_ok_rate": m["schema_ok_rate"] >= th["schema_ok_rate"],
        "ticket_type_acc": m["ticket_type_acc"] >= th["ticket_type_acc"],
        "fault_category_acc": m["fault_category_acc"] >= th["fault_category_acc"],
        "tag_id_acc": m["tag_id_acc"] >= th["tag_id_acc"],
        "blocking_miss": m["blocking_miss"] <= th["blocking_miss"],
        "sentiment_acc": sentiment_for_gate >= th["sentiment_acc"],
        "id_recall": (
            m["id_recall"] is None or m["id_recall"] >= th["id_recall"]
        ),
    }


def _pass_voc(m: dict[str, Any], th: dict[str, Any]) -> dict[str, bool]:
    return {
        "schema_ok_rate": m["schema_ok_rate"] >= th["schema_ok_rate"],
        "tag_id_acc": m["tag_id_acc"] >= th["tag_id_acc"],
        "blocking_miss": m["blocking_miss"] <= th["blocking_miss"],
        "sentiment_acc": m["sentiment_acc"] >= th["sentiment_acc"],
        "tag_domain_acc": m["tag_domain_acc"] >= th["tag_domain_acc"],
        "oov_tag_rate": m["oov_tag_rate"] <= th["oov_tag_rate_max"],
    }


def _md_report(report: dict[str, Any]) -> str:
    lines = [
        "# Extraction 金标评测报告",
        "",
        f"> 生成时间：{report['generated_at']}",
        f"> 脚本：`scripts/eval_extraction.py`",
        "",
        "## 总览",
        "",
        f"- 总体通过：**{'PASS' if report['overall_pass'] else 'FAIL'}**",
        f"- ticket_fields：{'PASS' if report['ticket']['pass_all'] else 'FAIL'}",
        f"- voc_entities：{'PASS' if report['voc']['pass_all'] else 'FAIL'}",
        "",
        "## ticket_fields",
        "",
        "| 指标 | 实测 | 门槛 | 结果 |",
        "|------|------|------|------|",
    ]
    th = report["ticket"]["thresholds"]
    m = report["ticket"]["metrics"]
    checks = report["ticket"]["checks"]
    mapping = [
        ("schema_ok_rate", "Schema 合规率"),
        ("ticket_type_acc", "ticket_type 准确率"),
        ("fault_category_acc", "fault_category 准确率"),
        ("tag_id_acc", "tag_id Top-1"),
        ("blocking_miss", "阻断漏报数"),
        ("sentiment_acc", "sentiment 准确率"),
        ("id_recall", "ID 召回"),
    ]
    for key, label in mapping:
        gate = th.get(key) if key != "id_recall" else th.get("id_recall")
        if key == "sentiment_acc":
            val = f"{m.get('sentiment_acc')}（严格）/ {m.get('sentiment_acc_tolerant')}（容忍，验收用）"
        else:
            val = m.get(key)
        ok = checks.get(key)
        lines.append(f"| {label} | {val} | {gate} | {'✅' if ok else '❌'} |")
    lines += [
        "",
        "> ticket sentiment 验收口径：阶段一允许非投诉句 `neu↔neg` 一档容忍。",
        "",
        "## voc_entities",
        "",
        "| 指标 | 实测 | 门槛 | 结果 |",
        "|------|------|------|------|",
    ]
    thv = report["voc"]["thresholds"]
    mv = report["voc"]["metrics"]
    cv = report["voc"]["checks"]
    for key, label in [
        ("schema_ok_rate", "Schema 合规率"),
        ("tag_id_acc", "tag_id 命中"),
        ("blocking_miss", "阻断漏报数"),
        ("sentiment_acc", "sentiment 准确率"),
        ("tag_domain_acc", "tag_domain 准确率"),
        ("oov_tag_rate", "字典外标签率"),
    ]:
        gate = thv.get(key) if key != "oov_tag_rate" else thv.get("oov_tag_rate_max")
        lines.append(
            f"| {label} | {mv.get(key)} | {gate} | {'✅' if cv.get(key) else '❌'} |"
        )
    lines += ["", "## 失败/告警样例", ""]
    fails = [
        r
        for r in report["ticket"]["rows"] + report["voc"]["rows"]
        if not r.get("ok") or r.get("tag_hit") is False or r.get("blocking_ok") is False
    ]
    if not fails:
        lines.append("无。")
    else:
        for r in fails[:30]:
            lines.append(
                f"- `{r.get('id')}` stop={r.get('stop_reason')} tag={r.get('tag_id_pred')} "
                f"sent={r.get('sentiment_pred')} tag_hit={r.get('tag_hit')} blocking_ok={r.get('blocking_ok')}"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extraction gold-set eval")
    parser.add_argument("--limit", type=int, default=None, help="每套最多 N 条（调试）")
    parser.add_argument("--ticket-only", action="store_true")
    parser.add_argument("--voc-only", action="store_true")
    args = parser.parse_args()

    ticket_gold = json.loads(GOLD_TICKET.read_text(encoding="utf-8"))
    voc_gold = json.loads(GOLD_VOC.read_text(encoding="utf-8"))

    do_ticket = not args.voc_only
    do_voc = not args.ticket_only

    ticket_part: dict[str, Any] = {
        "metrics": {},
        "rows": [],
        "thresholds": ticket_gold["thresholds"],
        "checks": {},
        "pass_all": True,
    }
    voc_part: dict[str, Any] = {
        "metrics": {},
        "rows": [],
        "thresholds": voc_gold["thresholds"],
        "checks": {},
        "pass_all": True,
    }

    if do_ticket:
        print(f"Evaluating ticket_fields n={len(ticket_gold['cases'])} …")
        out = eval_ticket(ticket_gold["cases"], limit=args.limit)
        checks = _pass_ticket(out["metrics"], ticket_gold["thresholds"])
        ticket_part = {
            **out,
            "thresholds": ticket_gold["thresholds"],
            "checks": checks,
            "pass_all": all(checks.values()),
        }
        print("ticket metrics:", json.dumps(out["metrics"], ensure_ascii=False))
        print("ticket checks:", checks)

    if do_voc:
        print(f"Evaluating voc_entities n={len(voc_gold['cases'])} …")
        out = eval_voc(voc_gold["cases"], limit=args.limit)
        checks = _pass_voc(out["metrics"], voc_gold["thresholds"])
        voc_part = {
            **out,
            "thresholds": voc_gold["thresholds"],
            "checks": checks,
            "pass_all": all(checks.values()),
        }
        print("voc metrics:", json.dumps(out["metrics"], ensure_ascii=False))
        print("voc checks:", checks)

    report = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "overall_pass": ticket_part["pass_all"] and voc_part["pass_all"],
        "ticket": ticket_part,
        "voc": voc_part,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = REPORT_DIR / f"eval-{stamp}.json"
    md_path = REPORT_DIR / f"eval-{stamp}.md"
    latest_json = REPORT_DIR / "latest.json"
    latest_md = REPORT_DIR / "latest.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md = _md_report(report)
    md_path.write_text(md, encoding="utf-8")
    latest_json.write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_md.write_text(md, encoding="utf-8")

    print(f"report: {md_path}")
    print(f"overall: {'PASS' if report['overall_pass'] else 'FAIL'}")
    raise SystemExit(0 if report["overall_pass"] else 1)


if __name__ == "__main__":
    main()
