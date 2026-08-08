#!/usr/bin/env python3
"""1.6 地基冒烟（绕过 Agent）

链路：
  DataFetcher 读主数据
    → ToolRegistry.extract_ticket_fields / write_ai_output
    → SharedStore 落盘
    → read_ai_outputs / check_outreach_block（Story2 阻断）

不启动任何 agents/* 控制环。失败以非 0 退出。
"""

from __future__ import annotations

import json
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.datafetcher import DataFetcher  # noqa: E402
from shared.models import Customer, Renewal, Vehicle  # noqa: E402
from shared.store import SharedStore  # noqa: E402
from shared.tools import ToolContext, ToolRegistry  # noqa: E402


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class SmokeReport:
    checks: list[CheckResult] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append(CheckResult(name=name, ok=ok, detail=detail))

    @property
    def passed(self) -> bool:
        return all(c.ok for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "total": len(self.checks),
            "failed": sum(1 for c in self.checks if not c.ok),
            "checks": [
                {"name": c.name, "ok": c.ok, "detail": c.detail} for c in self.checks
            ],
        }


def _must(report: SmokeReport, name: str, cond: bool, detail: str = "") -> None:
    report.add(name, cond, detail if cond else (detail or "assertion failed"))
    if not cond:
        raise AssertionError(f"[FAIL] {name}: {detail}")


def run_story1(
    report: SmokeReport,
    *,
    fetcher: DataFetcher,
    registry: ToolRegistry,
    store: SharedStore,
    seed: dict[str, Any],
) -> dict[str, Any]:
    inp = seed["input"]
    expect = seed["expect_write_ai_output"]
    ctx = ToolContext(run_id="foundation-story1", skill_id="fill_ticket", agent_type=None)

    customer = fetcher.get_customer(inp["customer_id"])
    vehicle = fetcher.get_vehicle(inp["vin"])
    _must(report, "story1.fetcher.customer", isinstance(customer, Customer), inp["customer_id"])
    _must(report, "story1.fetcher.vehicle", isinstance(vehicle, Vehicle), inp["vin"])
    _must(
        report,
        "story1.fetcher.vehicle_owner_match",
        vehicle is not None and vehicle.customer_id == inp["customer_id"],
        f"vehicle.customer_id={getattr(vehicle, 'customer_id', None)}",
    )

    r_log = registry.call("log_step", {"step_name": "foundation.story1.start"}, context=ctx)
    _must(report, "story1.tool.log_step", r_log.ok, r_log.error or "")

    extracted = registry.call(
        "extract_ticket_fields",
        {
            "text": inp["text"],
            "customer_id": inp["customer_id"],
            "vin": inp["vin"],
            "channel": inp["channel"],
        },
        context=ctx,
    )
    _must(report, "story1.tool.extract_ticket_fields", extracted.ok, extracted.error or "")
    draft = extracted.data["ticket_draft"]
    _must(
        report,
        "story1.extract.tag_complaint",
        draft.get("tag_id") == "TAG-投诉未结",
        str(draft.get("tag_id")),
    )

    payload = {
        **draft,
        "ticket_id": seed.get("fixture_ticket_id"),
        "customer_id": inp["customer_id"],
        "vin": inp["vin"],
    }
    for key in expect["payload_keys"]:
        _must(report, f"story1.payload.has.{key}", key in payload and payload[key] is not None, str(payload.get(key)))

    written = registry.call(
        "write_ai_output",
        {
            "producer_skill": expect["producer_skill"],
            "consumer_allow": expect["consumer_allow"],
            "payload_schema": "ticket_draft_v1",
            "payload": payload,
        },
        context=ctx,
    )
    _must(report, "story1.tool.write_ai_output", written.ok, written.error or "")
    ai_output = written.data["ai_output"]
    ai_id = ai_output["ai_output_id"]
    _must(report, "story1.write.has_id", bool(ai_id), ai_id or "")

    # 直连 store 校验落盘（绕过 tool 再读一遍）
    persisted = store.get_ai_output(ai_id)
    _must(report, "story1.store.persisted", persisted is not None, ai_id)
    _must(
        report,
        "story1.store.producer",
        persisted is not None and persisted.producer_skill == "fill_ticket",
        getattr(persisted, "producer_skill", None) or "",
    )

    # 运行时文件存在
    runtime_file = store.ai_outputs_file
    _must(report, "story1.runtime_file.exists", runtime_file.exists(), str(runtime_file))

    return {"ai_output_id": ai_id, "payload": payload, "customer": customer, "vehicle": vehicle}


def run_story2(
    report: SmokeReport,
    *,
    fetcher: DataFetcher,
    registry: ToolRegistry,
    store: SharedStore,
    seed: dict[str, Any],
    story1_payload: dict[str, Any],
) -> dict[str, Any]:
    inp = seed["input"]
    expect = seed["expect"]
    ctx = ToolContext(run_id="foundation-story2", skill_id="renewal_plan", agent_type=None)

    renewal = fetcher.get_renewal(inp["customer_id"], inp["vin"])
    _must(report, "story2.fetcher.renewal", isinstance(renewal, Renewal), inp["customer_id"])

    # 跨 Skill 消费：renewal_plan 读 fill_ticket 产出
    read = registry.call(
        "read_ai_outputs",
        {
            "consumer_skill": "renewal_plan",
            "customer_id": inp["customer_id"],
            "vin": inp["vin"],
        },
        context=ctx,
    )
    _must(report, "story2.tool.read_ai_outputs", read.ok, read.error or "")
    _must(report, "story2.read.count>=1", read.data["count"] >= 1, str(read.data.get("count")))

    tags = registry.call(
        "read_shared_tags",
        {"customer_id": inp["customer_id"], "vin": inp["vin"]},
        context=ctx,
    )
    _must(report, "story2.tool.read_shared_tags", tags.ok, tags.error or "")
    tag_ids = [t.get("tag_id") for t in tags.data.get("tags", [])]
    _must(report, "story2.tags.has_complaint", "TAG-投诉未结" in tag_ids, str(tag_ids))

    block = registry.call(
        "check_outreach_block",
        {
            "customer_id": inp["customer_id"],
            "vin": inp["vin"],
            "consumer_skill": "renewal_plan",
        },
        context=ctx,
    )
    _must(report, "story2.tool.check_outreach_block", block.ok, block.error or "")
    _must(
        report,
        "story2.block.allow_outreach_false",
        block.data.get("allow_outreach") is False,
        str(block.data),
    )
    reason = block.data.get("block_reason") or ""
    _must(
        report,
        "story2.block.reason_contains",
        expect["block_reason_contains"] in reason or any(
            expect["block_reason_contains"] in t for t in block.data.get("blocking_tags", [])
        ),
        reason or str(block.data.get("blocking_tags")),
    )

    # 直连 store 辅助 API（与 tool 结果一致）
    blocked, found = store.has_blocking_tag(
        customer_id=inp["customer_id"],
        vin=inp["vin"],
        consumer_skill="renewal_plan",
    )
    _must(report, "story2.store.has_blocking_tag", blocked is True, str(found))

    scored = registry.call(
        "score_renewal",
        {"customer_id": inp["customer_id"], "vin": inp["vin"]},
        context=ctx,
    )
    _must(report, "story2.tool.score_renewal", scored.ok, scored.error or "")

    return {
        "allow_outreach": block.data.get("allow_outreach"),
        "blocking_tags": block.data.get("blocking_tags"),
        "renewal_score": scored.data.get("score"),
        "shared_tag_ids": tag_ids,
        "story1_tag": story1_payload.get("tag_id"),
    }


def run_foundation_extras(
    report: SmokeReport,
    *,
    fetcher: DataFetcher,
    registry: ToolRegistry,
) -> None:
    """额外地基检查：KB、能力目录、白名单、VIN 护栏。"""
    kb = registry.call(
        "search_kb",
        {"query": "续航低于标称", "domain": "repair", "top_k": 3},
        context=ToolContext(run_id="foundation-kb", skill_id="repair_kb"),
    )
    _must(report, "extra.search_kb", kb.ok and kb.data["count"] >= 1, kb.error or str(kb.data))

    caps = fetcher.list_capabilities()
    _must(report, "extra.capabilities>=6", len(caps) >= 6, str(len(caps)))
    fill = fetcher.get_capability("fill_ticket")
    _must(
        report,
        "extra.fill_ticket.allowlist",
        fill is not None and "write_ai_output" in (fill.allowed_tools or []),
        str(getattr(fill, "allowed_tools", None)),
    )

    # fill_ticket 不得调用 score_renewal
    denied = registry.call(
        "score_renewal",
        {"customer_id": "CUS-10001"},
        context=ToolContext(run_id="foundation-deny", skill_id="fill_ticket"),
    )
    _must(
        report,
        "extra.allowlist.deny_cross_skill",
        denied.ok is False and denied.error_code == "TOOL_NOT_ALLOWED",
        f"{denied.error_code}:{denied.error}",
    )

    bad_vin = registry.call(
        "get_vehicle",
        {"vin": "WVWZZZ1JZXW000001"},
        context=ToolContext(run_id="foundation-vin", skill_id="crm_lookup"),
    )
    _must(
        report,
        "extra.vin.synthetic_only",
        bad_vin.ok is False and bad_vin.error_code == "VIN_NOT_SYNTHETIC",
        f"{bad_vin.error_code}:{bad_vin.error}",
    )

    tool_count = len(registry.list_tools())
    _must(report, "extra.tool_count>=40", tool_count >= 40, str(tool_count))


def main() -> int:
    report = SmokeReport()
    seed1 = json.loads((ROOT / "data/seeds/story_1_fill_ticket.json").read_text(encoding="utf-8"))
    seed2 = json.loads((ROOT / "data/seeds/story_2_renewal_block.json").read_text(encoding="utf-8"))

    fetcher = DataFetcher()
    store = SharedStore(persist=True)
    registry = ToolRegistry(fetcher=fetcher, store=store, enforce_skill_allowlist=True)

    print("=" * 60)
    print("Qingshu Mobility · Foundation Smoke (no Agent)")
    print("=" * 60)

    try:
        store.clear_runtime()
        report.add("setup.clear_runtime", True, str(store.stats()))

        s1 = run_story1(report, fetcher=fetcher, registry=registry, store=store, seed=seed1)
        print(f"[Story1] write_ai_output -> {s1['ai_output_id']}")

        s2 = run_story2(
            report,
            fetcher=fetcher,
            registry=registry,
            store=store,
            seed=seed2,
            story1_payload=s1["payload"],
        )
        print(
            f"[Story2] allow_outreach={s2['allow_outreach']} "
            f"tags={s2['blocking_tags']}"
        )

        run_foundation_extras(report, fetcher=fetcher, registry=registry)

    except AssertionError as exc:
        report.add("aborted", False, str(exc))
        print(exc)
    except Exception as exc:  # noqa: BLE001
        report.add("unexpected_error", False, f"{type(exc).__name__}: {exc}")
        traceback.print_exc()

    out = report.to_dict()
    out["store_stats"] = store.stats()
    print("-" * 60)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("-" * 60)
    if out["passed"]:
        print("FOUNDATION STABLE ✓")
        return 0
    print("FOUNDATION UNSTABLE ✗")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
