#!/usr/bin/env python3
"""B3 API 验收：POST /v1/planning/runs 与统一 POST /v1/runs（control_loop=plan）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from apps.api import app
from shared.store.store import default_store
from shared.tools.base import ToolContext
from shared.tools.registry import default_registry


def _ok(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'OK' if cond else 'FAIL'}] {name}" + (f" · {detail}" if detail else ""))
    if not cond:
        raise SystemExit(1)


def main() -> None:
    client = TestClient(app)
    seed2 = json.loads((ROOT / "data/seeds/story_2_renewal_block.json").read_text(encoding="utf-8"))
    cid = seed2["input"]["customer_id"]
    vin = seed2["input"]["vin"]

    r = client.get("/v1/meta")
    _ok("meta.200", r.status_code == 200)
    meta = r.json()
    _ok("meta.unified_runs_api", meta.get("unified_runs_api") == "/v1/runs", str(meta.get("unified_runs_api")))
    _ok(
        "meta.legacy_api_paths.plan",
        (meta.get("legacy_api_paths") or {}).get("plan") == "/v1/planning/runs",
    )
    _ok(
        "meta.embed.planning",
        (meta.get("embed") or {}).get("planning_api") == "POST /v1/planning/runs",
    )
    _ok(
        "meta.runs_api.unified",
        (meta.get("runs_api") or {}).get("unified") == "/v1/runs",
    )

    # 上游另次写投诉标签
    default_store.clear_runtime()
    written = default_registry.call(
        "write_ai_output",
        {
            "producer_skill": "fill_ticket",
            "consumer_allow": ["renewal_plan"],
            "payload_schema": "ticket_draft_v1",
            "payload": {
                "customer_id": cid,
                "vin": vin,
                "tag_id": "TAG-投诉未结",
                "sentiment": "neg",
                "ticket_id": "TK-B3-API",
                "desc_text": "B3 API 阻断",
            },
        },
        context=ToolContext(run_id="b3-up", skill_id="fill_ticket", agent_type="act"),
    )
    _ok("upstream.write", written.ok, written.error or "")

    # --- 专用路径 ---
    r = client.post(
        "/v1/planning/runs",
        json={
            "feature_id": "F-UO-017",
            "input": {"customer_id": cid, "vin": vin},
            "run_id": "b3-plan-dedicated",
            "options": {"return_steps": True},
        },
    )
    _ok("dedicated.200", r.status_code == 200, r.text[:200])
    body = r.json()
    ext = body.get("extensions") or {}
    _ok("dedicated.control_loop", body.get("control_loop") == "plan")
    _ok("dedicated.legacy", ext.get("agent_type_legacy") == "planning")
    _ok("dedicated.api_path", ext.get("api_path") == "/v1/planning/runs")
    _ok("dedicated.ok", body.get("ok") is True)
    _ok("dedicated.final_text", bool(body.get("final_text")))
    _ok(
        "dedicated.blocked",
        ext.get("stop_reason") == "blocked",
        str(ext.get("stop_reason")),
    )
    _ok(
        "dedicated.allow=false",
        (body.get("gate") or {}).get("allow_outreach") is False,
        str(body.get("gate")),
    )
    _ok("dedicated.feature", ext.get("feature_id") == "F-UO-017")
    _ok("dedicated.skill", body.get("skill_id") == "renewal_plan")

    r = client.get("/v1/planning/runs/b3-plan-dedicated")
    _ok("dedicated.get.200", r.status_code == 200)
    _ok("dedicated.get.loop", r.json().get("control_loop") == "plan")

    # 非 plan feature → 400
    r = client.post(
        "/v1/planning/runs",
        json={"feature_id": "F-SVC-001", "input": {"text": "x"}},
    )
    _ok("dedicated.reject_non_plan", r.status_code == 400, str(r.status_code))

    # --- 统一路径：显式 control_loop=plan ---
    r = client.post(
        "/v1/runs",
        json={
            "control_loop": "plan",
            "skill_id": "renewal_plan",
            "input": {"customer_id": cid, "vin": vin},
            "run_id": "b3-plan-unified",
        },
    )
    _ok("unified.plan.200", r.status_code == 200, r.text[:200])
    u = r.json()
    uext = u.get("extensions") or {}
    _ok("unified.plan.resolved_via", uext.get("resolved_via") == "POST /v1/runs")
    _ok("unified.plan.legacy_path", uext.get("legacy_api_path") == "/v1/planning/runs")
    _ok("unified.plan.blocked", uext.get("stop_reason") == "blocked")
    _ok("unified.plan.allow=false", (u.get("gate") or {}).get("allow_outreach") is False)

    # 统一路径：历史别名 agent_type=planning
    r = client.post(
        "/v1/runs",
        json={
            "agent_type": "planning",
            "feature_id": "F-UO-017",
            "input": {"customer_id": cid, "vin": vin},
            "run_id": "b3-plan-alias",
        },
    )
    _ok("unified.alias.200", r.status_code == 200, r.text[:200])
    _ok("unified.alias.loop", r.json().get("control_loop") == "plan")
    _ok(
        "unified.alias.blocked",
        (r.json().get("extensions") or {}).get("stop_reason") == "blocked",
    )

    # 统一路径：仅 feature_id 推断环
    r = client.post(
        "/v1/runs",
        json={
            "feature_id": "F-UO-017",
            "input": {"customer_id": cid, "vin": vin},
            "run_id": "b3-plan-infer",
        },
    )
    _ok("unified.infer.200", r.status_code == 200, r.text[:200])
    _ok("unified.infer.loop", r.json().get("control_loop") == "plan")

    # 统一路径：缺推断信息 → 400
    r = client.post("/v1/runs", json={"input": {"customer_id": cid}})
    _ok("unified.missing.400", r.status_code == 400, str(r.status_code))

    print(
        json.dumps(
            {
                "verdict": "B3 PASS · planning/runs + /v1/runs?control_loop=plan",
                "dedicated_gate": body.get("gate"),
                "unified_stop": (u.get("extensions") or {}).get("stop_reason"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
