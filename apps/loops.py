"""平台控制环口径（V2）· 规范 ID 与历史别名。

规范名（对外主口径 / AGENT_TYPES / OpenAPI meta）：
  retrieve | act | extract | plan

历史名（Skill YAML、旧 API 路径、CLI、存量 FEATURES 兼容）：
  rag | react | extraction | planning

子模式（非平台主清单，不进 AGENT_TYPES）：
  rule_llm → Plan 闸门扩展
  vision   → Extract 感知扩展
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# 规范四环
# ---------------------------------------------------------------------------

PLATFORM_LOOPS: tuple[str, ...] = ("retrieve", "act", "extract", "plan")

LOOP_META: dict[str, dict[str, Any]] = {
    "retrieve": {
        "name": "Retrieve（检索）",
        "legacy": "rag",
        "status": "ready",
        "blurb": "平台控制环 Retrieve：retrieve → stuff → generate → cite。Skill：repair_kb / policy_kb / hr_rules。",
        "dir": "agents/rag/",
        "api_path": "/v1/rag/runs",
    },
    "act": {
        "name": "Act（行动）",
        "legacy": "react",
        "status": "ready",
        "blurb": "平台控制环 Act：think → act → observe。Skill：fill_ticket / crm_lookup / channel_ops 等。",
        "dir": "agents/react/",
        "api_path": "/v1/react/runs",
    },
    "extract": {
        "name": "Extract（抽取）",
        "legacy": "extraction",
        "status": "ready",
        "blurb": "平台控制环 Extract：schema → extract → validate。Skill：ticket_fields / voc_entities。",
        "dir": "agents/extraction/",
        "api_path": "/v1/extraction/runs",
    },
    "plan": {
        "name": "Plan（规划）",
        "legacy": "planning",
        "status": "ready",
        "blurb": "平台控制环 Plan：读共享 → 闸门/多步计划。Skill：renewal_plan（Story2）。API：POST /v1/planning/runs 或 POST /v1/runs + control_loop=plan。",
        "dir": "agents/planning/",
        "api_path": "/v1/planning/runs",
    },
}

# 历史名 → 规范名（单向主表）
AGENT_TYPE_ALIASES: dict[str, str] = {
    "rag": "retrieve",
    "react": "act",
    "extraction": "extract",
    "planning": "plan",
    # 规范名自映射，便于统一 resolve
    "retrieve": "retrieve",
    "act": "act",
    "extract": "extract",
    "plan": "plan",
}

# 规范名 → 历史名（API 路径 / Skill YAML 仍用）
LOOP_TO_LEGACY: dict[str, str] = {
    "retrieve": "rag",
    "act": "react",
    "extract": "extraction",
    "plan": "planning",
}

# 子模式：可解析，但不进平台主清单
EXTENSION_TYPES: dict[str, dict[str, Any]] = {
    "rule_llm": {
        "name": "扩展 · 规则闸门",
        "parent_loop": "plan",
        "status": "planned",
        "blurb": "归入 Plan 闸门子模式讲解；非平台主清单第六环。",
    },
    "vision": {
        "name": "扩展 · 视觉感知",
        "parent_loop": "extract",
        "status": "planned",
        "blurb": "归入 Extract 感知子模式；三期扩展位，非平台主清单第七环。",
    },
}

DISPLAY_NAMES: dict[str, str] = {
    "retrieve": "Retrieve",
    "act": "Act",
    "extract": "Extract",
    "plan": "Plan",
    "rag": "Retrieve",
    "react": "Act",
    "extraction": "Extract",
    "planning": "Plan",
    "rule_llm": "规则闸门",
    "vision": "视觉感知",
}


def canonicalize(agent_type: str | None) -> str | None:
    """任意历史名/规范名 → 规范 loop id；扩展类型原样返回；未知返回原值。"""
    if agent_type is None:
        return None
    key = str(agent_type).strip()
    if not key:
        return None
    if key in AGENT_TYPE_ALIASES:
        return AGENT_TYPE_ALIASES[key]
    if key in EXTENSION_TYPES:
        return key
    return key


def to_legacy(agent_type: str | None) -> str | None:
    """规范名 → 历史名；已是历史名则原样；扩展类型原样。"""
    if agent_type is None:
        return None
    key = str(agent_type).strip()
    canon = canonicalize(key)
    if canon in LOOP_TO_LEGACY:
        return LOOP_TO_LEGACY[canon]
    return key


def is_platform_loop(agent_type: str | None) -> bool:
    return canonicalize(agent_type) in PLATFORM_LOOPS


def same_loop(a: str | None, b: str | None) -> bool:
    """两侧任一用历史名或规范名，按环等价比较。"""
    ca, cb = canonicalize(a), canonicalize(b)
    if ca is None or cb is None:
        return False
    return ca == cb


def display_name(agent_type: str | None) -> str:
    if not agent_type:
        return ""
    return DISPLAY_NAMES.get(agent_type, DISPLAY_NAMES.get(canonicalize(agent_type) or "", agent_type))


def aliases_for(loop_id: str) -> list[str]:
    """某规范环的历史别名列表（不含自身）。"""
    legacy = LOOP_TO_LEGACY.get(loop_id)
    return [legacy] if legacy else []


def build_agent_types() -> list[dict[str, Any]]:
    """生成 catalog.AGENT_TYPES 主清单（仅四环）。"""
    out: list[dict[str, Any]] = []
    for loop_id in PLATFORM_LOOPS:
        meta = LOOP_META[loop_id]
        out.append(
            {
                "agent_type": loop_id,
                "loop_id": loop_id,
                "name": meta["name"],
                "status": meta["status"],
                "blurb": meta["blurb"],
                "legacy_alias": meta["legacy"],
                "aliases": aliases_for(loop_id),
                "manage_separately": True,
            }
        )
    return out


def meta_payload() -> dict[str, Any]:
    """供 OpenAPI /v1/meta 挂载的环口径块。"""
    ready = [lid for lid in PLATFORM_LOOPS if LOOP_META[lid]["status"] == "ready"]
    return {
        "control_loops": list(PLATFORM_LOOPS),
        "agent_types_ready": ready,
        "agent_type_aliases": {
            k: v for k, v in AGENT_TYPE_ALIASES.items() if k != v
        },
        "loop_to_legacy": dict(LOOP_TO_LEGACY),
        "legacy_api_paths": {lid: LOOP_META[lid]["api_path"] for lid in PLATFORM_LOOPS},
        "unified_runs_api": "/v1/runs",
        "extension_types": {
            k: {"parent_loop": v["parent_loop"], "status": v["status"]}
            for k, v in EXTENSION_TYPES.items()
        },
    }
