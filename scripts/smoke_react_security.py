"""模块四安全闸门冒烟（不强制调用 LLM）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.react.prompts import build_system_prompt
from agents.react.security import (
    precheck_tool_args,
    precheck_tool_calls_count,
    redact_pii_text,
    sanitize_observation,
    should_stop_for_outreach,
)
from agents.react.skill_loader import load_skill
from agents.react.skill_schema import PROMPT_SECTION_ORDER
from shared.tools.base import ToolContext
from shared.tools.registry import ToolRegistry


def main() -> None:
    assert "F_security" in PROMPT_SECTION_ORDER

    fill = load_skill("fill_ticket")
    prompt = build_system_prompt(fill, fill.allowed_tools)
    assert "【安全边界】" in prompt
    assert fill.security.redact_pii_in_observation is True

    # 单步 tool 过多
    too_many = precheck_tool_calls_count(fill, fill.security.max_tool_calls_per_step + 1)
    assert too_many.allow is False and too_many.code == "TOO_MANY_TOOL_CALLS"

    # kb 域限制（构造临时 security）
    from agents.react.skill_schema import SkillSecurity

    fill.security = SkillSecurity(kb_domains_allow=["repair"])
    denied = precheck_tool_args(fill, "search_kb", {"query": "续航", "domain": "hr"})
    assert denied.allow is False and denied.code == "KB_DOMAIN_DENIED"
    ok_kb = precheck_tool_args(fill, "search_kb", {"query": "续航", "domain": "repair"})
    assert ok_kb.allow is True and ok_kb.args["domain"] == "repair"

    # get_kb_document 绕域：工具层 + 预检双闸
    from shared.datafetcher import default_fetcher

    hr_docs = [
        d for d in default_fetcher._knowledge.list_docs("hr")  # noqa: SLF001 - smoke
    ]
    assert hr_docs, "need hr kb fixture"
    bypass = precheck_tool_args(
        fill,
        "get_kb_document",
        {"kb_doc_id": hr_docs[0].kb_doc_id},
        fetcher=default_fetcher,
    )
    assert bypass.allow is False and bypass.code == "KB_DOMAIN_DENIED"

    reg_kb = ToolRegistry()
    ctx_repair = ToolContext(
        run_id="sec-kb",
        skill_id="fill_ticket",
        kb_domains_allow=["repair"],
    )
    # 放宽 skill 白名单以测 kb 域闸（直接指定 allowed_tools）
    ctx_repair.allowed_tools = ["get_kb_document", "search_kb", "list_kb_domains"]
    blocked_doc = reg_kb.call(
        "get_kb_document",
        {"kb_doc_id": hr_docs[0].kb_doc_id},
        context=ctx_repair,
    )
    assert blocked_doc.ok is False and blocked_doc.error_code == "KB_DOMAIN_DENIED"

    cross = reg_kb.call(
        "search_kb",
        {"query": "制度", "domain": "hr"},
        context=ctx_repair,
    )
    assert cross.ok is False and cross.error_code == "KB_DOMAIN_DENIED"

    # observation 脱敏
    obs = sanitize_observation(
        {"ok": True, "data": {"phone": "13812345678", "note": "x"}},
        fill,
    )
    blob = str(obs)
    assert "13812345678" not in blob
    assert "1**********" in redact_pii_text("电话13812345678结束")

    # 触达阻断硬停
    from agents.react.skill_schema import SkillConfig, SkillTone

    renewal_like = SkillConfig(
        skill_id="renewal_probe",
        goal="probe",
        tone=SkillTone(label="t", style="s"),
        allowed_tools=["check_outreach_block"],
        security=SkillSecurity(block_on_outreach=True),
    )
    stop = should_stop_for_outreach(
        renewal_like,
        "check_outreach_block",
        {"blocked": True, "allow_outreach": False, "block_reason": "投诉未结"},
    )
    assert stop.allow is False and stop.code == "OUTREACH_BLOCKED"

    # 工具层：密钥禁写
    reg = ToolRegistry()
    secret = reg.call(
        "write_ai_output",
        {
            "producer_skill": "shared_write",
            "payload": {"token": "sk-abcdefghijklmnop"},
        },
        context=ToolContext(run_id="sec-smoke", skill_id="shared_write"),
    )
    assert secret.ok is False and secret.error_code == "SECRET_FORBIDDEN"

    # 白名单：fill_ticket 不可 score_renewal
    deny = reg.call(
        "score_renewal",
        {"customer_id": "CUS-10057"},
        context=ToolContext(run_id="sec-smoke", skill_id="fill_ticket"),
    )
    assert deny.ok is False and deny.error_code == "TOOL_NOT_ALLOWED"

    print("OK react security smoke")


if __name__ == "__main__":
    main()
