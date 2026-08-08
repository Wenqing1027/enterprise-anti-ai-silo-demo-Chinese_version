"""Skill ↔ 平台控制环归属（V2）。

每个现成 Skill 归属且只归属一个 control_loop：
  retrieve | act | extract | plan

机读台账：data/entities/skill_loop_map.json
运行时：peek / load_skill_public 会附带 control_loop。
"""

from __future__ import annotations

from typing import Any

from apps.loops import PLATFORM_LOOPS, canonicalize, to_legacy

# 已落地 Skill（目录存在）
SKILL_CONTROL_LOOPS: dict[str, str] = {
    # retrieve
    "repair_kb": "retrieve",
    "policy_kb": "retrieve",
    "hr_rules": "retrieve",
    # act
    "fill_ticket": "act",
    "crm_lookup": "act",
    "channel_ops": "act",
    "shared_write": "act",
    # extract
    "ticket_fields": "extract",
    "voc_entities": "extract",
    "voc_tagging": "extract",
    # plan
    "renewal_plan": "plan",
}

# 契约占位（尚无 skills/<id>/）
PLANNED_SKILL_CONTROL_LOOPS: dict[str, str] = {}

KIND_TO_LOOP: dict[str, str] = {
    "rag": "retrieve",
    "react": "act",
    "extraction": "extract",
    "planning": "plan",
    # 规范名自映射
    "retrieve": "retrieve",
    "act": "act",
    "extract": "extract",
    "plan": "plan",
}


def all_skill_loops() -> dict[str, str]:
    return {**SKILL_CONTROL_LOOPS, **PLANNED_SKILL_CONTROL_LOOPS}


def control_loop_for_skill(skill_id: str | None) -> str | None:
    if not skill_id:
        return None
    return all_skill_loops().get(str(skill_id).strip())


def control_loop_from_kind(agent_kind: str | None) -> str | None:
    if not agent_kind:
        return None
    return KIND_TO_LOOP.get(str(agent_kind).strip()) or canonicalize(agent_kind)


def resolve_skill_control_loop(
    *,
    skill_id: str | None = None,
    declared: str | None = None,
    agent_kind: str | None = None,
    agent_type: str | None = None,
) -> str | None:
    """优先级：显式声明 → skill 台账 → agent_kind/type 推断。"""
    if declared:
        return canonicalize(declared)
    from_map = control_loop_for_skill(skill_id)
    if from_map:
        return from_map
    return control_loop_from_kind(agent_kind or agent_type)


def ledger_snapshot() -> dict[str, Any]:
    by_loop: dict[str, list[str]] = {c: [] for c in PLATFORM_LOOPS}
    for sid, loop in sorted(SKILL_CONTROL_LOOPS.items()):
        by_loop[loop].append(sid)
    planned_by: dict[str, list[str]] = {c: [] for c in PLATFORM_LOOPS}
    for sid, loop in sorted(PLANNED_SKILL_CONTROL_LOOPS.items()):
        planned_by[loop].append(sid)
    return {
        "version": "v2",
        "description": "每个 Skill 归属一个平台控制环。运行时真相源 apps/skill_loops.py。",
        "control_loops": list(PLATFORM_LOOPS),
        "skills": dict(sorted(SKILL_CONTROL_LOOPS.items())),
        "planned_skills": dict(sorted(PLANNED_SKILL_CONTROL_LOOPS.items())),
        "by_loop": by_loop,
        "planned_by_loop": planned_by,
        "legacy_agent_type": {loop: to_legacy(loop) for loop in PLATFORM_LOOPS},
        "note": "Skill YAML 字段 control_loop 为规范名；RAG 仍保留 agent_type: rag 供 loader 识别。",
    }
