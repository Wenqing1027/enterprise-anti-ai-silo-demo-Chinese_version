#!/usr/bin/env python3
"""阶段 D：统一 RunResult 契约冒烟（四环 API + /v1/runs）。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

for _k in (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
):
    os.environ.pop(_k, None)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

from fastapi.testclient import TestClient

from apps.api import app
from apps.run_result import RUN_RESULT_VERSION, assert_run_result_shape
from shared.store.store import default_store


def _ok(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'OK' if cond else 'FAIL'}] {name}" + (f" · {detail}" if detail else ""))
    if not cond:
        raise SystemExit(1)


def main() -> None:
    client = TestClient(app)
    default_store.clear_runtime()

    r = client.get("/v1/meta")
    meta = r.json()
    _ok("meta.run_result_version", meta.get("run_result_version") == RUN_RESULT_VERSION)
    _ok("meta.run_result.common", "final_text" in (meta.get("run_result") or {}).get("common", []))

    # Act（轻量：可能调 LLM）
    seed1 = json.loads((ROOT / "data/seeds/story_1_fill_ticket.json").read_text(encoding="utf-8"))
    r = client.post(
        "/v1/react/runs",
        json={"feature_id": "F-SVC-001", "input": seed1["input"], "run_id": "d-act"},
    )
    _ok("act.http", r.status_code == 200, r.text[:120])
    act = r.json()
    errs = assert_run_result_shape(act, expect_loop="act")
    _ok("act.shape", not errs, str(errs))
    _ok("act.final_text", bool(act.get("final_text") or act.get("final_answer")))
    _ok("act.ext.stop", "stop_reason" in (act.get("extensions") or {}))

    # Extract
    seed_e = json.loads(
        (ROOT / "data/seeds/story_1_ticket_fields.json").read_text(encoding="utf-8")
    )
    default_store.clear_runtime()
    r = client.post(
        "/v1/extraction/runs",
        json={
            "feature_id": "F-SVC-001-EXT",
            "input": seed_e.get("input") or seed_e,
            "run_id": "d-extract",
        },
    )
    _ok("extract.http", r.status_code == 200, r.text[:120])
    ext = r.json()
    errs = assert_run_result_shape(ext, expect_loop="extract")
    _ok("extract.shape", not errs, str(errs))
    _ok("extract.payload", isinstance(ext.get("payload"), dict))
    _ok("extract.ai_ids", bool(ext.get("ai_output_ids")))

    # Retrieve
    r = client.post(
        "/v1/rag/runs",
        json={
            "feature_id": "F-SVC-002",
            "input": {"query": "续航低于标称怎么排查？"},
            "run_id": "d-retrieve",
        },
    )
    _ok("retrieve.http", r.status_code == 200, r.text[:120])
    rag = r.json()
    errs = assert_run_result_shape(rag, expect_loop="retrieve")
    _ok("retrieve.shape", not errs, str(errs))
    _ok("retrieve.citations", isinstance(rag.get("citations"), list))
    _ok("retrieve.final_text", bool(rag.get("final_text")))

    # Plan（消费 extract 写出的标签）
    seed2 = json.loads((ROOT / "data/seeds/story_2_renewal_block.json").read_text(encoding="utf-8"))
    r = client.post(
        "/v1/planning/runs",
        json={
            "feature_id": "F-UO-017",
            "input": seed2["input"],
            "run_id": "d-plan",
        },
    )
    _ok("plan.http", r.status_code == 200, r.text[:120])
    plan = r.json()
    errs = assert_run_result_shape(plan, expect_loop="plan")
    _ok("plan.shape", not errs, str(errs))
    gate = plan.get("gate") or {}
    _ok("plan.gate.blocked", gate.get("blocked") is True, str(gate))
    _ok("plan.gate.reason", bool(gate.get("reason")), str(gate.get("reason")))
    _ok("plan.gate.tag_ids", isinstance(gate.get("tag_ids"), list) and bool(gate.get("tag_ids")))

    # 统一入口
    r = client.post(
        "/v1/runs",
        json={
            "control_loop": "plan",
            "skill_id": "renewal_plan",
            "input": seed2["input"],
            "run_id": "d-unified",
        },
    )
    _ok("unified.http", r.status_code == 200, r.text[:120])
    uni = r.json()
    errs = assert_run_result_shape(uni, expect_loop="plan")
    _ok("unified.shape", not errs, str(errs))
    _ok(
        "unified.ext.resolved_via",
        (uni.get("extensions") or {}).get("resolved_via") == "POST /v1/runs",
    )

    print(
        json.dumps(
            {
                "verdict": "D PASS · 统一 RunResult",
                "version": RUN_RESULT_VERSION,
                "sample_keys": sorted(plan.keys()),
                "gate": gate,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
