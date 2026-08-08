#!/usr/bin/env python3
"""B1 Plan 验收：上游独立写标签 → 另跑 renewal_plan → 必须阻断。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.planning.agent import run_planning
from apps.skill_dispatch import load_skill_public, peek_skill_kind
from apps.catalog import get_feature, list_agent_types
from shared.store.store import default_store
from shared.tools.base import ToolContext
from shared.tools.registry import default_registry


def _ok(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'OK' if cond else 'FAIL'}] {name}" + (f" · {detail}" if detail else ""))
    if not cond:
        raise SystemExit(1)


def main() -> None:
    pub = load_skill_public("renewal_plan")
    _ok("skill.control_loop=plan", pub["control_loop"] == "plan")
    _ok("skill.kind=planning", peek_skill_kind("renewal_plan") == "planning")

    feat = get_feature("F-UO-017")
    _ok("feature.demo_ready", bool(feat and feat.get("demo_ready")))
    _ok("feature.skill=renewal_plan", feat.get("skill_id") == "renewal_plan")
    _ok("feature.loop=plan", feat.get("agent_type") == "plan")

    types = list_agent_types()
    plan_row = next(t for t in types if t["agent_type"] == "plan")
    _ok("agent_types.plan.ready", plan_row["status"] == "ready")
    _ok("agent_types.plan.demo>=1", plan_row["demo_count"] >= 1, str(plan_row["demo_count"]))

    seed2 = json.loads((ROOT / "data/seeds/story_2_renewal_block.json").read_text(encoding="utf-8"))
    seed1 = json.loads((ROOT / "data/seeds/story_1_fill_ticket.json").read_text(encoding="utf-8"))
    cid = seed2["input"]["customer_id"]
    vin = seed2["input"]["vin"]

    # 上游另次独立运行（工具写共享，不调 Act Agent）
    default_store.clear_runtime()
    ctx_up = ToolContext(run_id="b1-upstream-write", skill_id="fill_ticket", agent_type="act")
    written = default_registry.call(
        "write_ai_output",
        {
            "producer_skill": "fill_ticket",
            "consumer_allow": ["renewal_plan", "voc_tagging"],
            "payload_schema": "ticket_draft_v1",
            "payload": {
                "customer_id": cid,
                "vin": vin,
                "tag_id": "TAG-投诉未结",
                "sentiment": "neg",
                "ticket_id": seed1.get("fixture_ticket_id") or "TK-B1-DEMO",
                "desc_text": "投诉未结演示",
            },
        },
        context=ctx_up,
    )
    _ok("upstream.write_ai_output", written.ok, written.error or "")
    aio = (written.data or {}).get("ai_output") or {}
    _ok("upstream.ai_output_id", bool(aio.get("ai_output_id")), str(aio.get("ai_output_id")))

    # Plan 另次独立运行
    result = run_planning(
        "renewal_plan",
        {"customer_id": cid, "vin": vin},
        run_id="b1-plan-renewal",
    )
    _ok("plan.ok", result.ok, result.stop_reason)
    _ok("plan.stop=blocked", result.stop_reason == "blocked", result.stop_reason)
    _ok("plan.gate.blocked", result.gate.get("blocked") is True, str(result.gate))
    _ok(
        "plan.gate.allow_outreach=false",
        result.gate.get("allow_outreach") is False,
        str(result.gate),
    )
    reason = result.gate.get("reason") or ""
    _ok("plan.reason.has_complaint", "投诉" in reason or "TAG-投诉未结" in str(result.gate), reason)
    _ok("plan.final_answer", "阻断" in result.final_answer, result.final_answer[:80])

    print(
        json.dumps(
            {
                "verdict": "B1 PASS · Plan 独立运行阻断触达",
                "upstream_ai_output_id": aio.get("ai_output_id"),
                "plan_run_id": result.run_id,
                "gate": result.gate,
                "plan": result.plan,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
