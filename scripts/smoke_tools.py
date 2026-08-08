#!/usr/bin/env python3
"""1.5 ToolRegistry 冒烟：全量注册 + Skill 白名单 + Story1/2 工具链。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.tools import ToolContext, default_registry  # noqa: E402


def main() -> None:
    reg = default_registry
    tools = reg.list_tools()
    assert len(tools) >= 40, len(tools)
    names = {t["name"] for t in tools}
    for must in (
        "get_customer",
        "get_vehicle",
        "extract_ticket_fields",
        "write_ai_output",
        "read_ai_outputs",
        "check_outreach_block",
        "score_renewal",
        "search_kb",
        "list_capabilities",
        "log_step",
    ):
        assert must in names, must

    # V2 治理三类
    by_class = {t["name"]: t["tool_class"] for t in tools}
    assert by_class["get_customer"] == "read"
    assert by_class["search_kb"] == "knowledge"
    assert by_class["write_ai_output"] == "write_govern"
    assert by_class["check_outreach_block"] == "write_govern"
    assert by_class["list_capabilities"] == "write_govern"
    summary = reg.tool_class_summary()
    assert summary["counts"]["knowledge"] == 3
    assert summary["counts"]["write_govern"] >= 5
    assert set(summary["tool_classes"]) == {"read", "knowledge", "write_govern"}
    assert len(reg.list_tools(tool_class="knowledge")) == 3

    seed1 = json.loads((ROOT / "data/seeds/story_1_fill_ticket.json").read_text(encoding="utf-8"))
    seed2 = json.loads((ROOT / "data/seeds/story_2_renewal_block.json").read_text(encoding="utf-8"))
    inp = seed1["input"]

    # 清空运行时，保证可重复
    from shared.store import clear_runtime

    clear_runtime()

    ctx1 = ToolContext(run_id="smoke-tools-s1", skill_id="fill_ticket", agent_type="react")

    # 白名单：fill_ticket 不能调 score_renewal
    denied = reg.call("score_renewal", {"customer_id": inp["customer_id"]}, context=ctx1)
    assert denied.ok is False and denied.error_code == "TOOL_NOT_ALLOWED"

    # VIN 限制：拒绝非 QS0
    bad_vin = reg.call("get_vehicle", {"vin": "WVWZZZ1JZXW000001"}, context=ctx1)
    assert bad_vin.ok is False and bad_vin.error_code == "VIN_NOT_SYNTHETIC"

    r_log = reg.call("log_step", {"step_name": "fill_ticket.start"}, context=ctx1)
    assert r_log.ok

    extracted = reg.call(
        "extract_ticket_fields",
        {
            "text": inp["text"],
            "customer_id": inp["customer_id"],
            "vin": inp["vin"],
            "channel": inp["channel"],
        },
        context=ctx1,
    )
    assert extracted.ok, extracted.error
    draft = extracted.data["ticket_draft"]
    assert draft["tag_id"] == "TAG-投诉未结"

    written = reg.call(
        "write_ai_output",
        {
            "producer_skill": "fill_ticket",
            "consumer_allow": ["renewal_plan", "voc_tagging"],
            "payload_schema": "ticket_draft_v1",
            "payload": {
                **draft,
                "ticket_id": seed1["fixture_ticket_id"],
            },
        },
        context=ctx1,
    )
    assert written.ok, written.error
    ai_id = written.data["ai_output"]["ai_output_id"]

    # Story2
    ctx2 = ToolContext(run_id="smoke-tools-s2", skill_id="renewal_plan", agent_type="planning")
    scored = reg.call(
        "score_renewal",
        {"customer_id": seed2["input"]["customer_id"], "vin": seed2["input"]["vin"]},
        context=ctx2,
    )
    assert scored.ok, scored.error

    block = reg.call(
        "check_outreach_block",
        {
            "customer_id": seed2["input"]["customer_id"],
            "vin": seed2["input"]["vin"],
            "consumer_skill": "renewal_plan",
        },
        context=ctx2,
    )
    assert block.ok and block.data["allow_outreach"] is False
    assert any("投诉未结" in t for t in block.data["blocking_tags"])

    # 明文手机号禁止写入
    ctx_sw = ToolContext(run_id="smoke-pii", skill_id="shared_write")
    pii = reg.call(
        "write_ai_output",
        {
            "producer_skill": "shared_write",
            "payload": {"phone": "13812345678", "note": "bad"},
        },
        context=ctx_sw,
    )
    assert pii.ok is False and pii.error_code == "PII_FORBIDDEN"

    print("OK ToolRegistry smoke")
    print(
        json.dumps(
            {
                "tool_count": len(tools),
                "tool_classes": summary["counts"],
                "domains": sorted({t["category"] for t in tools}),
                "story1_ai_output_id": ai_id,
                "story2_allow_outreach": block.data["allow_outreach"],
                "story2_blocking_tags": block.data["blocking_tags"],
                "renewal_score": scored.data.get("score"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
