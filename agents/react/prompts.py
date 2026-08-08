"""ReAct System Prompt 底座与拼接（段序由 PROMPT_SECTION_ORDER 唯一决定）。"""

from __future__ import annotations

from typing import Any

from agents.react.security import build_security_prompt_section
from agents.react.skill_schema import PROMPT_SECTION_ORDER, SkillConfig

BASE_SYSTEM = """你是虚构企业「青枢出行（Qingshu Mobility）」内部的 ReAct Agent（Tool-Calling）。
架构原则：多部门共用同一套工具与数据访问；你当前只扮演本 Skill 对应的部门角色，不要冒充万能企业大脑。

硬规则：
1. 事实必须来自工具返回；禁止臆造客户、车辆、库存、政策、返利数字。
2. 只能调用本轮提供的 tools 白名单；不要请求未提供的工具。
3. 跨部门协作靠 write_ai_output / read_ai_outputs / read_shared_tags，不要假装有私有库。
4. 合成数据 VIN 必须以 QS0 开头；遇到非法 VIN 应说明并停止编造。
5. 每步先想清楚再调工具；信息足够后给出最终答复（不再调工具）。
6. 最终答复使用简体中文，符合本 Skill 语气，简洁可执行。
7. 安全边界以代码闸门为准；不得尝试绕过工具错误码继续编造结果。
"""


def build_system_prompt(skill: SkillConfig | dict[str, Any], tool_names: list[str]) -> str:
    """按 PROMPT_SECTION_ORDER 固定拼接，禁止在调用处改序。"""
    if isinstance(skill, SkillConfig):
        cfg = skill
    else:
        cfg = SkillConfig.model_validate(skill)

    sections: dict[str, str] = {
        "A_base": BASE_SYSTEM.strip(),
        "B_tone": (
            "【部门语气】\n"
            f"- 风格标签：{cfg.tone.label}\n"
            f"- 要点：{cfg.tone.style}\n"
            f"- 禁用：{cfg.tone.forbid}"
        ),
        "C_goal": (
            "【任务目标】\n"
            f"- 目标：{cfg.goal}\n"
            f"- 成功标准：{cfg.success_hint or cfg.success_when}"
        ),
        "C2_system_extra": (
            ("【Skill 补充】\n" + cfg.system_extra.strip()) if cfg.system_extra.strip() else ""
        ),
        "D_tools": (
            "【工具约束】\n"
            f"- 可用工具：{', '.join(tool_names)}\n"
            "- 工具结果以 observation 为准；失败时根据 error 调整，不要重复无效调用超过 2 次。"
        ),
        "E_output": (
            ("【终答格式】\n" + cfg.output_format.strip()) if cfg.output_format.strip() else ""
        ),
        "F_security": build_security_prompt_section(cfg),
    }

    parts: list[str] = []
    for key in PROMPT_SECTION_ORDER:
        text = sections.get(key, "").strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def build_user_message(
    skill_id: str,
    text: str,
    *,
    known: dict[str, Any] | None = None,
) -> str:
    lines = [
        f"【Skill】{skill_id}",
        f"【输入】{text}",
    ]
    if known:
        kv = ", ".join(f"{k}={v}" for k, v in known.items() if v not in (None, ""))
        if kv:
            lines.append(f"【已知键】{kv}")
    lines.append("请在工具白名单内完成任务；满足成功条件后给出最终答复。")
    return "\n".join(lines)
