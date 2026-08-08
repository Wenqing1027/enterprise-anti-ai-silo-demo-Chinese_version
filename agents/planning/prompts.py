"""Plan 环 Prompt 占位（B1 闸门以规则+工具为主，可不调 LLM）。"""

from __future__ import annotations

from agents.planning.skill_schema import PlanningSkillConfig


def build_system_prompt(cfg: PlanningSkillConfig) -> str:
    return (
        f"你是青枢出行 Plan 控制环助手（Skill={cfg.skill_id}）。\n"
        f"语气：{cfg.tone.label} — {cfg.tone.style}\n"
        f"禁止：{cfg.tone.forbid or '无'}\n"
        "职责：读共享标签 → 触达闸门 → 给出阻断说明或短计划。"
        "不联跑上游 Agent；只读 L7 共享层。\n"
        f"{cfg.system_extra}"
    )
