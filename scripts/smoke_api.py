"""模块五 API 冒烟（不强制调用 LLM）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from apps.api import app
from apps.catalog import DEPARTMENTS, FEATURES
from shared.store.store import default_store


def main() -> None:
    client = TestClient(app)

    r = client.get("/health")
    assert r.status_code == 200 and r.json()["ok"] is True

    r = client.get("/v1/meta")
    meta = r.json()
    assert r.status_code == 200
    assert meta.get("business_ui", "").startswith("/business")
    assert "ops_embed" in meta
    assert meta.get("control_loops") == ["retrieve", "act", "extract", "plan"]
    assert set(meta.get("agent_types_ready") or []) == {
        "retrieve",
        "act",
        "extract",
        "plan",
    }
    assert meta.get("agent_type_aliases", {}).get("rag") == "retrieve"
    assert meta.get("agent_type_aliases", {}).get("react") == "act"
    assert meta.get("agent_type_aliases", {}).get("extraction") == "extract"
    assert meta.get("agent_type_aliases", {}).get("planning") == "plan"
    assert meta.get("tool_classes") == ["read", "knowledge", "write_govern"]
    assert meta.get("unified_runs_api") == "/v1/runs"
    assert (meta.get("legacy_api_paths") or {}).get("plan") == "/v1/planning/runs"
    assert (meta.get("runs_api") or {}).get("unified") == "/v1/runs"
    assert (meta.get("embed") or {}).get("unified_runs_api") == "POST /v1/runs"
    assert (meta.get("embed") or {}).get("planning_api") == "POST /v1/planning/runs"

    r = client.get("/v1/departments")
    assert r.status_code == 200
    deps = r.json()["departments"]
    assert len(deps) == len(DEPARTMENTS)
    assert "roles" in deps[0] or deps[0].get("feature_count") is not None

    r = client.get("/v1/departments/service/roles")
    assert r.status_code == 200
    assert r.json()["count"] >= 1

    r = client.get("/v1/features")
    assert r.status_code == 200
    assert r.json()["count"] == len(FEATURES)

    r = client.get("/v1/features?department_id=service&role_id=agent")
    assert r.status_code == 200
    feats = r.json()["features"]
    assert any(f["feature_id"] == "F-SVC-001" for f in feats)

    r = client.get("/v1/features?demo_only=true")
    demos = r.json()["features"]
    assert all(f["demo_ready"] for f in demos)
    assert len(demos) >= 1

    r = client.get("/v1/agent-types")
    assert r.status_code == 200
    types = r.json()["agent_types"]
    assert len(types) == 4
    assert any(t["agent_type"] == "plan" and t["status"] == "ready" for t in types)
    assert any(t["agent_type"] == "act" and t["status"] == "ready" for t in types)
    assert any(t["agent_type"] == "retrieve" and t["status"] == "ready" for t in types)
    assert any(t["agent_type"] == "extract" and t["status"] == "ready" for t in types)
    # 历史别名可解析
    r = client.get("/v1/agent-types/rag")
    assert r.status_code == 200 and r.json()["agent_type"] == "retrieve"
    r = client.get("/v1/agent-types/react")
    assert r.status_code == 200 and r.json()["agent_type"] == "act"

    # 非 demo feature → 403
    planned = next(f for f in FEATURES if not f.get("demo_ready"))
    r = client.post(
        "/v1/react/runs",
        json={"feature_id": planned["feature_id"], "input": {"text": "x"}},
    )
    assert r.status_code == 403, r.text

    r = client.get("/v1/skills")
    assert r.status_code == 200 and r.json()["count"] >= 4
    skills = r.json()["skills"]
    assert all(s.get("control_loop") in {"retrieve", "act", "extract", "plan"} for s in skills)
    assert any(s["skill_id"] == "fill_ticket" and s["control_loop"] == "act" for s in skills)
    assert any(s["skill_id"] == "repair_kb" and s["control_loop"] == "retrieve" for s in skills)

    r = client.get("/v1/flows")
    assert r.status_code == 200 and r.json()["count"] >= 2
    flow = next(f for f in r.json()["flows"] if f["flow_id"] == "service_ticket_to_shared")
    assert all(n.get("kind") == "skill" for n in flow["nodes"])
    assert {n["control_loop"] for n in flow["nodes"]} == {"extract", "act"}
    assert all(n.get("skill_id") for n in flow["nodes"])

    r = client.get("/v1/capabilities")
    assert r.status_code == 200 and r.json()["count"] >= 1

    r = client.get("/v1/tools")
    assert r.status_code == 200
    tools_body = r.json()
    assert tools_body["count"] >= 40
    assert tools_body["tool_classes"] == ["read", "knowledge", "write_govern"]
    assert tools_body["counts"]["knowledge"] == 3
    r = client.get("/v1/tools?tool_class=knowledge")
    assert r.status_code == 200 and r.json()["count"] == 3
    r = client.get("/v1/tools?tool_class=write_govern")
    assert r.status_code == 200 and r.json()["count"] >= 5
    assert any(t["name"] == "write_ai_output" for t in r.json()["tools"])

    r = client.get("/business")
    assert r.status_code == 200 and "业务工作台" in r.text

    r = client.get("/ops/embed?agent_type=act")
    assert r.status_code == 200 and ("运维" in r.text or "Ops" in r.text)
    r = client.get("/ops/embed?agent_type=react")
    assert r.status_code == 200 and ("运维" in r.text or "Ops" in r.text)

    r = client.get("/ui", follow_redirects=False)
    assert r.status_code in (307, 302)
    loc = r.headers.get("location") or ""
    assert loc.startswith("/business")

    r = client.get("/static/business.js")
    assert r.status_code == 200 and "feature_id" in r.text

    r = client.get("/static/ops.js")
    assert r.status_code == 200 and ("agent_type" in r.text or "LOOPS" in r.text or "retrieve" in r.text)

    # B3：Plan 专用 API + 统一 /v1/runs（不依赖 LLM；无阻断标签时放行）
    default_store.clear_runtime()
    r = client.post(
        "/v1/planning/runs",
        json={
            "skill_id": "renewal_plan",
            "input": {"customer_id": "CUS-10057", "vin": "QS0F65B984410D7B6"},
            "run_id": "smoke-api-plan",
        },
    )
    assert r.status_code == 200, r.text
    plan_body = r.json()
    assert plan_body.get("control_loop") == "plan"
    assert plan_body.get("ok") is True
    assert "final_text" in plan_body
    assert isinstance(plan_body.get("extensions"), dict)
    assert (plan_body.get("extensions") or {}).get("stop_reason") in {"planned", "blocked"}
    assert meta.get("run_result_version")
    assert "final_text" in (meta.get("run_result") or {}).get("common", [])

    r = client.post(
        "/v1/runs",
        json={
            "control_loop": "plan",
            "skill_id": "renewal_plan",
            "input": {"customer_id": "CUS-10057", "vin": "QS0F65B984410D7B6"},
            "run_id": "smoke-api-unified-plan",
        },
    )
    assert r.status_code == 200, r.text
    uni = r.json()
    assert (uni.get("extensions") or {}).get("resolved_via") == "POST /v1/runs"
    assert uni.get("control_loop") == "plan"
    assert (uni.get("extensions") or {}).get("legacy_api_path") == "/v1/planning/runs"
    assert "gate" in uni
    print("OK api smoke")


if __name__ == "__main__":
    main()
