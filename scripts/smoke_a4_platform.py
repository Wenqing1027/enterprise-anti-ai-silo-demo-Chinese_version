#!/usr/bin/env python3
"""A4 平台口径冒烟：4×3 + 一功能一 Skill；三环回归。

验收：
1. 平台 4 control_loops × 3 tool_classes
2. 每个现成 Skill 有且仅有一个 control_loop
3. Story1 两功能各自单跑（fill_ticket=act · ticket_fields=extract）
4. Retrieve 一条（repair_kb）
5. foundation store 阻断仍绿（Story2 闸门语义）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)


def _ok(name: str, cond: bool, detail: str = "") -> None:
    mark = "OK" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f" · {detail}" if detail else ""))
    if not cond:
        raise SystemExit(1)


def check_platform_4x3() -> dict:
    from apps.loops import PLATFORM_LOOPS
    from apps.skill_loops import SKILL_CONTROL_LOOPS, all_skill_loops
    from apps.skill_dispatch import list_skill_ids, load_skill_public
    from shared.tools.governance import TOOL_CLASSES
    from shared.tools.registry import default_registry
    from apps.catalog import list_flows, load_department_flows

    _ok("platform.loops=4", list(PLATFORM_LOOPS) == ["retrieve", "act", "extract", "plan"])
    _ok("platform.tool_classes=3", list(TOOL_CLASSES) == ["read", "knowledge", "write_govern"])
    summary = default_registry.tool_class_summary()
    _ok("tools.mapped", summary["total"] >= 40, str(summary["counts"]))

    disk = set(list_skill_ids())
    _ok("skills.disk==map", disk == set(SKILL_CONTROL_LOOPS), f"n={len(disk)}")
    for sid in sorted(disk):
        pub = load_skill_public(sid)
        _ok(
            f"skill.{sid}.one_loop",
            pub.get("control_loop") == SKILL_CONTROL_LOOPS[sid],
            pub.get("control_loop"),
        )

    load_department_flows.cache_clear()
    raw = load_department_flows()
    _ok("flows.version=v2", raw.get("version") == "v2")
    skill_nodes = 0
    for fl in list_flows():
        for n in fl.get("nodes") or []:
            if n.get("kind") == "skill":
                skill_nodes += 1
                _ok(
                    f"flow.{fl['flow_id']}.{n['node_id']}.skill",
                    bool(n.get("skill_id")) and n.get("control_loop") in PLATFORM_LOOPS,
                    f"{n.get('skill_id')}@{n.get('control_loop')}",
                )
    _ok("flows.skill_nodes>0", skill_nodes >= 2, str(skill_nodes))
    return {
        "loops": list(PLATFORM_LOOPS),
        "tool_classes": list(TOOL_CLASSES),
        "tool_counts": summary["counts"],
        "skills": dict(sorted(SKILL_CONTROL_LOOPS.items())),
        "planned": {k: v for k, v in all_skill_loops().items() if k not in SKILL_CONTROL_LOOPS},
        "skill_nodes": skill_nodes,
    }


def run_act_fill_ticket() -> dict:
    """Story1 功能一：Act · fill_ticket（独立单跑）。"""
    from agents.react.agent import run_react
    from apps.skill_dispatch import load_skill_public

    pub = load_skill_public("fill_ticket")
    _ok("act.control_loop", pub["control_loop"] == "act")
    seed = json.loads((ROOT / "data/seeds/story_1_fill_ticket.json").read_text(encoding="utf-8"))
    result = run_react("fill_ticket", seed.get("input") or seed, run_id="a4-act-fill-ticket")
    _ok("act.fill_ticket.ok", result.ok, f"stop={result.stop_reason}")
    data = result.to_dict()
    return {
        "control_loop": "act",
        "skill_id": "fill_ticket",
        "run_id": data.get("run_id"),
        "ok": result.ok,
        "stop_reason": data.get("stop_reason"),
        "steps": len(data.get("steps") or []),
    }


def run_extract_ticket_fields() -> dict:
    """Story1 功能二：Extract · ticket_fields（独立单跑，与 fill_ticket 并行可选）。"""
    from agents.extraction.agent import run_extraction
    from apps.skill_dispatch import load_skill_public

    pub = load_skill_public("ticket_fields")
    _ok("extract.control_loop", pub["control_loop"] == "extract")
    seed = json.loads((ROOT / "data/seeds/story_1_ticket_fields.json").read_text(encoding="utf-8"))
    result = run_extraction("ticket_fields", seed, run_id="a4-extract-ticket-fields")
    _ok("extract.ticket_fields.ok", result.ok, f"stop={result.stop_reason}")
    _ok("extract.payload.tag", bool(result.payload and result.payload.get("tag_id")))
    return {
        "control_loop": "extract",
        "skill_id": "ticket_fields",
        "run_id": result.run_id,
        "ok": result.ok,
        "stop_reason": result.stop_reason,
        "ai_output_id": result.ai_output_id,
        "tag_id": (result.payload or {}).get("tag_id"),
    }


def run_retrieve_rag() -> dict:
    """Retrieve 一条：repair_kb。"""
    from agents.rag.agent import run_rag
    from apps.skill_dispatch import load_skill_public

    pub = load_skill_public("repair_kb")
    _ok("retrieve.control_loop", pub["control_loop"] == "retrieve")
    result = run_rag(
        "repair_kb",
        {"query": "续航突然变短怎么排查？"},
        run_id="a4-retrieve-repair-kb",
    )
    _ok("retrieve.repair_kb.ok", result.ok, f"stop={result.stop_reason}")
    _ok("retrieve.has_answer", bool(result.final_answer))
    return {
        "control_loop": "retrieve",
        "skill_id": "repair_kb",
        "run_id": result.run_id,
        "ok": result.ok,
        "stop_reason": result.stop_reason,
        "citations": len(result.citations or []),
        "answer_preview": (result.final_answer or "")[:120],
    }


def run_foundation_block() -> dict:
    """foundation store 阻断仍绿（Write/Govern · Story2 语义）。"""
    import subprocess

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/smoke_foundation.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    _ok("foundation.exit0", proc.returncode == 0, out[-400:].replace("\n", " | "))
    _ok("foundation.stable_mark", "FOUNDATION STABLE" in out)
    return {"ok": proc.returncode == 0, "tail": out.strip().splitlines()[-3:]}


def main() -> None:
    print("======== A4 · 平台口径 + 三环回归 ========")
    platform = check_platform_4x3()
    print("--- Story1 功能单跑（各算一个功能）---")
    act = run_act_fill_ticket()
    extract = run_extract_ticket_fields()
    print("--- Retrieve 一条 ---")
    retrieve = run_retrieve_rag()
    print("--- foundation store 阻断 ---")
    foundation = run_foundation_block()

    report = {
        "verdict": "平台 4×3 + 一功能一 Skill；三环回归不挂",
        "platform": platform,
        "runs": {
            "act.fill_ticket": act,
            "extract.ticket_fields": extract,
            "retrieve.repair_kb": retrieve,
            "foundation_block": foundation,
        },
        "three_loops_green": all(
            [
                act["ok"],
                extract["ok"],
                retrieve["ok"],
                foundation["ok"],
            ]
        ),
    }
    print("======== REPORT ========")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    _ok("A4.three_loops_green", report["three_loops_green"])
    print("A4 PASS ✓ 平台4×3 + 一功能一Skill；三环回归不挂")


if __name__ == "__main__":
    main()
