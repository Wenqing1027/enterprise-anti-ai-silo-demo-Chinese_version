#!/usr/bin/env python3
"""B2 Story2 验收：renewal_plan 对齐 user_ops_renewal_gate / story2_outreach_gate。

路径：
1) 上游另次写投诉标签 → Plan 阻断
2) 无阻断标签 → Plan 放行并产出 channels / renew_pool_layer
3) 流节点：仅一处 skill renewal_plan（无重复二次跑节点）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.planning.agent import run_planning
from agents.planning.skill_loader import load_planning_skill
from apps.catalog import get_feature, get_flow
from apps.skill_dispatch import load_skill_public
from shared.store.store import default_store
from shared.tools.base import ToolContext
from shared.tools.registry import default_registry


def _ok(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'OK' if cond else 'FAIL'}] {name}" + (f" · {detail}" if detail else ""))
    if not cond:
        raise SystemExit(1)


def main() -> None:
    cfg = load_planning_skill("renewal_plan")
    pub = load_skill_public("renewal_plan")
    _ok("skill.control_loop=plan", cfg.control_loop == "plan")
    _ok(
        "skill.flow_ids",
        "user_ops_renewal_gate" in cfg.flow_ids and "story2_outreach_gate" in cfg.flow_ids,
        str(cfg.flow_ids),
    )
    _ok(
        "skill.consumes_from",
        set(cfg.consumes_from) >= {"fill_ticket", "ticket_fields", "voc_entities"},
        str(cfg.consumes_from),
    )
    for t in (
        "read_shared_tags",
        "check_outreach_block",
        "route_renewal_pool",
        "score_renewal",
        "get_renewal",
    ):
        _ok(f"skill.tool.{t}", t in cfg.allowed_tools)
    _ok("public.flow_ids", "user_ops_renewal_gate" in (pub.get("flow_ids") or []))

    feat = get_feature("F-UO-017")
    _ok("F-UO-017.demo_ready", bool(feat and feat.get("demo_ready")))
    _ok("F-UO-017.skill", feat.get("skill_id") == "renewal_plan")

    flow = get_flow("user_ops_renewal_gate")
    _ok("flow.user_ops_renewal_gate", bool(flow and flow.get("demo_ready")))
    skill_nodes = [
        n for n in (flow.get("nodes") or []) if n.get("kind") == "skill" and n.get("skill_id") == "renewal_plan"
    ]
    _ok("flow.single_renewal_plan_skill", len(skill_nodes) == 1, str([n.get("node_id") for n in skill_nodes]))
    gate = next(n for n in flow["nodes"] if n["node_id"] == "n_gate")
    _ok("flow.n_gate.skill", gate.get("skill_id") == "renewal_plan" and gate.get("control_loop") == "plan")
    plan_out = next((n for n in flow["nodes"] if n["node_id"] == "n_plan_out"), None)
    _ok("flow.n_plan_out.placeholder", bool(plan_out) and plan_out.get("kind") == "placeholder")
    _ok("flow.no_duplicate_n_plan_skill", not any(n.get("node_id") == "n_plan" for n in flow["nodes"]))

    story2 = get_flow("story2_outreach_gate")
    _ok("flow.story2_outreach_gate", bool(story2 and story2.get("demo_ready")))
    down = next(n for n in story2["nodes"] if n["node_id"] == "n_down")
    _ok("story2.n_down=renewal_plan", down.get("skill_id") == "renewal_plan")

    seed2 = json.loads((ROOT / "data/seeds/story_2_renewal_block.json").read_text(encoding="utf-8"))
    cid = seed2["input"]["customer_id"]
    vin = seed2["input"]["vin"]

    # --- 路径 A：上游写投诉 → 阻断 ---
    default_store.clear_runtime()
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
                "ticket_id": "TK-B2-STORY2",
                "desc_text": "Story2 投诉未结",
            },
        },
        context=ToolContext(run_id="b2-up", skill_id="fill_ticket", agent_type="act"),
    )
    _ok("A.upstream.write", written.ok, written.error or "")

    blocked = run_planning("renewal_plan", {"customer_id": cid, "vin": vin}, run_id="b2-block")
    _ok("A.plan.ok", blocked.ok, blocked.stop_reason)
    _ok("A.stop=blocked", blocked.stop_reason == "blocked")
    _ok("A.allow=false", blocked.gate.get("allow_outreach") is False, str(blocked.gate))
    expect_kw = seed2["expect"].get("block_reason_contains") or "投诉"
    reason = blocked.gate.get("reason") or ""
    _ok("A.reason", expect_kw in reason or "TAG-投诉未结" in str(blocked.gate), reason)
    _ok("A.plan.action=block", (blocked.plan or {}).get("action") == "block_outreach")

    # --- 路径 B：无阻断标签 → 放行短计划 ---
    default_store.clear_runtime()
    allowed = run_planning("renewal_plan", {"customer_id": cid, "vin": vin}, run_id="b2-allow")
    _ok("B.plan.ok", allowed.ok, allowed.stop_reason)
    _ok("B.stop=planned", allowed.stop_reason == "planned", allowed.stop_reason)
    _ok("B.allow=true", allowed.gate.get("allow_outreach") is True, str(allowed.gate))
    plan = allowed.plan or {}
    _ok("B.plan.action=allow", plan.get("action") == "allow_outreach")
    channels = plan.get("channels") or []
    _ok("B.plan.channels", len(channels) >= 1, str(channels))
    step_names = [s.get("name") for s in allowed.steps]
    _ok("B.steps.has_gate", "check_outreach_block" in step_names)
    _ok(
        "B.steps.has_route_or_score",
        "route_renewal_pool" in step_names or "score_renewal" in step_names,
        str(step_names),
    )

    print(
        json.dumps(
            {
                "verdict": "B2 PASS · renewal_plan 对齐 Story2 / user_ops_renewal_gate",
                "blocked_gate": blocked.gate,
                "allowed_plan": {
                    "channels": channels,
                    "renew_pool_layer": plan.get("renew_pool_layer"),
                    "intent_level": plan.get("intent_level"),
                },
                "flow_skill_nodes": [n.get("node_id") for n in skill_nodes],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
