"""ReAct 模块四：Skill 级安全预检与 observation 脱敏。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from agents.react.skill_schema import SkillConfig, SkillSecurity

_PHONE_RE = re.compile(r"(?<!\*)(1[3-9]\d{9})(?!\*)")
_SECRET_RE = re.compile(
    r"(?i)(sk-[a-z0-9]{10,}|api[_-]?key\s*[:=]\s*\S+|deepseek_api_key\s*[:=]\s*\S+|bearer\s+[a-z0-9\-._]+)"
)


@dataclass
class SecurityVerdict:
    allow: bool
    code: str | None = None
    message: str | None = None
    args: dict[str, Any] | None = None


def precheck_tool_calls_count(skill: SkillConfig, n_calls: int) -> SecurityVerdict:
    sec = skill.security
    cap = sec.max_tool_calls_per_step
    if n_calls > cap:
        return SecurityVerdict(
            allow=False,
            code="TOO_MANY_TOOL_CALLS",
            message=f"单步 tool_calls={n_calls} 超过上限 {cap}",
        )
    return SecurityVerdict(allow=True)


def precheck_tool_args(
    skill: SkillConfig,
    tool_name: str,
    args: dict[str, Any],
    *,
    fetcher: Any | None = None,
) -> SecurityVerdict:
    """调用 Registry 前的 Skill 安全预检（不替代 Registry 白名单）。

    覆盖：search_kb 漏传/错传 domain；get_kb_document 用外域 doc_id 绕过。
    """
    sec = skill.security
    cleaned = dict(args)
    allow = list(sec.kb_domains_allow)

    if not allow:
        return SecurityVerdict(allow=True, args=cleaned)

    if tool_name == "search_kb":
        domain = cleaned.get("domain")
        if domain is None or str(domain).strip() == "":
            if len(allow) == 1:
                cleaned["domain"] = allow[0]
            else:
                return SecurityVerdict(
                    allow=False,
                    code="KB_DOMAIN_REQUIRED",
                    message=f"必须指定 domain，允许：{allow}",
                )
        else:
            d = str(domain).strip().lower()
            if d not in allow:
                return SecurityVerdict(
                    allow=False,
                    code="KB_DOMAIN_DENIED",
                    message=f"domain={d} 不在本 Skill 允许域 {allow}",
                )
            cleaned["domain"] = d
        return SecurityVerdict(allow=True, args=cleaned)

    if tool_name == "get_kb_document":
        doc_id = cleaned.get("kb_doc_id")
        if not doc_id:
            return SecurityVerdict(allow=True, args=cleaned)
        if fetcher is None:
            return SecurityVerdict(
                allow=False,
                code="KB_DOMAIN_CHECK_UNAVAILABLE",
                message="无法校验 kb 域：缺少 fetcher",
            )
        row = fetcher.get_kb_document(str(doc_id))
        if row is None:
            return SecurityVerdict(allow=True, args=cleaned)
        domain = getattr(row, "kb_domain", None)
        if domain is None and isinstance(row, dict):
            domain = row.get("kb_domain")
        d = str(domain or "").strip().lower()
        if d not in allow:
            return SecurityVerdict(
                allow=False,
                code="KB_DOMAIN_DENIED",
                message=f"文档域={d or '?'} 不在本 Skill 允许域 {allow}",
            )
        return SecurityVerdict(allow=True, args=cleaned)

    if tool_name == "list_kb_domains":
        # 无参；真正过滤在 tool handler + context.kb_domains_allow
        return SecurityVerdict(allow=True, args=cleaned)

    return SecurityVerdict(allow=True, args=cleaned)


def should_stop_for_outreach(skill: SkillConfig, tool_name: str, result_data: Any) -> SecurityVerdict:
    if not skill.security.block_on_outreach:
        return SecurityVerdict(allow=True)
    if tool_name != "check_outreach_block":
        return SecurityVerdict(allow=True)
    if not isinstance(result_data, dict):
        return SecurityVerdict(allow=True)
    if result_data.get("blocked") or result_data.get("allow_outreach") is False:
        reason = result_data.get("block_reason") or "存在触达阻断标签"
        return SecurityVerdict(
            allow=False,
            code="OUTREACH_BLOCKED",
            message=f"触达已阻断：{reason}",
        )
    return SecurityVerdict(allow=True)


def redact_pii_text(text: str) -> str:
    text = _PHONE_RE.sub("1**********", text)
    text = _SECRET_RE.sub("[REDACTED_SECRET]", text)
    return text


def sanitize_observation(
    observation: dict[str, Any],
    skill: SkillConfig,
) -> dict[str, Any]:
    if not skill.security.redact_pii_in_observation:
        return observation
    import json

    raw = json.dumps(observation, ensure_ascii=False, default=str)
    redacted = redact_pii_text(raw)
    if redacted == raw:
        return observation
    try:
        return json.loads(redacted)
    except json.JSONDecodeError:
        return {"ok": observation.get("ok"), "redacted": True, "content": redacted}


def build_security_prompt_section(skill: SkillConfig) -> str:
    sec: SkillSecurity = skill.security
    lines = [
        "【安全边界】",
        "- 禁止输出或回显 API Key / 密码 / 明文手机号。",
        "- 禁止编造未由工具返回的事实；合成 VIN 仅 QS0 前缀。",
        f"- 单步最多 {sec.max_tool_calls_per_step} 个 tool_calls。",
    ]
    if sec.kb_domains_allow:
        lines.append(f"- 知识库域仅允许：{', '.join(sec.kb_domains_allow)}。")
    if sec.block_on_outreach:
        lines.append("- 若 check_outreach_block 显示阻断，立即停止触达话术。")
    if sec.prompt_forbid_extra.strip():
        lines.append(f"- 额外禁止：{sec.prompt_forbid_extra.strip()}")
    if skill.tone.forbid.strip():
        lines.append(f"- 语气禁用（重申）：{skill.tone.forbid.strip()}")
    return "\n".join(lines)
