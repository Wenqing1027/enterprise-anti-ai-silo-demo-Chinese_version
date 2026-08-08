#!/usr/bin/env python3
"""C4 联调冒烟：Act → Extract → Retrieve → Plan；Plan 通后再强调 Story2 两步。

默认走 FastAPI TestClient（同进程可 clear_runtime）。
可选：BASE_URL=http://127.0.0.1:8000 打 live（无法跨进程清共享层时跳过「放行」断言）。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

for _k in (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "SOCKS_PROXY",
    "SOCKS5_PROXY",
    "socks_proxy",
    "socks5_proxy",
):
    os.environ.pop(_k, None)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

BASE_URL = (os.getenv("BASE_URL") or "").rstrip("/")


def _ok(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'OK' if cond else 'FAIL'}] {name}" + (f" · {detail}" if detail else ""))
    if not cond:
        raise SystemExit(1)


def _ext(body: dict) -> dict:
    return body.get("extensions") or {}


def _stop(body: dict) -> str:
    return str(_ext(body).get("stop_reason") or body.get("stop_reason") or "")


def _flags(body: dict) -> dict:
    return _ext(body).get("success_flags") or body.get("success_flags") or {}


class _Client:
    def __init__(self) -> None:
        self.live = bool(BASE_URL)
        if self.live:
            import urllib.request

            self._urllib = urllib.request
            self._base = BASE_URL
        else:
            from fastapi.testclient import TestClient
            from apps.api import app

            self._tc = TestClient(app)

    def post(self, path: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if self.live:
            import json as _json
            from urllib.error import HTTPError
            from urllib.request import Request

            req = Request(
                self._base + path,
                data=_json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with self._urllib.urlopen(req, timeout=180) as resp:  # type: ignore[attr-defined]
                    return resp.status, _json.loads(resp.read().decode("utf-8"))
            except HTTPError as e:
                raw = e.read().decode("utf-8", errors="replace")
                try:
                    data = _json.loads(raw)
                except Exception:
                    data = {"detail": raw}
                return e.code, data
        r = self._tc.post(path, json=body)
        try:
            data = r.json()
        except Exception:
            data = {"detail": r.text}
        return r.status_code, data

    def clear(self) -> None:
        if self.live:
            print("[SKIP] runtime.clear · live BASE_URL 无法跨进程清共享层")
            return
        from shared.store.store import default_store

        default_store.clear_runtime()
        print("[OK] runtime.cleared")


def _seed(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "data/seeds" / name).read_text(encoding="utf-8"))


def main() -> None:
    c = _Client()
    mode = f"live:{BASE_URL}" if c.live else "TestClient"
    print(f"======== C4 · 联调 Act → Extract → Retrieve → Plan（{mode}）========")

    seed_act = _seed("story_1_fill_ticket.json")
    seed_ext = _seed("story_1_ticket_fields.json")
    seed2 = _seed("story_2_renewal_block.json")
    cid = seed2["input"]["customer_id"]
    vin = seed2["input"]["vin"]

    # ---------- ① Act ----------
    print("--- ① Act · fill_ticket ---")
    c.clear()
    code, act = c.post(
        "/v1/react/runs",
        {
            "feature_id": "F-SVC-001",
            "skill_id": "fill_ticket",
            "input": seed_act["input"],
            "run_id": "c4-act",
            "options": {"return_steps": True},
        },
    )
    _ok("act.http", code == 200, f"{code} {str(act.get('detail') or '')[:160]}")
    _ok("act.ok", act.get("ok") is True, _stop(act))
    _ok("act.run_result", "final_text" in act and "extensions" in act)
    flags = _flags(act)
    _ok(
        "act.wrote_or_success",
        bool(flags.get("wrote_ai_output")) or _stop(act) in {"success", "wrote_ai_output"},
        str(flags or _stop(act)),
    )

    # ---------- ② Extract ----------
    print("--- ② Extract · ticket_fields ---")
    c.clear()
    code, ext = c.post(
        "/v1/extraction/runs",
        {
            "feature_id": "F-SVC-001-EXT",
            "skill_id": "ticket_fields",
            "input": seed_ext.get("input") or seed_ext,
            "run_id": "c4-extract",
            "options": {"return_steps": True},
        },
    )
    _ok("extract.http", code == 200, f"{code} {str(ext.get('detail') or '')[:160]}")
    _ok("extract.ok", ext.get("ok") is True, _stop(ext))
    payload = ext.get("payload") or {}
    tag = payload.get("tag_id")
    _ok("extract.tag", bool(tag), str(tag))
    _ok(
        "extract.ai_output",
        bool(ext.get("ai_output_ids") or _ext(ext).get("ai_output_id")),
        str(ext.get("ai_output_ids")),
    )

    # ---------- ③ Retrieve ----------
    print("--- ③ Retrieve · repair_kb ---")
    # 正交：不依赖共享标签；可不清
    code, rag = c.post(
        "/v1/rag/runs",
        {
            "feature_id": "F-SVC-002",
            "skill_id": "repair_kb",
            "input": {"query": "续航低于标称怎么排查？"},
            "run_id": "c4-retrieve",
            "options": {"return_steps": True},
        },
    )
    _ok("retrieve.http", code == 200, f"{code} {str(rag.get('detail') or '')[:160]}")
    _ok("retrieve.ok", rag.get("ok") is True, _stop(rag))
    _ok("retrieve.citations", isinstance(rag.get("citations"), list))
    answer = rag.get("final_text") or rag.get("final_answer") or ""
    _ok("retrieve.answer", bool(str(answer).strip()), str(answer)[:80])

    # ---------- ④ Plan（消费 ② 的共享标签；若 live 且无清层则可能已有标签）----------
    print("--- ④ Plan · renewal_plan（应阻断；依赖上游写出投诉标签）---")
    # 确保有投诉标签：TestClient 下 ② 已写；live 再补跑一次 extract 不 clear
    if c.live:
        c.post(
            "/v1/extraction/runs",
            {
                "feature_id": "F-SVC-001-EXT",
                "input": seed_ext.get("input") or seed_ext,
                "run_id": "c4-extract-for-plan",
            },
        )
    code, plan = c.post(
        "/v1/planning/runs",
        {
            "feature_id": "F-UO-017",
            "skill_id": "renewal_plan",
            "input": {"customer_id": cid, "vin": vin},
            "run_id": "c4-plan",
            "options": {"return_steps": True},
        },
    )
    _ok("plan.http", code == 200, f"{code} {str(plan.get('detail') or '')[:160]}")
    _ok("plan.ok", plan.get("ok") is True, _stop(plan))
    _ok("plan.control_loop", plan.get("control_loop") == "plan")
    _ok("plan.stop=blocked", _stop(plan) == "blocked", _stop(plan))
    gate = plan.get("gate") or {}
    _ok("plan.allow=false", gate.get("allow_outreach") is False, str(gate))
    _ok("plan.gate.tag_ids", bool(gate.get("tag_ids")), str(gate.get("tag_ids")))

    # ---------- ⑤ Story2 两步演示（强调：两次独立运行）----------
    print("--- ⑤ Story2 两步演示（①写出投诉标签 → ②另跑 Plan 阻断）---")
    c.clear()
    code, s1 = c.post(
        "/v1/react/runs",
        {
            "feature_id": "F-SVC-001",
            "input": seed_act["input"],
            "run_id": "c4-story2-step1",
        },
    )
    _ok("story2.step1.act.http", code == 200, str(code))
    _ok("story2.step1.act.ok", s1.get("ok") is True, _stop(s1))
    s1_flags = _flags(s1)
    _ok(
        "story2.step1.wrote",
        bool(s1_flags.get("wrote_ai_output")) or _stop(s1) in {"success", "wrote_ai_output"},
        str(s1_flags),
    )

    code, s2 = c.post(
        "/v1/planning/runs",
        {
            "feature_id": "F-UO-017",
            "input": {"customer_id": cid, "vin": vin},
            "run_id": "c4-story2-step2",
        },
    )
    _ok("story2.step2.plan.http", code == 200, str(code))
    _ok("story2.step2.blocked", _stop(s2) == "blocked", _stop(s2))
    _ok(
        "story2.independent_runs",
        (s1.get("run_id") or "c4-story2-step1") != (s2.get("run_id") or "c4-story2-step2"),
        f"{s1.get('run_id')} / {s2.get('run_id')}",
    )
    s2_gate = s2.get("gate") or {}
    _ok("story2.allow=false", s2_gate.get("allow_outreach") is False, str(s2_gate))

    print(
        json.dumps(
            {
                "verdict": "C4 PASS · Act→Extract→Retrieve→Plan 联调 OK；Story2 两步阻断成立",
                "mode": mode,
                "loops": {
                    "act": _stop(act),
                    "extract": {"stop": _stop(ext), "tag": tag},
                    "retrieve": _stop(rag),
                    "plan": _stop(plan),
                },
                "story2": {
                    "step1_run": s1.get("run_id"),
                    "step2_run": s2.get("run_id"),
                    "gate": s2_gate,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
